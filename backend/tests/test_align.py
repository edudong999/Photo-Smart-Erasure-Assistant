import io
import pytest
from PIL import Image
from app.services.align import align_mask, resize_image_if_oversize
from app.core.exceptions import MaskEmpty


def _img(mode, size, color):
    return Image.new(mode, size, color)


def test_align_same_size_passes_through():
    orig = _img("RGB", (100, 80), "white")
    mask = _img("L", (100, 80), 128)
    out, was_resized = align_mask(orig, mask)
    assert out.size == (100, 80)
    assert was_resized is False


def test_align_resizes_mask_to_image_dimensions():
    orig = _img("RGB", (200, 100), "white")
    mask = _img("L", (100, 50), 128)
    out, was_resized = align_mask(orig, mask)
    assert out.size == (200, 100)
    assert was_resized is True


def test_align_binarizes_above_threshold_to_white():
    orig = _img("RGB", (10, 10), "white")
    mask = _img("L", (10, 10), 100)
    mask.putpixel((5, 5), 200)
    out, was_resized = align_mask(orig, mask)
    assert out.getpixel((0, 0)) == 0
    assert out.getpixel((5, 5)) == 255


def test_align_empty_mask_raises():
    orig = _img("RGB", (10, 10), "white")
    mask = _img("L", (10, 10), 0)
    with pytest.raises(MaskEmpty):
        align_mask(orig, mask)


def test_align_preserves_binarization_after_resize():
    orig = _img("RGB", (200, 100), "white")
    mask = _img("L", (100, 50), 255)
    out, was_resized = align_mask(orig, mask)
    assert was_resized is True
    assert all(out.getpixel((x, y)) == 255 for x in range(0, 200, 50) for y in range(0, 100, 25))


def test_align_converts_rgba_mask_to_grayscale():
    orig = _img("RGB", (10, 10), "white")
    mask = _img("LA", (10, 10), (200, 255))
    out, was_resized = align_mask(orig, mask)
    assert out.mode == "L"
    assert was_resized is False


def test_resize_image_if_oversize_passes_through_when_within_limit():
    img = _img("RGB", (1000, 1000), "white")
    out, was_resized = resize_image_if_oversize(img, 2048)
    assert out.size == (1000, 1000)
    assert was_resized is False


def test_resize_image_if_oversize_shrinks_oversized():
    img = _img("RGB", (4000, 3000), "white")
    out, was_resized = resize_image_if_oversize(img, 2048)
    assert max(out.size) == 2048
    assert was_resized is True
    assert out.size[0] / out.size[1] == pytest.approx(4000 / 3000, rel=0.01)


def test_resize_image_if_oversize_handles_portrait():
    img = _img("RGB", (1500, 3000), "white")
    out, was_resized = resize_image_if_oversize(img, 2048)
    assert max(out.size) == 2048
    assert was_resized is True
    assert out.size[1] == 2048