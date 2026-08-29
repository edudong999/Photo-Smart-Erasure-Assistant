import pytest
from pathlib import Path
from app.storage.local import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(base_dir=tmp_path)


def test_save_and_read_bytes(storage):
    storage.save("t_abc", "image.png", b"fake-png")
    assert storage.read("t_abc", "image.png") == b"fake-png"


def test_save_creates_subdir_per_task(storage):
    storage.save("t_xyz", "image.png", b"x")
    assert (storage.base_dir / "t_xyz" / "image.png").exists()


def test_exists(storage):
    assert not storage.exists("t_abc", "image.png")
    storage.save("t_abc", "image.png", b"x")
    assert storage.exists("t_abc", "image.png")


def test_delete_removes_entire_task_dir(storage):
    storage.save("t_abc", "image.png", b"x")
    storage.save("t_abc", "mask.png", b"y")
    storage.delete_task("t_abc")
    assert not (storage.base_dir / "t_abc").exists()


def test_iter_files_returns_paths_older_than_threshold(storage):
    storage.save("t_old", "image.png", b"x")
    storage.save("t_new", "image.png", b"y")
    files = list(storage.iter_files())
    assert len(files) == 2


def test_path_for_task_file(storage):
    p = storage.path_for("t_abc", "result.png")
    assert p == storage.base_dir / "t_abc" / "result.png"
