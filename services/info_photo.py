"""
info_photo.py — information cards for marketplaces (Uzum): the product photo with titles, benefits,
characteristics, size lines and icons, drawn by the AI image model in the style of real Uzum cards.

The image model now spells Russian and Uzbek text correctly most of the time, but "most of the time" is not
good enough for a price, a size or a spelling on a product card. So every generated card is *verified*:
a second AI call reads the text back from the picture and it is compared with the text the seller approved;
a mismatch triggers a retry with the exact strings repeated. The server-drawn poster (services/poster.py)
stays available as the always-exact alternative.

Pure functions only (prompts, parsing, comparison): the network calls live in services/ai_service.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

LIMITS = {"title": 48, "tagline": 56, "benefit": 44, "spec_name": 22, "spec_value": 30, "badge": 34, "use": 16}
MAX_BENEFITS, MAX_SPECS, MAX_USES = 4, 5, 4
MAX_FACT_LINES = 10


def _clean(value: Any, limit: int) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())[:limit]


# ---------------------------------------------------------------------------
# What goes on the card
# ---------------------------------------------------------------------------
@dataclass
class InfoSpec:
    title: str = ""
    tagline: str = ""
    benefits: List[str] = field(default_factory=list)
    specs: List[Tuple[str, str]] = field(default_factory=list)
    badge: str = ""
    uses: List[str] = field(default_factory=list)
    lang: str = "ru"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InfoSpec":
        specs: List[Tuple[str, str]] = []
        for item in (data.get("specs") or [])[:MAX_SPECS]:
            if isinstance(item, dict):
                name, value = item.get("name"), item.get("value")
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                name, value = item
            else:
                continue
            name, value = _clean(name, LIMITS["spec_name"]), _clean(value, LIMITS["spec_value"])
            if name and value:
                specs.append((name, value))
        return cls(
            title=_clean(data.get("title"), LIMITS["title"]),
            tagline=_clean(data.get("tagline"), LIMITS["tagline"]),
            benefits=[b for b in (_clean(x, LIMITS["benefit"]) for x in (data.get("benefits") or [])[:MAX_BENEFITS * 2]) if b][:MAX_BENEFITS],
            specs=specs,
            badge=_clean(data.get("badge"), LIMITS["badge"]),
            uses=[u for u in (_clean(x, LIMITS["use"]) for x in (data.get("uses") or [])[:MAX_USES * 2]) if u][:MAX_USES],
            lang="uz" if data.get("lang") == "uz" else "ru",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title, "tagline": self.tagline, "benefits": list(self.benefits),
            "specs": [{"name": n, "value": v} for n, v in self.specs], "badge": self.badge,
            "uses": list(self.uses), "lang": self.lang,
        }


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
            benefits.append(_clean(line, LIMITS["benefit"]))
        if len(benefits) + len(specs) >= MAX_FACT_LINES:
            break
    return benefits, specs


# Claims a seller must be able to stand behind: the AI may not add them on its own (the seller can still write them)
_RISKY = re.compile(
    r"преми|престиж|высок\w*\s+качеств|лучш|№\s*1|номер\s+один|гаранти|сертифиц|100\s*%|оригинал|эксклюзив|"
    r"premium|prestij|eng\s+yaxshi|kafolat|sertifikat|original|eksklyuziv|yuqori\s+sifat",
    re.IGNORECASE,
)


def build_spec(suggestions: Dict[str, Any], facts_text: Optional[str], title_hint: str, lang: str,
               allowed_text: Optional[str] = None) -> InfoSpec:
    """Seller facts first; AI suggestions only fill the gaps (and are shown to the seller for review).

    AI-written lines containing promises or superlatives ("premium", "highest quality", "guarantee", "100%", ...)
    are dropped unless the seller wrote such a word themselves (in the facts or in the product description).
    """
    own_benefits, own_specs = parse_facts(facts_text)
    ai = InfoSpec.from_dict({**suggestions, "lang": lang})
    seller_text = f"{facts_text or ''}\n{allowed_text or ''}"

    def safe(text: str) -> bool:
        found = _RISKY.search(text)
        return not found or bool(re.search(re.escape(found.group(0)), seller_text, re.IGNORECASE))

    ai_benefits = [b for b in ai.benefits if b not in own_benefits and safe(b)]
    return InfoSpec(
        title=ai.title if (ai.title and safe(ai.title)) else _clean(title_hint, LIMITS["title"]),
        tagline=ai.tagline if safe(ai.tagline) else "",
        benefits=(own_benefits + ai_benefits)[:MAX_BENEFITS],
        specs=own_specs[:MAX_SPECS],  # sizes, weights, materials: only what the seller wrote, never guessed
        badge=ai.badge if safe(ai.badge) else "",
        uses=[u for u in ai.uses if safe(u)],
        lang="uz" if lang == "uz" else "ru",
    )


# ---------------------------------------------------------------------------
# Design briefs: one per template, modelled on real Uzum cards
# ---------------------------------------------------------------------------
BRIEFS: Dict[str, str] = {
    "info_white_specs": (
        "Clean e-commerce card on a pure white background. The title sits at the top in bold black capital letters. "
        "The product is shown large in the centre. If sizes are listed, draw thin dimension lines with small arrowheads "
        "next to the product carrying exactly those size labels. Under the product, a simple two-column block of "
        "characteristics in dark grey text (name on the left, value on the right). Minimalist, lots of white space."
    ),
    "info_theme_benefits": (
        "Dynamic themed advertising poster. A rich colourful background that matches the product's main colour and mood. "
        "A huge bold title at the top with the tagline in smaller letters under it. The product is large and dominant. "
        "The benefits are stacked on the left side, each with a small round line icon and a short caption. "
        "A round starburst badge in a lower corner carries the badge text (only if a badge text is given). "
        "Along the very bottom runs a row of small icon tiles with short captions (only if captions are listed)."
    ),
    "info_headline": (
        "Lifestyle product photo: the product shown in a natural, stylish use scene (no faces, hands or legs only, or a "
        "tasteful surface). A giant heavy-weight headline with the title spans the lower part of the image in a bold "
        "colour that contrasts with the photo. Up to two small icon-and-word labels sit in the top-left corner."
    ),
    "info_collection": (
        "Collector's-edition poster: a dramatic themed background, the product (or the group of items) in the foreground "
        "looking premium, a huge stylised title across the top. A row of small icons with short captions runs along the "
        "bottom edge, one per listed benefit."
    ),
    "info_dark_list": (
        "Dark grunge poster: a black and charcoal textured background, the product large on one side. A bold stylised "
        "title with the tagline under it. A vertical list of the benefits, each with a small circular line icon and a "
        "short bold caption. If a characteristic is listed, show it as a bold stamp-like label near the lower left. "
        "A thin strip with short captions runs along the bottom edge (only if captions are listed)."
    ),
    "info_dark_pills": (
        "Premium dark satin-textured background with subtle sparkles. The product is centred and lit like a jewellery "
        "shot. The title is large at the top with the tagline in smaller letters beneath it. The benefits appear as "
        "rounded translucent pills with a small icon each, placed on both sides of the product."
    ),
    "info_callouts": (
        "Clean marketplace infographic on a light neutral gradient background. The product is large in the centre. "
        "The title is at the top. The benefits are short callouts placed around the product, each connected to it with "
        "a thin line ending in a small dot. Modern sans-serif typography."
    ),
    "info_table": (
        "Clean marketplace card. The product occupies the upper half on a soft light studio background. Below it, a tidy "
        "characteristics table with one row per listed characteristic: the name on the left in bold, the value on the "
        "right. The title is at the very top."
    ),
}

# Which parts of the spec each template shows (the prompt and the verification use only these)
SLOTS: Dict[str, Dict[str, int]] = {
    "info_white_specs": {"tagline": 0, "benefits": 0, "specs": 4, "badge": 0, "uses": 0},
    "info_theme_benefits": {"tagline": 1, "benefits": 3, "specs": 0, "badge": 1, "uses": 4},
    "info_headline": {"tagline": 0, "benefits": 0, "specs": 0, "badge": 0, "uses": 2},
    "info_collection": {"tagline": 0, "benefits": 3, "specs": 0, "badge": 0, "uses": 0},
    "info_dark_list": {"tagline": 1, "benefits": 4, "specs": 1, "badge": 0, "uses": 4},
    "info_dark_pills": {"tagline": 1, "benefits": 3, "specs": 0, "badge": 0, "uses": 0},
    "info_callouts": {"tagline": 0, "benefits": 4, "specs": 0, "badge": 0, "uses": 0},
    "info_table": {"tagline": 0, "benefits": 0, "specs": 5, "badge": 0, "uses": 0},
}


def apply_slots(spec: InfoSpec, style_id: str) -> InfoSpec:
    """The part of the spec that this template actually shows."""
    slots = SLOTS.get(style_id, SLOTS["info_callouts"])
    return InfoSpec(
        title=spec.title,
        tagline=spec.tagline if slots["tagline"] else "",
        benefits=spec.benefits[: slots["benefits"]],
        specs=spec.specs[: slots["specs"]],
        badge=spec.badge if slots["badge"] else "",
        uses=spec.uses[: slots["uses"]],
        lang=spec.lang,
    )


_LANG_NAME = {"ru": "Russian (Cyrillic)", "uz": "Uzbek (Latin script, with the apostrophes in o', g' and the like)"}


def text_items(spec: InfoSpec) -> List[Tuple[str, str]]:
    """(role, exact string) pairs in the order they are written into the prompt."""
    items: List[Tuple[str, str]] = []
    if spec.title:
        items.append(("Title", spec.title))
    if spec.tagline:
        items.append(("Tagline", spec.tagline))
    for i, b in enumerate(spec.benefits, 1):
        items.append(("Benefit", b))
    for name, value in spec.specs:
        items.append(("Characteristic", f"{name}: {value}"))
    if spec.badge:
        items.append(("Badge", spec.badge))
    for i, u in enumerate(spec.uses, 1):
        items.append(("Caption", u))
    return items


def expected_strings(spec: InfoSpec, style_id: Optional[str] = None) -> List[str]:
    """Strings that must be readable on the finished card (characteristics are checked name and value apart)."""
    if style_id:
        spec = apply_slots(spec, style_id)
    out: List[str] = []
    out += [spec.title, spec.tagline] + spec.benefits + [spec.badge] + spec.uses
    for name, value in spec.specs:
        out += [name, value]
    return [s for s in out if s]


def build_info_prompt(style_id: str, spec: InfoSpec, aspect: str = "3:4", retry_missing: Optional[List[str]] = None) -> str:
    spec = apply_slots(spec, style_id)
    brief = BRIEFS.get(style_id, BRIEFS["info_callouts"])
    lines = [
        f"Design a marketplace product card image for Uzum Market, vertical {aspect}.",
        "Use the product from the reference photo EXACTLY as it is: same shape, colours, pattern and every detail. "
        "Remove the original background and all clutter or other objects around it.",
        f"All text on the card is in {_LANG_NAME[spec.lang]}.",
        f"DESIGN: {brief}",
        "TEXT: write ONLY the following strings, spelled exactly letter by letter as given between the quotation marks. "
        "If an element below is not listed, leave that element out.",
    ]
    for role, value in text_items(spec):
        lines.append(f'- {role}: "{value}"')
    lines.append(
        "RULES: do not add any other words, numbers, prices, discounts, logos, brand names, stamps or watermarks and do not "
        "invent facts. Use plain, highly legible typefaces only (no ornamental, calligraphic or script fonts). Letters must be "
        "sharp, correctly spelled, high-contrast and large enough to read on a phone. Never print the labels 'Title', "
        "'Tagline', 'Benefit', 'Characteristic', 'Badge' or 'Caption' themselves. Keep all text fully inside the image "
        "with a comfortable margin."
    )
    if retry_missing:
        lines.append(
            "IMPORTANT: a previous attempt misspelled or omitted these strings. Render them again with perfect spelling: "
            + "; ".join(f'"{m}"' for m in retry_missing)
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Checking the finished picture
# ---------------------------------------------------------------------------
# Latin letters that look exactly like Cyrillic ones: the image reader may return either for the same glyph
_LOOKALIKES = str.maketrans({"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у", "k": "к"})


def normalize(text: str) -> str:
    """Letters and digits only, lower case. Apostrophe styles (' ’ ʻ ʼ), dashes, spacing, caps and look-alike
    Latin/Cyrillic letters do not matter: the same transformation is applied to both sides of a comparison."""
    text = text.casefold().replace("ё", "е")
    text = re.sub(r"[\W_]+", "", text)
    return text.translate(_LOOKALIKES)


def find_missing(found_lines: Iterable[str], expected: Iterable[str]) -> List[str]:
    """Expected strings that cannot be found in the text read back from the picture."""
    haystack = normalize("".join(found_lines))
    return [e for e in expected if normalize(e) and normalize(e) not in haystack]


def find_unexpected(found_lines: Iterable[str], expected: Iterable[str]) -> List[str]:
    """Text on the picture that was not requested (reported to the seller; not a reason to retry)."""
    allowed = normalize("".join(expected))
    return [l for l in found_lines if len(normalize(l)) >= 4 and normalize(l) not in allowed]
