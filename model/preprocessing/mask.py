import numpy as np
from PIL import Image, ImageFilter


def binarize(mask: Image.Image, threshold: int = 127) -> Image.Image:
    """转灰度并二值化：>threshold 视为待擦除区（255），其余为保留区（0）"""
    gray = mask.convert("L")
    return gray.point(lambda p: 255 if p > threshold else 0)


def dilate(mask: Image.Image, px: int) -> Image.Image:
    """用 MaxFilter 对白色区域做形态学膨胀，改善擦除边缘残留"""
    if px <= 0:
        return mask
    size = px * 2 + 1
    return mask.filter(ImageFilter.MaxFilter(size))


def prepare_mask(
    mask: Image.Image, target_size: tuple[int, int], dilate_px: int = 0
) -> Image.Image:
    """二值化 + 对齐到原图尺寸 + 膨胀，输出 L 模式 0/255 蒙版"""
    mask = binarize(mask)
    if mask.size != target_size:
        mask = mask.resize(target_size, Image.NEAREST)
    return dilate(mask, dilate_px)


def pad_to_modulo(arr: np.ndarray, mod: int) -> np.ndarray:
    """将 CHW 数组右/下 reflect 填充到 mod 的整数倍"""
    _, h, w = arr.shape
    pad_h = (mod - h % mod) % mod
    pad_w = (mod - w % mod) % mod
    if pad_h == 0 and pad_w == 0:
        return arr
    return np.pad(arr, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")
