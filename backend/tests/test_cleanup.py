import os
import time
import pytest
from app.core.cleanup import cleanup_once
from app.storage.local import LocalStorage
from app.services.cache import HashCache


def test_cleanup_once_removes_old_files(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    cache = HashCache()
    storage.save("t_old", "image.png", b"x")
    storage.save("t_old", "result.png", b"y")

    old_time = time.time() - 700
    os.utime(storage.path_for("t_old", "image.png"), (old_time, old_time))
    os.utime(storage.path_for("t_old", "result.png"), (old_time, old_time))

    removed = cleanup_once(storage, cache, ttl_seconds=600)
    assert removed == 2
    assert not storage.path_for("t_old", "image.png").exists()


def test_cleanup_once_keeps_recent_files(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    cache = HashCache()
    storage.save("t_new", "image.png", b"x")
    removed = cleanup_once(storage, cache, ttl_seconds=600)
    assert removed == 0
    assert storage.path_for("t_new", "image.png").exists()


def test_cleanup_once_evicts_cache_for_removed_task(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    cache = HashCache()
    cache.put("ih", "mh", "t_xyz")
    storage.save("t_xyz", "image.png", b"x")
    old_path = storage.path_for("t_xyz", "image.png")
    old_time = time.time() - 700
    os.utime(old_path, (old_time, old_time))

    cleanup_once(storage, cache, ttl_seconds=600)
    assert cache.get("ih", "mh") is None
