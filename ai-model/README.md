# AI 模型开发指南

## 你的职责

照片智能擦除小助手的 AI 推理服务：
- 对接专用图像修复 API（LaMa / Stable Diffusion Inpainting）
- 分场景调优 Prompt 模板库（人物擦除 / 宠物擦除 / 物体擦除）
- 测试多场景效果
- 调参方案

参考原始需求：`../项目5.pdf` §3 核心功能 [2]、§4 技术选型 [3]。

## 技术选型

| 方案 | 说明 | 适用 |
|---|---|---|
| **方案 A（优先）** | 专用图像修复 API（LaMa / SD Inpainting），端侧部署 | 离线可用，延迟低 |
| 方案 B（备选） | 豆包/千问等大模型 API，密钥后端保管 | 远程调用，效果好但贵 |

## 与后端的接口契约

**后端调用你的接口**：`POST <AI_BASE_URL>/inpaint`

```
请求：
  Content-Type: multipart/form-data
  - image: 原图（PNG，已对齐）
  - mask: 蒙版（PNG，已对齐+二值化）
  - prompt: string（可选，场景提示如 "remove person"）

响应 200：image/png 二进制流（修复后的图）
超时：60s（后端默认 AI_TIMEOUT_SECONDS）
错误：4xx 参数错误 / 5xx 服务异常
```

**蒙版约定**（重要）：
- 蒙版是灰度 PNG
- **白色（255）= 待修复区域**
- 黑色（0）= 保留区域
- 与原图同尺寸（后端已自动对齐）
- 已经二值化，不需要你再做

**Prompt 模板建议**（按 `prompt` 字段透传）：

```python
prompts = {
    "person": "remove the person, seamlessly blend with the background",
    "pet": "remove the pet, fill with natural background texture",
    "object": "remove the object, restore the original scene",
}
# prompt 为空时，使用通用 prompt："remove the masked region, blend naturally"
```

## 启动你的服务

- 端口建议：8001（与后端 8000 错开）
- 起服务后告诉后端同学 `AI_BASE_URL`，后端切 `AI_CLIENT_MODE=http`

## 后端切到你的服务的步骤

```bash
# 后端同学在 backend/.env 修改
AI_CLIENT_MODE=http
AI_BASE_URL=http://<你的地址>:8001

# 重启后端
.venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

联调验证：
```bash
# 后端的 e2e 测试会直接调你的接口
cd ../backend
.venv/Scripts/pytest tests/test_e2e.py -v
```

## 当前后端的 mock 行为（参考）

方便你调试。后端默认 `AI_CLIENT_MODE=mock`，会调用 `MockAIClient` 返回固定 PNG（100x100 白色）：

`backend/app/services/ai_client.py` 中的 `MockAIClient`

## 文件组织建议

```
ai-model/
├── lama/                          # LaMa 模型代码
│   ├── inpaint.py                 # POST /inpaint 接口入口
│   ├── model.py
│   └── ...
├── prompts/
│   └── templates.py               # 分场景 prompt 库
├── tests/
│   ├── test_person.py             # 人物擦除测试
│   ├── test_pet.py
│   └── ...
├── requirements.txt
└── README.md  ← 你正在看
```

## 当前状态

⚠️ 待开发。建议先用 LaMa（轻量、效果好）跑通最小 demo，再做 Prompt 调优。