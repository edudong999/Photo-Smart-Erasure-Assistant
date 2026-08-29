from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MODEL_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=MODEL_DIR / ".env", case_sensitive=False, extra="ignore"
    )

    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"

    # 云端 Qwen（DashScope 多模态图像编辑）
    dashscope_api_key: str = ""
    dashscope_base_url: str = ""
    qwen_model: str = "qwen-image-edit"
    qwen_timeout_seconds: int = 300

    #OSS凭证
    oss_accessKeyId:str = ""
    oss_accessKeySecret: str = ""
    oss_endpoint:str
    oss_bucket_name:str

    # 端侧 LaMa（ONNX Runtime）
    lama_onnx_path: Path = MODEL_DIR / "weights" / "big-lama.onnx"
    mask_dilate_px: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()

