"""
info_photo.py — every picture with text (information card, poster, promo, infographic, story) is drawn by the
AI image model. Nothing on a marketing picture is drawn by the server or the browser any more.

That only works if the text is right, so the pipeline is built around one text model and one check:

  CopySpec   what is written on the picture: a fixed set of short slots (title, bullets, price, ...).
  FORMATS    per style: which slots it shows and how many, tighter length limits, the layout brief and where
             each slot goes, the aspect ratios it supports.
  prompts    build_render_prompt() lists every string in quotes with its role and position;
             build_edit_prompt() asks to replace only the strings that came out wrong.
  check      verify_text() compares what a vision model read back from the picture with the approved strings,
             line by line: digits, currency, percent signs and Uzbek apostrophes must match exactly.

Facts are protected: characteristics come only from the seller, the price only from the seller's form through
format_price(), and AI-written lines with promises ("premium", "guarantee", "100%") are dropped.

Pure functions only: the network calls live in services/ai_service.py.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from services.copy_utils import format_price

# Default length limits, in characters. A format may tighten them (FORMATS[style]["limits"]).
LIMITS: Dict[str, int] = {
    "title": 32, "subtitle": 40, "bullet": 28, "spec_name": 18, "spec_value": 22, "price": 24, "old_price": 24,
    "discount": 6, "badge": 18, "deadline": 28, "cta": 18, "contact": 30, "brand_name": 24, "use": 14,
}
MAX_BULLETS, MAX_SPECS, MAX_USES = 4, 5, 4
MAX_FACT_LINES = 10
MAX_BLOCKS, MAX_BLOCKS_STORY = 6, 4

DEFAULT_CTA = {"ru": "Заказать", "uz": "Buyurtma berish"}


def _clean(value: Any, limit: int) -> str:
    """One line, single spaces, cut at a word boundary where possible (half a word on a picture looks like a typo)."""
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if text[limit] != " " and " " in cut and len(cut.rsplit(" ", 1)[0]) >= limit * 0.6:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-–—·")


def _amount(value: Any) -> Optional[float]:
    """The number in a price field: 380000, "380 000", "380 000 сум", "380 000,00" -> 380000.0; no digits -> None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(round(value)) if value > 0 else None
    text = str(value or "")
    m = re.search(r"\d[\d\s\u00a0']*", text)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(0))
    return float(digits) if digits and int(digits) > 0 else None


def _discount(value: Any) -> str:
    """"15", "-15%", "−15 %" -> "−15%"; anything without a sensible percentage -> ""."""
    m = re.search(r"\d{1,2}", str(value or ""))
    return f"−{int(m.group(0))}%" if m and 0 < int(m.group(0)) < 100 else ""


