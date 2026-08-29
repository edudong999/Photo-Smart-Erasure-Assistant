"""端到端冒烟：backend(real 模式, :8000) -> model(:8001) 本地 LaMa 链路

用法：先分别启动 model 服务与 backend 服务，再运行本脚本。
"""

import io
import sys
import time

import httpx
import numpy as np
from PIL import Image, ImageDraw

BACKEND = "http://127.0.0.1:8000/api/v1"


def make_inputs():
    w, h = 320, 240
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[..., 1] = np.linspace(80, 200, w, dtype=np.uint8)[None, :]
    img = Image.fromarray(arr)
    ImageDraw.Draw(img).rectangle([130, 90, 190, 150], fill=(220, 30, 30))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle([130, 90, 190, 150], fill=255)

    def png(im):
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()

    return png(img), png(mask)


def main() -> int:
    image_bytes, mask_bytes = make_inputs()

    submit = httpx.post(
        f"{BACKEND}/inpaint",
        files={
            "image": ("image.png", image_bytes, "image/png"),
            "mask": ("mask.png", mask_bytes, "image/png"),
        },
        timeout=30,
    )
    print("submit:", submit.status_code, submit.json())
    assert submit.status_code == 202, submit.text
    task_id = submit.json()["task_id"]

    status = None
    for _ in range(60):
        task = httpx.get(f"{BACKEND}/tasks/{task_id}", timeout=10).json()
        status = task["status"]
        if status in ("success", "failed"):
            break
        time.sleep(1)
    print("task:", task)
    assert status == "success", f"任务未成功: {task}"

    result = httpx.get(f"{BACKEND}/results/{task_id}.png", timeout=30)
    assert result.status_code == 200, result.text
    img = Image.open(io.BytesIO(result.content)).convert("RGB")
    assert img.size == (320, 240)

    r = np.asarray(img)
    mean_red = r[110:130, 150:170, 0].mean()
    print(f"擦除区域红色均值: {mean_red:.1f}（原为 220）")
    assert mean_red < 120, "干扰物未被擦除"

    print("E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
