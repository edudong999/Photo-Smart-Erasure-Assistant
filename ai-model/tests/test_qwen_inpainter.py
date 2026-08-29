"""QwenInpainter 单元测试：不发起真实 DashScope / OSS / 下载请求

覆盖范围：
- is_ready
- API Key 缺失
- _call_dashscope：异常 / 非 200 / 响应里没有 image
- _download：httpx MockTransport，200 与 HTTP 错误
- inpaint 完整链路（SDK + 下载全部 mock）
"""
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from core.exceptions import ModelNotReady, UpstreamError
from services.qwen_inpainter import QwenInpainter


# ---------- 公共辅助 ----------

def _make_qwen(api_key: str = "sk-test", timeout: int = 10) -> QwenInpainter:
    return QwenInpainter(api_key=api_key, model="qwen-image-edit",
                         base_url="", timeout_seconds=timeout)


def _patch_dashscope_call(monkeypatch, *,
                          status_code: int = HTTPStatus.OK,
                          code: str = "",
                          message: str = "",
                          content=None,
                          raise_in_call: Exception | None = None):
    """替换 MultiModalConversation.call，返回受控的响应对象。

    _call_dashscope 内部 `import dashscope; from dashscope import MultiModalConversation`，
    所以补丁目标是真实 dashscope 模块的属性。
    """
    import dashscope
    rsp = SimpleNamespace(
        status_code=status_code,
        code=code,
        message=message,
        output=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content or []))]
        ),
    )
    call_mock = MagicMock()
    if raise_in_call is not None:
        call_mock.side_effect = raise_in_call
    else:
        call_mock.return_value = rsp

    fake_multi_modal = SimpleNamespace(call=call_mock)
    monkeypatch.setattr(dashscope, "MultiModalConversation", fake_multi_modal)
    monkeypatch.setattr(dashscope, "base_http_api_url", "")
    return call_mock, rsp


# ---------- is_ready ----------

def test_is_ready_true_when_api_key_set():
    qwen = _make_qwen(api_key="sk-test")
    assert qwen.is_ready() is True


def test_is_ready_false_when_api_key_empty():
    qwen = _make_qwen(api_key="")
    assert qwen.is_ready() is False


async def test_inpaint_raises_when_api_key_empty():
    qwen = _make_qwen(api_key="")
    with pytest.raises(ModelNotReady):
        await qwen.inpaint(b"img", b"mask", "擦除")


# ---------- _call_dashscope：错误分支 ----------

def test_call_dashscope_non_200_raises_upstream_error(monkeypatch):
    qwen = _make_qwen()
    _patch_dashscope_call(
        monkeypatch,
        status_code=HTTPStatus.BAD_REQUEST,
        code="InvalidParameter",
        message="bad image",
    )
    with pytest.raises(UpstreamError) as exc:
        qwen._call_dashscope(b"img", b"mask", "")
    assert "400" in str(exc.value)
    assert "InvalidParameter" in str(exc.value)


def test_call_dashscope_sdk_exception_raises_upstream_error(monkeypatch):
    """SDK 调用本身抛异常时，被捕获并包装为 UpstreamError。

    注意：生产代码 except 分支里调用了 to_data_uri，需要一并 mock，
    避免真实去 OSS 上传。
    """
    monkeypatch.setattr(
        "services.qwen_inpainter.to_data_uri",
        lambda b: "https://oss.example/uploaded.png",
    )
    qwen = _make_qwen()
    _patch_dashscope_call(
        monkeypatch, raise_in_call=RuntimeError("network unreachable")
    )
    with pytest.raises(UpstreamError) as exc:
        qwen._call_dashscope(b"img", b"mask", "")
    assert "DashScope 调用异常" in str(exc.value)
    assert "network unreachable" in str(exc.value)