# ---------------------------------------------------------------------------
# What goes on the picture
# ---------------------------------------------------------------------------
@dataclass
class CopySpec:
    title: str = ""
    subtitle: str = ""
    bullets: List[str] = field(default_factory=list)
    specs: List[Tuple[str, str]] = field(default_factory=list)
    price: str = ""
    old_price: str = ""
    discount: str = ""
    badge: str = ""
    deadline: str = ""
    cta: str = ""
    contact: str = ""
    brand_name: str = ""
    uses: List[str] = field(default_factory=list)
    lang: str = "ru"
    legacy: bool = False  # a card migrated from the old server-drawn posters

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]], limits: Optional[Dict[str, int]] = None) -> "CopySpec":
        """Clean and clamp untrusted input (the AI's suggestions, the seller's edits, a stored card).

        Prices are re-formatted from their digits, so whatever was typed the picture shows "380 000 сум";
        the discount is computed from the two prices when both are given. Old field names are accepted
        (tagline -> subtitle, benefits -> bullets, badge_text -> badge).
        """
        data = data or {}
        lim = {**LIMITS, **(limits or {})}
        lang = "uz" if data.get("lang") == "uz" else "ru"
        specs: List[Tuple[str, str]] = []
        for item in (data.get("specs") or [])[:MAX_SPECS * 2]:
            if isinstance(item, dict):
                name, value = item.get("name"), item.get("value")
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                name, value = item
            else:
                continue
            name, value = _clean(name, lim["spec_name"]), _clean(value, lim["spec_value"])
            if name and value and len(specs) < MAX_SPECS:
                specs.append((name, value))

        def many(key: str, alias: str, limit_key: str, cap: int) -> List[str]:
            raw = data.get(key) if data.get(key) is not None else data.get(alias)
            out: List[str] = []
            for x in (raw or [])[:cap * 2]:
                text = _clean(x, lim[limit_key])
                if text and text not in out:
                    out.append(text)
            return out[:cap]

        price_amount, old_amount = _amount(data.get("price")), _amount(data.get("old_price"))
        if old_amount and price_amount and old_amount <= price_amount:
            old_amount = None  # an "old price" that is not higher is a mistake, not a discount
        if old_amount and not price_amount:
            old_amount = None
        if price_amount and old_amount:
            pct = round((1 - price_amount / old_amount) * 100)
            discount = f"−{pct}%" if 0 < pct < 100 else ""
        else:
            discount = _discount(data.get("discount"))
        return cls(
            title=_clean(data.get("title"), lim["title"]),
            subtitle=_clean(data.get("subtitle") or data.get("tagline"), lim["subtitle"]),
            bullets=many("bullets", "benefits", "bullet", MAX_BULLETS),
            specs=specs,
            price=format_price(price_amount, lang),
            old_price=format_price(old_amount, lang),
            discount=discount,
            badge=_clean(data.get("badge") or data.get("badge_text"), lim["badge"]),
            deadline=_clean(data.get("deadline"), lim["deadline"]),
            cta=_clean(data.get("cta"), lim["cta"]),
            contact=_clean(data.get("contact"), lim["contact"]),
            brand_name=_clean(data.get("brand_name"), lim["brand_name"]),
            uses=many("uses", "uses", "use", MAX_USES),
            lang=lang,
            legacy=bool(data.get("legacy")),
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "title": self.title, "subtitle": self.subtitle, "bullets": list(self.bullets),
            "specs": [{"name": n, "value": v} for n, v in self.specs],
            "price": self.price, "old_price": self.old_price, "discount": self.discount, "badge": self.badge,
            "deadline": self.deadline, "cta": self.cta, "contact": self.contact, "brand_name": self.brand_name,
            "uses": list(self.uses), "lang": self.lang,
        }
        if self.legacy:
            out["legacy"] = True
        return out


_BULLET = re.compile(r"^[\s•\-–—*·✅✔▪●]+")


