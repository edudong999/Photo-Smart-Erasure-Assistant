class ModelServiceError(Exception):
    """model 服务基础异常"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidInput(ModelServiceError):
    """输入图像/蒙版无效 -> HTTP 400"""


class ModelNotReady(ModelServiceError):
    """模型未就绪（权重缺失 / 未配置 API Key）-> HTTP 503"""


class UpstreamError(ModelServiceError):
    """云端上游调用失败 -> HTTP 502"""


class InpaintFailed(ModelServiceError):
    """推理过程失败 -> HTTP 500"""
