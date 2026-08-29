from typing import Optional


class BusinessError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str, request_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.request_id = request_id

    def to_envelope(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "request_id": self.request_id,
            }
        }


class InvalidImageFormat(BusinessError):
    code = "INVALID_IMAGE_FORMAT"
    http_status = 400


class InvalidMaskSize(BusinessError):
    code = "INVALID_MASK_SIZE"
    http_status = 400


class MaskEmpty(BusinessError):
    code = "MASK_EMPTY"
    http_status = 400


class PayloadTooLarge(BusinessError):
    code = "PAYLOAD_TOO_LARGE"
    http_status = 413


class TaskNotFound(BusinessError):
    code = "TASK_NOT_FOUND"
    http_status = 404


class ResultExpired(BusinessError):
    code = "RESULT_EXPIRED"
    http_status = 404


class TaskNotReady(BusinessError):
    code = "TASK_NOT_READY"
    http_status = 400


class AIUpstreamError(BusinessError):
    code = "AI_UPSTREAM_ERROR"
    http_status = 502


class AITimeout(BusinessError):
    code = "AI_TIMEOUT"
    http_status = 504
