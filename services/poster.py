"""
poster.py — draws the information on a poster over a product picture.

The AI image model draws the scene (and leaves calm space for text). Everything with a meaning —
title, price, benefits, contacts, discount — is drawn here, so numbers, Cyrillic and Uzbek letters
(o', g', sh, ch) are always exact and the seller can edit them without another AI call.

Public API:
    PosterSpec.from_dict(data)     validated, length-limited text fields + layout/aspect/palette
    render_poster(spec, background=None, source=None, logo=None) -> PIL.Image
    poster_to_png(image) -> bytes
    poster_defaults(card, desired_price, lang) -> dict   (text fields prefilled from an AI card)
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from services.presets import ASPECTS, DEFAULT_ASPECT, DEFAULT_PALETTE, LAYOUTS, PALETTES

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_WEIGHTS = {"regular": "Inter-Regular.otf", "medium": "Inter-Medium.otf", "bold": "Inter-Bold.otf", "xbold": "Inter-ExtraBold.otf"}
MAX_SOURCE_SIDE = 2400

LIMITS = {"title": 90, "price": 28, "old_price": 28, "bullet": 60, "badge_text": 14, "deadline": 36,
          "contact": 48, "cta": 32, "brand_name": 32}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------
def _clean(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return text[:limit]


@dataclass
class PosterSpec:
    layout: str = "showcase"
    aspect: str = DEFAULT_ASPECT
    palette: str = DEFAULT_PALETTE
    brand_color: str = ""
    lang: str = "ru"
    title: str = ""
    price: str = ""
    old_price: str = ""
    bullets: List[str] = field(default_factory=list)
    badge_text: str = ""
    deadline: str = ""
    contact: str = ""
    cta: str = ""
    brand_name: str = ""
    show_logo: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PosterSpec":
        layout = data.get("layout") if data.get("layout") in LAYOUTS else "showcase"
        aspect = data.get("aspect") if data.get("aspect") in ASPECTS else LAYOUTS[layout]["aspect"]
        palette = data.get("palette") if (data.get("palette") in PALETTES or data.get("palette") == "custom") else DEFAULT_PALETTE
        brand_color = str(data.get("brand_color") or "")
        brand_color = brand_color if _HEX.match(brand_color) else ""
        if palette == "custom" and not brand_color:
            palette = DEFAULT_PALETTE
        bullets_raw = data.get("bullets") or []
        bullets = [_clean(b, LIMITS["bullet"]) for b in bullets_raw if _clean(b, LIMITS["bullet"])][:4]
        return cls(
            layout=layout, aspect=aspect, palette=palette, brand_color=brand_color,
            lang="uz" if data.get("lang") == "uz" else "ru",
            title=_clean(data.get("title"), LIMITS["title"]),
            price=_clean(data.get("price"), LIMITS["price"]),
            old_price=_clean(data.get("old_price"), LIMITS["old_price"]),
            bullets=bullets,
            badge_text=_clean(data.get("badge_text"), LIMITS["badge_text"]),
            deadline=_clean(data.get("deadline"), LIMITS["deadline"]),
            contact=_clean(data.get("contact"), LIMITS["contact"]),
            cta=_clean(data.get("cta"), LIMITS["cta"]),
            brand_name=_clean(data.get("brand_name"), LIMITS["brand_name"]),
            show_logo=bool(data.get("show_logo", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout": self.layout, "aspect": self.aspect, "palette": self.palette, "brand_color": self.brand_color,
            "lang": self.lang, "title": self.title, "price": self.price, "old_price": self.old_price,
            "bullets": list(self.bullets), "badge_text": self.badge_text, "deadline": self.deadline,
            "contact": self.contact, "cta": self.cta, "brand_name": self.brand_name, "show_logo": self.show_logo,
        }


# ---------------------------------------------------------------------------
# Colours & fonts
# ---------------------------------------------------------------------------
def _rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(rgb: Tuple[int, int, int]) -> float:
    def lin(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def readable_on(bg: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """White or near-black, whichever reads better on `bg`."""
    dark, light = (17, 24, 39), (255, 255, 255)
    return light if contrast_ratio(bg, light) >= contrast_ratio(bg, dark) else dark


def _readable_plate(plate: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Mid-tone brand colours (e.g. grey) read badly with both white and black text: darken them just enough."""
    for _ in range(12):
        if max(contrast_ratio(plate, (255, 255, 255)), contrast_ratio(plate, (17, 24, 39))) >= 4.6:
            break
        plate = _mix(plate, (0, 0, 0), 0.08)
    return plate


