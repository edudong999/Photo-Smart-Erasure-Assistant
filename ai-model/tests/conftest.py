import io
import sys
from pathlib import Path

import pytest
from PIL import Image

MODEL_DIR = Path(__file__).resolve().parents[1]
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))


def make_png(size=(64, 48), color="white", mode="RGB") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def image_png() -> bytes:
    return make_png(color="blue")


@pytest.fixture
def mask_png() -> bytes:
    return make_png(color="white", mode="L")
