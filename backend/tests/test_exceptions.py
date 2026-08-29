import pytest
from app.core.exceptions import (
    BusinessError,
    InvalidImageFormat,
    InvalidMaskSize,
    MaskEmpty,
    PayloadTooLarge,
    TaskNotFound,
    ResultExpired,
    TaskNotReady,
    AIUpstreamError,
    AITimeout,
)


def test_business_error_has_code_and_http_status():
    err = InvalidImageFormat("bad format")
    assert err.code == "INVALID_IMAGE_FORMAT"
    assert err.http_status == 400
    assert "bad format" in str(err)


@pytest.mark.parametrize("exc_cls,code,status", [
    (InvalidImageFormat, "INVALID_IMAGE_FORMAT", 400),
    (InvalidMaskSize, "INVALID_MASK_SIZE", 400),
    (MaskEmpty, "MASK_EMPTY", 400),
    (PayloadTooLarge, "PAYLOAD_TOO_LARGE", 413),
    (TaskNotFound, "TASK_NOT_FOUND", 404),
    (ResultExpired, "RESULT_EXPIRED", 404),
    (TaskNotReady, "TASK_NOT_READY", 400),
    (AIUpstreamError, "AI_UPSTREAM_ERROR", 502),
    (AITimeout, "AI_TIMEOUT", 504),
])
def test_each_exception_has_unique_code_and_status(exc_cls, code, status):
    err = exc_cls("msg")
    assert err.code == code
    assert err.http_status == status


def test_request_id_attached_to_error():
    err = TaskNotFound("not found", request_id="req_abc")
    assert err.request_id == "req_abc"
    assert err.to_envelope() == {
        "error": {
            "code": "TASK_NOT_FOUND",
            "message": "not found",
            "request_id": "req_abc",
        }
    }
