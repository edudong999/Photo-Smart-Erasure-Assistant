import io
from typing import Optional, Protocol

import httpx
from PIL import Image

from app.core.exceptions import AIUpstreamError, AITimeout


DEFAULT_PROMPT = "remove the masked region, blend naturally with the surrounding background"


class AIClientError(Exception):
    pass


class AITimeoutError(Exception):
    pass


class AIClient(Protocol):
    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str]
    ) -> bytes: ...


class MockAIClient:
    def __init__(self, fixed_image_bytes: bytes):
        self._fixed = fixed_image_bytes

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str]
    ) -> bytes:
        return self._fixed


class HttpxAIClient:
    def __init__(self, base_url: str, timeout_seconds: int = 60):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str]
    ) -> bytes:
        files = {
            "image": ("image.png", image_bytes, "image/png"),
            "mask": ("mask.png", mask_bytes, "image/png"),
        }
        data = {"prompt": prompt} if prompt else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/inpaint", files=files, data=data
                )
        except httpx.TimeoutException as e:
            raise AITimeoutError(str(e))
        except httpx.HTTPError as e:
            raise AIClientError(str(e))

        if resp.status_code >= 500:
            raise AIClientError(f"AI upstream {resp.status_code}: {resp.text}")
        if resp.status_code >= 400:
            raise AIClientError(f"AI rejected {resp.status_code}: {resp.text}")

        return resp.content


def make_client(mode: str, base_url: str, timeout_seconds: int) -> AIClient:
    if mode == "mock":
        placeholder = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(placeholder, format="PNG")
        return MockAIClient(fixed_image_bytes=placeholder.getvalue())
    return HttpxAIClient(base_url=base_url, timeout_seconds=timeout_seconds)
