import io
import time
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


def _png_bytes(size=(100, 100), color="white"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
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


def test_full_flow_submit_poll_download(client):
    img = _png_bytes()
    mask = _mask_bytes()

    resp = client.post(
        "/api/v1/inpaint",
        files={"image": ("i.png", img, "image/png"), "mask": ("m.png", mask, "image/png")},
    )
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    deadline = time.time() + 10
    while time.time() < deadline:
        s = client.get(f"/api/v1/tasks/{task_id}").json()
        if s["status"] == "success":
            break
        time.sleep(0.1)
    else:
        pytest.fail("task did not complete in 10s")

    result_url = s["result"]["result_url"]
    resp = client.get(result_url)
    assert resp.status_code == 200
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_cache_hit_returns_same_task_id_on_identical_input(client):
    img = _png_bytes()
    mask = _mask_bytes()

    r1 = client.post(
        "/api/v1/inpaint",
        files={"image": ("i.png", img, "image/png"), "mask": ("m.png", mask, "image/png")},
    )
    task_id_1 = r1.json()["task_id"]

    deadline = time.time() + 5
    while time.time() < deadline:
        s = client.get(f"/api/v1/tasks/{task_id_1}").json()
        if s["status"] == "success":
            break
        time.sleep(0.1)

    r2 = client.post(
        "/api/v1/inpaint",
        files={"image": ("i.png", img, "image/png"), "mask": ("m.png", mask, "image/png")},
    )
    assert r2.json()["task_id"] == task_id_1
    assert r2.json()["status"] == "success"