def _mix(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))  # type: ignore[return-value]


@dataclass
class Colors:
    plate: Tuple[int, int, int]
    text: Tuple[int, int, int]
    accent: Tuple[int, int, int]
    on_accent: Tuple[int, int, int]


def resolve_colors(spec: PosterSpec) -> Colors:
    if spec.palette == "custom" and spec.brand_color:
        plate = _readable_plate(_rgb(spec.brand_color))
        text = readable_on(plate)
        # accent: a light tint for dark brand colours, a deep shade for light ones
        accent = _mix(plate, (255, 255, 255), 0.82) if _luminance(plate) < 0.4 else _mix(plate, (0, 0, 0), 0.55)
    else:
        pal = PALETTES.get(spec.palette, PALETTES[DEFAULT_PALETTE])
        plate, text, accent = _rgb(pal["plate"]), _rgb(pal["text"]), _rgb(pal["accent"])
    return Colors(plate=plate, text=text, accent=accent, on_accent=readable_on(accent))


@lru_cache(maxsize=64)
def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / _WEIGHTS[weight]), size=max(8, int(size)))


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: float) -> List[str]:
    lines: List[str] = []
    cur = ""
    for word in (w for w in text.split(" ") if w):
        trial = word if not cur else f"{cur} {word}"
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur)
            cur = ""
        if draw.textlength(word, font=font) <= max_w:
            cur = word
        else:  # a single very long word: break by characters
            piece = ""
            for ch in word:
                if draw.textlength(piece + ch, font=font) <= max_w:
                    piece += ch
                else:
                    lines.append(piece)
                    piece = ch
            cur = piece
    if cur:
        lines.append(cur)
    return lines


def _ellipsize(draw: ImageDraw.ImageDraw, line: str, font: ImageFont.FreeTypeFont, max_w: float) -> str:
    if draw.textlength(line, font=font) <= max_w:
        return line
    while line and draw.textlength(line + "…", font=font) > max_w:
        line = line[:-1]
    return line.rstrip() + "…"


@dataclass
class Fitted:
    lines: List[str]
    font: ImageFont.FreeTypeFont
    size: int
    line_h: int

    @property
    def height(self) -> int:
        return self.line_h * len(self.lines)

    def width(self, draw: ImageDraw.ImageDraw) -> float:
        return max((draw.textlength(l, font=self.font) for l in self.lines), default=0.0)


def fit_text(draw: ImageDraw.ImageDraw, text: str, weight: str, max_w: float, max_h: float,
             max_size: int, min_size: int, max_lines: int, spacing: float = 1.2) -> Fitted:
    """Largest font size at which `text` wraps into <= max_lines lines inside max_w x max_h."""
    size = int(max_size)
    min_size = int(min(min_size, max_size))
    while size >= min_size:
        font = _font(weight, size)
        longest = max((draw.textlength(w, font=font) for w in text.split(" ") if w), default=0)
        lines = _wrap(draw, text, font, max_w)
        if longest <= max_w and len(lines) <= max_lines and len(lines) * size * spacing <= max_h:
            return Fitted(lines, font, size, int(size * spacing))
        size -= max(1, int(size * 0.04))
    font = _font(weight, min_size)
    all_lines = _wrap(draw, text, font, max_w)
    lines = all_lines[:max_lines] or [""]
    # still too long at the smallest size: cut the last visible line with an ellipsis
    lines[-1] = _ellipsize(draw, lines[-1] + ("…" if len(all_lines) > max_lines else ""), font, max_w)
    return Fitted(lines, font, min_size, int(min_size * spacing))


def draw_lines(draw: ImageDraw.ImageDraw, x: float, y: float, fitted: Fitted, fill, align: str = "left", box_w: float = 0) -> float:
    for line in fitted.lines:
        w = draw.textlength(line, font=fitted.font)
        px = x if align == "left" else (x + (box_w - w) / 2 if align == "center" else x + box_w - w)
        draw.text((px, y), line, font=fitted.font, fill=fill)
        y += fitted.line_h
    return y


def _rrect(draw: ImageDraw.ImageDraw, box, radius: float, fill) -> None:
    draw.rounded_rectangle([int(v) for v in box], radius=int(radius), fill=fill)


