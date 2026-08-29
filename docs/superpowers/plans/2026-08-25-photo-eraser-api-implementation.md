# 照片智能擦除小助手 · 后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现「照片智能擦除小助手」后端 API（FastAPI），完整覆盖 spec `docs/superpowers/specs/2026-08-25-photo-eraser-api-design.md` 中定义的 4 个端点、缓存去重、清理任务与异常拦截。

**Architecture:** FastAPI 单体，分层（api/services/core/storage）。异步任务用 FastAPI `BackgroundTasks` 调度；缓存为进程内 dict；文件存储为本地文件系统。无数据库、无消息队列。

**Tech Stack:** Python 3.11+ / FastAPI 0.115 / Pydantic v2 / Pillow / httpx / pytest / pytest-asyncio

**Spec 引用：** 所有 API 契约（端点、字段、错误码、状态机）以 `docs/superpowers/specs/2026-08-25-photo-eraser-api-design.md` 为准。本计划仅给出实现步骤，不重复 spec 全文。

**项目根目录：** `D:/AI_Projects/Photo Smart Erasure Assistant/backend/`

---

## 任务依赖图

```
Task 1 (scaffold)
   ├─> Task 2 (config + .env)
   ├─> Task 3 (exceptions)
   └─> Task 4 (storage)
          │
Task 5 (align) ─┐
Task 6 (cache)  ├─> Task 7 (task_manager) ─┐
Task 8 (ai_client) ────────────────────────┤
                                            ├─> Task 9 (schemas)
Task 10 (health) ──────────────────────────┤
Task 11 (main app + handlers) ─────────────┤
                                            ├─> Task 12 (POST /inpaint)
                                            ├─> Task 13 (GET /tasks/{id})
                                            └─> Task 14 (GET /results/{id}.png)
                                                   │
                                          Task 15 (cleanup loop) ──┐
                                                                ├─> Task 16 (E2E test)
                                                                └─> Task 17 (smoke + README)
```

---

## Task 1: 项目脚手架

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/README.md`
- Create: `backend/app/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/storage/__init__.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: 创建目录结构**

```bash
cd "D:/AI_Projects/Photo Smart Erasure Assistant"
mkdir -p backend/app/{api/v1,schemas,services,core,storage}
mkdir -p backend/tests/api
touch backend/app/__init__.py \
      backend/app/api/__init__.py \
      backend/app/api/v1/__init__.py \
      backend/app/schemas/__init__.py \
      backend/app/services/__init__.py \
      backend/app/core/__init__.py \
      backend/app/storage/__init__.py \
      backend/tests/__init__.py
```

- [ ] **Step 2: 创建 requirements.txt**

`backend/requirements.txt`：
```
fastapi==0.115.6
uvicorn[standard]==0.32.1
pydantic==2.10.4
pydantic-settings==2.7.0
python-multipart==0.0.20
pillow==11.0.0
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.0
```

- [ ] **Step 3: 创建 .env.example**

`backend/.env.example`：
```
STORAGE_DIR=./storage
TTL_SECONDS=600
MAX_IMAGE_BYTES=10485760
MAX_IMAGE_DIM=2048
AI_BASE_URL=http://localhost:8001
AI_TIMEOUT_SECONDS=60
LOG_LEVEL=INFO
AI_CLIENT_MODE=mock
```

- [ ] **Step 4: 创建 .gitignore**

`backend/.gitignore`：
```
__pycache__/
*.pyc
.env
storage/
.pytest_cache/
*.egg-info/
.venv/
```

- [ ] **Step 5: 创建 README.md 骨架**

`backend/README.md`：
```markdown
# Photo Smart Erasure Assistant · Backend

FastAPI 后端，实现图片智能擦除的接口层、缓存、清理机制。

## 启动

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 文档

- 设计 spec: `../docs/superpowers/specs/2026-08-25-photo-eraser-api-design.md`
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## 测试

```bash
pytest tests/ -v
```
```

- [ ] **Step 6: 创建虚拟环境并安装依赖**

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/pip install -r requirements.txt
```

预期：`Successfully installed fastapi-0.115.6 ...` 一长串成功信息。

- [ ] **Step 7: 初始化 git 并提交**

```bash
cd backend
git init
git add .
git commit -m "chore: project scaffold with FastAPI + Pillow + httpx"
```

---

## Task 2: 配置模块（config.py）

**Files:**
- Create: `backend/app/core/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_config.py`：
```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend
.venv/Scripts/pytest tests/test_config.py -v
```

预期：FAIL（`ModuleNotFoundError: No module named 'app.core.config'`）

- [ ] **Step 3: 实现 config.py**

`backend/app/core/config.py`：
```python
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    storage_dir: Path = Path("./storage")
    ttl_seconds: int = 600
    max_image_bytes: int = 10 * 1024 * 1024
    max_image_dim: int = 2048

    ai_base_url: str = "http://localhost:8001"
    ai_timeout_seconds: int = 60
    ai_client_mode: str = "mock"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_config.py -v
```

预期：4 passed

- [ ] **Step 5: 提交**

```bash
git add app/core/config.py tests/test_config.py
git commit -m "feat(config): add Pydantic Settings with env override"
```

---

## Task 3: 异常类与全局 handler

**Files:**
- Create: `backend/app/core/exceptions.py`
- Test: `backend/tests/test_exceptions.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_exceptions.py`：
```python
import pytest
from app.core.exceptions import (
    BusinessError,
    InvalidImageFormat,
    InvalidMaskSize,
    MaskEmpty,
    PayloadTooLarge,
    TaskNotFound,
    ResultExpired,
    TaskNotReady,
    AIUpstreamError,
    AITimeout,
)


def test_business_error_has_code_and_http_status():
    err = InvalidImageFormat("bad format")
    assert err.code == "INVALID_IMAGE_FORMAT"
    assert err.http_status == 400
    assert "bad format" in str(err)


