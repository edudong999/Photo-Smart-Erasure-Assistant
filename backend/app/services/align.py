from PIL import Image
from app.core.exceptions import MaskEmpty


THRESHOLD = 127


def resize_image_if_oversize(image: Image.Image, max_dim: int) -> tuple[Image.Image, bool]:
    if max(image.size) <= max_dim:
        return image, False
    ratio = max_dim / max(image.size)
    new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
    return image.resize(new_size, Image.LANCZOS), True


def align_mask(image: Image.Image, mask: Image.Image) -> tuple[Image.Image, bool]:
    was_resized = False
    if mask.mode != "L":
        mask = mask.convert("L")

    if mask.size != image.size:
        mask = mask.resize(image.size, Image.NEAREST)
        was_resized = True

    mask = mask.point(lambda p: 255 if p > THRESHOLD else 0)

    if mask.getextrema() == (0, 0):
        raise MaskEmpty("蒙版全黑，用户未涂抹任何区域")

    return mask, was_resized