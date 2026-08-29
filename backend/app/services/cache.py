from typing import Optional


class HashCache:
    def __init__(self):
        self._data: dict[tuple[str, str], str] = {}

    @staticmethod
    def make_key(image_hash: str, mask_hash: str) -> tuple[str, str]:
        return (image_hash, mask_hash)

    def get(self, image_hash: str, mask_hash: str) -> Optional[str]:
        return self._data.get(self.make_key(image_hash, mask_hash))

    def put(self, image_hash: str, mask_hash: str, task_id: str) -> None:
        self._data[self.make_key(image_hash, mask_hash)] = task_id

    def evict_by_task(self, task_id: str) -> int:
        to_remove = [k for k, v in self._data.items() if v == task_id]
        for k in to_remove:
            del self._data[k]
        return len(to_remove)

    def size(self) -> int:
        return len(self._data)