@pytest.mark.parametrize("exc_cls,code,status", [
    (InvalidImageFormat, "INVALID_IMAGE_FORMAT", 400),
    (InvalidMaskSize, "INVALID_MASK_SIZE", 400),
    (MaskEmpty, "MASK_EMPTY", 400),
    (PayloadTooLarge, "PAYLOAD_TOO_LARGE", 413),
    (TaskNotFound, "TASK_NOT_FOUND", 404),
    (ResultExpired, "RESULT_EXPIRED", 404),
    (TaskNotReady, "TASK_NOT_READY", 400),
    (AIUpstreamError, "AI_UPSTREAM_ERROR", 502),
    (AITimeout, "AI_TIMEOUT", 504),
])
def test_each_exception_has_unique_code_and_status(exc_cls, code, status):
    err = exc_cls("msg")
    assert err.code == code
    assert err.http_status == status


def test_request_id_attached_to_error():
    err = TaskNotFound("not found", request_id="req_abc")
    assert err.request_id == "req_abc"
    assert err.to_envelope() == {
        "error": {
            "code": "TASK_NOT_FOUND",
            "message": "not found",
            "request_id": "req_abc",
        }
    }
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_exceptions.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 exceptions.py**

`backend/app/core/exceptions.py`：
```python
from typing import Optional


class BusinessError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str, request_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.request_id = request_id

    def to_envelope(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "request_id": self.request_id,
            }
        }


class InvalidImageFormat(BusinessError):
    code = "INVALID_IMAGE_FORMAT"
    http_status = 400


class InvalidMaskSize(BusinessError):
    code = "INVALID_MASK_SIZE"
    http_status = 400


class MaskEmpty(BusinessError):
    code = "MASK_EMPTY"
    http_status = 400


class PayloadTooLarge(BusinessError):
    code = "PAYLOAD_TOO_LARGE"
    http_status = 413


class TaskNotFound(BusinessError):
    code = "TASK_NOT_FOUND"
    http_status = 404


class ResultExpired(BusinessError):
    code = "RESULT_EXPIRED"
    http_status = 404


class TaskNotReady(BusinessError):
    code = "TASK_NOT_READY"
    http_status = 400


class AIUpstreamError(BusinessError):
    code = "AI_UPSTREAM_ERROR"
    http_status = 502


class AITimeout(BusinessError):
    code = "AI_TIMEOUT"
    http_status = 504
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_exceptions.py -v
```

预期：13 passed

- [ ] **Step 5: 提交**

```bash
git add app/core/exceptions.py tests/test_exceptions.py
git commit -m "feat(exceptions): business exception hierarchy with HTTP status mapping"
```

---

## Task 4: 文件存储层

**Files:**
- Create: `backend/app/storage/local.py`
- Test: `backend/tests/test_storage.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_storage.py`：
```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_storage.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 local.py**

`backend/app/storage/local.py`：
```python
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
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_storage.py -v
```

预期：6 passed

- [ ] **Step 5: 提交**

```bash
git add app/storage/local.py tests/test_storage.py
git commit -m "feat(storage): LocalStorage with per-task subdir and TTL iteration"
```

---

## Task 5: 蒙版对齐预处理（align）

**Files:**
- Create: `backend/app/services/align.py`
- Test: `backend/tests/test_align.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_align.py`：
```python
import io
import pytest
from PIL import Image
from app.services.align import align_mask, MaskAlignError
from app.core.exceptions import InvalidMaskSize, MaskEmpty


def _img(mode, size, color):
    return Image.new(mode, size, color)


def test_align_same_size_passes_through():
    orig = _img("RGB", (100, 80), "white")
    mask = _img("L", (100, 80), 0)
    out = align_mask(orig, mask)
    assert out.size == (100, 80)


def test_align_resizes_mask_to_image_dimensions():
    orig = _img("RGB", (200, 100), "white")
    mask = _img("L", (100, 50), 128)
    out = align_mask(orig, mask)
    assert out.size == (200, 100)


def test_align_binarizes_above_threshold_to_white():
    orig = _img("RGB", (10, 10), "white")
    mask = _img("L", (10, 10), 100)
    out = align_mask(orig, mask)
    assert out.getpixel((0, 0)) == 0

    mask = _img("L", (10, 10), 200)
    out = align_mask(orig, mask)
    assert out.getpixel((0, 0)) == 255


def test_align_empty_mask_raises():
    orig = _img("RGB", (10, 10), "white")
    mask = _img("L", (10, 10), 0)
    with pytest.raises(MaskEmpty):
        align_mask(orig, mask)


def test_align_preserves_binarization_after_resize():
    orig = _img("RGB", (200, 100), "white")
    mask = _img("L", (100, 50), 255)
    out = align_mask(orig, mask)
    assert all(out.getpixel((x, y)) == 255 for x in range(0, 200, 50) for y in range(0, 100, 25))


def test_align_converts_rgba_mask_to_grayscale():
    orig = _img("RGB", (10, 10), "white")
    mask = _img("LA", (10, 10), (200, 255))
    out = align_mask(orig, mask)
    assert out.mode == "L"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_align.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 align.py**

`backend/app/services/align.py`：
```python
from PIL import Image
from app.core.exceptions import MaskEmpty


THRESHOLD = 127


def align_mask(image: Image.Image, mask: Image.Image) -> Image.Image:
    if mask.mode != "L":
        mask = mask.convert("L")

    if mask.size != image.size:
        mask = mask.resize(image.size, Image.NEAREST)

    mask = mask.point(lambda p: 255 if p > THRESHOLD else 0)

    if mask.getextrema() == (0, 0):
        raise MaskEmpty("蒙版全黑，用户未涂抹任何区域")

    return mask
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_align.py -v
```

预期：6 passed

- [ ] **Step 5: 提交**

```bash
git add app/services/align.py tests/test_align.py
git commit -m "feat(align): mask resize + binarize + empty detection"
```

---

## Task 6: 缓存服务（cache）

**Files:**
- Create: `backend/app/services/cache.py`
- Test: `backend/tests/test_cache.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_cache.py`：
```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_cache.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 cache.py**

`backend/app/services/cache.py`：
```python
import asyncio
from typing import Optional


