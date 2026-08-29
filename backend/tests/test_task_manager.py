import pytest
from app.services.task_manager import TaskManager, TaskStatus


@pytest.fixture
def mgr():
    return TaskManager()


def test_create_task_returns_id_and_submitted_status(mgr):
    task_id = mgr.create(image_hash="ih", mask_hash="mh")
    assert task_id.startswith("t_")
    task = mgr.get(task_id)
    assert task["status"] == TaskStatus.SUBMITTED


def test_get_nonexistent_task_raises(mgr):
    from app.core.exceptions import TaskNotFound
    with pytest.raises(TaskNotFound):
        mgr.get("t_nope")


def test_mark_processing_then_success(mgr):
    task_id = mgr.create(image_hash="ih", mask_hash="mh")
    mgr.set_processing(task_id)
    assert (mgr.get(task_id))["status"] == TaskStatus.PROCESSING
    mgr.set_success(task_id, result_url="/results/x.png", width=100, height=100, bytes_=1234)
    task = mgr.get(task_id)
    assert task["status"] == TaskStatus.SUCCESS
    assert task["result"]["result_url"] == "/results/x.png"


def test_mark_failed_with_error_code(mgr):
    task_id = mgr.create(image_hash="ih", mask_hash="mh")
    mgr.set_processing(task_id)
    mgr.set_failed(task_id, code="AI_UPSTREAM_ERROR", message="boom")
    task = mgr.get(task_id)
    assert task["status"] == TaskStatus.FAILED
    assert task["error"]["code"] == "AI_UPSTREAM_ERROR"


def test_hash_keys_stored_on_task(mgr):
    task_id = mgr.create(image_hash="img_sha", mask_hash="mask_sha")
    task = mgr.get(task_id)
    assert task["image_hash"] == "img_sha"
    assert task["mask_hash"] == "mask_sha"


def test_created_at_and_expires_at_set(mgr):
    task_id = mgr.create(image_hash="ih", mask_hash="mh", ttl_seconds=600)
    task = mgr.get(task_id)
    delta = (task["expires_at"] - task["created_at"]).total_seconds()
    assert delta == 600
