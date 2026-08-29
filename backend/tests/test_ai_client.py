import io
import pytest
from PIL import Image
from app.services.ai_client import MockAIClient, HttpxAIClient, AIClientError, AITimeoutError


def _make_png(size=(10, 10), color="white"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_mock_client_returns_fixed_png():
    client = MockAIClient(fixed_image_bytes=_make_png())
    result = await client.inpaint(b"img", b"mask", prompt=None)
    assert result[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_mock_client_with_prompt_returns_same_size():
    client = MockAIClient(fixed_image_bytes=_make_png())
    r1 = await client.inpaint(b"img", b"mask", prompt=None)
    r2 = await client.inpaint(b"img", b"mask", prompt="remove person")
    assert len(r1) == len(r2)


@pytest.mark.asyncio
async def test_http_client_raises_on_5xx(httpx_mock):
    httpx_mock.add_response(status_code=500, text="server error")
    client = HttpxAIClient(base_url="http://ai", timeout_seconds=5)
    with pytest.raises(AIClientError):
        await client.inpaint(b"img", b"mask", prompt=None)


@pytest.mark.asyncio
async def test_http_client_raises_timeout_on_slow(httpx_mock):
    import httpx
    httpx_mock.add_exception(httpx.TimeoutException("slow"))
    client = HttpxAIClient(base_url="http://ai", timeout_seconds=1)
    with pytest.raises(AITimeoutError):
        await client.inpaint(b"img", b"mask", prompt=None)


@pytest.mark.asyncio
async def test_http_client_returns_png_bytes(httpx_mock):
    png = _make_png()
    httpx_mock.add_response(status_code=200, content=png, headers={"content-type": "image/png"})
    client = HttpxAIClient(base_url="http://ai", timeout_seconds=5)
    result = await client.inpaint(b"img", b"mask", prompt=None)
    assert result == png