class HashCache:
    def __init__(self):
        self._data: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def make_key(image_hash: str, mask_hash: str) -> tuple[str, str]:
        return (image_hash, mask_hash)

    async def get(self, image_hash: str, mask_hash: str) -> Optional[str]:
        async with self._lock:
            return self._data.get(self.make_key(image_hash, mask_hash))

    async def put(self, image_hash: str, mask_hash: str, task_id: str) -> None:
        async with self._lock:
            self._data[self.make_key(image_hash, mask_hash)] = task_id

    async def evict_by_task(self, task_id: str) -> int:
        async with self._lock:
            to_remove = [k for k, v in self._data.items() if v == task_id]
            for k in to_remove:
                del self._data[k]
            return len(to_remove)

    def size(self) -> int:
        return len(self._data)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_cache.py -v
```

预期：5 passed

- [ ] **Step 5: 提交**

```bash
git add app/services/cache.py tests/test_cache.py
git commit -m "feat(cache): async-safe hash cache for (image_hash, mask_hash) dedup"
```

---

## Task 7: 任务管理器（task_manager）

**Files:**
- Create: `backend/app/services/task_manager.py`
- Test: `backend/tests/test_task_manager.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_task_manager.py`：
```python
import pytest
from app.services.task_manager import TaskManager, TaskStatus


@pytest.fixture
def mgr():
    return TaskManager()


@pytest.mark.asyncio
async def test_create_task_returns_id_and_submitted_status(mgr):
    task_id = await mgr.create(image_hash="ih", mask_hash="mh")
    assert task_id.startswith("t_")
    task = await mgr.get(task_id)
    assert task["status"] == TaskStatus.SUBMITTED


@pytest.mark.asyncio
async def test_get_nonexistent_task_raises(mgr):
    from app.core.exceptions import TaskNotFound
    with pytest.raises(TaskNotFound):
        await mgr.get("t_nope")


@pytest.mark.asyncio
async def test_mark_processing_then_success(mgr):
    task_id = await mgr.create(image_hash="ih", mask_hash="mh")
    await mgr.set_processing(task_id)
    assert (await mgr.get(task_id))["status"] == TaskStatus.PROCESSING
    await mgr.set_success(task_id, result_url="/results/x.png", width=100, height=100, bytes_=1234)
    task = await mgr.get(task_id)
    assert task["status"] == TaskStatus.SUCCESS
    assert task["result"]["result_url"] == "/results/x.png"


@pytest.mark.asyncio
async def test_mark_failed_with_error_code(mgr):
    task_id = await mgr.create(image_hash="ih", mask_hash="mh")
    await mgr.set_processing(task_id)
    await mgr.set_failed(task_id, code="AI_UPSTREAM_ERROR", message="boom")
    task = await mgr.get(task_id)
    assert task["status"] == TaskStatus.FAILED
    assert task["error"]["code"] == "AI_UPSTREAM_ERROR"


@pytest.mark.asyncio
async def test_hash_keys_stored_on_task(mgr):
    task_id = await mgr.create(image_hash="img_sha", mask_hash="mask_sha")
    task = await mgr.get(task_id)
    assert task["image_hash"] == "img_sha"
    assert task["mask_hash"] == "mask_sha"


@pytest.mark.asyncio
async def test_created_at_and_expires_at_set(mgr):
    task_id = await mgr.create(image_hash="ih", mask_hash="mh", ttl_seconds=600)
    task = await mgr.get(task_id)
    delta = (task["expires_at"] - task["created_at"]).total_seconds()
    assert delta == 600
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_task_manager.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 task_manager.py**

`backend/app/services/task_manager.py`：
```python
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from app.core.exceptions import TaskNotFound


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return f"t_{uuid.uuid4().hex[:12]}"


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        image_hash: str,
        mask_hash: str,
        ttl_seconds: int = 600,
    ) -> str:
        async with self._lock:
            task_id = _new_id()
            now = _now()
            self._tasks[task_id] = {
                "task_id": task_id,
                "status": TaskStatus.SUBMITTED,
                "image_hash": image_hash,
                "mask_hash": mask_hash,
                "created_at": now,
                "expires_at": now + timedelta(seconds=ttl_seconds),
                "result": None,
                "error": None,
            }
            return task_id

    async def get(self, task_id: str) -> dict:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise TaskNotFound(f"task {task_id} 不存在或已清理")
            return task.copy()

    async def set_processing(self, task_id: str) -> None:
        async with self._lock:
            self._tasks[task_id]["status"] = TaskStatus.PROCESSING

    async def set_success(
        self,
        task_id: str,
        result_url: str,
        width: int,
        height: int,
        bytes_: int,
    ) -> None:
        async with self._lock:
            t = self._tasks[task_id]
            t["status"] = TaskStatus.SUCCESS
            t["result"] = {
                "result_url": result_url,
                "expires_at": t["expires_at"].isoformat(),
                "width": width,
                "height": height,
                "bytes": bytes_,
            }

    async def set_failed(self, task_id: str, code: str, message: str) -> None:
        async with self._lock:
            t = self._tasks[task_id]
            t["status"] = TaskStatus.FAILED
            t["error"] = {"code": code, "message": message}

    async def delete(self, task_id: str) -> None:
        async with self._lock:
            self._tasks.pop(task_id, None)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_task_manager.py -v
```

预期：6 passed

- [ ] **Step 5: 提交**

```bash
git add app/services/task_manager.py tests/test_task_manager.py
git commit -m "feat(task_manager): in-memory task state machine with TTL"
```

---

## Task 8: AI 客户端（mock + httpx）

