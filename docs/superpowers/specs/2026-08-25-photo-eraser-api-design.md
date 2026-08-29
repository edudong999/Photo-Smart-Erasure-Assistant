# 照片智能擦除小助手 · 后端接口设计

**日期**：2026-08-25
**状态**：待用户复核
**范围**：后端 API 设计（不含 AI 模型内部、不含 Android 前端）
**对应项目**：项目五 · 照片智能擦除小助手（图像实例分割与修复方向）

---

## 1. 目标与约束

### 1.1 项目定位

面向日常修图场景：用户在 Android 端手动涂抹框选多余元素（人物、宠物等），后端调用 AI 自动完成目标区域擦除并补全背景纹理与光影，返回修复后图片。

### 1.2 后端职责（来自项目文档）

1. 接口设计
2. 蒙版与原图像素级对齐预处理
3. 异步封装调用 AI API 处理修复请求
4. 实现请求缓存去重
5. 异常拦截
6. 服务器端图片定期清理机制

### 1.3 关键约束

- **轻量**：FastAPI 单体，不引入数据库、消息队列、对象存储（联调阶段）
- **隐私**：原图、蒙版、修复图不持久留存；修复完成 10 分钟后自动清理
- **异步**：AI 推理耗时秒级到分钟级，必须异步任务模式
- **联调友好**：自动生成 OpenAPI 文档；统一错误结构；统一字段命名

---

## 2. 架构总览

### 2.1 技术栈

- **框架**：FastAPI 0.115+（Python 3.11+）
- **ASGI**：uvicorn[standard]
- **图像处理**：Pillow
- **异步 HTTP**：httpx
- **校验**：Pydantic v2
- **测试**：pytest + httpx AsyncClient

无数据库、无 Redis、无 Celery。

### 2.2 目录结构

```
photo-eraser-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口、路由挂载、lifespan
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── inpaint.py       # POST /inpaint, GET /tasks/{id}, GET /results/{file}
│   │       └── health.py        # GET /health
│   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── inpaint.py
│   │   └── task.py
│   ├── services/                # 业务逻辑（路由薄、业务厚）
│   │   ├── __init__.py
│   │   ├── task_manager.py      # 任务创建/查询/状态机
│   │   ├── cache.py             # (image_hash, mask_hash) 缓存
│   │   ├── align.py             # 蒙版与原图像素级对齐预处理
│   │   └── ai_client.py         # 封装 AI 模型同学的接口
│   ├── core/                    # 跨层基础设施
│   │   ├── __init__.py
│   │   ├── config.py            # 配置（路径、TTL、限额、AI base URL）
│   │   ├── exceptions.py        # 业务异常 + 全局 handler
│   │   └── cleanup.py           # 后台定时清理（asyncio 循环）
│   └── storage/
│       ├── __init__.py
│       └── local.py             # 本地文件系统存储（抽象接口）
├── tests/
│   ├── test_align.py
│   ├── test_cache.py
│   ├── test_task_manager.py
│   └── api/
│       ├── test_inpaint.py
│       └── test_health.py
├── requirements.txt
├── README.md
└── .env.example
```

### 2.3 模块职责

| 模块 | 单一职责 | 输入 | 输出 |
|---|---|---|---|
| `api/v1/inpaint.py` | HTTP 路由，参数解析，业务异常抛出 | HTTP 请求 | JSON 响应 |
| `services/task_manager.py` | 任务 CRUD、状态机推进、缓存读写协调 | image_bytes, mask_bytes | task_id, status |
| `services/cache.py` | (image_hash, mask_hash) → task_id 映射，进程内 dict | hash 键 | 缓存命中/未命中 |
| `services/align.py` | 蒙版与原图尺寸对齐 + 二值化 | image, mask | aligned_mask (PIL.Image) |
| `services/ai_client.py` | 异步调用 AI 模型接口、超时与重试 | image, mask, prompt | 修复图 PNG bytes |
| `core/cleanup.py` | 每 60s 扫描 storage，TTL 过期文件删除 | — | — |
| `storage/local.py` | 文件读写、路径生成 | task_id | file path |

---

## 3. API 端点

基础路径：`/api/v1`
内容类型：`application/json`（除文件上传/下载）
统一错误结构（见 §6）

### 3.1 POST /api/v1/inpaint —— 提交修复任务

