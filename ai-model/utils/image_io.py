import io
import time
import uuid

import oss2

from PIL import Image
from config import get_settings
from core.exceptions import InvalidInput


def bytes_to_image(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise InvalidInput("无法解析图像数据，可能已损坏或格式不支持")
    return img


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _detect_image_format(data: bytes) -> tuple[str, str]:
    """读 magic bytes 检测图片格式，返回 (extension, mime)。

    不依赖 filetype 等第三方库，按 ISO/IEC 文件头规范匹配。
    失败时默认按 PNG 处理，保证 DashScope 至少能拿到一张可解析的图。
    """
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    # JPEG: FF D8 FF
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    # WebP: RIFF .... WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    # BMP: BM
    if data.startswith(b"BM"):
        return "bmp", "image/bmp"
    # GIF87a / GIF89a
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif", "image/gif"
    # TIFF (little-endian / big-endian)
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff", "image/tiff"
    return "png", "image/png"


def to_data_uri(image_bytes: bytes) -> str:
    """上传图片到 OSS，返回签名 URL。

    关键点：
    - 用 magic bytes 检测真实格式（不依赖 filetype 库）
    - 显式设 Content-Type，避免 OSS 默认 application/octet-stream
      导致 DashScope/qwen-image-edit 解析失败
    - 文件名后缀与 Content-Type 严格对齐
    """
    settings = get_settings()
    auth = oss2.Auth(settings.oss_accessKeyId, settings.oss_accessKeySecret)
    bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)

    ext, mime = _detect_image_format(image_bytes)

    date = time.strftime("%y%m%d")
    unique_id = uuid.uuid4().hex
    object_name = f"inpainting/{date}/{unique_id}.{ext}"

    headers = {"Content-Type": mime}
    bucket.put_object(object_name, image_bytes, headers=headers)

    signed_url = bucket.sign_url("GET", object_name, 1800)
    return signed_url