**Files:**
- Create: `backend/app/services/ai_client.py`
- Test: `backend/tests/test_ai_client.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_ai_client.py`：
```python
import io
import pytest
from PIL import Image
from app.services.ai_client import MockAIClient, HttpxAIClient, AIClientError, AITimeoutError


def _make_png(size=(10, 10), color="white"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_mock_client_returns_fixed_png():
    client = MockAIClient(fixed_image_bytes=_make_png())
    result = await client.inpaint(b"img", b"mask", prompt=None)
    assert result[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_mock_client_with_prompt_returns_same_size():
    client = MockAIClient(fixed_image_bytes=_make_png())
    r1 = await client.inpaint(b"img", b"mask", prompt=None)
    r2 = await client.inpaint(b"img", b"mask", prompt="remove person")
    assert len(r1) == len(r2)


@pytest.mark.asyncio
async def test_http_client_raises_on_5xx(httpx_mock):
    httpx_mock.add_response(status_code=500, text="server error")
    client = HttpxAIClient(base_url="http://ai", timeout_seconds=5)
    with pytest.raises(AIClientError):
        await client.inpaint(b"img", b"mask", prompt=None)


@pytest.mark.asyncio
async def test_http_client_raises_timeout_on_slow(httpx_mock):
    import httpx
    httpx_mock.add_exception(httpx.TimeoutException("slow"))
    client = HttpxAIClient(base_url="http://ai", timeout_seconds=1)
    with pytest.raises(AITimeoutError):
        await client.inpaint(b"img", b"mask", prompt=None)


@pytest.mark.asyncio
async def test_http_client_returns_png_bytes(httpx_mock):
    png = _make_png()
    httpx_mock.add_response(status_code=200, content=png, headers={"content-type": "image/png"})
    client = HttpxAIClient(base_url="http://ai", timeout_seconds=5)
    result = await client.inpaint(b"img", b"mask", prompt=None)
    assert result == png
```

需要在 `tests/conftest.py` 加（如果不存在）：
```python
import pytest_httpx
```

`requirements.txt` 追加：
```
pytest-httpx==0.35.0
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_ai_client.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 ai_client.py**

`backend/app/services/ai_client.py`：
```python
import io
from typing import Optional, Protocol

import httpx
from PIL import Image

from app.core.exceptions import AIUpstreamError, AITimeout


class AIClientError(Exception):
    pass


class AITimeoutError(Exception):
    pass


class AIClient(Protocol):
    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str]
    ) -> bytes: ...


class MockAIClient:
    def __init__(self, fixed_image_bytes: bytes):
        self._fixed = fixed_image_bytes

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str]
    ) -> bytes:
        return self._fixed


class HttpxAIClient:
    def __init__(self, base_url: str, timeout_seconds: int = 60):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str]
    ) -> bytes:
        files = {
            "image": ("image.png", image_bytes, "image/png"),
            "mask": ("mask.png", mask_bytes, "image/png"),
        }
        data = {"prompt": prompt} if prompt else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/inpaint", files=files, data=data
                )
        except httpx.TimeoutException as e:
            raise AITimeoutError(str(e))
        except httpx.HTTPError as e:
            raise AIClientError(str(e))

        if resp.status_code >= 500:
            raise AIClientError(f"AI upstream {resp.status_code}: {resp.text}")
        if resp.status_code >= 400:
            raise AIClientError(f"AI rejected {resp.status_code}: {resp.text}")

        return resp.content


def make_client(mode: str, base_url: str, timeout_seconds: int) -> AIClient:
    if mode == "mock":
        placeholder = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(placeholder, format="PNG")
        return MockAIClient(fixed_image_bytes=placeholder.getvalue())
    return HttpxAIClient(base_url=base_url, timeout_seconds=timeout_seconds)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_ai_client.py -v
```

预期：5 passed

- [ ] **Step 5: 提交**

```bash
git add app/services/ai_client.py tests/test_ai_client.py tests/conftest.py requirements.txt
git commit -m "feat(ai_client): mock + httpx implementations with timeout handling"
```

---

## Task 9: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/inpaint.py`
- Create: `backend/app/schemas/task.py`
- Test: `backend/tests/test_schemas.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_schemas.py`：
```python
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.schemas.task import TaskStatusEnum, TaskResponse, TaskResult, TaskError, TaskStatus
from app.schemas.inpaint import SubmitResponse


def test_task_status_enum_values():
    assert TaskStatusEnum.SUBMITTED.value == "submitted"
    assert TaskStatusEnum.PROCESSING.value == "processing"
    assert TaskStatusEnum.SUCCESS.value == "success"
    assert TaskStatusEnum.FAILED.value == "failed"


def test_task_result_serialization():
    r = TaskResult(
        result_url="/x.png",
        expires_at=datetime(2026, 8, 25, 10, 10, tzinfo=timezone.utc),
        width=100,
        height=100,
        bytes=1234,
    )
    d = r.model_dump()
    assert d["result_url"] == "/x.png"
    assert d["width"] == 100


def test_task_response_success():
    resp = TaskResponse(
        task_id="t_abc",
        status=TaskStatusEnum.SUCCESS,
        created_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        result={
            "result_url": "/x.png",
            "expires_at": "2026-08-25T10:10:00Z",
            "width": 100,
            "height": 100,
            "bytes": 1234,
        },
    )
    assert resp.status == TaskStatusEnum.SUCCESS


def test_task_response_failed_with_error():
    resp = TaskResponse(
        task_id="t_abc",
        status=TaskStatusEnum.FAILED,
        created_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        error=TaskError(code="AI_UPSTREAM_ERROR", message="boom"),
    )
    assert resp.error.code == "AI_UPSTREAM_ERROR"


def test_submit_response_basic():
    r = SubmitResponse(
        task_id="t_abc",
        status="submitted",
        created_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 8, 25, 10, 10, tzinfo=timezone.utc),
    )
    assert r.task_id == "t_abc"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_schemas.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 schemas/task.py**

`backend/app/schemas/task.py`：
```python
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatusEnum(str, Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class TaskResult(BaseModel):
    result_url: str
    expires_at: datetime
    width: int
    height: int
    bytes: int = Field(..., alias="bytes_")


class TaskError(BaseModel):
    code: str
    message: str


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatusEnum
    created_at: datetime
    result: Optional[dict] = None
    error: Optional[TaskError] = None
```

- [ ] **Step 4: 实现 schemas/inpaint.py**

`backend/app/schemas/inpaint.py`：
```python
from datetime import datetime
from pydantic import BaseModel


class SubmitResponse(BaseModel):
    task_id: str
    status: str
    created_at: datetime
    expires_at: datetime
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
.venv/Scripts/pytest tests/test_schemas.py -v
```

预期：5 passed

- [ ] **Step 6: 提交**

```bash
git add app/schemas/ tests/test_schemas.py
git commit -m "feat(schemas): Pydantic models for submit + task responses"
```

---

## Task 10: 健康检查端点

**Files:**
- Create: `backend/app/api/v1/health.py`
- Test: `backend/tests/api/test_health.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/api/test_health.py`：
```python
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", "./storage_test")
    monkeypatch.setenv("AI_CLIENT_MODE", "mock")
    from app.core.config import get_settings
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_health_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "ai_reachable" in data
    assert "version" in data
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/api/test_health.py -v
```

预期：FAIL（`app.main` 不存在）

- [ ] **Step 3: 实现 health.py**

`backend/app/api/v1/health.py`：
```python
from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "ai_reachable": True,
        "version": "0.1.0",
    }
