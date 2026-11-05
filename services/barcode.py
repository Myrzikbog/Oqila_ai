"""
barcode.py — Code 128 (subset B) encoder for scannable shipping labels.

encode_code128() returns the barcode as a list of module widths (bar, space, bar, ...),
starting with a bar, so it can be drawn as SVG rectangles or with Pillow.
Subset B covers printable ASCII (32-127): digits, letters and '-', which is
everything an Uzum posting number contains.
"""
from __future__ import annotations

from typing import List, Tuple

# Widths of bar/space elements for each Code 128 symbol value (0-106), standard table.
_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
]
START_B = 104
STOP = 106
QUIET_ZONE_MODULES = 10


def code128_values(text: str) -> List[int]:
    """Symbol values for `text` in subset B, including start, checksum and stop."""
    if not text:
        raise ValueError("Barcode text must not be empty")
    values = [START_B]
    for ch in text:
        code = ord(ch)
        if code < 32 or code > 127:
            raise ValueError(f"Character {ch!r} cannot be encoded in Code 128 subset B")
        values.append(code - 32)
    checksum = values[0] + sum(i * v for i, v in enumerate(values[1:], start=1))
    values.append(checksum % 103)
    values.append(STOP)
    return values


def encode_code128(text: str) -> List[int]:
    """Module widths (bar, space, bar, ...) for `text`, without quiet zones."""
    widths: List[int] = []
    for value in code128_values(text):
        widths.extend(int(w) for w in _PATTERNS[value])
    return widths


def barcode_bars(text: str, x: float, max_width: float) -> Tuple[List[Tuple[float, float]], float]:
    """Lay out the barcode inside [x, x + max_width].

    Returns (bars, module): each bar is (left, width) in pixels, centred in the area with
    quiet zones on both sides. The module width is a whole number of pixels so thermal
    printers render crisp, scannable bars.
    """
    widths = encode_code128(text)
    total_modules = sum(widths) + 2 * QUIET_ZONE_MODULES
    module = max(1, int(max_width // total_modules))
    used = total_modules * module
    cursor = x + (max_width - used) / 2 + QUIET_ZONE_MODULES * module
    bars: List[Tuple[float, float]] = []
    for i, w in enumerate(widths):
        if i % 2 == 0:  # even positions are bars, odd positions are spaces
            bars.append((cursor, w * module))
        cursor += w * module
    return bars, module


def sanitize_barcode_text(text: str, fallback: str) -> str:
    """Keep only characters Code 128 B can encode (and limit the length so it fits a label)."""
    clean = "".join(ch for ch in str(text or "") if 32 <= ord(ch) <= 126).strip()
    return (clean or fallback)[:24]
