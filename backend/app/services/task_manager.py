import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from app.core.exceptions import TaskNotFound


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return f"t_{uuid.uuid4().hex[:12]}"


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, dict] = {}

    def create(
        self,
        image_hash: str,
        mask_hash: str,
        ttl_seconds: int = 600,
    ) -> str:
        task_id = _new_id()
        now = _now()
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.SUBMITTED,
            "image_hash": image_hash,
            "mask_hash": mask_hash,
            "created_at": now,
            "expires_at": now + timedelta(seconds=ttl_seconds),
            "result": None,
            "error": None,
        }
        return task_id

    def get(self, task_id: str) -> dict:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFound(f"task {task_id} 不存在或已清理")
        return task.copy()

    def set_processing(self, task_id: str) -> None:
        self._tasks[task_id]["status"] = TaskStatus.PROCESSING

    def set_success(
        self,
        task_id: str,
        result_url: str,
        width: int,
        height: int,
        bytes_: int,
    ) -> None:
        t = self._tasks[task_id]
        t["status"] = TaskStatus.SUCCESS
        t["result"] = {
            "result_url": result_url,
            "expires_at": t["expires_at"].isoformat(),
            "width": width,
            "height": height,
            "bytes": bytes_,
        }

    def set_failed(self, task_id: str, code: str, message: str) -> None:
        t = self._tasks[task_id]
        t["status"] = TaskStatus.FAILED
        t["error"] = {"code": code, "message": message}

    def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)
