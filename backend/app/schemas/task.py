from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatusEnum(str, Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class TaskResult(BaseModel):
    result_url: str
    expires_at: datetime
    width: int
    height: int
    bytes: int = Field(..., alias="bytes_")


class TaskError(BaseModel):
    code: str
    message: str


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatusEnum
    created_at: datetime
    result: Optional[dict] = None
    error: Optional[TaskError] = None
