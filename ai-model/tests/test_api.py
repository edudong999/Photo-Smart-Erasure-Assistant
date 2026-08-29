from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from core.base_inpainter import BaseInpainter
from core.exceptions import UpstreamError
from main import create_app
from services.dispatcher import InpaintDispatcher
from services.lama_inpainter import LamaInpainter
from tests.conftest import make_png


class FakeInpainter(BaseInpainter):
    def __init__(self, name: str, result: bytes = b"", error: Exception = None):
        self.name = name
        self._result = result or make_png(size=(64, 48))
        self._error = error

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str] = None
    ) -> bytes:
        if self._error:
            raise self._error
        return self._result


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


def _files(image_png, mask_png):
    return {
        "image": ("image.png", image_png, "image/png"),
        "mask": ("mask.png", mask_png, "image/png"),
    }


def test_inpaint_without_prompt_returns_png(app, client, image_png, mask_png):
    app.state.dispatcher = InpaintDispatcher(
        FakeInpainter("qwen"), FakeInpainter("lama", result=b"lama-png")
    )
    resp = client.post("/inpaint", files=_files(image_png, mask_png))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == b"lama-png"


def test_inpaint_with_prompt_routes_to_qwen(app, client, image_png, mask_png):
    app.state.dispatcher = InpaintDispatcher(
        FakeInpainter("qwen", result=b"qwen-png"), FakeInpainter("lama")
    )
    resp = client.post(
        "/inpaint", files=_files(image_png, mask_png), data={"prompt": "去掉水印"}
    )
    assert resp.status_code == 200
    assert resp.content == b"qwen-png"


def test_invalid_image_returns_400(client, mask_png):
    resp = client.post("/inpaint", files=_files(b"not-an-image", mask_png))
    assert resp.status_code == 400


def test_size_mismatch_returns_400(client, image_png):
    small_mask = make_png(size=(10, 10), mode="L")
    resp = client.post("/inpaint", files=_files(image_png, small_mask))
    assert resp.status_code == 400
    assert "不一致" in resp.json()["detail"]


def test_upstream_error_returns_502(app, client, image_png, mask_png):
    app.state.dispatcher = InpaintDispatcher(
        FakeInpainter("qwen", error=UpstreamError("云端失败")), FakeInpainter("lama")
    )
    resp = client.post(
        "/inpaint", files=_files(image_png, mask_png), data={"prompt": "去掉水印"}
    )
    assert resp.status_code == 502


def test_missing_weights_returns_503(app, client, image_png, mask_png):
    lama = LamaInpainter(onnx_path=Path("weights/__not_exist__.onnx"))
    app.state.dispatcher = InpaintDispatcher(FakeInpainter("qwen"), lama)
    resp = client.post("/inpaint", files=_files(image_png, mask_png))
    assert resp.status_code == 503


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "local_model_loaded" in body
    assert "cloud_configured" in body