**请求**：`multipart/form-data`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `image` | File | ✓ | JPEG/PNG/WEBP；≤ 10 MB；长边 ≤ 2048 px |
| `mask` | File | ✓ | PNG 灰度图；与原图同尺寸 |
| `prompt` | string | ✗ | ≤ 200 字符，透传给 AI 模型 |

**响应 202**：
```json
{
  "task_id": "t_8f3a2b1c",
  "status": "submitted",
  "created_at": "2026-08-25T10:00:00Z",
  "expires_at": "2026-08-25T10:10:00Z"
}
```

**缓存命中**：若 `(sha256(image_bytes), sha256(mask_bytes))` 已存在成功的修复结果，立即返回该 task_id 的 `success` 状态（result 字段已填）。

**错误**：
- `400 INVALID_IMAGE_FORMAT` — 格式不支持或图像损坏
- `400 INVALID_MASK_SIZE` — 蒙版与原图尺寸不一致且自动 resize 失败
- `400 MASK_EMPTY` — 蒙版全黑（用户未涂抹）
- `413 PAYLOAD_TOO_LARGE` — 超过 10 MB 或长边超过 2048 px
- `429 RATE_LIMITED` — 同图同蒙版短时间内请求过多

### 3.2 GET /api/v1/tasks/{task_id} —— 轮询任务状态

**路径参数**：`task_id` 字符串

**响应 200**（统一 schema，状态不同时字段填充不同；v0.1 示例）：
```json
{
  "task_id": "t_8f3a2b1c",
  "status": "processing",
  "created_at": "2026-08-25T10:00:00Z",
  "result": null,
  "error": null
}
```

**status 取值**：`submitted` | `processing` | `success` | `failed`

**status=success 时的 result**：
```json
{
  "result_url": "/api/v1/results/t_8f3a2b1c.png",
  "expires_at": "2026-08-25T10:10:00Z",
  "width": 1920,
  "height": 1080,
  "bytes": 384210
}
```

**status=failed 时的 error**：
```json
{
  "code": "AI_UPSTREAM_ERROR",
  "message": "上游 AI 服务暂时不可用"
}
```

**字段说明**：
- `progress`：v0.1 不返回此字段（OpenAPI schema 中保留为可选）。v0.2 由后端基于等待时长粗略估算（0-30s→0，30-60s→50，>60s→90）；v0.3 由 AI 模型同学通过心跳接口提供精确进度
- `created_at` / `expires_at`：ISO 8601 UTC

**错误**：
- `404 TASK_NOT_FOUND` — task_id 不存在或已被清理
- `400 INVALID_TASK_ID` — task_id 格式不合法

### 3.3 GET /api/v1/results/{task_id}.png —— 下载修复图

**路径参数**：`task_id` 字符串

**响应 200**：`image/png` 二进制流
- 响应头：`Cache-Control: private, max-age=300`
- 响应头：`Content-Disposition: inline; filename="{task_id}.png"`

**错误**：
- `404 RESULT_EXPIRED` — 文件已被清理
- `404 TASK_NOT_FOUND` — task_id 不存在或任务未成功
- `400 TASK_NOT_READY` — 任务仍在 processing（应继续轮询）

### 3.4 GET /api/v1/health —— 健康检查

**响应 200**：
```json
{
  "status": "ok",
  "ai_reachable": true,
  "version": "0.1.0"
}
```

`ai_reachable`：后端探测 AI 模型同学接口是否可达（轻量 ping，不消耗推理资源）。

---

## 4. 数据流与状态机

### 4.1 端到端请求流

```
Android                    FastAPI 后端                       AI 模型
  │                            │                                 │
  │ POST /inpaint              │                                 │
  │ (image, mask, prompt?)     │                                 │
  ├───────────────────────────>│                                 │
  │                            │ 1. 校验格式/尺寸/大小           │
  │                            │ 2. 算 sha256(image)+sha256(mask)│
  │                            │ 3. 查缓存：命中 → 返回旧 task_id│
  │                            │ 4. 未命中：                     │
  │                            │    - 落盘原图/蒙版到 storage    │
  │                            │    - 创建 task (status=submitted)│
  │                            │    - BackgroundTasks:           │
  │                            │      align → call AI → save     │
  │ 202 {task_id, status}      │                                 │
  │<───────────────────────────┤                                 │
  │                            │                  inpaint(orig,   │
  │                            │                   mask, prompt)  │
  │                            ├────────────────────────────────>│
  │                            │                  repaired PNG    │
  │                            │<────────────────────────────────┤
  │                            │ 5. 落盘 result → status=success │
  │                            │ 6. 写缓存 (hash → task_id)      │
  │                            │                                 │
  │ GET /tasks/{id} (轮询)     │                                 │
  ├───────────────────────────>│                                 │
  │ 200 {status, result_url}   │                                 │
  │<───────────────────────────┤                                 │
  │                            │                                 │
  │ GET /results/{id}.png      │                                 │
  ├───────────────────────────>│                                 │
  │<──── image/png ───────────┤                                 │
  │                            │                                 │
  │                  T+10min   │                                 │
  │                            │ cleanup 任务: 删原图/蒙版/结果  │
  │                            │ 清缓存条目                       │
```

