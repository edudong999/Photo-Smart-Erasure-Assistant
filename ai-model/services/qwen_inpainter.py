import asyncio
from http import HTTPStatus
from typing import Optional

import httpx
from PIL import Image

from core.base_inpainter import BaseInpainter
from core.exceptions import ModelNotReady, UpstreamError
from prompts.templates import build_erase_prompt
from utils.image_io import bytes_to_image, to_data_uri
from utils.logger import get_logger

logger = get_logger(__name__)


class QwenInpainter(BaseInpainter):
    """云端修复器：DashScope wanx2.1-imageedit 局部重绘，有 prompt 时使用"""

    name = "qwen-cloud"

    def __init__(
        self,
        api_key: str,
        model: str = "wanx2.1-imageedit",
        base_url: str = "",
        timeout_seconds: int = 50,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout = timeout_seconds

    def is_ready(self) -> bool:
        return bool(self._api_key)

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str] = None
    ) -> bytes:
        if not self._api_key:
            raise ModelNotReady(f"未配置 DASHSCOPE_API_KEY，云端 Qwen 修复不可用{self._api_key}")

        result_url = await asyncio.to_thread(
            self._call_dashscope, image_bytes, mask_bytes, prompt or ""
        )
        print(result_url)
        result_bytes = await self._download(result_url)
        return result_bytes

    def _call_dashscope(self, image_bytes: bytes, mask_bytes: bytes, prompt: str) -> str:
        import dashscope
        from dashscope import MultiModalConversation

        if self._base_url:
            dashscope.base_http_api_url = self._base_url

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": to_data_uri(image_bytes)},
                        {"image": to_data_uri(mask_bytes)},
                        {"text": build_erase_prompt(prompt)},
                    ],
                }
            ]
            rsp = MultiModalConversation.call(
                api_key=self._api_key,
                model=self._model,
                messages=messages,      
            )
        except Exception as e:
            print(to_data_uri(image_bytes))
            raise UpstreamError(f"DashScope 调用异常: {e}")

        if rsp.status_code != HTTPStatus.OK:
            raise UpstreamError(
                f"DashScope 返回 {rsp.status_code}, code={rsp.code}, message={rsp.message}"
            )
        try:
            content_list = rsp.output.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as e:
            raise UpstreamError(f"DashScope 响应结构异常: {e}")

        for item in content_list:
            if isinstance(item, dict) and item.get("image"):
                return item["image"]

        raise UpstreamError("DashScope 响应中不包含结果图 URL")

    async def _download(self, url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except httpx.HTTPError as e:
            raise UpstreamError(f"下载结果图失败: {e}")
        return resp.content
