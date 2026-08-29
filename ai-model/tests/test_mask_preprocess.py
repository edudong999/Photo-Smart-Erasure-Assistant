import numpy as np
from PIL import Image

from preprocessing.mask import binarize, dilate, pad_to_modulo, prepare_mask


def test_binarize_produces_only_black_and_white():
    mask = Image.new("L", (10, 10))
    mask.putpixel((0, 0), 200)
    mask.putpixel((1, 1), 50)
    result = binarize(mask)
    values = set(result.getdata())
    assert values <= {0, 255}
    assert result.getpixel((0, 0)) == 255
    assert result.getpixel((1, 1)) == 0


def test_binarize_converts_rgb_mask():
    mask = Image.new("RGB", (8, 8), "white")
    result = binarize(mask)
    assert result.mode == "L"
    assert result.getpixel((0, 0)) == 255


def test_dilate_expands_white_region():
    mask = Image.new("L", (11, 11), 0)
    mask.putpixel((5, 5), 255)
    result = dilate(mask, 2)
    assert result.getpixel((3, 3)) == 255
    assert result.getpixel((0, 0)) == 0


def test_dilate_zero_px_is_noop():
    mask = Image.new("L", (5, 5), 0)
    assert dilate(mask, 0) is mask


def test_prepare_mask_resizes_to_target():
    mask = Image.new("L", (32, 32), 255)
    result = prepare_mask(mask, (64, 48), dilate_px=0)
    assert result.size == (64, 48)
    assert result.mode == "L"


def test_pad_to_modulo_shapes():
    arr = np.zeros((3, 45, 62), dtype=np.float32)
    padded = pad_to_modulo(arr, 8)
    assert padded.shape == (3, 48, 64)

    aligned = np.zeros((1, 48, 64), dtype=np.float32)
    assert pad_to_modulo(aligned, 8) is aligned
