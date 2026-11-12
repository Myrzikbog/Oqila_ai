"""
imaging.py — final touches for marketplace pictures.

Uzum requirements (seller manual, checked November 2026): a plain, unobtrusive background, the front side of the
product visible, a file of at most 5 MB, at least 750x1000 px (3:4). Cards are delivered at 1080x1440 JPEG.
"""
from __future__ import annotations

import base64
import io
from typing import Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

CARD_SIZE: Tuple[int, int] = (1080, 1440)
MAX_BYTES = 5 * 1024 * 1024

# Decompression bombs: a 10000x10000 PNG is a few kilobytes on the wire and 300 MB once decoded.
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
UPLOAD_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ImageRejected(ValueError):
    """An uploaded file that is not an acceptable picture; `reason` is "format", "too_large" or "broken"."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def open_checked(raw: bytes) -> Image.Image:
    """Open an untrusted picture. The header is validated (real format, pixel count) BEFORE any pixel is decoded;
    the type comes from the file's magic bytes, never from the client's Content-Type."""
    try:
        img = Image.open(io.BytesIO(raw))  # lazy: reads the header only
    except Image.DecompressionBombError as exc:
        raise ImageRejected("too_large") from exc
    except Exception as exc:
        raise ImageRejected("format") from exc
    if img.format not in UPLOAD_FORMATS:
        raise ImageRejected("format")
    if img.width * img.height > MAX_PIXELS:
        raise ImageRejected("too_large")
    try:
        img.load()
    except Exception as exc:
        raise ImageRejected("broken") from exc
    return img


def _whiten_background(img: Image.Image) -> Image.Image:
    """Turn the almost-white, neutral background pure white (the model leaves a faint grey/blue tint).

    Only very bright, nearly colourless pixels that are connected to the edge of the frame are touched, i.e. the
    background itself: shadows, the product's own colours and even the light body of a white product stay as they are.
    """
    r, g, b = img.split()
    lowest = ImageChops.darker(ImageChops.darker(r, g), b)
    highest = ImageChops.lighter(ImageChops.lighter(r, g), b)
    spread = ImageChops.subtract(highest, lowest)
    bright = lowest.point(lambda v: 0 if v < 228 else min(255, int((v - 228) * 255 / 13)))
    neutral = spread.point(lambda v: 255 if v <= 14 else 0)
    candidate = ImageChops.multiply(bright, neutral)

    # keep only the region connected to the border (flood fill on a small copy keeps this fast)
    small = candidate.resize((max(1, img.width // 4), max(1, img.height // 4)), Image.BILINEAR).point(lambda v: 255 if v > 128 else 0)
    w, h = small.size
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)):
        if small.getpixel(seed) == 255:
            ImageDraw.floodfill(small, seed, 128)
    border = small.point(lambda v: 255 if v == 128 else 0).resize(img.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
    mask = ImageChops.multiply(candidate, border)
    return Image.composite(Image.new("RGB", img.size, (255, 255, 255)), img, mask)


def finalize_card(raw: bytes, whiten: bool = False, size: Tuple[int, int] = CARD_SIZE) -> bytes:
    """Model output (PNG/JPEG bytes) -> 1080x1440 JPEG under 5 MB; `whiten` makes a neutral background pure white."""
    img = Image.open(io.BytesIO(raw))
    if img.width * img.height > MAX_PIXELS:
        raise ValueError("image too large")
    img = ImageOps.exif_transpose(img).convert("RGB")
    if img.size != size:
        img = ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.5))
    if whiten:
        img = _whiten_background(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    for quality in (93, 88, 82, 75, 68):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, subsampling=0 if quality > 85 else 2)
        if buf.tell() <= MAX_BYTES:
            break
    return buf.getvalue()


def to_data_url(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


def corner_whiteness(raw: bytes) -> int:
    """Lowest channel value over the four corners (255 = pure white): a quick 'is the background clean' check."""
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    box = max(4, min(w, h) // 25)
    values = []
    for x, y in ((0, 0), (w - box, 0), (0, h - box), (w - box, h - box)):
        values.append(min(img.crop((x, y, x + box, y + box)).resize((1, 1), Image.BOX).getpixel((0, 0))))
    return min(values)


def normalize_logo(raw: bytes, max_side: int = 512) -> bytes:
    """Validate an uploaded logo and return it as a small PNG (raises ValueError if it is not an image)."""
    img = ImageOps.exif_transpose(open_checked(raw)).convert("RGBA")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def normalize_source(raw: bytes, max_side: int = 2048) -> bytes:
    """Validate the seller's photo and return a compact JPEG (raises ValueError if it is not an image).
    The same JPEG is stored and sent to the AI: no raw client bytes go any further."""
    img = ImageOps.exif_transpose(open_checked(raw)).convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()