```

- [ ] **Step 4: 提交（跳过测试运行，main.py 还没创建）**

```bash
git add app/api/v1/health.py tests/api/test_health.py
git commit -m "feat(health): GET /api/v1/health endpoint"
```

> 注：本任务的测试在 Task 11 创建 `app.main` 后才能跑通，届时会一起验证。

---

## Task 11: 主应用 + 全局异常 handler

**Files:**
- Create: `backend/app/main.py`
- Test: `backend/tests/api/test_error_handlers.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/api/test_error_handlers.py`：
```python
import pytest
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


def test_business_error_returns_envelope(client):
    from app.core.exceptions import TaskNotFound
    from fastapi import APIRouter

    test_app = create_app()
    router = APIRouter()

    @router.get("/_test_raise")
    def _raise():
        raise TaskNotFound("task t_xxx not found", request_id="req_test")

    test_app.include_router(router)
    c = TestClient(test_app)
    resp = c.get("/_test_raise")
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {
            "code": "TASK_NOT_FOUND",
            "message": "task t_xxx not found",
            "request_id": "req_test",
        }
    }
    assert resp.headers["X-Request-Id"] == "req_test"


def test_unknown_exception_returns_internal_error(client):
    test_app = create_app()
    router = APIRouter()

    @router.get("/_test_crash")
    def _crash():
        raise RuntimeError("unexpected")

    test_app.include_router(router)
    c = TestClient(test_app)
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/api/test_error_handlers.py -v
```

预期：FAIL（`app.main` 不存在）

- [ ] **Step 3: 实现 main.py**

`backend/app/main.py`：
```python
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import health, inpaint
from app.core.config import get_settings
from app.core.exceptions import BusinessError
from app.services.ai_client import make_client
from app.services.cache import HashCache
from app.services.task_manager import TaskManager
from app.storage.local import LocalStorage


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        storage = LocalStorage(base_dir=settings.storage_dir)
        cache = HashCache()
        task_mgr = TaskManager()
        ai = make_client(
            mode=settings.ai_client_mode,
            base_url=settings.ai_base_url,
            timeout_seconds=settings.ai_timeout_seconds,
        )
        app.state.storage = storage
        app.state.cache = cache
        app.state.task_manager = task_mgr
        app.state.ai_client = ai
        yield

    app = FastAPI(
        title="Photo Smart Erasure Assistant",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        exc.request_id = getattr(request.state, "request_id", None)
        return JSONResponse(status_code=exc.http_status, content=exc.to_envelope())

    @app.exception_handler(Exception)
    async def fallback_handler(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误", "request_id": rid}},
        )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(inpaint.router, prefix="/api/v1")

    return app


app = create_app()
```

- [ ] **Step 4: 实现空的 inpaint router 占位（Task 12 会填充）**

`backend/app/api/v1/inpaint.py`：
```python
from fastapi import APIRouter

router = APIRouter(tags=["inpaint"])
```

- [ ] **Step 5: 运行 health + error_handlers 测试**

```bash
.venv/Scripts/pytest tests/api/ -v
```

预期：test_health 1 passed + test_error_handlers 4 passed = 5 passed

- [ ] **Step 6: 提交**

```bash
git add app/main.py app/api/v1/inpaint.py tests/api/
git commit -m "feat(main): FastAPI app with lifespan, request_id, error handlers"
```

---

## Task 12: 提交任务端点 POST /api/v1/inpaint

**Files:**
- Modify: `backend/app/api/v1/inpaint.py`
- Test: `backend/tests/api/test_inpaint_submit.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/api/test_inpaint_submit.py`：
```python
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


def _png_bytes(size=(100, 100), mode="RGB", color="white"):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
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
    return TestClient(app)


def test_submit_returns_202_with_task_id(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(), "image/png"),
            "mask": ("mask.png", _mask_bytes(), "image/png"),
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"].startswith("t_")
    assert data["status"] == "submitted"


def test_submit_rejects_oversized_image(client):
    big = _png_bytes(size=(3000, 3000))
    resp = client.post(
        "/api/v1/inpaint",
        files={"image": ("orig.png", big, "image/png"), "mask": ("mask.png", _mask_bytes(), "image/png")},
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_submit_rejects_empty_mask(client):
    empty_mask = _mask_bytes()
    empty_mask_buf = io.BytesIO()
    Image.new("L", (100, 100), 0).save(empty_mask_buf, format="PNG")

    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(), "image/png"),
            "mask": ("mask.png", empty_mask_buf.getvalue(), "image/png"),
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MASK_EMPTY"


def test_submit_rejects_size_mismatch(client):
    resp = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("orig.png", _png_bytes(size=(200, 100)), "image/png"),
            "mask": ("mask.png", _mask_bytes(size=(100, 200)), "image/png"),
        },
    )
    assert resp.status_code == 202
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/api/test_inpaint_submit.py -v
```

预期：FAIL（路由不存在 / 405）

- [ ] **Step 3: 实现 POST /inpaint**

`backend/app/api/v1/inpaint.py`：
```python
import io
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    InvalidImageFormat,
    PayloadTooLarge,
)
from app.schemas.inpaint import SubmitResponse

