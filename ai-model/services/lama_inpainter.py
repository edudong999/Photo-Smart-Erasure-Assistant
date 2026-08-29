import asyncio
import threading
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from core.base_inpainter import BaseInpainter
from core.exceptions import InpaintFailed, ModelNotReady
from preprocessing.mask import pad_to_modulo, prepare_mask
from utils.image_io import bytes_to_image, image_to_png_bytes
from utils.logger import get_logger

logger = get_logger(__name__)

PAD_MOD = 8


class LamaInpainter(BaseInpainter):
    """端侧修复器：onnxruntime + big-lama，无 prompt 时使用"""

    name = "lama-onnx"

    def __init__(self, onnx_path: Path, mask_dilate_px: int = 5):
        self._onnx_path = Path(onnx_path)
        self._mask_dilate_px = mask_dilate_px
        self._session = None
        self._lock = threading.Lock()

    def is_ready(self) -> bool:
        return self._session is not None or self._onnx_path.exists()

    def _get_session(self):
        if self._session is None:
            with self._lock:
                if self._session is None:
                    if not self._onnx_path.exists():
                        raise ModelNotReady(
                            f"本地 LaMa 权重不存在: {self._onnx_path}，"
                            "请先运行 python scripts/download_weights.py"
                        )
                    import onnxruntime as ort

                    logger.info("加载 LaMa ONNX 权重: %s", self._onnx_path)
                    self._session = ort.InferenceSession(
                        str(self._onnx_path), providers=["CPUExecutionProvider"]
                    )
        return self._session

    async def inpaint(
        self, image_bytes: bytes, mask_bytes: bytes, prompt: Optional[str] = None
    ) -> bytes:
        return await asyncio.to_thread(self._inpaint_sync, image_bytes, mask_bytes)

    @staticmethod
    def _fixed_input_hw(session) -> Optional[tuple[int, int]]:
        """若模型为固定输入尺寸（如 512x512）返回 (H, W)，动态尺寸返回 None"""
        shape = session.get_inputs()[0].shape  # 如 [1, 3, 512, 512] 或含动态维
        h, w = shape[2], shape[3]
        if isinstance(h, int) and isinstance(w, int):
            return h, w
        return None

    def _inpaint_sync(self, image_bytes: bytes, mask_bytes: bytes) -> bytes:
        session = self._get_session()

        img = bytes_to_image(image_bytes).convert("RGB")
        mask = prepare_mask(bytes_to_image(mask_bytes), img.size, self._mask_dilate_px)

        # 固定输入尺寸的导出（如 Carve lama_fp32 的 512x512）需缩放到模型尺寸推理；
        # 动态尺寸导出则 pad 到 8 的整数倍
        fixed_hw = self._fixed_input_hw(session)
        if fixed_hw:
            infer_img = img.resize((fixed_hw[1], fixed_hw[0]), Image.LANCZOS)
            infer_mask = mask.resize((fixed_hw[1], fixed_hw[0]), Image.NEAREST)
        else:
            infer_img, infer_mask = img, mask

        img_np = np.asarray(infer_img, dtype=np.float32).transpose(2, 0, 1) / 255.0
        mask_np = (np.asarray(infer_mask, dtype=np.float32)[None, ...] > 127).astype(
            np.float32
        )

        if not fixed_hw:
            img_np = pad_to_modulo(img_np, PAD_MOD)
            mask_np = pad_to_modulo(mask_np, PAD_MOD)

        # 按输入声明顺序映射 image / mask，兼容不同导出的输入名
        input_names = [i.name for i in session.get_inputs()]
        feed = {input_names[0]: img_np[None], input_names[1]: mask_np[None]}
        try:
            output = session.run(None, feed)[0][0]  # CHW
        except Exception as e:
            raise InpaintFailed(f"LaMa 推理失败: {e}")

        # 部分导出输出为 0~1，统一换算到 0~255
        if float(output.max()) <= 1.5:
            output = output * 255.0

        result = np.clip(output, 0, 255).astype(np.uint8).transpose(1, 2, 0)
        if fixed_hw:
            result = np.asarray(
                Image.fromarray(result).resize(img.size, Image.LANCZOS)
            )
        else:
            result = result[: img.height, : img.width]

        # 蒙版外区域回贴原图像素，保证未擦除区域零损失
        orig_np = np.asarray(img, dtype=np.uint8)
        mask_bool = (np.asarray(mask) > 127)[..., None]
        result = np.where(mask_bool, result, orig_np)

        return image_to_png_bytes(Image.fromarray(result))
