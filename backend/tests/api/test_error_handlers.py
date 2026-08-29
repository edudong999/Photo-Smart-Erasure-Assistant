import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("AI_CLIENT_MODE", "mock")
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_business_error_returns_envelope():
    from app.core.exceptions import TaskNotFound

    get_settings.cache_clear()
    test_app = create_app()
    router = APIRouter()

    @router.get("/_test_raise")
    def _raise():
        raise TaskNotFound("task t_xxx not found", request_id="req_test")

    test_app.include_router(router)
    c = TestClient(test_app, raise_server_exceptions=False)
    resp = c.get("/_test_raise")
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {
            "code": "TASK_NOT_FOUND",
            "message": "task t_xxx not found",
            "request_id": "req_test",
        }
    }
    assert "X-Request-Id" in resp.headers
    assert resp.headers["X-Request-Id"].startswith("req_")


def test_unknown_exception_returns_internal_error():
    get_settings.cache_clear()
    test_app = create_app()
    router = APIRouter()

    @router.get("/_test_crash")
    def _crash():
        raise RuntimeError("unexpected")

    test_app.include_router(router)
    c = TestClient(test_app, raise_server_exceptions=False)
    resp = c.get("/_test_crash")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_ERROR"


def test_request_id_header_on_every_response(client):
    resp = client.get("/api/v1/health")
    assert "X-Request-Id" in resp.headers


def test_openapi_schema_available(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/v1/health" in schema["paths"]