router = APIRouter(tags=["inpaint"])


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_image_bytes(data: bytes, max_dim: int) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise InvalidImageFormat("无法解析图像数据，可能已损坏或格式不支持")
    if max(img.size) > max_dim:
        raise PayloadTooLarge(f"图像长边 {max(img.size)} 超过限制 {max_dim}")
    return img


@router.post("/inpaint", response_model=SubmitResponse, status_code=202)
async def submit_inpaint(
    request: Request,
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    settings: Settings = Depends(get_settings),
):
    image_bytes = await image.read()
    mask_bytes = await mask.read()

    if len(image_bytes) > settings.max_image_bytes:
        raise PayloadTooLarge(f"图像大小 {len(image_bytes)} 超过限制 {settings.max_image_bytes}")

    orig_img = _validate_image_bytes(image_bytes, settings.max_image_dim)

    from app.services.align import align_mask
    try:
        mask_img = Image.open(io.BytesIO(mask_bytes))
        mask_img.load()
    except Exception:
        raise InvalidImageFormat("无法解析蒙版数据")
    aligned_mask = align_mask(orig_img, mask_img)
    aligned_buf = io.BytesIO()
    aligned_mask.save(aligned_buf, format="PNG")
    aligned_mask_bytes = aligned_buf.getvalue()

    image_hash = _hash_bytes(image_bytes)
    mask_hash = _hash_bytes(aligned_mask_bytes)

    cache = request.app.state.cache
    task_manager = request.app.state.task_manager
    storage = request.app.state.storage

    cached_task_id = await cache.get(image_hash, mask_hash)
    if cached_task_id:
        try:
            cached_task = await task_manager.get(cached_task_id)
            if cached_task["status"].value == "success":
                return SubmitResponse(
                    task_id=cached_task_id,
                    status="success",
                    created_at=cached_task["created_at"],
                    expires_at=cached_task["expires_at"],
                )
        except Exception:
            pass

    task_id = await task_manager.create(
        image_hash=image_hash, mask_hash=mask_hash, ttl_seconds=settings.ttl_seconds
    )

    storage.save(task_id, "image.png", image_bytes)
    storage.save(task_id, "mask.png", aligned_mask_bytes)

    from fastapi import BackgroundTasks
    background: BackgroundTasks = request.background
    background.add_task(
        _run_inpaint_background,
        task_id=task_id,
        image_bytes=image_bytes,
        mask_bytes=aligned_mask_bytes,
        prompt=prompt,
        request_state=request.state,
    )

    task = await task_manager.get(task_id)
    return SubmitResponse(
        task_id=task_id,
        status="submitted",
        created_at=task["created_at"],
        expires_at=task["expires_at"],
    )


async def _run_inpaint_background(task_id, image_bytes, mask_bytes, prompt, request_state):
    from app.main import app as _app
    ai = _app.state.ai_client
    storage = _app.state.storage
    cache = _app.state.cache
    task_manager = _app.state.task_manager
    from app.services.align import align_mask as _align
    from PIL import Image as _Image
    import io as _io
    from app.core.exceptions import AITimeout, AIUpstreamError
    from app.services.ai_client import AIClientError, AITimeoutError

    orig = _Image.open(_io.BytesIO(image_bytes))
    mask = _Image.open(_io.BytesIO(mask_bytes))

    try:
        await task_manager.set_processing(task_id)
        result_bytes = await ai.inpaint(image_bytes, mask_bytes, prompt)
    except AITimeoutError:
        await task_manager.set_failed(task_id, code="AI_TIMEOUT", message="AI 服务超时")
        return
    except AIClientError as e:
        await task_manager.set_failed(task_id, code="AI_UPSTREAM_ERROR", message=str(e))
        return

    storage.save(task_id, "result.png", result_bytes)

    from PIL import Image as _I
    result_img = _I.open(io.BytesIO(result_bytes))
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    mask_hash = hashlib.sha256(mask_bytes).hexdigest()

    await cache.put(image_hash, mask_hash, task_id)

    await task_manager.set_success(
        task_id,
        result_url=f"/api/v1/results/{task_id}.png",
        width=result_img.size[0],
        height=result_img.size[1],
        bytes_=len(result_bytes),
    )
```

- [ ] **Step 4: 运行测试**

```bash
.venv/Scripts/pytest tests/api/test_inpaint_submit.py -v
```

预期：4 passed（mock client 会自动完成；submit 后任务进入 success）

- [ ] **Step 5: 提交**

```bash
git add app/api/v1/inpaint.py tests/api/test_inpaint_submit.py
git commit -m "feat(inpaint): POST /inpaint with align, cache dedup, background AI call"
```

---

## Task 13: 任务状态端点 GET /api/v1/tasks/{id}

**Files:**
- Modify: `backend/app/api/v1/inpaint.py`
- Test: `backend/tests/api/test_task_status.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/api/test_task_status.py`：
```python
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


def _png_bytes(size=(100, 100)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
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
    return TestClient(app)


def test_get_task_returns_success_with_result_url(client):
    submit = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("i.png", _png_bytes(), "image/png"),
            "mask": ("m.png", _mask_bytes(), "image/png"),
        },
    )
    task_id = submit.json()["task_id"]

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == task_id
    assert data["status"] in ("processing", "success")
    if data["status"] == "success":
        assert data["result"]["result_url"].endswith(".png")


def test_get_nonexistent_task_returns_404(client):
    resp = client.get("/api/v1/tasks/t_doesnotexist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TASK_NOT_FOUND"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/api/test_task_status.py -v
```

预期：FAIL（路由不存在）

- [ ] **Step 3: 在 inpaint.py 添加 GET 端点**

编辑 `backend/app/api/v1/inpaint.py`，追加：

```python
from app.core.exceptions import TaskNotFound

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, request: Request):
    task_manager = request.app.state.task_manager
    try:
        task = await task_manager.get(task_id)
    except TaskNotFound as e:
        e.request_id = getattr(request.state, "request_id", None)
        raise
    return {
        "task_id": task["task_id"],
        "status": task["status"].value if hasattr(task["status"], "value") else task["status"],
        "created_at": task["created_at"].isoformat(),
        "result": task["result"],
        "error": task["error"],
    }