### 4.2 任务状态机

```
        submit
          │
          ▼
     ┌──────────┐
     │submitted │
     └────┬─────┘
          │ 调度到后台（< 1s）
          ▼
    ┌───────────┐    AI 失败     ┌────────┐
    │processing │ ─────────────> │ failed │
    └─────┬─────┘                └────────┘
          │ AI 成功
          ▼
     ┌─────────┐
     │ success │ ── TTL=10min ──> 文件清理（task_id 失效，返回 404）
     └─────────┘
```

- `submitted` 持续 < 1s（同步调度进入 processing）
- `processing` v0.1 不返回 progress（字段保留）；v0.2 由后端基于等待时长粗略估算
- 终态（success/failed）保留 10 分钟供下载，之后清理

### 4.3 蒙版对齐预处理（services/align.py）

后端在调用 AI 前执行，保证 mask 与原图像素级精确对应：

1. **尺寸对齐**：若 mask 与原图尺寸不一致，自动 resize（最近邻插值，保护二值边界），并在响应头 `X-Mask-Aligned: true` 标注
2. **二值化**：将灰度图 >127 视为 255（白），其余 0；防止涂抹边界抗锯齿影响
3. **蒙版有效性检查**：若 mask 全黑（用户没涂抹），拒绝并返回 `MASK_EMPTY`

---

## 5. 缓存与清理

### 5.1 缓存策略（services/cache.py）

| 维度 | 策略 |
|---|---|
| Key | `sha256(image_bytes) + ":" + sha256(mask_bytes)` |
| Value | task_id（指向 success 终态任务） |
| 存储 | 进程内 `dict` + `asyncio.Lock`；未来可换 Redis |
| 失效 | 文件清理时同步删除缓存条目 |
| 命中行为 | 直接复用：返回原 task_id 的 success 状态，前端无感 |

### 5.2 清理任务（core/cleanup.py）

FastAPI `lifespan` 启动时拉起 `asyncio` 后台循环，每 60s 扫描一次 `storage/`：

```python
async def cleanup_loop():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        for path in storage.iter_files():
            if path.mtime + TTL_SECONDS < now:
                path.unlink()
                cache.evict_by_file(path)
```

`TTL_SECONDS = 600`（10 分钟）。所有文件（原图、蒙版、修复结果）从 `mtime` 起算 10 分钟过期。典型场景下任务在上传后 1 分钟内完成，用户有约 9 分钟可下载修复结果。

---

## 6. 错误处理

### 6.1 异常分层

| 层 | 类型 | HTTP | code |
|---|---|---|---|
| 参数 | `InvalidImageFormat` | 400 | `INVALID_IMAGE_FORMAT` |
| 参数 | `InvalidMaskSize` | 400 | `INVALID_MASK_SIZE` |
| 参数 | `MaskEmpty` | 400 | `MASK_EMPTY` |
| 参数 | `PayloadTooLarge` | 413 | `PAYLOAD_TOO_LARGE` |
| 业务 | `TaskNotFound` | 404 | `TASK_NOT_FOUND` |
| 业务 | `ResultExpired` | 404 | `RESULT_EXPIRED` |
| 业务 | `TaskNotReady` | 400 | `TASK_NOT_READY` |
| 上游 | `AIUpstreamError` | 502 | `AI_UPSTREAM_ERROR` |
| 上游 | `AITimeout` | 504 | `AI_TIMEOUT` |
| 系统 | `InternalError`（兜底） | 500 | `INTERNAL_ERROR` |

### 6.2 统一响应

```json
{
  "error": {
    "code": "INVALID_MASK_SIZE",
    "message": "蒙版尺寸 1920x1080 与原图 1080x1920 不一致",
    "request_id": "req_8f3a2b1c"
  }
}
```

