import io
import hashlib
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AIUpstreamError,
    AITimeout,
    InvalidImageFormat,
    PayloadTooLarge,
    ResultExpired,
    TaskNotFound,
    TaskNotReady,
)
from app.schemas.inpaint import SubmitResponse
from app.services.ai_client import DEFAULT_PROMPT
from app.services.align import align_mask, resize_image_if_oversize

router = APIRouter(tags=["inpaint"])


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_image_bytes(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise InvalidImageFormat("无法解析图像数据，可能已损坏或格式不支持")
    return img


def _validate_mask_bytes(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise InvalidImageFormat("无法解析蒙版数据")
    return img


async def _run_inpaint(
    task_id: str,
    image_bytes: bytes,
    aligned_mask_bytes: bytes,
    prompt: Optional[str],
):
    from app.services.ai_client import AIClientError, AITimeoutError

    storage = _state_ref["storage"]
    cache = _state_ref["cache"]
    task_manager = _state_ref["task_manager"]
    ai = _state_ref["ai_client"]

    effective_prompt = prompt if prompt is not None else DEFAULT_PROMPT

    try:
        task_manager.set_processing(task_id)
        result_bytes = await ai.inpaint(image_bytes, aligned_mask_bytes, effective_prompt)
    except AITimeoutError:
        task_manager.set_failed(task_id, code="AI_TIMEOUT", message="AI 服务超时")
        return
    except AIClientError as e:
        task_manager.set_failed(task_id, code="AI_UPSTREAM_ERROR", message=str(e))
        return

    storage.save(task_id, "result.png", result_bytes)

    result_img = Image.open(io.BytesIO(result_bytes))
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    mask_hash = hashlib.sha256(aligned_mask_bytes).hexdigest()

    cache.put(image_hash, mask_hash, task_id)

    task_manager.set_success(
        task_id,
        result_url=f"/api/v1/results/{task_id}.png",
        width=result_img.size[0],
        height=result_img.size[1],
        bytes_=len(result_bytes),
    )


_state_ref: dict = {}


@router.post("/inpaint", response_model=SubmitResponse, status_code=202)
async def submit_inpaint(
    request: Request,
    response: Response,
    background: BackgroundTasks,
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    settings: Settings = Depends(get_settings),
):
    image_bytes = await image.read()
    mask_bytes = await mask.read()

    if len(image_bytes) > settings.max_image_bytes:
        raise PayloadTooLarge(f"图像大小 {len(image_bytes)} 超过限制 {settings.max_image_bytes}")

    orig_img = _validate_image_bytes(image_bytes)
    mask_img = _validate_mask_bytes(mask_bytes)

    orig_img, img_was_resized = resize_image_if_oversize(orig_img, settings.max_image_dim)
    aligned_mask, mask_was_resized = align_mask(orig_img, mask_img)

    if img_was_resized:
        response.headers["X-Image-Resized"] = "true"
    if mask_was_resized:
        response.headers["X-Mask-Aligned"] = "true"

    aligned_buf = io.BytesIO()
    aligned_mask.save(aligned_buf, format="PNG")
    aligned_mask_bytes = aligned_buf.getvalue()

    image_hash = _hash_bytes(image_bytes)
    mask_hash = _hash_bytes(aligned_mask_bytes)

    state = request.app.state
    _state_ref["storage"] = state.storage
    _state_ref["cache"] = state.cache
    _state_ref["task_manager"] = state.task_manager
    _state_ref["ai_client"] = state.ai_client

    cached_task_id = state.cache.get(image_hash, mask_hash)
    if cached_task_id:
        try:
            cached_task = state.task_manager.get(cached_task_id)
            if cached_task["status"].value == "success":
                return SubmitResponse(
                    task_id=cached_task_id,
                    status="success",
                    created_at=cached_task["created_at"],
                    expires_at=cached_task["expires_at"],
                )
        except Exception:
            pass

    task_id = state.task_manager.create(
        image_hash=image_hash, mask_hash=mask_hash, ttl_seconds=settings.ttl_seconds
    )

    state.storage.save(task_id, "image.png", image_bytes)
    state.storage.save(task_id, "mask.png", aligned_mask_bytes)

    background.add_task(
        _run_inpaint,
        task_id=task_id,
        image_bytes=image_bytes,
        aligned_mask_bytes=aligned_mask_bytes,
        prompt=prompt,
    )

    task = state.task_manager.get(task_id)
    return SubmitResponse(
        task_id=task_id,
        status="submitted",
        created_at=task["created_at"],
        expires_at=task["expires_at"],
    )


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, request: Request):
    task_manager = request.app.state.task_manager
    try:
        task = task_manager.get(task_id)
    except Exception as e:
        from app.core.exceptions import TaskNotFound
        if isinstance(e, TaskNotFound):
            raise
        raise
    status = task["status"].value if hasattr(task["status"], "value") else task["status"]
    return {
        "task_id": task["task_id"],
        "status": status,
        "created_at": task["created_at"].isoformat(),
        "result": task["result"],
        "error": task["error"],
    }


@router.get("/results/{filename}")
async def download_result(filename: str, request: Request):
    if not filename.endswith(".png"):
        raise ResultExpired("文件名格式错误")
    task_id = filename[:-4]
    storage = request.app.state.storage
    task_manager = request.app.state.task_manager

    if not storage.exists(task_id, "result.png"):
        raise ResultExpired(f"task {task_id} 修复结果不存在或已清理")

    try:
        task = task_manager.get(task_id)
    except TaskNotFound:
        raise ResultExpired(f"task {task_id} 已被清理")

    status = task["status"].value if hasattr(task["status"], "value") else task["status"]
    if status != "success":
        raise TaskNotReady(f"task {task_id} 仍在 {status}")

    data = storage.read(task_id, "result.png")
    return Response(
        content=data,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{task_id}.png"',
        },
    )
