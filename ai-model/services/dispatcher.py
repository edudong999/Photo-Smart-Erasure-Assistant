from typing import Optional

from core.base_inpainter import BaseInpainter
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_PROMPT: str = "remove the masked region, blend naturally with the surrounding background"

class InpaintDispatcher:
    """路由核心：prompt 存在 -> 云端 Qwen；prompt 为空 -> 端侧 LaMa"""
    

    def __init__(self, qwen: BaseInpainter, lama: BaseInpainter):
        self._qwen = qwen
        self._lama = lama

    def select(self, prompt: Optional[str]) -> BaseInpainter:
        if prompt == DEFAULT_PROMPT:
           return self._lama
        return self._qwen

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str]
    ) -> bytes:
        inpainter = self.select(prompt)
        logger.info(
            "分发到 %s (has_prompt=%s)", inpainter.name, bool(not prompt==DEFAULT_PROMPT)
        )
        return await inpainter.inpaint(image_bytes, mask_bytes, prompt)
