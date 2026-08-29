from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.schemas.task import TaskStatusEnum, TaskResponse, TaskResult, TaskError
from app.schemas.inpaint import SubmitResponse


def test_task_status_enum_values():
    assert TaskStatusEnum.SUBMITTED.value == "submitted"
    assert TaskStatusEnum.PROCESSING.value == "processing"
    assert TaskStatusEnum.SUCCESS.value == "success"
    assert TaskStatusEnum.FAILED.value == "failed"


def test_task_result_serialization():
    r = TaskResult(
        result_url="/x.png",
        expires_at=datetime(2026, 8, 25, 10, 10, tzinfo=timezone.utc),
        width=100,
        height=100,
        bytes_=1234,
    )
    d = r.model_dump(by_alias=True)
    assert d["result_url"] == "/x.png"
    assert d["width"] == 100


def test_task_response_success():
    resp = TaskResponse(
        task_id="t_abc",
        status=TaskStatusEnum.SUCCESS,
        created_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        result={
            "result_url": "/x.png",
            "expires_at": "2026-08-25T10:10:00Z",
            "width": 100,
            "height": 100,
            "bytes": 1234,
        },
    )
    assert resp.status == TaskStatusEnum.SUCCESS


def test_task_response_failed_with_error():
    resp = TaskResponse(
        task_id="t_abc",
        status=TaskStatusEnum.FAILED,
        created_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        error=TaskError(code="AI_UPSTREAM_ERROR", message="boom"),
    )
    assert resp.error.code == "AI_UPSTREAM_ERROR"


def test_submit_response_basic():
    r = SubmitResponse(
        task_id="t_abc",
        status="submitted",
        created_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 8, 25, 10, 10, tzinfo=timezone.utc),
    )
    assert r.task_id == "t_abc"
