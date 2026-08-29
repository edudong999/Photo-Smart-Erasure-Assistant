# Android 端开发指南

## 你的职责

照片智能擦除小助手的 Android 移动端：
- 相机/相册调用
- 画笔涂抹交互（可调粗细、撤销/重做）
- Loading 状态展示
- Before/After 滑动对比
- 本地历史记录管理
- 修复图片保存到本地相册

参考原始需求：`../项目5.pdf` §3 核心功能 [1][3]。

## 技术选型

- **首选**：原生 Android（Kotlin/Java）
- 备选：Flutter、微信小程序
- 当前项目计划用 Android 原生

## 与后端的接口

**接口契约**：`../docs/superpowers/specs/2026-08-25-photo-eraser-api-design.md`

需要调用 4 个端点：

| 时机 | 端点 | 说明 |
|---|---|---|
| 启动时探活 | `GET /api/v1/health` | 返回 `{"status":"ok","ai_reachable":true}` |
| 用户涂抹完成 | `POST /api/v1/inpaint` | multipart 上传 image + mask + prompt?，拿到 task_id |
| 轮询进度 | `GET /api/v1/tasks/{task_id}` | 间隔 1-2s 轮询 status |
| status=success | `GET {result_url}` | 下载 PNG 二进制 |

详细字段、错误码、状态机见 spec §3。

## 蒙版生成

用户在前端画笔涂抹时，生成与原图**同尺寸的灰度 PNG**：
- 涂抹区域 = 白色（255）
- 未涂抹 = 黑色（0）
- 直接传给后端，后端会自动对齐/二值化

## 启动联调

```bash
# 1. 后端先起
cd ../backend
.venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Android 端把 BASE_URL 指向后端
#    - 模拟器：使用 http://10.0.2.2:8000 访问宿主机
#    - 真机：使用后端机器的局域网 IP
```

后端 Swagger UI 提供完整接口示例：`http://localhost:8000/docs`

## 关键约束

- 图片大小：≤10MB，长边 ≤2048px
- 多任务：每次涂抹后提交一个新任务，结果可滑动对比
- 离线体验：本地历史记录需缓存原图与 task_id 关联
- API 密钥：**前端不持有任何密钥**

## 文件组织建议

```
android/
├── app/src/main/
│   ├── java/com/example/photoeraser/
│   │   ├── MainActivity.kt          # 主入口
│   │   ├── ui/
│   │   │   ├── BrushView.kt         # 画笔涂抹组件
│   │   │   └── CompareView.kt       # Before/After 滑动对比
│   │   ├── data/
│   │   │   ├── api/                 # Retrofit / OkHttp 客户端
│   │   │   └── local/               # Room 本地历史
│   │   └── viewmodel/
│   └── AndroidManifest.xml
├── build.gradle.kts
└── README.md  ← 你正在看
```

## 当前状态

⚠️ 待开发。建议先用 Retrofit + OkHttp 调通 4 个端点，再做 UI 打磨。