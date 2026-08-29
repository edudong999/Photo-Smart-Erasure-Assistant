import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


def _png_bytes(size=(100, 100), mode="RGB", color="white"):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


def _mask_bytes(size=(100, 100)):
    buf = io.BytesIO()
    Image.new("L", size, 255).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("AI_CLIENT_MODE", "mock")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_submit_returns_202_with_task_id(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(), "image/png"),
            "mask": ("mask.png", _mask_bytes(), "image/png"),
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"].startswith("t_")
    assert data["status"] == "submitted"


def test_submit_resizes_oversized_image(client):
    big = _png_bytes(size=(3000, 3000))
    resp = client.post(
        "/api/v1/inpaint",
        files={"image": ("orig.png", big, "image/png"), "mask": ("mask.png", _mask_bytes(), "image/png")},
    )
    assert resp.status_code == 202
    assert resp.headers.get("X-Image-Resized") == "true"


def test_submit_no_resize_header_when_within_limit(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(size=(1000, 1000)), "image/png"),
            "mask": ("mask.png", _mask_bytes(size=(1000, 1000)), "image/png"),
        },
    )
    assert resp.status_code == 202
    assert "X-Image-Resized" not in resp.headers


def test_submit_rejects_empty_mask(client):
    empty_mask_buf = io.BytesIO()
    Image.new("L", (100, 100), 0).save(empty_mask_buf, format="PNG")

    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(), "image/png"),
            "mask": ("mask.png", empty_mask_buf.getvalue(), "image/png"),
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MASK_EMPTY"


def test_submit_auto_resizes_mismatched_mask_with_header(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(size=(200, 100)), "image/png"),
            "mask": ("mask.png", _mask_bytes(size=(100, 200)), "image/png"),
        },
    )
    assert resp.status_code == 202
    assert resp.headers.get("X-Mask-Aligned") == "true"


def test_submit_no_mask_aligned_header_when_sizes_match(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(), "image/png"),
            "mask": ("mask.png", _mask_bytes(), "image/png"),
        },
    )
    assert resp.status_code == 202
    assert "X-Mask-Aligned" not in resp.headers


def test_submit_accepts_prompt_field(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(), "image/png"),
            "mask": ("mask.png", _mask_bytes(), "image/png"),
        },
        data={"prompt": "remove the person"},
    )
    assert resp.status_code == 202


def test_submit_works_without_prompt_field(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(), "image/png"),
            "mask": ("mask.png", _mask_bytes(), "image/png"),
        },
    )
    assert resp.status_code == 202