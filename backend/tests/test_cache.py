import pytest
from app.services.cache import HashCache


@pytest.fixture
def cache():
    return HashCache()


def test_cache_miss_returns_none(cache):
    assert cache.get("imghash", "maskhash") is None


def test_cache_put_and_get(cache):
    cache.put("imghash", "maskhash", "t_abc")
    assert cache.get("imghash", "maskhash") == "t_abc"


def test_cache_key_format(cache):
    cache.put("aaa", "bbb", "t_1")
    assert cache._data == {("aaa", "bbb"): "t_1"}


def test_cache_evict_by_task_id_removes_all_entries_with_that_task(cache):
    cache.put("a", "b", "t_1")
    cache.put("c", "d", "t_1")
    cache.put("e", "f", "t_2")
    cache.evict_by_task("t_1")
    assert cache.get("a", "b") is None
    assert cache.get("c", "d") is None
    assert cache.get("e", "f") == "t_2"


def test_cache_size(cache):
    cache.put("a", "b", "t_1")
    cache.put("c", "d", "t_2")
    assert cache.size() == 2
