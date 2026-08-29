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

- `mock`：内置 mock client，返回固定 PNG（联调阶段使用）
- `http`：调用 `POST {AI_BASE_URL}/inpaint`，接收 multipart（image, mask, prompt），返回 image/png

## 当前状态

- v0.1: mock AI client + 完整流程
- 切换到 AI 模型同学真实接口：修改 `.env` 中 `AI_CLIENT_MODE=http` 和 `AI_BASE_URL`
