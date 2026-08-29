from typing import Optional

from core.base_inpainter import BaseInpainter
from services.dispatcher import InpaintDispatcher


class FakeInpainter(BaseInpainter):
    def __init__(self, name: str):
        self.name = name
        self.calls = 0

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str] = None
    ) -> bytes:
        self.calls += 1
        return self.name.encode()


def make_dispatcher():
    qwen = FakeInpainter("qwen")
    lama = FakeInpainter("lama")
    return InpaintDispatcher(qwen, lama), qwen, lama


async def test_prompt_routes_to_qwen():
    dispatcher, qwen, lama = make_dispatcher()
    result = await dispatcher.inpaint(b"img", b"mask", "去掉背景里的路人")
    assert result == b"qwen"
    assert qwen.calls == 1
    assert lama.calls == 0


async def test_no_prompt_routes_to_lama():
    dispatcher, qwen, lama = make_dispatcher()
    result = await dispatcher.inpaint(b"img", b"mask", None)
    assert result == b"lama"
    assert qwen.calls == 0
    assert lama.calls == 1


async def test_blank_prompt_routes_to_lama():
    dispatcher, qwen, lama = make_dispatcher()
    result = await dispatcher.inpaint(b"img", b"mask", "   ")
    assert result == b"lama"
    assert qwen.calls == 0
    assert lama.calls == 1


def test_select_returns_correct_inpainter():
    dispatcher, qwen, lama = make_dispatcher()
    assert dispatcher.select("erase person") is qwen
    assert dispatcher.select("") is lama
    assert dispatcher.select(None) is lama
