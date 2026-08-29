import pytest
from app.core.config import Settings, get_settings


def test_settings_default_values(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    settings = Settings()
    assert settings.storage_dir == tmp_path
    assert settings.ttl_seconds == 600
    assert settings.max_image_bytes == 10 * 1024 * 1024
    assert settings.max_image_dim == 2048
    assert settings.ai_timeout_seconds == 60
    assert settings.ai_client_mode in ("mock", "http")


def test_settings_override_via_env(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("TTL_SECONDS", "120")
    monkeypatch.setenv("MAX_IMAGE_BYTES", "5242880")
    settings = Settings()
    assert settings.ttl_seconds == 120
    assert settings.max_image_bytes == 5242880


def test_get_settings_returns_singleton(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_get_settings_reloads_when_env_changes(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    s1 = get_settings()
    monkeypatch.setenv("TTL_SECONDS", "300")
    get_settings.cache_clear()
    s2 = get_settings()
    assert s2.ttl_seconds == 300
