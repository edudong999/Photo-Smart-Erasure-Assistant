from abc import ABC, abstractmethod
from typing import Optional


class BaseInpainter(ABC):
    """修复器抽象基类：输入原图/蒙版 PNG 字节，返回结果 PNG 字节"""

    name: str = "base"

    @abstractmethod
    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str] = None
    ) -> bytes: ...

    def is_ready(self) -> bool:
        return True
