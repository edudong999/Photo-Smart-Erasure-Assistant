# AI 模型推理服务（model）

照片智能擦除小助手的 AI 推理后端：对接专用图像修复 API（LaMa / DashScope Qwen），按 `prompt` 是否为空路由到端侧或云端模型。

> ⚠️ **仓库不含模型权重与 `.env` 环境变量**，首次启动需本地准备：
> 1. `weights/big-lama.onnx`（约 200MB，本地 LaMa 权重，见下方下载说明）
> 2. `.env`（DASHSCOPE_API_KEY 等密钥，参考 `.env.example`）

---

## 目录结构

```
model/
├── main.py                 # FastAPI 入口，提供 POST /inpaint、GET /health
├── config.py               # pydantic-settings 配置（读取 .env）
├── requirements.txt        # Python 依赖
├── .gitignore              # 排除 __pycache__ / .env / weights/*.onnx
│
├── core/                   # 抽象与异常
│   ├── base_inpainter.py   # BaseInpainter 抽象基类
│   └── exceptions.py       # ModelNotReady / UpstreamError / InvalidInput 等
│
├── preprocessing/          # 蒙版预处理
│   └── mask.py             # 蒙版对齐 / 膨胀 / 二值化
│
├── prompts/                # 场景化 Prompt 模板
│   └── templates.py        # build_erase_prompt(user_prompt) → 完整擦除指令
│
├── services/               # 推理器实现
│   ├── dispatcher.py       # InpaintDispatcher：根据 prompt 是否为空路由
│   ├── lama_inpainter.py   # 端侧 ONNX Runtime + LaMa，无 prompt 时使用
│   └── qwen_inpainter.py   # 云端 DashScope qwen-image-edit，带 prompt 时使用
│
├── utils/
│   ├── image_io.py         # bytes ↔ PIL.Image，OSS 上传（magic bytes 格式探测）
│   └── logger.py           # 日志初始化
│
└── weights/                # ⚠️ 需本地准备（仅占位 .gitkeep 入库）
    ├── .gitkeep
    └── big-lama.onnx       # ← 下载放置此处
```

---

## API 契约

后端（`backend/`）通过 HTTP 调用本服务，约定如下：

### `POST /inpaint`

**请求**：`multipart/form-data`

| 字段 | 类型 | 说明 |
|---|---|---|
| `image` | file | 原图（PNG/JPEG，二进制流） |
| `mask` | file | 蒙版（PNG 灰度，白=待修复，黑=保留；尺寸已对齐） |
| `prompt` | string（可选） | 场景提示，如 `"remove person"`。**空字符串或缺省 → 走本地 LaMa** |

**响应**：`200 OK`，`Content-Type: image/png`，二进制 PNG 字节流

**错误码**：

| 状态码 | 触发条件 | 对应异常 |
|---|---|---|
| 400 | 原图/蒙版格式损坏、尺寸不匹配 | `InvalidInput` |
| 500 | ONNX 推理失败 | `InpaintFailed` |
| 502 | DashScope 上游失败 / OSS 下载失败 | `UpstreamError` |
| 503 | 未配置 API Key 或本地权重缺失 | `ModelNotReady` |

### `GET /health`

**响应**：
```json
{
  "status": "ok",                  // ok | degraded
  "local_model_loaded": true,      // LaMa 权重是否加载
  "cloud_configured": true         // DASHSCOPE_API_KEY 是否配置
}
```

---

## 路由策略

```
InpaintDispatcher.inpaint(image, mask, prompt)
  ├─ prompt 非空 → QwenInpainter（云端 DashScope，效果好但贵）
  └─ prompt 空   → LamaInpainter（端侧 ONNX，离线可用，延迟低）
```

实现见 `services/dispatcher.py::InpaintDispatcher.select()`。

---

## 环境变量（`.env`）

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `HOST` | 否 | `0.0.0.0` | 服务监听地址 |
| `PORT` | 否 | `8001` | 服务端口（与后端 8000 错开） |
| `LOG_LEVEL` | 否 | `INFO` | |
| `DASHSCOPE_API_KEY` | 云端模式必填 | 空 | DashScope 控制台申请 |
| `DASHSCOPE_BASE_URL` | 否 | 空 | 自定义网关 |
| `QWEN_MODEL` | 否 | `qwen-image-edit` | 可选 `qwen-image-3.0-pro` |
| `QWEN_TIMEOUT_SECONDS` | 否 | `50` | DashScope 调用超时 |
| `OSS_ACCESS_KEY_ID` | OSS 上传必填 | 空 | 阿里云 OSS |
| `OSS_ACCESS_KEY_SECRET` | OSS 上传必填 | 空 | |
| `OSS_ENDPOINT` | OSS 上传必填 | 空 | 如 `oss-cn-beijing.aliyuncs.com` |
| `OSS_BUCKET_NAME` | OSS 上传必填 | 空 | |
| `LAMA_ONNX_PATH` | 否 | `weights/big-lama.onnx` | 本地 LaMa 权重路径 |
| `MASK_DILATE_PX` | 否 | `5` | 蒙版边缘膨胀像素 |

---

## 本地启动

```bash
cd model
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. 准备权重（首次必须）
python scripts/download_weights.py     # 下载 big-lama.onnx 到 weights/
# 或手动从 https://github.com/advimman/lama/releases 下载放到 weights/

# 2. 配置 .env（参考 .env.example）

# 3. 启动
python main.py
# 或：uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

启动后访问 `http://127.0.0.1:8001/health` 应返回 `status: ok`。

---

## 后端联调

后端默认 `AI_CLIENT_MODE=mock`（返回固定白色占位图）。切到本服务：

```bash
# 后端 .env
AI_CLIENT_MODE=http
AI_BASE_URL=http://<AI 服务地址>:8001
```

后端重启后，`POST /api/v1/inpaint` 的请求会代理到本服务的 `/inpaint`。

---

## 缺失项说明

| 项 | 来源 | 是否进仓库 |
|---|---|---|
| `weights/big-lama.onnx`（~200MB） | [LaMa 官方 release](https://github.com/advimman/lama) 或运行 `scripts/download_weights.py` | ❌ 仓库仅留 `.gitkeep` 占位 |
| `.env` | 自行从 `.env.example` 复制并填入真实密钥 | ❌ `.gitignore` 已排除 |

---

## 与后端 / 前端的协作

- **后端**：`POST /inpaint` 的请求代理 + 任务队列 + 结果缓存
- **前端**：上传原图 + 用户涂抹蒙版，可选输入 prompt，提交后轮询任务状态
- **蒙版约定**：白=擦除、黑=保留，已二值化、已与原图对齐，无需本服务再做处理

参考原始需求：见仓库根 `项目5.pdf` §3 核心功能 [2]、§4 技术选型 [3]。
