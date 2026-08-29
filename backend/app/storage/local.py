from pathlib import Path
from typing import Iterator


class LocalStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, task_id: str, filename: str) -> Path:
        return self.base_dir / task_id / filename

    def save(self, task_id: str, filename: str, data: bytes) -> Path:
        path = self.path_for(task_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def read(self, task_id: str, filename: str) -> bytes:
        return self.path_for(task_id, filename).read_bytes()

    def exists(self, task_id: str, filename: str) -> bool:
        return self.path_for(task_id, filename).exists()

    def delete_task(self, task_id: str) -> None:
        task_dir = self.base_dir / task_id
        if task_dir.exists():
            for child in task_dir.iterdir():
                child.unlink()
            task_dir.rmdir()

    def iter_files(self) -> Iterator[Path]:
        for task_dir in sorted(self.base_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            for f in task_dir.iterdir():
                if f.is_file():
                    yield f
