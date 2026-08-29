import io

import numpy as np
from PIL import Image, ImageDraw

from services.lama_inpainter import LamaInpainter


class FakeInput:
    def __init__(self, name, shape):
        self.name = name
        self.shape = shape


class FakeSession:
    """假 ONNX session：修复区域输出灰色(128)，其余回显输入图"""

    def __init__(self, h="H", w="W"):
        self._inputs = [
            FakeInput("image", [1, 3, h, w]),
            FakeInput("mask", [1, 1, h, w]),
        ]

    def get_inputs(self):
        return self._inputs

    def run(self, _, feed):
        img = feed["image"][0]  # CHW, 0~1
        mask = feed["mask"][0]  # 1HW, 0/1
        out = img * (1 - mask) + 0.5 * mask
        return [out[None] * 255.0]


def _png_pair():
    img = Image.new("RGB", (100, 80), (200, 40, 40))
    mask = Image.new("L", (100, 80), 0)
    ImageDraw.Draw(mask).rectangle([40, 30, 60, 50], fill=255)

    def png(im):
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()

    return png(img), png(mask)


def _run_with_session(session):
    lama = LamaInpainter(onnx_path="weights/__unused__.onnx", mask_dilate_px=0)
    lama._session = session
    image_bytes, mask_bytes = _png_pair()
    result_bytes = lama._inpaint_sync(image_bytes, mask_bytes)
    return np.asarray(Image.open(io.BytesIO(result_bytes)).convert("RGB"))


def test_fixed_input_hw_detection():
    assert LamaInpainter._fixed_input_hw(FakeSession(512, 512)) == (512, 512)
    assert LamaInpainter._fixed_input_hw(FakeSession("H", "W")) is None


def test_dynamic_session_inpaints_masked_region():
    result = _run_with_session(FakeSession("H", "W"))
    assert result.shape == (80, 100, 3)
    # 蒙版内被修复为灰色
    assert abs(int(result[40, 50, 0]) - 128) <= 2
    # 蒙版外保持原图
    assert tuple(result[0, 0]) == (200, 40, 40)


def test_fixed_512_session_resizes_and_restores_original_size():
    result = _run_with_session(FakeSession(512, 512))
    assert result.shape == (80, 100, 3)
    assert abs(int(result[40, 50, 0]) - 128) <= 8  # 缩放往返有轻微插值误差
    assert tuple(result[0, 0]) == (200, 40, 40)