def test_call_dashscope_response_without_image_raises(monkeypatch):
    qwen = _make_qwen()
    # content 里只有 text，没有 image 字段
    _patch_dashscope_call(monkeypatch, content=[{"text": "no image here"}])
    with pytest.raises(UpstreamError) as exc:
        qwen._call_dashscope(b"img", b"mask", "")
    assert "不包含结果图 URL" in str(exc.value)


def test_call_dashscope_response_structure_broken_raises(monkeypatch):
    """响应缺 output.choices 时抛 UpstreamError"""
    import dashscope
    qwen = _make_qwen()
    rsp = SimpleNamespace(status_code=HTTPStatus.OK, code="", message="",
                           output=SimpleNamespace(choices=[]))
    call_mock = MagicMock(return_value=rsp)
    monkeypatch.setattr(dashscope, "MultiModalConversation", SimpleNamespace(call=call_mock))
    monkeypatch.setattr(dashscope, "base_http_api_url", "")
    with pytest.raises(UpstreamError) as exc:
        qwen._call_dashscope(b"img", b"mask", "")
    assert "响应结构异常" in str(exc.value)


def test_call_dashscope_returns_image_url_on_success(monkeypatch):
    """正常路径：返回第一个 content 项里的 image URL"""
    qwen = _make_qwen()
    url = "https://dashscope-result-sz.oss-cn-shenzhen.aliyuncs.com/x.png?Expires=1"
    _patch_dashscope_call(monkeypatch, content=[{"image": url}])
    out = qwen._call_dashscope(b"img", b"mask", "擦除")
    assert out == url


# ---------- _download：使用 httpx MockTransport ----------

def _patch_async_client_with_transport(monkeypatch, handler):
    """让 httpx.AsyncClient 在 qwen_inpainter 模块里也走 MockTransport。"""
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


async def test_download_returns_bytes_on_200(monkeypatch):
    payload = b"\x89PNG\r\n\x1a\n" + b"x" * 1024

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    _patch_async_client_with_transport(monkeypatch, handler)
    qwen = _make_qwen()
    out = await qwen._download("https://example.com/img.png")
    assert out == payload


async def test_download_raises_upstream_error_on_http_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    _patch_async_client_with_transport(monkeypatch, handler)
    qwen = _make_qwen()
    with pytest.raises(UpstreamError) as exc:
        await qwen._download("https://example.com/img.png")
    assert "下载结果图失败" in str(exc.value)


# ---------- inpaint 完整链路 ----------

async def test_inpaint_full_path_returns_downloaded_bytes(monkeypatch):
    """完整链路：mock SDK 拿到 URL → mock 下载拿到字节 → 直接返回下载字节。"""
    qwen = _make_qwen()
    url = "https://dashscope-result-sz.oss-cn-shenzhen.aliyuncs.com/x.png?Expires=1"
    _patch_dashscope_call(monkeypatch, content=[{"image": url}])

    download_mock = AsyncMock(return_value=b"raw-png-bytes")
    monkeypatch.setattr(qwen, "_download", download_mock)

    out = await qwen.inpaint(b"img", b"mask", "擦除")

    assert out == b"raw-png-bytes"
    download_mock.assert_awaited_once_with(url)


async def test_inpaint_empty_prompt_still_calls_qwen(monkeypatch):
    """inpaint 接收空 prompt 时仍然走云端 Qwen 路径（路由由 dispatcher 决定）。"""
    qwen = _make_qwen()
    url = "https://example.com/out.png"
    _patch_dashscope_call(monkeypatch, content=[{"image": url}])
    monkeypatch.setattr(qwen, "_download", AsyncMock(return_value=b"raw"))

    out = await qwen.inpaint(b"img", b"mask", "")
    assert out == b"raw"


async def test_inpaint_propagates_upstream_error_from_dashscope(monkeypatch):
    qwen = _make_qwen()
    _patch_dashscope_call(monkeypatch,
                          status_code=HTTPStatus.UNAUTHORIZED,
                          code="InvalidApiKey",
                          message="key invalid")
    with pytest.raises(UpstreamError):
        await qwen.inpaint(b"img", b"mask", "擦除")