# ---------------------------------------------------------------------------
# Backgrounds
# ---------------------------------------------------------------------------
def _limit_size(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > MAX_SOURCE_SIDE:
        img.thumbnail((MAX_SOURCE_SIDE, MAX_SOURCE_SIDE))
    return img


# Where the product sits in the fallback (no AI scene) composition, as fractions of the canvas
_PRODUCT_BOX = {
    "showcase": (0.12, 0.31, 0.88, 0.77), "magazine": (0.45, 0.08, 0.96, 0.84), "minimal": (0.14, 0.06, 0.86, 0.66),
    "sale": (0.10, 0.28, 0.90, 0.74), "new_arrival": (0.12, 0.10, 0.88, 0.64), "limited": (0.12, 0.10, 0.88, 0.64),
    "callouts": (0.31, 0.15, 0.69, 0.78), "story": (0.10, 0.30, 0.90, 0.66),
}


def _scene_background(size: Tuple[int, int], scene: Image.Image) -> Image.Image:
    return ImageOps.fit(_limit_size(scene), size, method=Image.LANCZOS, centering=(0.5, 0.5))


def _fallback_background(size: Tuple[int, int], source: Image.Image, layout: str, plate: Tuple[int, int, int]) -> Image.Image:
    """No AI scene (offline mode or AI error): blurred, tinted copy of the photo with the product in a card."""
    source = _limit_size(source)
    W, H = size
    bg = ImageOps.fit(source, size, method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(26))
    bg = Image.blend(bg, Image.new("RGB", size, plate), 0.55)
    x0, y0, x1, y1 = _PRODUCT_BOX.get(layout, _PRODUCT_BOX["showcase"])
    box_w, box_h = int((x1 - x0) * W), int((y1 - y0) * H)
    product = ImageOps.contain(source, (box_w, box_h), method=Image.LANCZOS)
    mask = Image.new("L", product.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, product.size[0] - 1, product.size[1] - 1], radius=int(0.035 * W), fill=255)
    px = int(x0 * W + (box_w - product.size[0]) / 2)
    py = int(y0 * H + (box_h - product.size[1]) / 2)
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([px, py + 14, px + product.size[0], py + product.size[1] + 14], radius=int(0.035 * W), fill=(0, 0, 0, 110))
    bg = Image.alpha_composite(bg.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(18))).convert("RGB")
    bg.paste(product, (px, py), mask)
    return bg


def _plain_background(size: Tuple[int, int], plate: Tuple[int, int, int]) -> Image.Image:
    top, bottom = _mix(plate, (255, 255, 255), 0.25), _mix(plate, (0, 0, 0), 0.35)
    base = Image.new("RGB", size, top)
    grad = Image.linear_gradient("L").resize(size)
    return Image.composite(Image.new("RGB", size, bottom), base, grad)


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def keep_numbers_together(text: str) -> str:
    """Non-breaking spaces between digit groups, so a phone number is never split across lines."""
    return re.sub(r"(?<=\d) (?=\d)", "\u00a0", text)


class _Ctx:
    def __init__(self, img: Image.Image, spec: PosterSpec, colors: Colors, logo: Optional[Image.Image]):
        self.img, self.spec, self.c, self.logo = img, spec, colors, logo
        self.W, self.H = img.size
        self.draw = ImageDraw.Draw(img, "RGBA")
        self.m = int(0.05 * self.W)
        self.plate_rgba = (*colors.plate, 236)

    @property
    def uz(self) -> bool:
        return self.spec.lang == "uz"


