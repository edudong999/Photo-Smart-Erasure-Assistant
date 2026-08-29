"""真实样本冒烟：用 data/ 下的真实图片测试 QwenInpainter 完整链路

- 原图：data/1787916956111.jpg（海边游客，4K）
- 蒙版：data/Gemini_Generated_Image_r9fdx8r9fdx8r9fd_4096x3072.jpg（白色人形蒙版）
- 目标：擦除站在中间的男孩，背景露出沙滩 / 海面 / 远处游客 / 天空

用法：
    cd model
    python scripts/smoke_qwen_real.py

前置：
    1. .env 中 DASHSCOPE_API_KEY 已配置
    2. utils/image_io.to_data_uri 已修复（设 Content-Type、用 mine.extension）
"""
import asyncio
import io
import sys
import time
from pathlib import Path

# 让脚本能 import 到 model 包
MODEL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODEL_DIR))

from PIL import Image

from config import get_settings
from services.qwen_inpainter import QwenInpainter

DATA_DIR = MODEL_DIR.parent / "data"
IMAGE_PATH = DATA_DIR / "1787916956111.jpg"
MASK_PATH = DATA_DIR / "Gemini_Generated_Image_r9fdx8r9fdx8r9fd_4096x3072.jpg"

OUTPUT_DIR = MODEL_DIR / "scripts" / "outputs"
OUTPUT_PATH = OUTPUT_DIR / "qwen_real_result.png"


def _png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def main() -> int:
    if not IMAGE_PATH.exists():
        print(f"找不到原图: {IMAGE_PATH}")
        return 1
    if not MASK_PATH.exists():
        print(f"找不到蒙版: {MASK_PATH}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    if not settings.dashscope_api_key:
        print("未配置 DASHSCOPE_API_KEY，无法调用云端 Qwen")
        return 2

    image = Image.open(IMAGE_PATH).convert("RGB")
    mask = Image.open(MASK_PATH).convert("L")
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.NEAREST)

    image_bytes = _png_bytes(image)
    mask_bytes = _png_bytes(mask)

    print(f"原图: {IMAGE_PATH.name}  size={image.size}  {len(image_bytes)/1024/1024:.2f}MB")
    print(f"蒙版: {MASK_PATH.name}  size={mask.size}")

    qwen = QwenInpainter(
        api_key=settings.dashscope_api_key,
        model=settings.qwen_model or "qwen-image-edit",
        base_url=settings.dashscope_base_url,
        timeout_seconds=settings.qwen_timeout_seconds,
    )

    # 中文描述足够具体：男孩 + 衣着 + 场景，Qwen 才能精准合成背景
    user_prompt = (
        "移除蒙版中站在海边的男孩（穿灰色 BUSY 3 T 恤、戴黑框眼镜、背紫色书包），"
        "露出他身后的沙滩、海面、远处公园凉亭和零散游客，云层和天空保持原样"
    )

    print(f"Prompt: {user_prompt}")
    print(f"Model:  {qwen._model}")
    print("调用 DashScope （OSS 上传 + 云端推理，预计 10~60s）")

    t0 = time.monotonic()
    try:
        result_bytes = await qwen.inpaint(image_bytes, mask_bytes, user_prompt)
    except Exception as e:
        print(f"调用失败: {type(e).__name__}: {e}")
        return 3
    elapsed = time.monotonic() - t0

    OUTPUT_PATH.write_bytes(result_bytes)
    result_img = Image.open(io.BytesIO(result_bytes))
    print(f"完成: {OUTPUT_PATH}  size={result_img.size}  {len(result_bytes)/1024:.1f}KB  耗时 {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
