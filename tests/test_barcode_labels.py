"""Scannable Code 128 barcodes on Uzum shipping labels."""
import io
import itertools

import pytest
from PIL import Image

from conftest import auth, login
from services.barcode import code128_values, encode_code128, sanitize_barcode_text

barcode_ref = pytest.importorskip("barcode")
zxingcpp = pytest.importorskip("zxingcpp")


def _modules(text):
    return "".join(("1" if i % 2 == 0 else "0") * w for i, w in enumerate(encode_code128(text)))


def test_every_symbol_matches_reference_encoder():
    # Digits separated by letters so the reference encoder stays in subset B
    chars = "".join(c + "x" if c.isdigit() else c for c in map(chr, range(32, 127)))
    for i in range(0, len(chars), 20):
        chunk = chars[i : i + 20]
        assert _modules(chunk) == barcode_ref.get("code128", chunk).build()[0]


def test_every_checksum_symbol_matches_reference_encoder():
    seen = set()
    for a, b, c in itertools.product("ABCDEFGHIJKLMNOPQRSTUVWXYZ-", repeat=3):
        text = f"UZ{a}{b}{c}"
        checksum = code128_values(text)[-2]
        if checksum in seen:
            continue
        seen.add(checksum)
        assert _modules(text) == barcode_ref.get("code128", text).build()[0]
    assert seen == set(range(103))


def test_unencodable_text_is_rejected_or_sanitized():
    with pytest.raises(ValueError):
        encode_code128("Xon-atlas ʻ")
    assert sanitize_barcode_text("UZ-FBS-1\n", "x") == "UZ-FBS-1"
    assert sanitize_barcode_text("ʻʻ", "849201") == "849201"


@pytest.mark.parametrize("size", ["LARGE", "BIG"])
def test_png_label_barcode_scans_back_to_posting_number(client, size):
    from services.uzum_service import uzum_service

    user = login(client, tg_id=910001)
    client.post("/api/uzum/settings", json={"is_demo": True}, headers=auth(user))
    for order in client.get("/api/uzum/orders", headers=auth(user)).json()["orders"][:3]:
        png = uzum_service.generate_thermal_label_image(user["user_id"], order["order_id"], size=size)
        decoded = zxingcpp.read_barcodes(Image.open(io.BytesIO(png)))
        assert [(r.format.name, r.text) for r in decoded] == [("Code128", order["posting_number"])]


def test_svg_label_contains_code128_bars(client):
    from services.uzum_service import uzum_service

    user = login(client, tg_id=910002)
    client.post("/api/uzum/settings", json={"is_demo": True}, headers=auth(user))
    order = client.get("/api/uzum/orders", headers=auth(user)).json()["orders"][0]
    svg = uzum_service.generate_thermal_label_svg(user["user_id"], order["order_id"])
    bar_count = svg.count('fill="#000000" />')
    assert bar_count == sum(1 for i, _ in enumerate(encode_code128(order["posting_number"])) if i % 2 == 0)
    assert order["posting_number"] in svg
