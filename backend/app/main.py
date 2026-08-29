import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import health, inpaint
from app.core.cleanup import cleanup_loop
from app.core.config import get_settings
from app.core.exceptions import BusinessError
from app.services.ai_client import make_client
from app.services.cache import HashCache
from app.services.task_manager import TaskManager
from app.storage.local import LocalStorage


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        storage = LocalStorage(base_dir=settings.storage_dir)
        cache = HashCache()
        task_mgr = TaskManager()
        ai = make_client(
            mode=settings.ai_client_mode,
            base_url=settings.ai_base_url,
            timeout_seconds=settings.ai_timeout_seconds,
        )
        app.state.storage = storage
        app.state.cache = cache
        app.state.task_manager = task_mgr
        app.state.ai_client = ai

        cleanup_task = asyncio.create_task(
            cleanup_loop(storage, cache, settings.ttl_seconds, interval_seconds=60)
        )
        try:
            yield
        finally:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="Photo Smart Erasure Assistant",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        if exc.request_id is None:
            exc.request_id = getattr(request.state, "request_id", None)
        return JSONResponse(status_code=exc.http_status, content=exc.to_envelope())

    @app.exception_handler(Exception)
    async def fallback_handler(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误", "request_id": rid}},
        )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(inpaint.router, prefix="/api/v1")

    return app


app = create_app()
