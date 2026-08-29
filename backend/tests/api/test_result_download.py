import io
import time
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


def _png_bytes(size=(100, 100)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
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


def test_download_result_returns_png(client):
    submit = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("i.png", _png_bytes(), "image/png"),
            "mask": ("m.png", _mask_bytes(), "image/png"),
        },
    )
    task_id = submit.json()["task_id"]

    deadline = time.time() + 10
    while time.time() < deadline:
        s = client.get(f"/api/v1/tasks/{task_id}").json()["status"]
        if s == "success":
            break
        time.sleep(0.1)
    else:
        pytest.fail("task did not reach success")

    resp = client.get(f"/api/v1/results/{task_id}.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_download_nonexistent_returns_404(client):
    resp = client.get("/api/v1/results/t_nope.png")
    assert resp.status_code == 404