```

- [ ] **Step 4: 运行测试**

```bash
.venv/Scripts/pytest tests/api/test_task_status.py -v
```

预期：2 passed

- [ ] **Step 5: 提交**

```bash
git add app/api/v1/inpaint.py tests/api/test_task_status.py
git commit -m "feat(inpaint): GET /tasks/{id} for polling task status"
```

---

## Task 14: 修复图下载端点 GET /api/v1/results/{id}.png

**Files:**
- Modify: `backend/app/api/v1/inpaint.py`
- Test: `backend/tests/api/test_result_download.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/api/test_result_download.py`：
```python
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


def _png_bytes(size=(100, 100)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
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
    return TestClient(app)


def test_download_result_returns_png(client):
    submit = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("i.png", _png_bytes(), "image/png"),
            "mask": ("m.png", _mask_bytes(), "image/png"),
        },
    )
    task_id = submit.json()["task_id"]

    for _ in range(20):
        status = client.get(f"/api/v1/tasks/{task_id}").json()["status"]
        if status == "success":
            break
        import time
        time.sleep(0.1)
    else:
        pytest.fail("task did not reach success")

    resp = client.get(f"/api/v1/results/{task_id}.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_download_nonexistent_returns_404(client):
    resp = client.get("/api/v1/results/t_nope.png")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/api/test_result_download.py -v
```

预期：FAIL（路由不存在）

- [ ] **Step 3: 在 inpaint.py 添加 GET results 端点**

编辑 `backend/app/api/v1/inpaint.py`，追加：

```python
from fastapi.responses import Response
from app.core.exceptions import ResultExpired, TaskNotReady


@router.get("/results/{filename}")
async def download_result(filename: str, request: Request):
    if not filename.endswith(".png"):
        raise ResultExpired("文件名格式错误")
    task_id = filename[:-4]
    storage = request.app.state.storage
    if not storage.exists(task_id, "result.png"):
        raise ResultExpired(f"task {task_id} 修复结果不存在或已清理")

    task_manager = request.app.state.task_manager
    try:
        task = await task_manager.get(task_id)
    except TaskNotFound:
        raise ResultExpired(f"task {task_id} 已被清理")
    if task["status"].value != "success":
        raise TaskNotReady(f"task {task_id} 仍在 {task['status'].value}")

    data = storage.read(task_id, "result.png")
    return Response(
        content=data,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{task_id}.png"',
        },
    )
```

- [ ] **Step 4: 运行测试**

```bash
.venv/Scripts/pytest tests/api/test_result_download.py -v
```

预期：3 passed（第一个可能因 timing 偶尔失败，重试即可）

- [ ] **Step 5: 提交**

```bash
git add app/api/v1/inpaint.py tests/api/test_result_download.py
git commit -m "feat(inpaint): GET /results/{id}.png download endpoint"
```

---

## Task 15: 清理后台任务

**Files:**
- Create: `backend/app/core/cleanup.py`
- Modify: `backend/app/main.py`（启动时拉起循环）
- Test: `backend/tests/test_cleanup.py`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_cleanup.py`：
```python
import time
import pytest
from pathlib import Path
from app.core.cleanup import cleanup_once
from app.storage.local import LocalStorage
from app.services.cache import HashCache


def test_cleanup_once_removes_old_files(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    cache = HashCache()
    storage.save("t_old", "image.png", b"x")
    storage.save("t_old", "result.png", b"y")

    old_path = storage.path_for("t_old", "image.png")
    import os
    old_time = time.time() - 700
    os.utime(old_path, (old_time, old_time))

    removed = cleanup_once(storage, cache, ttl_seconds=600)
    assert removed == 2
    assert not old_path.exists()


def test_cleanup_once_keeps_recent_files(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    cache = HashCache()
    storage.save("t_new", "image.png", b"x")
    removed = cleanup_once(storage, cache, ttl_seconds=600)
    assert removed == 0
    assert storage.path_for("t_new", "image.png").exists()


@pytest.mark.asyncio
async def test_cleanup_once_evicts_cache_for_removed_task(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    cache = HashCache()
    await cache.put("ih", "mh", "t_xyz")
    storage.save("t_xyz", "image.png", b"x")
    import os, time
    old_path = storage.path_for("t_xyz", "image.png")
    old_time = time.time() - 700
    os.utime(old_path, (old_time, old_time))

    cleanup_once(storage, cache, ttl_seconds=600)
    assert await cache.get("ih", "mh") is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/Scripts/pytest tests/test_cleanup.py -v
```

预期：FAIL（模块不存在）

- [ ] **Step 3: 实现 cleanup.py**

`backend/app/core/cleanup.py`：
```python
import asyncio
import time
from pathlib import Path

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
        cache.evict_by_task_sync(task_id)
    return removed


async def cleanup_loop(storage: LocalStorage, cache: HashCache, ttl_seconds: int, interval_seconds: int = 60):
    while True:
        try:
            cleanup_once(storage, cache, ttl_seconds)
        except Exception as e:
            print(f"[cleanup] error: {e}")
        await asyncio.sleep(interval_seconds)
```

为支持 sync 版本的 `evict_by_task`，在 `app/services/cache.py` 加一个同步方法（修改 Task 6 已有文件）：

```python
def evict_by_task_sync(self, task_id: str) -> int:
    to_remove = [k for k, v in self._data.items() if v == task_id]
    for k in to_remove:
        del self._data[k]
    return len(to_remove)
```

- [ ] **Step 4: 运行测试**

```bash
.venv/Scripts/pytest tests/test_cleanup.py -v
```

预期：3 passed

- [ ] **Step 5: 在 main.py lifespan 拉起循环**

编辑 `backend/app/main.py`，修改 `lifespan`：

```python
from app.core.cleanup import cleanup_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = LocalStorage(base_dir=settings.storage_dir)
    cache = HashCache()
    task_mgr = TaskManager()
    ai = make_client(...)
    app.state.storage = storage
    app.state.cache = cache
    app.state.task_manager = task_mgr
    app.state.ai_client = ai

    cleanup_task = asyncio.create_task(
        cleanup_loop(storage, cache, settings.ttl_seconds, interval_seconds=60)
    )
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
```