def _footer(ctx: _Ctx, bottom: int) -> int:
    """Brand + contacts bar. Returns the y of its top edge (or `bottom` if there is nothing to show)."""
    s, c, d = ctx.spec, ctx.c, ctx.draw
    logo = ctx.logo if (ctx.logo is not None and s.show_logo) else None
    if not (s.contact or s.brand_name or logo):
        return bottom
    h = int(0.088 * ctx.W)
    x0, x1, y1 = ctx.m, ctx.W - ctx.m, bottom
    y0 = y1 - h
    _rrect(d, (x0, y0, x1, y1), h * 0.3, ctx.plate_rgba)
    pad = int(h * 0.2)
    cx = x0 + pad
    contact = keep_numbers_together(s.contact)
    if logo is not None:
        chip = h - 2 * pad
        tile = ImageOps.contain(logo.convert("RGBA"), (chip, chip), method=Image.LANCZOS)
        _rrect(d, (cx, y0 + pad, cx + chip, y0 + pad + chip), chip * 0.22, (255, 255, 255, 255))
        ctx.img.paste(tile, (cx + (chip - tile.size[0]) // 2, y0 + pad + (chip - tile.size[1]) // 2), tile)
        cx += chip + pad
    avail = x1 - pad - cx
    contact_w = avail * (0.62 if s.brand_name else 1.0)
    brand_w = avail - contact_w - pad if s.brand_name and s.contact else avail
    if s.brand_name:
        f = fit_text(d, s.brand_name, "bold", brand_w, h - 2 * pad, int(h * 0.36), int(h * 0.2), 1)
        draw_lines(d, cx, y0 + (h - f.height) / 2, f, c.text, "left", brand_w)
    if s.contact:
        f = fit_text(d, contact, "medium", contact_w, h - 2 * pad, int(h * 0.34), int(h * 0.2), 1)
        draw_lines(d, x1 - pad - contact_w, y0 + (h - f.height) / 2, f, c.text, "right", contact_w)
    return y0


def _title_plate(ctx: _Ctx, y: int, max_size_frac: float = 0.072, max_lines: int = 3, width_frac: float = 1.0, x_offset: int = 0) -> int:
    """Rounded plate with the title. Returns its bottom y."""
    s, c, d = ctx.spec, ctx.c, ctx.draw
    if not s.title:
        return y
    pad = int(0.032 * ctx.W)
    plate_w = int((ctx.W - 2 * ctx.m) * width_frac)
    f = fit_text(d, s.title, "xbold", plate_w - 2 * pad, 0.22 * ctx.H, int(max_size_frac * ctx.W), int(0.04 * ctx.W), max_lines)
    ph = f.height + 2 * pad
    x0 = ctx.m + x_offset
    _rrect(d, (x0, y, x0 + plate_w, y + ph), 0.3 * pad * 2, ctx.plate_rgba)
    draw_lines(d, x0 + pad, y + pad, f, c.text, "left", plate_w - 2 * pad)
    return y + ph


def _chips(ctx: _Ctx, y: int, items: List[str], max_rows: int = 2) -> int:
    """Benefit chips flowing left to right. Returns bottom y."""
    s, c, d = ctx.spec, ctx.c, ctx.draw
    if not items:
        return y
    size = int(0.03 * ctx.W)
    font = _font("bold", size)
    pad_x, pad_y, gap = int(size * 0.7), int(size * 0.45), int(size * 0.5)
    x, row, h = ctx.m, 0, size + 2 * pad_y
    for item in items:
        text = _ellipsize(d, item, font, ctx.W - 2 * ctx.m - 2 * pad_x)
        w = int(d.textlength(text, font=font)) + 2 * pad_x
        if x + w > ctx.W - ctx.m:
            row += 1
            x = ctx.m
            if row >= max_rows:
                break
        top = y + row * (h + gap)
        _rrect(d, (x, top, x + w, top + h), h / 2, (*c.accent, 245))
        d.text((x + pad_x, top + pad_y - 1), text, font=font, fill=c.on_accent)
        x += w + gap
    return y + (min(row, max_rows - 1) + 1) * (h + gap)


def _price_block(ctx: _Ctx, bottom: int, x: Optional[int] = None, align: str = "left", size_frac: float = 0.085) -> int:
    """Price pill (+ struck-through old price above it). Returns the y of the block's top edge."""
    s, c, d = ctx.spec, ctx.c, ctx.draw
    if not s.price:
        return bottom
    x = ctx.m if x is None else x
    max_w = ctx.W - 2 * ctx.m
    f = fit_text(d, s.price, "xbold", max_w * 0.8, 0.12 * ctx.H, int(size_frac * ctx.W), int(0.045 * ctx.W), 1)
    pad_x, pad_y = int(f.size * 0.5), int(f.size * 0.28)
    w, h = int(f.width(d)) + 2 * pad_x, f.height + 2 * pad_y
    px = x if align == "left" else (x - w if align == "right" else x - w // 2)
    top = bottom - h
    _rrect(d, (px, top, px + w, bottom), h * 0.32, (*c.accent, 255))
    d.text((px + pad_x, top + pad_y - int(f.size * 0.04)), f.lines[0], font=f.font, fill=c.on_accent)
    if s.old_price:
        of = fit_text(d, s.old_price, "bold", max_w * 0.5, 0.06 * ctx.H, int(f.size * 0.5), int(0.025 * ctx.W), 1)
        ow = int(of.width(d))
        ox = px + pad_x
        oy = top - of.height - int(0.008 * ctx.W)
        _rrect(d, (ox - pad_x // 2, oy - 2, ox + ow + pad_x // 2, oy + of.height), of.size * 0.3, (*c.plate, 228))
        d.text((ox, oy), of.lines[0], font=of.font, fill=c.text)
        d.line([(ox, oy + of.height * 0.55), (ox + ow, oy + of.height * 0.55)], fill=(*c.accent, 255), width=max(2, int(of.size * 0.1)))
        top = oy - 2
    return top


def _pill(ctx: _Ctx, x: int, y: int, text: str, size: int, fill, text_fill, weight: str = "xbold", center: bool = False) -> Tuple[int, int]:
    d = ctx.draw
    font = _font(weight, size)
    text = _ellipsize(d, text, font, ctx.W - 2 * ctx.m - size)
    pad_x, pad_y = int(size * 0.8), int(size * 0.42)
    w, h = int(d.textlength(text, font=font)) + 2 * pad_x, int(size * 1.2) + 2 * pad_y - int(size * 0.2)
    if center:
        x = x - w // 2
    _rrect(d, (x, y, x + w, y + h), h / 2, fill)
    d.text((x + pad_x, y + pad_y - int(size * 0.08)), text, font=font, fill=text_fill)
    return w, h


def _title_price_bar(ctx: _Ctx, bottom: int) -> int:
    """Wide bar: title on the left, price on the right. Returns its top y."""
    s, c, d = ctx.spec, ctx.c, ctx.draw
    if not (s.title or s.price):
        return bottom
    pad = int(0.032 * ctx.W)
    inner_w = ctx.W - 2 * ctx.m - 2 * pad
    price_w = 0
    pf = None
    if s.price:
        pf = fit_text(d, s.price, "xbold", inner_w * 0.42, 0.1 * ctx.H, int(0.075 * ctx.W), int(0.04 * ctx.W), 1)
        price_w = int(pf.width(d))
    title_w = inner_w - price_w - (pad if price_w else 0)
    tf = fit_text(d, s.title, "xbold", title_w, 0.14 * ctx.H, int(0.058 * ctx.W), int(0.034 * ctx.W), 2) if s.title else None
    content_h = max(tf.height if tf else 0, (pf.height if pf else 0) + (int(pf.size * 0.9) if (pf and s.old_price) else 0))
    h = content_h + 2 * pad
    y0 = bottom - h
    _rrect(d, (ctx.m, y0, ctx.W - ctx.m, bottom), pad * 0.7, ctx.plate_rgba)
    if tf:
        draw_lines(d, ctx.m + pad, y0 + (h - tf.height) / 2, tf, c.text, "left", title_w)
    if pf:
        px = ctx.W - ctx.m - pad - price_w
        py = y0 + (h - pf.height) / 2 + (int(pf.size * 0.45) if s.old_price else 0)
        d.text((px, py), pf.lines[0], font=pf.font, fill=c.accent)
        if s.old_price:
            of = fit_text(d, s.old_price, "bold", price_w + pad, 0.05 * ctx.H, int(pf.size * 0.5), int(0.022 * ctx.W), 1)
            ow = of.width(d)
            ox, oy = ctx.W - ctx.m - pad - ow, y0 + pad * 0.55
            d.text((ox, oy), of.lines[0], font=of.font, fill=(*c.text, 210))
            d.line([(ox, oy + of.height * 0.55), (ox + ow, oy + of.height * 0.55)], fill=(*c.accent, 255), width=max(2, int(of.size * 0.1)))
    return y0


def _check(ctx: _Ctx, cx: float, cy: float, r: float) -> None:
    d, c = ctx.draw, ctx.c
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*c.accent, 255))
    d.line([(cx - r * 0.45, cy), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.38)], fill=c.on_accent, width=max(2, int(r * 0.22)), joint="curve")


# ---------------------------------------------------------------------------
# Layouts
# ---------------------------------------------------------------------------
def _layout_showcase(ctx: _Ctx) -> None:
    s = ctx.spec
    y = _title_plate(ctx, ctx.m, max_lines=2)
    if s.bullets:
        _chips(ctx, y + int(0.014 * ctx.W), s.bullets[:3], max_rows=1)
    bottom = _footer(ctx, ctx.H - ctx.m) - int(0.015 * ctx.W)
    _price_block(ctx, bottom)


def _layout_magazine(ctx: _Ctx) -> None:
    s, c, d = ctx.spec, ctx.c, ctx.draw
    x0, x1 = ctx.m, int(0.43 * ctx.W)
    y0, y1 = ctx.m, ctx.H - ctx.m
    _rrect(d, (x0, y0, x1, y1), 0.04 * ctx.W, ctx.plate_rgba)
    pad = int(0.034 * ctx.W)
    inner_w = x1 - x0 - 2 * pad
    y = y0 + pad
    logo = ctx.logo if (ctx.logo is not None and s.show_logo) else None
    if logo is not None or s.brand_name:
        chip = int(0.075 * ctx.W)
        cx = x0 + pad
        if logo is not None:
            tile = ImageOps.contain(logo.convert("RGBA"), (chip, chip), method=Image.LANCZOS)
            _rrect(d, (cx, y, cx + chip, y + chip), chip * 0.22, (255, 255, 255, 255))
            ctx.img.paste(tile, (cx + (chip - tile.size[0]) // 2, y + (chip - tile.size[1]) // 2), tile)
            cx += chip + int(pad * 0.4)
        if s.brand_name:
            f = fit_text(d, s.brand_name, "bold", x1 - pad - cx, chip, int(chip * 0.4), int(chip * 0.22), 1)
            draw_lines(d, cx, y + (chip - f.height) / 2, f, c.text, "left", x1 - pad - cx)
        y += chip + int(pad * 0.7)
    if s.title:
        f = fit_text(d, s.title, "xbold", inner_w, 0.28 * ctx.H, int(0.062 * ctx.W), int(0.036 * ctx.W), 5)
        y = draw_lines(d, x0 + pad, y, f, c.text, "left", inner_w)
        d.rounded_rectangle([x0 + pad, y + 6, x0 + pad + int(0.12 * ctx.W), y + 12], radius=3, fill=(*c.accent, 255))
        y += int(pad * 0.7)
    bottom = y1 - pad
    if s.contact:
        f = fit_text(d, keep_numbers_together(s.contact), "medium", inner_w, 0.06 * ctx.H, int(0.03 * ctx.W), int(0.02 * ctx.W), 2)
        bottom -= f.height
        draw_lines(d, x0 + pad, bottom, f, c.text, "left", inner_w)
        bottom -= int(pad * 0.5)
    price_top = _price_block(ctx, bottom, x=x0 + pad, size_frac=0.06)
    # bullets fill the space between the title and the price
    bf = int(0.031 * ctx.W)
    for item in s.bullets[:4]:
        f = fit_text(d, item, "medium", inner_w - int(bf * 1.8), bf * 3.8, bf, int(bf * 0.75), 3, spacing=1.25)
        if y + f.height > price_top - int(pad * 0.4):
            break
        _check(ctx, x0 + pad + bf * 0.6, y + bf * 0.7, bf * 0.55)
        draw_lines(d, x0 + pad + int(bf * 1.6), y, f, c.text, "left", inner_w - int(bf * 1.8))
        y += f.height + int(bf * 0.6)


def _layout_minimal(ctx: _Ctx) -> None:
    bottom = _footer(ctx, ctx.H - ctx.m) - int(0.015 * ctx.W)
    _title_price_bar(ctx, bottom)


def _layout_sale(ctx: _Ctx) -> None:
    s, c, d = ctx.spec, ctx.c, ctx.draw
    badge = s.badge_text
    y = ctx.m
    width_frac = 0.66 if badge else 1.0
    bottom_title = _title_plate(ctx, y, max_size_frac=0.066, max_lines=2, width_frac=width_frac)
    if badge:
        r = int(0.14 * ctx.W)
        cx, cy = ctx.W - ctx.m - r, ctx.m + r + int(0.01 * ctx.W)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*c.accent, 255))
        d.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=(*c.plate, 255), width=4)
        f = fit_text(d, badge, "xbold", r * 1.5, r * 1.1, int(r * 0.85), int(r * 0.3), 1)
        d.text((cx - f.width(d) / 2, cy - f.height / 2 - f.size * 0.04), f.lines[0], font=f.font, fill=c.on_accent)
        bottom_title = max(bottom_title, cy + r)
    if s.deadline:
        _pill(ctx, ctx.m, bottom_title + int(0.015 * ctx.W), s.deadline, int(0.032 * ctx.W), (*c.accent, 255), c.on_accent)
    bottom = _footer(ctx, ctx.H - ctx.m) - int(0.015 * ctx.W)
    _price_block(ctx, bottom)


def _layout_new_arrival(ctx: _Ctx) -> None:
    s, c = ctx.spec, ctx.c
    label = s.badge_text or ("YANGILIK" if ctx.uz else "НОВИНКА")
    _pill(ctx, ctx.m, ctx.m, label, int(0.045 * ctx.W), (*c.accent, 255), c.on_accent)
    bottom = _footer(ctx, ctx.H - ctx.m) - int(0.015 * ctx.W)
    _title_price_bar(ctx, bottom)


def _layout_limited(ctx: _Ctx) -> None:
    s, c, d = ctx.spec, ctx.c, ctx.draw
    label = s.badge_text or ("CHEKLANGAN" if ctx.uz else "ЛИМИТ")
    w, h = _pill(ctx, ctx.W // 2, ctx.m, "★ " + label + " ★", int(0.038 * ctx.W), (*c.plate, 240), c.accent, center=True)
    if s.deadline:
        _pill(ctx, ctx.W // 2, ctx.m + h + int(0.012 * ctx.W), s.deadline, int(0.03 * ctx.W), (*c.accent, 255), c.on_accent, center=True)
    bottom = _footer(ctx, ctx.H - ctx.m) - int(0.015 * ctx.W)
    _title_price_bar(ctx, bottom)


def _layout_callouts(ctx: _Ctx) -> None:
    s, c, d = ctx.spec, ctx.c, ctx.draw
    y = _title_plate(ctx, ctx.m, max_size_frac=0.06, max_lines=2)
    bottom = _footer(ctx, ctx.H - ctx.m) - int(0.015 * ctx.W)
    price_top = _price_block(ctx, bottom, x=ctx.W // 2, align="center", size_frac=0.07)
    items = s.bullets[:4]
    if not items:
        return
    top, low = y + int(0.04 * ctx.H), price_top - int(0.03 * ctx.H)
    step = (low - top) / max(1, len(items))
    pill_w, size = int(0.36 * ctx.W), int(0.029 * ctx.W)
    font = _font("bold", size)
    for i, item in enumerate(items):
        lines = fit_text(d, item, "bold", pill_w - int(size * 3), size * 3.2, size, int(size * 0.75), 2, spacing=1.25).lines
        ph = len(lines) * int(size * 1.25) + int(size * 1.0)
        cy = int(top + step * (i + 0.5))
        left = i % 2 == 0
        x0 = ctx.m if left else ctx.W - ctx.m - pill_w
        _rrect(d, (x0, cy - ph // 2, x0 + pill_w, cy + ph // 2), ph / 2.4, ctx.plate_rgba)
        _check(ctx, x0 + size * 1.0, cy, size * 0.55)
        ty = cy - len(lines) * int(size * 1.25) / 2
        for line in lines:
            d.text((x0 + int(size * 2.0), ty), line, font=font, fill=c.text)
            ty += int(size * 1.25)
        # connector towards the product
        sx = x0 + pill_w if left else x0
        ex = ctx.W // 2 + (-int(0.1 * ctx.W) if left else int(0.1 * ctx.W))
        d.line([(sx, cy), (ex, cy)], fill=(*c.accent, 255), width=4)
        r = int(0.009 * ctx.W)
        d.ellipse([ex - r, cy - r, ex + r, cy + r], fill=(*c.accent, 255), outline=(255, 255, 255, 255), width=2)


def _layout_story(ctx: _Ctx) -> None:
    s, c, d = ctx.spec, ctx.c, ctx.draw
    top = int(0.075 * ctx.H)
    y = _title_plate(ctx, top, max_size_frac=0.075, max_lines=3)
    if s.bullets:
        _chips(ctx, y + int(0.012 * ctx.W), s.bullets[:3], max_rows=1)
    bottom_margin = int(0.085 * ctx.H)
    bottom = _footer(ctx, ctx.H - bottom_margin) - int(0.02 * ctx.W)
    cta = s.cta or ("Telegramda buyurtma" if ctx.uz else "Заказать в Telegram")
    h = int(0.1 * ctx.W)
    f = fit_text(d, cta, "xbold", ctx.W - 2 * ctx.m - int(0.1 * ctx.W), h * 0.6, int(h * 0.42), int(h * 0.24), 1)
    _rrect(d, (ctx.m, bottom - h, ctx.W - ctx.m, bottom), h / 2, (*c.accent, 255))
    d.text(((ctx.W - f.width(d)) / 2, bottom - h + (h - f.height) / 2 - f.size * 0.03), f.lines[0], font=f.font, fill=c.on_accent)
    _price_block(ctx, bottom - h - int(0.02 * ctx.W), x=ctx.W // 2, align="center", size_frac=0.08)


_LAYOUT_FUNCS = {
    "showcase": _layout_showcase, "magazine": _layout_magazine, "minimal": _layout_minimal, "sale": _layout_sale,
    "new_arrival": _layout_new_arrival, "limited": _layout_limited, "callouts": _layout_callouts, "story": _layout_story,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def render_poster(spec: PosterSpec, background: Optional[Image.Image] = None, source: Optional[Image.Image] = None,
                  logo: Optional[Image.Image] = None) -> Image.Image:
    """Draw the poster. `background` is the AI scene; `source` (the seller's own photo) is the fallback."""
    size = ASPECTS[spec.aspect]["size"]
    colors = resolve_colors(spec)
    if background is not None:
        canvas = _scene_background(size, background)
    elif source is not None:
        canvas = _fallback_background(size, source, spec.layout, colors.plate)
    else:
        canvas = _plain_background(size, colors.plate)
    if logo is not None:
        logo = ImageOps.exif_transpose(logo).convert("RGBA")
        logo.thumbnail((512, 512))
    ctx = _Ctx(canvas, spec, colors, logo)
    _LAYOUT_FUNCS[spec.layout](ctx)
    return canvas


def poster_to_png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False, compress_level=3)
    return buf.getvalue()


def normalize_logo(raw: bytes, max_side: int = 512) -> bytes:
    """Validate an uploaded logo and return it as a small PNG (raises ValueError if it is not an image)."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise ValueError("not an image") from exc
    if img.width * img.height > 40_000_000:
        raise ValueError("image too large")
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def normalize_source(raw: bytes, max_side: int = 1600) -> bytes:
    """Validate the seller's photo and return a compact JPEG (raises ValueError if it is not an image)."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise ValueError("not an image") from exc
    if img.width * img.height > 60_000_000:
        raise ValueError("image too large")
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Prefill from an AI card
# ---------------------------------------------------------------------------
_EMOJI = re.compile("[\U00010000-\U0010ffff☀-➿️‍]+")


def _strip_emoji(text: str) -> str:
    return " ".join(_EMOJI.sub("", text or "").split())


def format_price(value: Any, lang: str) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return ""
    if amount <= 0:
        return ""
    return f"{amount:,.0f}".replace(",", " ") + (" so'm" if lang == "uz" else " сум")


_AMOUNT = re.compile(r"\d[\d\s\u00a0.,]*\d|\d")


def _price_from_tag(tag: str, lang: str) -> str:
    """'380 000 – 420 000 сум' -> 'от 380 000 сум'; '380 000 сум' -> '380 000 сум'; no number -> ''."""
    amounts = []
    for m in _AMOUNT.finditer(tag):
        digits = re.sub(r"\D", "", m.group(0))
        if digits:
            amounts.append(int(digits))
    if not amounts:
        return ""
    price = format_price(amounts[0], lang)
    if len(amounts) > 1 and amounts[1] != amounts[0]:
        return f"{amounts[0]:,}".replace(",", " ") + " so'mdan" if lang == "uz" else "от " + price
    return price


def poster_defaults(card: Dict[str, Any], desired_price: Any, lang: str) -> Dict[str, Any]:
    """Text fields for the poster editor, taken from the generated card (the seller can change all of them)."""
    title = _strip_emoji(card.get("title", ""))
    if title.startswith(("«", '"', "“", "'")):
        title = re.sub(r"[«»“”\"]", "", title)  # AI titles often start with a quoted name: drop the stray marks
    title = title.strip(" -–—")
    price = format_price(desired_price, lang) or _price_from_tag(_strip_emoji(card.get("price_tag", "")), lang)
    short: List[str] = []
    long: List[str] = []
    for raw in (card.get("description") or "").splitlines():
        line = raw.strip()
        if line.startswith(("•", "-", "–", "✅", "✔")):
            text = _strip_emoji(line.lstrip("•-–✅✔ ").strip())
            if 3 <= len(text) <= 48:
                short.append(text)
            elif 48 < len(text) <= 70:
                long.append(text)
    bullets = (short + long)[:3]  # short benefits read best on a poster
    return {
        "title": _clean(title, LIMITS["title"]),
        "price": _clean(price, LIMITS["price"]),
        "bullets": bullets,
    }
