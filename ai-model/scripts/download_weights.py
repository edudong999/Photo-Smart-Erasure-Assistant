"""下载 big-lama ONNX 权重到 model/weights/big-lama.onnx

用法（在 model/ 目录下）：
    python scripts/download_weights.py
"""

import sys
from pathlib import Path

import httpx

WEIGHT_URL = "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx"
DEST = Path(__file__).resolve().parents[1] / "weights" / "big-lama.onnx"


def main() -> int:
    if DEST.exists():
        print(f"权重已存在: {DEST}")
        return 0

    DEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEST.with_suffix(".onnx.part")
    print(f"下载 {WEIGHT_URL}\n  -> {DEST}")
    try:
        with httpx.stream(
            "GET", WEIGHT_URL, follow_redirects=True, timeout=120
        ) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            done = 0
            with open(tmp, "wb") as f:
                for chunk in resp.iter_bytes(1024 * 1024):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(
                            f"\r  {done / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MB",
                            end="",
                            flush=True,
                        )
        print()
    except httpx.HTTPError as e:
        tmp.unlink(missing_ok=True)
        print(f"下载失败: {e}", file=sys.stderr)
        return 1

    tmp.replace(DEST)
    print("下载完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