def parse_facts(text: Optional[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
    """The seller's own facts, one per line: "Диаметр: 32 см" becomes a specification, any other line a benefit."""
    benefits: List[str] = []
    specs: List[Tuple[str, str]] = []
    for raw in (text or "").splitlines()[:MAX_FACT_LINES * 2]:
        line = _BULLET.sub("", raw).strip()
        if not line:
            continue
        m = re.match(r"^([^:—–]{2,%d})\s*(?::|—|–)\s*(.+)$" % LIMITS["spec_name"], line)
        if m and len(m.group(2).strip()) >= 1:
            specs.append((_clean(m.group(1), LIMITS["spec_name"]), _clean(m.group(2), LIMITS["spec_value"])))
        else:
            benefits.append(_clean(line, LIMITS["bullet"]))
        if len(benefits) + len(specs) >= MAX_FACT_LINES:
            break
    return benefits, specs


# Claims a seller must be able to stand behind: the AI may not add them on its own (the seller can still write them)
_RISKY = re.compile(
    r"преми|престиж|высок\w*\s+качеств|лучш|№\s*1|номер\s+один|гаранти|сертифиц|100\s*%|оригинал|эксклюзив|"
    r"premium|prestij|eng\s+yaxshi|kafolat|sertifikat|original|eksklyuziv|yuqori\s+sifat",
    re.IGNORECASE,
)


def build_copy(suggestions: Dict[str, Any], facts_text: Optional[str], title_hint: str, lang: str,
               allowed_text: Optional[str] = None, price: Any = None, old_price: Any = None,
               brand: Optional[Dict[str, Any]] = None) -> CopySpec:
    """The first version of the text, shown to the seller for review before anything is drawn.

    Seller facts come first; AI suggestions only fill the gaps. AI lines with promises or superlatives are dropped
    unless the seller wrote such a word themselves. Characteristics (sizes, weights, materials) are only ever the
    seller's own. The price is only the seller's form value: the AI's own "price" is ignored.
    """
    own_bullets, own_specs = parse_facts(facts_text)
    ai = CopySpec.from_dict({**{k: v for k, v in (suggestions or {}).items() if k not in ("price", "old_price", "discount", "specs")}, "lang": lang})
    seller_text = f"{facts_text or ''}\n{allowed_text or ''}"

    def safe(text: str) -> bool:
        found = _RISKY.search(text)
        return not found or bool(re.search(re.escape(found.group(0)), seller_text, re.IGNORECASE))

    brand = brand or {}
    lang = "uz" if lang == "uz" else "ru"
    return CopySpec.from_dict({
        "title": ai.title if (ai.title and safe(ai.title)) else title_hint,
        "subtitle": ai.subtitle if safe(ai.subtitle) else "",
        "bullets": own_bullets + [b for b in ai.bullets if b not in own_bullets and safe(b)],
        "specs": own_specs,
        "price": price, "old_price": old_price,
        "badge": ai.badge if safe(ai.badge) else "",
        "uses": [u for u in ai.uses if safe(u)],
        "cta": DEFAULT_CTA[lang],
        "contact": brand.get("brand_contact") or "",
        "brand_name": brand.get("brand_name") or "",
        "lang": lang,
    })


# ---------------------------------------------------------------------------
# Formats: one entry per style that carries text
# ---------------------------------------------------------------------------
_INFO_ASPECTS = ["3:4", "1:1", "4:5"]
_ALL_ASPECTS = ["3:4", "1:1", "4:5", "9:16"]


def _fmt(slots: Dict[str, int], brief: str, positions: Optional[Dict[str, str]] = None, limits: Optional[Dict[str, int]] = None,
         aspects: Optional[List[str]] = None, max_blocks: int = MAX_BLOCKS) -> Dict[str, Any]:
    return {"slots": slots, "brief": brief, "positions": positions or {}, "limits": limits or {},
            "aspects": aspects or _INFO_ASPECTS, "max_blocks": max_blocks}


FORMATS: Dict[str, Dict[str, Any]] = {
    # ---- information cards for marketplaces ----
    "info_white_specs": _fmt(
        {"title": 1, "specs": 4},
        "Clean e-commerce card on a pure white background. The product is shown large in the centre. If sizes are "
        "listed, draw thin dimension lines with small arrowheads next to the product carrying exactly those size "
        "labels. Under the product, a simple two-column block of characteristics in dark grey text (name on the "
        "left, value on the right). Minimalist, lots of white space.",
        {"title": "top, bold black capital letters", "spec": "characteristics block under the product"},
    ),
    "info_theme_benefits": _fmt(
        {"title": 1, "subtitle": 1, "bullets": 3, "badge": 1},
        "Dynamic themed advertising poster. A rich colourful background that matches the product's main colour and "
        "mood. The product is large and dominant. The benefits are stacked on the left side, each with a small round "
        "line icon. A round starburst badge sits in a lower corner (only if a badge text is given).",
        {"title": "top, huge and bold", "subtitle": "under the title, smaller", "bullet": "left side, with a small icon",
         "badge": "starburst badge in a lower corner"},
    ),
    "info_headline": _fmt(
        {"title": 1, "uses": 2},
        "Lifestyle product photo: the product shown in a natural, stylish use scene (no faces, hands or legs only, or "
        "a tasteful surface). A giant heavy-weight headline spans the lower part of the image in a bold colour that "
        "contrasts with the photo.",
        {"title": "giant headline across the lower part", "use": "small icon-and-word label, top-left corner"},
        limits={"title": 28},
    ),
    "info_collection": _fmt(
        {"title": 1, "bullets": 3},
        "Collector's-edition poster: a dramatic themed background, the product (or the group of items) in the "
        "foreground. A row of small icons with short captions runs along the bottom edge, one per listed benefit.",
        {"title": "huge stylised title across the top", "bullet": "caption under an icon in the bottom row"},
        limits={"bullet": 24},
    ),
    "info_dark_list": _fmt(
        {"title": 1, "subtitle": 1, "bullets": 3, "specs": 1},
        "Dark grunge poster: a black and charcoal textured background, the product large on one side. A vertical list "
        "of the benefits, each with a small circular line icon. If a characteristic is listed, show it as a bold "
        "stamp-like label near the lower left.",
        {"title": "top, bold and stylised", "subtitle": "under the title", "bullet": "vertical list beside the product",
         "spec": "stamp-like label, lower left"},
    ),
    "info_dark_pills": _fmt(
        {"title": 1, "subtitle": 1, "bullets": 3},
        "Premium dark satin-textured background with subtle sparkles. The product is centred and lit like a jewellery "
        "shot. The benefits appear as rounded translucent pills with a small icon each, on both sides of the product.",
        {"title": "top, large", "subtitle": "beneath the title, smaller", "bullet": "translucent pill beside the product"},
    ),
    "info_callouts": _fmt(
        {"title": 1, "bullets": 4},
        "Clean marketplace infographic on a light neutral gradient background. The product is large in the centre. "
        "The benefits are short callouts placed around the product, each connected to it with a thin line ending in "
        "a small dot. Modern sans-serif typography.",
        {"title": "top", "bullet": "callout beside the product, joined to it by a thin line"},
    ),
    "info_table": _fmt(
        {"title": 1, "specs": 5},
        "Clean marketplace card. The product occupies the upper half on a soft light studio background. Below it, a "
        "tidy characteristics table with one row per listed characteristic: the name on the left in bold, the value "
        "on the right.",
        {"title": "very top", "spec": "table row under the product"},
    ),
    "market_callouts": _fmt(
        {"title": 1, "bullets": 4, "price": 1},
        "Marketplace infographic: the product centred and large on a soft light neutral background. Each benefit is a "
        "callout with a thin leader line pointing to the exact part of the product it describes (handle, fabric, "
        "pattern, clasp, ...). Tidy, technical, easy to read.",
        {"title": "top", "bullet": "callout with a leader line to the matching part of the product",
         "price": "bottom-right, in a rounded plate, the largest number"},
    ),
    # ---- posters ----
    "poster_showcase": _fmt(
        {"title": 1, "bullets": 2, "price": 1, "contact": 1, "brand_name": 1},
        "Elegant advertising poster. The product is large, centred in the lower two thirds of the frame and "
        "beautifully lit; the upper third is a calm, softly blurred area that carries the title.",
        {"title": "upper third of the image, large", "bullet": "small line under the title",
         "price": "bottom-left, the largest number", "contact": "bottom-right, small", "brand_name": "very top, small"},
        aspects=_ALL_ASPECTS,
    ),
    "poster_magazine": _fmt(
        {"title": 1, "bullets": 3, "price": 1, "contact": 1},
        "Editorial magazine-style poster. The product is on the right half of the frame, beautifully lit; the left "
        "40% is a calm column that carries the title, a list of benefits with small check marks and the price.",
        {"title": "top of the left column, in the upper third", "bullet": "list in the left column, with a check mark",
         "price": "bottom of the left column, the largest number", "contact": "bottom edge, small"},
        aspects=_ALL_ASPECTS,
    ),
    "poster_minimal": _fmt(
        {"title": 1, "price": 1, "contact": 1},
        "Minimalist premium poster. The product is centred in the upper two thirds on a clean surface with generous "
        "negative space; a calm plain band along the bottom carries the text.",
        {"title": "upper third of the image, thin elegant letters", "price": "bottom band, left, the largest number",
         "contact": "bottom band, right, small"},
        aspects=_ALL_ASPECTS,
    ),
    # ---- promotions ----
    "promo_sale": _fmt(
        {"title": 1, "discount": 1, "price": 1, "old_price": 1, "deadline": 1},
        "Energetic sales promotion poster. The product is centred in the lower two thirds, vivid and bright; the top "
        "third is calm and carries the headline. A round discount badge sits in a top corner. The old price is "
        "crossed out with one clean line and stands right next to the new price.",
        {"title": "upper third, bold", "discount": "round badge in the top-right corner",
         "price": "bottom-left, the largest number", "old_price": "next to the new price, smaller, crossed out",
         "deadline": "bottom edge, small"},
        aspects=_ALL_ASPECTS,
    ),
    "promo_new": _fmt(
        {"title": 1, "badge": 1, "price": 1, "contact": 1},
        "Fresh new-arrival poster. The product is centred in the upper two thirds with a soft spotlight; a diagonal "
        "ribbon in a top corner carries the badge text; a calm band along the bottom carries the title and the price.",
        {"badge": "diagonal ribbon in the top-left corner", "title": "bottom band, bold",
         "price": "bottom band, right, the largest number", "contact": "very bottom, small"},
        aspects=_ALL_ASPECTS,
    ),
    "promo_limited": _fmt(
        {"title": 1, "badge": 1, "price": 1, "deadline": 1},
        "Exclusive limited-edition poster in a luxurious mood. The product is centred in the upper two thirds with "
        "dramatic soft lighting; an elegant label near the top carries the badge text; a calm band along the bottom "
        "carries the title and the price.",
        {"badge": "elegant label near the top", "title": "bottom band, serif capitals",
         "price": "bottom band, the largest number", "deadline": "under the price, small"},
        aspects=_ALL_ASPECTS,
    ),
    # ---- story ----
    "story_order": _fmt(
        {"title": 1, "price": 1, "cta": 1, "contact": 1},
        "Vertical social-media story. The product is centred in the middle of the frame, beautifully lit. Respect the "
        "story interface safe zones: keep the top 14% and the bottom 20% of the frame free of text, they are covered "
        "by the app's own controls.",
        {"title": "within the upper 20% of the image (below the safe zone), large",
         "price": "just above the button, the largest number",
         "cta": "rounded button within the lower 25% of the image (above the safe zone)",
         "contact": "small line directly under the button"},
        aspects=["9:16"], max_blocks=MAX_BLOCKS_STORY,
    ),
}

# Slot name -> (CopySpec attribute, is it a list, role name used in prompts and positions)
_SLOT_ATTRS: List[Tuple[str, str, bool, str]] = [
    ("brand_name", "brand_name", False, "brand_name"),
    ("badge", "badge", False, "badge"),
    ("discount", "discount", False, "discount"),
    ("title", "title", False, "title"),
    ("subtitle", "subtitle", False, "subtitle"),
    ("bullets", "bullets", True, "bullet"),
    ("specs", "specs", True, "spec"),
    ("price", "price", False, "price"),
    ("old_price", "old_price", False, "old_price"),
    ("deadline", "deadline", False, "deadline"),
    ("cta", "cta", False, "cta"),
    ("contact", "contact", False, "contact"),
    ("uses", "uses", True, "use"),
]
_ROLE_NAMES = {
    "brand_name": "shop name", "badge": "badge", "discount": "discount badge", "title": "title", "subtitle": "subtitle",
    "bullet": "benefit", "spec": "characteristic", "price": "price", "old_price": "old price, crossed out",
    "deadline": "deadline", "cta": "button label", "contact": "contact", "use": "caption",
}
_LIMIT_KEYS = {"bullets": "bullet", "uses": "use"}


def get_format(style_id: Optional[str]) -> Dict[str, Any]:
    return FORMATS.get(style_id or "", FORMATS["info_callouts"])


def format_limits(style_id: Optional[str]) -> Dict[str, int]:
    return {**LIMITS, **get_format(style_id)["limits"]}


def format_fields(style_id: Optional[str]) -> Dict[str, Any]:
    """What the text editor shows for a style: every slot with its count and its length limit(s)."""
    fmt, lim = get_format(style_id), format_limits(style_id)
    fields: Dict[str, Any] = {}
    for slot, count in fmt["slots"].items():
        if slot == "specs":
            fields[slot] = {"count": count, "limit_name": lim["spec_name"], "limit_value": lim["spec_value"]}
        else:
            fields[slot] = {"count": count, "limit": lim[_LIMIT_KEYS.get(slot, slot)]}
    return fields


def count_blocks(spec: CopySpec) -> int:
    """Separate pieces of text on the picture. The prices and the discount read as one block."""
    return (
        sum(1 for v in (spec.title, spec.subtitle, spec.badge, spec.deadline, spec.cta, spec.contact, spec.brand_name) if v)
        + len(spec.bullets) + len(spec.specs) + len(spec.uses) + (1 if (spec.price or spec.old_price or spec.discount) else 0)
    )


def apply_slots(spec: CopySpec, style_id: Optional[str]) -> CopySpec:
    """The part of the copy this format shows, re-clamped to the format's own limits.
    A slot the format does not have is dropped: a price passed to a format without a price never reaches the picture."""
    fmt = get_format(style_id)
    slots = fmt["slots"]
    data = spec.to_dict()
    kept: Dict[str, Any] = {"lang": spec.lang, "legacy": spec.legacy}
    for slot, attr, is_list, _ in _SLOT_ATTRS:
        count = slots.get(slot, 0)
        if not count:
            continue
        kept[attr] = data[attr][:count] if is_list else data[attr]
    if not slots.get("price"):
        kept.pop("old_price", None)
    out = CopySpec.from_dict(kept, format_limits(style_id))
    if not slots.get("discount"):
        out.discount = ""
    if not slots.get("old_price"):
        out.old_price = ""
    # Too many pieces of text is where image models start to misspell: trim the longest lists first
    while count_blocks(out) > fmt["max_blocks"]:
        if len(out.bullets) > 1 and len(out.bullets) >= max(len(out.specs), len(out.uses)):
            out.bullets.pop()
        elif len(out.specs) > 1 and len(out.specs) >= len(out.uses):
            out.specs.pop()
        elif out.uses:
            out.uses.pop()
        elif out.subtitle:
            out.subtitle = ""
        elif out.contact:
            out.contact = ""
        else:
            break
    return out


def shorten_copy(spec: CopySpec, style_id: Optional[str]) -> CopySpec:
    """A lighter version of the same copy for the last attempt: fewer and shorter strings are easier to draw right.
    Facts are not rewritten: optional lines are dropped (subtitle, captions, the last benefit), the rest stays."""
    out = CopySpec.from_dict(apply_slots(spec, style_id).to_dict(), format_limits(style_id))
    out.subtitle = ""
    out.uses = []
    if len(out.bullets) > 2:
        out.bullets = out.bullets[:-1]
    if len(out.specs) > 3:
        out.specs = out.specs[:3]
    return out


def too_long_fields(data: Dict[str, Any], style_id: Optional[str]) -> List[str]:
    """Slots whose raw text is longer than the format allows (the editor highlights them)."""
    lim = format_limits(style_id)
    out: List[str] = []
    for key in ("title", "subtitle", "badge", "deadline", "cta", "contact", "brand_name"):
        if len(" ".join(str(data.get(key) or "").split())) > lim[key]:
            out.append(key)
    for i, b in enumerate(data.get("bullets") or []):
        if len(" ".join(str(b).split())) > lim["bullet"]:
            out.append(f"bullets.{i}")
    return out


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
_LANG_RULE = {
    "ru": "All text is in Russian, Cyrillic script only. Do not translate or transliterate anything.",
    "uz": "All text is in Uzbek, Latin script; the apostrophe in oʻ gʻ (and in words like ta'm) must be visible "
          "exactly where it is given; do not transliterate to Cyrillic.",
}
_ORIENTATION = {
    "1:1": "square 1:1", "3:4": "vertical 3:4", "4:5": "vertical 4:5", "9:16": "tall vertical 9:16 (a phone screen)",
}


def escape_quotes(text: str) -> str:
    """Straight double quotes inside a seller's string would end the quoted string in the prompt: "x" -> «x»."""
    out, opened = [], False
    for ch in text:
        if ch in '"“”„':
            out.append("»" if opened else "«")
            opened = not opened
        else:
            out.append(ch)
    return "".join(out)


def text_items(spec: CopySpec, style_id: Optional[str] = None) -> List[Tuple[str, str]]:
    """(role, exact string) pairs in reading order. Call with the spec already cut to the format (apply_slots)."""
    items: List[Tuple[str, str]] = []
    for _slot, attr, is_list, role in _SLOT_ATTRS:
        value = getattr(spec, attr)
        if attr == "specs":
            items += [(role, f"{n}: {v}") for n, v in value]
        elif is_list:
            items += [(role, v) for v in value]
        elif value:
            items.append((role, value))
    return items


def expected_strings(spec: CopySpec, style_id: Optional[str] = None) -> List[str]:
    """Strings that must be readable on the finished picture (a characteristic is checked name and value apart,
    because a table puts them in different cells)."""
    if style_id:
        spec = apply_slots(spec, style_id)
    out: List[str] = []
    for role, value in text_items(spec):
        if role == "spec":
            name, _, val = value.partition(": ")
            out += [name, val]
        else:
            out.append(value)
    return [escape_quotes(s) for s in out if s]


def describe_color(hex_color: str) -> str:
    """A plain-words name for a brand colour: models follow "deep teal (#0f766e)" better than a bare hex code."""
    try:
        r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    except (ValueError, IndexError, TypeError):
        return ""
    hi, lo = max(r, g, b), min(r, g, b)
    light = (hi + lo) / 2
    if hi - lo < 0.08:
        return "white" if light > 0.9 else "black" if light < 0.12 else "grey"
    d = hi - lo
    if hi == r:
        hue = ((g - b) / d) % 6
    elif hi == g:
        hue = (b - r) / d + 2
    else:
        hue = (r - g) / d + 4
    hue *= 60
    name = next(n for limit, n in ((20, "red"), (45, "orange"), (70, "yellow"), (165, "green"), (200, "teal"),
                                   (255, "blue"), (290, "violet"), (335, "pink"), (361, "red")) if hue < limit)
    tone = "light " if light > 0.7 else "deep " if light < 0.35 else ""
    return tone + name


def build_render_prompt(copy: CopySpec, style: str, aspect: str = "3:4", brand: Optional[Dict[str, Any]] = None) -> str:
    """The prompt for one picture with text. `brand` may carry brand_color (#rrggbb) and has_logo."""
    spec = apply_slots(copy, style)
    fmt = get_format(style)
    brand = brand or {}
    lines = [
        f"Design a finished advertising image for an online shop, {_ORIENTATION.get(aspect, _ORIENTATION['3:4'])} orientation.",
        "Use the product from the first reference photo EXACTLY as it is: same shape, colours, pattern and every detail. "
        "Remove the original background and all clutter or other objects around it.",
        f"DESIGN: {fmt['brief']}",
        _LANG_RULE[spec.lang],
        "TEXT: write ONLY the text blocks below. Each string is given between quotation marks: copy it letter by letter. "
        "If a block is not listed, leave that element out.",
    ]
    for i, (role, value) in enumerate(text_items(spec), 1):
        position = fmt["positions"].get(role, "")
        lines.append(f'Text block {i} ({_ROLE_NAMES[role]}{", " + position if position else ""}): "{escape_quotes(value)}"')
    lines.append(
        "NUMBERS: write digits exactly as given; thousands separated by a space; the currency word after the number. "
        "Never round, change or reformat a number."
    )
    lines.append(
        "RULES: do not add any other text, numbers, prices, logos or watermarks, and do not invent facts. Never print "
        "the role names or the words 'Text block'. Use plain, highly legible typefaces only (no ornamental, calligraphic "
        "or script fonts). Letters must be sharp, correctly spelled, high-contrast and large enough to read on a phone. "
        "Keep every text block at least 6% of the image size away from every edge."
    )
    color = str(brand.get("brand_color") or "")
    if color and describe_color(color):
        lines.append(f"BRAND: use {describe_color(color)} ({color}) as the accent colour of plates, badges and highlights.")
    if brand.get("has_logo"):
        lines.append(
            "LOGO: the second reference image is the shop's logo. Place it as is, small, in a corner with a clear margin; "
            "do not redraw, recolour, restyle or re-letter it."
        )
    return "\n".join(lines)


def build_edit_prompt(problems: Sequence[Dict[str, str]], lang: str = "ru") -> str:
    """Ask the image model to fix only the strings that came out wrong, on the picture it already drew."""
    lines = ["Edit this image. Fix ONLY the text listed below; keep the layout, the product, the colours, the fonts and "
             "every other element unchanged."]
    for p in problems:
        expected, found = escape_quotes(p.get("expected") or ""), escape_quotes(p.get("found") or "")
        if expected and found:
            lines.append(f'- replace text "{found}" with exactly "{expected}"')
        elif expected:
            lines.append(f'- the text "{expected}" is missing or misspelled: write exactly "{expected}" in its place')
        elif found:
            lines.append(f'- remove the text "{found}": it must not be on the image')
    lines.append(_LANG_RULE["uz" if lang == "uz" else "ru"])
    lines.append("Write digits exactly as given; thousands separated by a space. Do not add any other text, numbers, "
                 "prices, logos or watermarks.")
    return "\n".join(lines)


OCR_PROMPT = (
    "You are an OCR engine. Scan the WHOLE image systematically from top to bottom, including small captions under "
    "icons, text at the very bottom and at the edges, and text inside badges, buttons and decorative elements. "
    "Transcribe every piece of text exactly as written, letter by letter: never correct spelling, never translate, "
    "do not normalise apostrophes or digits, never skip anything. Group the lines into visual blocks: lines that "
    "belong to the same paragraph, plate, badge or table cell go into one block, in reading order. "
    'Return JSON: {"blocks": [{"lines": ["..."]}]}.'
)


def parse_ocr(data: Any) -> List[List[str]]:
    """The reader's answer as blocks of lines. Accepts {"blocks": [{"lines": [...]}]}, {"lines": [...]} or a list."""
    def text(x: Any) -> str:
        return x if isinstance(x, str) else str(x.get("text", "")) if isinstance(x, dict) else str(x)

    if isinstance(data, dict) and isinstance(data.get("blocks"), list):
        blocks = []
        for block in data["blocks"]:
            lines = block.get("lines") if isinstance(block, dict) else block if isinstance(block, list) else [block]
            lines = [text(l).strip() for l in (lines or [])]
            if any(lines):
                blocks.append([l for l in lines if l])
        return blocks
    lines = data.get("lines", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    return [[text(l).strip()] for l in lines if text(l).strip()]  # no grouping given: every line is its own block


# ---------------------------------------------------------------------------
# Checking the finished picture
# ---------------------------------------------------------------------------
# Latin letters that look exactly like Cyrillic ones: the image reader may return either for the same glyph
_LOOKALIKES = str.maketrans({"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у", "k": "к"})
_APOSTROPHES = "'’ʻʼ‘`´ʹ′"
_DASHES = "-‐‑‒–—−"
_TOKEN_SPLIT = re.compile(r"[\s:;|•·/\\]+")


def _canon_token(token: str) -> str:
    """Soft: case, dashes, quotes and most punctuation do not matter. Strict: letters, digits, the percent sign,
    apostrophes (any style counts as the same apostrophe, but it may not disappear) and a decimal comma or point."""
    token = token.casefold().replace("ё", "е")
    out = []
    for i, ch in enumerate(token):
        if ch in _APOSTROPHES:
            out.append("'")
        elif ch.isalnum() or ch == "%":
            out.append(ch)
        elif ch in ".," and 0 < i < len(token) - 1 and token[i - 1].isdigit() and token[i + 1].isdigit():
            out.append(",")
    text = "".join(out).translate(_LOOKALIKES)
    return text if text.strip("'") else ""


def tokenize(text: str) -> List[str]:
    """Canonical tokens of a line. Runs of pure-digit tokens are joined: "380 000" and "380000" are the same number,
    and "1 380 000" is a different one."""
    raw = [t for t in (_canon_token(t) for t in _TOKEN_SPLIT.split(text.replace(" ", " "))) if t]
    out: List[str] = []
    for t in raw:
        if out and t.isdigit() and out[-1].isdigit():
            out[-1] += t
        else:
            out.append(t)
    return out


def _has_digit(token: str) -> bool:
    return any(c.isdigit() for c in token)


def _find_all(haystack: List[str], needle: List[str]) -> List[int]:
    n = len(needle)
    return [i for i in range(len(haystack) - n + 1) if haystack[i:i + n] == needle] if n else []


def verify_text(blocks: Sequence[Sequence[str]], expected: Iterable[str]) -> Dict[str, Any]:
    """Compare the text read from a picture with the approved strings.

    Every expected string must be found as whole tokens inside ONE line, or across consecutive lines of ONE block
    (a long title wraps). A string pieced together from two different blocks is not a match, and neither is a
    number that only appears inside a longer number.

    Returns {"verified", "problems": [{"expected", "found"}], "unexpected": [...]}:
      - a missing or misspelled string -> problem with the closest text that was read in `found`;
      - a number or price on the picture that nobody asked for -> problem with expected "" (it triggers a retry);
      - other extra words are only listed in `unexpected`.
    """
    expected = [e for e in expected if tokenize(e)]
    block_tokens: List[List[str]] = []
    block_owner: List[List[int]] = []  # token index -> line index inside the block
    all_lines: List[str] = []
    line_ids: List[List[int]] = []
    for block in blocks:
        tokens, owners, ids = [], [], []
        for line in block:
            ids.append(len(all_lines))
            all_lines.append(line)
            for t in tokenize(line):
                tokens.append(t)
                owners.append(len(ids) - 1)
        block_tokens.append(tokens)
        block_owner.append(owners)
        line_ids.append(ids)

    covered = [[False] * len(t) for t in block_tokens]
    problems: List[Dict[str, str]] = []
    for e in expected:
        needle = tokenize(e)
        hit = False
        for bi, tokens in enumerate(block_tokens):
            for start in _find_all(tokens, needle):
                hit = True
                for k in range(start, start + len(needle)):
                    covered[bi][k] = True
        if not hit:
            problems.append({"expected": e, "found": _closest(e, all_lines)})

    unexpected: List[str] = []
    for bi, tokens in enumerate(block_tokens):
        extra_by_line: Dict[int, List[str]] = {}
        for k, token in enumerate(tokens):
            if not covered[bi][k]:
                extra_by_line.setdefault(block_owner[bi][k], []).append(token)
        for li, extra in extra_by_line.items():
            line = all_lines[line_ids[bi][li]]
            if any(_has_digit(t) for t in extra):
                # an invented number, price or percentage is the worst mistake a card can have
                if not any(p["found"] == line for p in problems):
                    problems.append({"expected": "", "found": line})
            elif sum(len(t) for t in extra) >= 4 and line not in unexpected:
                unexpected.append(line)
    return {"verified": not problems, "problems": problems, "unexpected": unexpected}


def _closest(expected: str, lines: List[str]) -> str:
    """The line that most looks like the expected string (what the model probably wrote instead), or ""."""
    target = "".join(tokenize(expected))
    best, best_score = "", 0.55
    for line in lines:
        score = difflib.SequenceMatcher(None, target, "".join(tokenize(line))).ratio()
        if score > best_score:
            best, best_score = line, score
    return best
