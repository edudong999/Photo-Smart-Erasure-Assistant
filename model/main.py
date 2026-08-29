from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from config import MODEL_DIR, Settings, get_settings
from core.exceptions import (
    InpaintFailed,
    InvalidInput,
    ModelNotReady,
    ModelServiceError,
    UpstreamError,
)
from services.dispatcher import InpaintDispatcher
from services.lama_inpainter import LamaInpainter
from services.qwen_inpainter import QwenInpainter
from utils.image_io import bytes_to_image
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

_STATUS_MAP: dict[type, int] = {
    InvalidInput: 400,
    UpstreamError: 502,
    ModelNotReady: 503,
    InpaintFailed: 500,
}


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(title="AI Photo Eraser Model Service", version="1.0.0")

    app.state.qwen = QwenInpainter(
        api_key=settings.dashscope_api_key,
        model=settings.qwen_model,
        base_url=settings.dashscope_base_url,
        timeout_seconds=settings.qwen_timeout_seconds,
    )
    app.state.lama = LamaInpainter(
        onnx_path=settings.lama_onnx_path,
        mask_dilate_px=settings.mask_dilate_px,
    )
    app.state.dispatcher = InpaintDispatcher(app.state.qwen, app.state.lama)

    @app.exception_handler(ModelServiceError)
    async def model_service_error_handler(request: Request, exc: ModelServiceError):
        status = _STATUS_MAP.get(type(exc), 500)
        logger.error("%s: %s", type(exc).__name__, exc.message)
        return JSONResponse(status_code=status, content={"detail": exc.message})

    @app.post("/inpaint")
    async def inpaint(
        image: UploadFile = File(...),
        mask: UploadFile = File(...),
        prompt: Optional[str] = Form(None),
    ):
        image_bytes = await image.read()
        mask_bytes = await mask.read()

        img = bytes_to_image(image_bytes)
        msk = bytes_to_image(mask_bytes)
        if img.size != msk.size:
            raise InvalidInput(f"蒙版尺寸 {msk.size} 与原图尺寸 {img.size} 不一致")

        result_bytes = await app.state.dispatcher.inpaint(image_bytes, mask_bytes, prompt)
        return Response(content=result_bytes, media_type="image/png")

    @app.get("/health")
    async def health():
        local_ok = app.state.lama.is_ready()
        cloud_ok = app.state.qwen.is_ready()
        return {
            "status": "ok" if (local_ok or cloud_ok) else "degraded",
            "local_model_loaded": local_ok,
            "cloud_configured": cloud_ok,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port,reload=True,reload_dirs=[str(MODEL_DIR)])
