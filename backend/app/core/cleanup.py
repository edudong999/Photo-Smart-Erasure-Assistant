import asyncio
import time

from app.services.cache import HashCache
from app.storage.local import LocalStorage


def cleanup_once(storage: LocalStorage, cache: HashCache, ttl_seconds: int) -> int:
    now = time.time()
    removed = 0
    affected_tasks: set[str] = set()
    for f in list(storage.iter_files()):
        if f.stat().st_mtime + ttl_seconds < now:
            task_id = f.parent.name
            affected_tasks.add(task_id)
            f.unlink()
            removed += 1
    for task_id in affected_tasks:
        task_dir = storage.base_dir / task_id
        if task_dir.exists() and not any(task_dir.iterdir()):
            task_dir.rmdir()
        cache.evict_by_task(task_id)
    return removed


async def cleanup_loop(storage: LocalStorage, cache: HashCache, ttl_seconds: int, interval_seconds: int = 60):
    while True:
        try:
            cleanup_once(storage, cache, ttl_seconds)
        except Exception as e:
            print(f"[cleanup] error: {e}")
        await asyncio.sleep(interval_seconds)