- 每个请求生成 `request_id`（`uuid4().hex[:12]`）
- 写入响应头 `X-Request-Id`
- 写入结构化日志（包含 method、path、status、duration_ms、request_id）
- 上游错误**不**向上抛 500，对前端屏蔽 AI 内部细节

### 6.3 全局 handler 位置

`app/main.py` 中注册：

```python
@app.exception_handler(BusinessError)
async def business_error_handler(request, exc): ...
@app.exception_handler(Exception)
async def fallback_handler(request, exc): ...
```

---

## 7. 联调配套

### 7.1 自动文档

- `GET /docs` —— Swagger UI（前端同学可直接打开看接口）
- `GET /openapi.json` —— OpenAPI 3.x schema（可用 codegen 生成 Android Retrofit interface）

### 7.2 CORS

联调期：`Access-Control-Allow-Origin: *`
生产期：仅允许 Android 包名对应 origin（待定）

### 7.3 启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

环境变量（`.env`）：

```
STORAGE_DIR=./storage
TTL_SECONDS=600
MAX_IMAGE_BYTES=10485760
MAX_IMAGE_DIM=2048
AI_BASE_URL=<待 AI 同学提供>
AI_TIMEOUT_SECONDS=60
LOG_LEVEL=INFO
```

### 7.4 AI 模型接口契约（待对齐）

```
POST {AI_BASE_URL}/inpaint
  Content-Type: multipart/form-data
  body:
    - image: 原图（已对齐）
    - mask: 蒙版（已对齐+二值化）
    - prompt: string (可选)
  response: image/png binary
  timeout: 60s

错误（AI 端返回）：
  4xx 参数错误
  5xx 服务异常

后端兜底：若 AI 调用超过 `AI_TIMEOUT_SECONDS`（默认 60s）未响应，后端标记任务 `failed` 并返回 `AI_TIMEOUT`（HTTP 504 给前端的轮询接口）。
```

具体 base URL、鉴权 header 由 AI 模型同学确认后写入 `core/config.py`。

---

## 8. 测试策略

| 层 | 工具 | 覆盖 |
|---|---|---|
| 单元 | pytest | align（resize/二值化）、cache（命中/失效/并发）、task_manager 状态机 |
| 接口 | httpx AsyncClient + FastAPI TestClient | 正常流、参数错误、超限、AI mock 失败 |
| 集成 | docker-compose 起本地 AI stub | 端到端：上传 → 轮询 → 下载 → 清理 |
| 契约 | schemathesis（基于 OpenAPI） | 与前端字段对齐自动校验 |

### 8.1 联调通过标准（Minimum Viable）

- [ ] 上传一张测试图 + 涂抹蒙版，返回 task_id
- [ ] 轮询 GET /tasks/{id} 拿到 status=success 和 result_url
- [ ] GET /results/{id}.png 下载到修复图
- [ ] AI 模型同学提供 stub 接口（输入 → 输出固定 PNG）即可联调
- [ ] T+10min 后 GET /results/{id}.png 返回 404 RESULT_EXPIRED

---

## 9. 验收清单

- [ ] 4 个端点全部实现并通过 OpenAPI schema 校验
- [ ] 蒙版自动 resize + 二值化逻辑单元测试覆盖
- [ ] 同图同蒙版第二次提交命中缓存，AI 调用次数 = 0
- [ ] T+10min 文件自动清理，原图/蒙版/结果均不存在
- [ ] 统一错误响应格式（code/message/request_id）
- [ ] GET /health 返回 ai_reachable 字段
- [ ] 日志包含 request_id、duration_ms、status
- [ ] Swagger UI 可访问（`/docs`）
- [ ] 与 AI 模型同学完成接口契约对齐并写入 config

---

## 10. 范围之外（明确不做）

- 用户系统、登录、JWT、API Key 鉴权（联调期不要求）
- 数据库持久化（仅进程内 + 文件）
- Redis / Celery 等分布式组件
- CDN / 对象存储（仅本地文件）
- 批量提交、任务取消接口（YAGNI）
- 限流与配额（仅做最基础保护）
- Android 端实现（前端同学负责）
- AI 模型选型与调参（AI 同学负责）

---

## 11. 后续待办

1. 与 AI 模型同学对齐 `/inpaint` 接口契约（base URL、鉴权、错误码）
2. 与前端同学对齐字段命名（task_id、result_url 等命名是否一致）
3. 联调期结束后再决定是否引入鉴权（API Key）
4. 部署方案（Docker / 裸机）由组长统一决定
