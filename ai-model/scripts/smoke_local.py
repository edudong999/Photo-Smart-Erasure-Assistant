"""本地 LaMa 链路冒烟：构造带干扰物的测试图 + 蒙版，请求 /inpaint 验证结果"""

import io
import sys

import httpx
import numpy as np
from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8001"


def make_inputs():
    # 320x240 绿色渐变背景 + 中央红色方块（待擦除干扰物）
    w, h = 320, 240
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[..., 1] = np.linspace(80, 200, w, dtype=np.uint8)[None, :]
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    draw.rectangle([130, 90, 190, 150], fill=(220, 30, 30))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle([130, 90, 190, 150], fill=255)

    def png(im):
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()

    return png(img), png(mask)


def main() -> int:
    health = httpx.get(f"{BASE}/health", timeout=10).json()
    print("health:", health)
    assert health["local_model_loaded"], "本地权重未就绪"

    image_bytes, mask_bytes = make_inputs()
    resp = httpx.post(
        f"{BASE}/inpaint",
        files={
            "image": ("image.png", image_bytes, "image/png"),
            "mask": ("mask.png", mask_bytes, "image/png"),
        },
        timeout=300,
    )
    print("status:", resp.status_code, "content-type:", resp.headers.get("content-type"))
    assert resp.status_code == 200, resp.text

    result = Image.open(io.BytesIO(resp.content))
    print("result size:", result.size, "mode:", result.mode)
    assert result.size == (320, 240)

    # 验证红色方块已被擦除：蒙版中心区域红色通道应显著下降
    r = np.asarray(result.convert("RGB"))
    center = r[110:130, 150:170]
    mean_red = center[..., 0].mean()
    mean_green = center[..., 1].mean()
    print(f"擦除区域均值 R={mean_red:.1f} G={mean_green:.1f}（原为 R=220 G=30）")
    assert mean_red < 120, "红色干扰物未被有效擦除"
    assert mean_green > mean_red, "擦除区域未被背景填充"

    # 验证蒙版外像素与原图一致（回贴逻辑）
    orig = np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    outside = np.array_equal(r[:50, :50], orig[:50, :50])
    print("蒙版外像素与原图一致:", outside)
    assert outside

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