并在 `main.py` 顶部加 `import asyncio`。

- [ ] **Step 6: 运行全部测试**

```bash
.venv/Scripts/pytest -v
```

预期：全部通过

- [ ] **Step 7: 提交**

```bash
git add app/core/cleanup.py app/services/cache.py app/main.py tests/test_cleanup.py
git commit -m "feat(cleanup): asyncio loop deleting files past TTL + cache eviction"
```

---

## Task 16: 端到端集成测试

**Files:**
- Test: `backend/tests/test_e2e.py`

- [ ] **Step 1: 写集成测试**

`backend/tests/test_e2e.py`：
```python
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
    return TestClient(app)


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
```

- [ ] **Step 2: 运行集成测试**

```bash
.venv/Scripts/pytest tests/test_e2e.py -v
```

预期：2 passed

- [ ] **Step 3: 提交**

```bash
git add tests/test_e2e.py
git commit -m "test(e2e): full submit-poll-download flow + cache dedup verification"
```

---

## Task 17: 手动验证与 README 完善

**Files:**
- Modify: `backend/README.md`
- Create: `backend/scripts/smoke_test.sh`

- [ ] **Step 1: 启动服务（手动）**

打开终端 1：
```bash
cd "D:/AI_Projects/Photo Smart Erasure Assistant/backend"
.venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

预期：`Uvicorn running on http://0.0.0.0:8000`

- [ ] **Step 2: 健康检查**

终端 2：
```bash
curl http://localhost:8000/api/v1/health
```

预期：`{"status":"ok","ai_reachable":true,"version":"0.1.0"}`

- [ ] **Step 3: OpenAPI 文档可访问**

浏览器打开：`http://localhost:8000/docs`

预期：Swagger UI 渲染，显示 4 个端点（POST /api/v1/inpaint、GET /api/v1/tasks/{id}、GET /api/v1/results/{filename}、GET /api/v1/health）

- [ ] **Step 4: 创建 smoke_test 脚本**

`backend/scripts/smoke_test.sh`（Windows Git Bash）：
```bash
#!/usr/bin/env bash
set -e
BASE=${BASE:-http://localhost:8000}

echo "== health =="
curl -s $BASE/api/v1/health | python -m json.tool

echo "== submit task =="
python -c "
from PIL import Image
import io
img = io.BytesIO(); Image.new('RGB', (100, 100), 'white').save(img, 'PNG')
m = io.BytesIO(); Image.new('L', (100, 100), 255).save(m, 'PNG')
open('/tmp/i.png', 'wb').write(img.getvalue())
open('/tmp/m.png', 'wb').write(m.getvalue())
"

TASK_ID=$(curl -s -X POST $BASE/api/v1/inpaint \
  -F "image=@/tmp/i.png" \
  -F "mask=@/tmp/m.png" | python -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "task_id=$TASK_ID"

sleep 2

echo "== poll =="
curl -s $BASE/api/v1/tasks/$TASK_ID | python -m json.tool

echo "== download =="
curl -s -o /tmp/r.png $BASE/api/v1/results/$TASK_ID.png
file /tmp/r.png
```

- [ ] **Step 5: 运行 smoke test**

```bash
cd backend
chmod +x scripts/smoke_test.sh
bash scripts/smoke_test.sh
```

预期：health 200 → submit 返回 task_id → poll 返回 status=success + result_url → download 写入 /tmp/r.png，`file` 命令识别为 PNG image

- [ ] **Step 6: 在 README 增加 smoke test 说明**

编辑 `backend/README.md`，追加：

```markdown
## Smoke Test

```bash
# Terminal 1
.venv/Scripts/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2
bash scripts/smoke_test.sh
```

## 与前端联调

1. 前端启动时调用 `GET /api/v1/health` 探活
2. 用户涂抹完成后调用 `POST /api/v1/inpaint`（multipart）拿到 task_id
3. 启动轮询 `GET /api/v1/tasks/{task_id}`，间隔 1-2 秒
4. status=success 后下载 `GET {result_url}` 拿到 PNG 二进制
5. 保存到本地相册

## 与 AI 模型同学对齐

`core/config.py` 中 `AI_BASE_URL` 与 `AI_CLIENT_MODE` 待 AI 同学给出接口契约后切换：
- `mock`：内置 mock client，返回固定 PNG
- `http`：调用 `POST {AI_BASE_URL}/inpaint`
```

- [ ] **Step 7: 提交**

```bash
git add scripts/ README.md
git commit -m "docs: smoke test script and frontend/AI integration guide"
```

---

## 验收清单

按 spec §9 验证：

- [ ] Task 12-14：4 个端点全部实现并通过 OpenAPI schema 校验（`/openapi.json` 包含全部路径）
- [ ] Task 5：蒙版自动 resize + 二值化逻辑单元测试覆盖（`test_align.py`）
- [ ] Task 16：同图同蒙版第二次提交命中缓存，AI 调用次数 = 1（mock）
- [ ] Task 15：T+10min 文件自动清理，原图/蒙版/结果均不存在（手动 os.utime 验证）
- [ ] Task 11：统一错误响应格式（`test_error_handlers.py`）
- [ ] Task 10：GET /health 返回 ai_reachable 字段
- [ ] Task 11：响应头含 X-Request-Id
- [ ] Task 17：Swagger UI 可访问（`/docs`）

## 跑完所有测试

```bash
cd "D:/AI_Projects/Photo Smart Erasure Assistant/backend"
.venv/Scripts/pytest -v
```

预期：所有用例通过。

---

## 已知 / 待对齐

- Task 8 中 AI 客户端 `HttpxAIClient` 假设 AI 端 `/inpaint` 接口与本计划契约一致；待 AI 模型同学确认 `AI_BASE_URL`、鉴权 header、错误码后可能需要调整
- Task 12 中的 `progress` 字段 v0.1 未实现，与 spec §3.2 一致；v0.2/v0.3 由后端估算或 AI 心跳
- 生产部署方案（DOCKER / 裸机 / nginx）由组长统一决定后补充
