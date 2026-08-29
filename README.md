# 照片智能擦除小助手

> 课程项目 · 图像实例分割与修复方向 · 三人小组

## 项目简介

面向日常修图场景：用户在 Android 端手动涂抹框选多余元素（人物、宠物等），AI 自动完成目标区域擦除并补全背景纹理与光影。

完整需求见 `项目5.pdf`。

## 分工与目录结构

```
Photo Smart Erasure Assistant/
├── 项目5.pdf                                # 项目原始需求
├── docs/
│   └── superpowers/
│       ├── specs/2026-08-25-photo-eraser-api-design.md         # ✅ 后端接口设计（已完成）
│       └── plans/2026-08-25-photo-eraser-api-implementation.md # 后端实现计划
├── backend/                                 # ✅ 后端（FastAPI，已完成 v0.1）
│   └── README.md                              # 后端启动 / 联调说明
├── android/                                 # ⚠️ 移动端（Android，待开发）
│   └── README.md                            # Android 开发指南
└── model/                                   # AI 模型推理服务（FastAPI + LaMa + Qwen）
    └── README.md                            # AI 模型推理服务说明（含 API 契约、缺失项）
```

## 角色分工

| 角色 | 负责 | 当前目录 | 当前状态 |
|---|---|---|---|
| 后端 | 接口设计、蒙版对齐、异步 AI 调用、缓存去重、清理 | `backend/` | ✅ v0.1 完成（mock AI） |
| AI 模型 | LaMa/SD Inpainting 对接、Prompt 调优、多场景测试 | `model/` | ✅ v0.1 完成（端侧 LaMa + 云端 Qwen 双路由） |
| 移动端 | 相机/相册、画笔涂抹、Loading、Before/After 对比、本地历史 | `android/` | ⚠️ 待开发 |

## 联调步骤（建议顺序）

1. **后端 + AI 模型联调**：AI 同学提供 `/inpaint` 接口 → 后端切换 `AI_CLIENT_MODE=http`
2. **后端 + Android 联调**：Android 同学按 `docs/.../spec` 实现 4 个端点调用 → 端到端跑通
3. **三端联调**：完整提交 → 轮询 → 下载 → 对比 → 保存

## 接口契约位置

📄 `docs/superpowers/specs/2026-08-25-photo-eraser-api-design.md`

- 4 个端点：`POST /inpaint`、`GET /tasks/{id}`、`GET /results/{id}.png`、`GET /health`
- 字段命名：`task_id`、`result_url`、`expires_at` 已固定
- 错误码：10 种业务异常统一格式 `{error: {code, message, request_id}}`
- 限制：图像 ≤10MB / 长边 ≤2048px / 文件 TTL 10 分钟

## 启动后端（供联调）

```bash
cd backend
.venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs
```

当前为 **mock 模式**（联调阶段）。切到真实 AI：

```bash
# 在 backend/.env 中设置
AI_CLIENT_MODE=http
AI_BASE_URL=http://<AI 同学提供的地址>:<端口>
```

## 沟通

- 接口字段 / 错误码 / 状态机：以 `docs/.../spec` 为唯一权威
- 任何字段调整：先在 spec 提 PR，三方确认后再改代码