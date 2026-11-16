"""Phase 4 backend: downloads, send to chat, original photo, export tokens, language kept on the server."""

from conftest import ADMIN_KEY, auth, login, media_qs
from services.imaging import finalize_card


def _card(client, who, png=None):
    import io

    from PIL import Image

    from services.database import save_generated_card
    from services.imaging import to_data_url
    from services.media_storage import store_bytes

    buf = io.BytesIO()
    Image.new("RGB", (60, 80), "teal").save(buf, format="PNG")
    source = store_bytes("source", buf.getvalue(), "jpg")
    return save_generated_card(title="t", description="", price_tag="", hashtags=[], marketing_tip="",
                               studio_photo_url=to_data_url(finalize_card(buf.getvalue())), user_id=who["user_id"], source_photo_url=source)


def test_the_original_photo_is_served_to_its_owner_and_listed_in_the_history(client):
    alice, bob = login(client, tg_id=840001), login(client, tg_id=840002)
    card_id = _card(client, alice)
    item = next(i for i in client.get("/api/history", headers=auth(alice)).json()["items"] if i["id"] == card_id)
    assert item["source_photo_url"] == f"/api/cards/{card_id}/source"
    assert client.get(f"/api/cards/{card_id}/source?{media_qs(client, alice)}").status_code == 200
    assert client.get(f"/api/cards/{card_id}/source?{media_qs(client, bob)}").status_code == 404
    assert client.get(f"/api/cards/{card_id}/source?token={alice['session_token']}").status_code == 401


def test_send_card_to_the_telegram_chat(client, monkeypatch):
    from services.telegram_service import telegram_service

    sent = []

    async def fake_send_document(chat_id, data, filename="x", caption=None, reply_markup=None, mime="text/csv"):
        sent.append((chat_id, filename, mime, data[:3]))
        return True

    monkeypatch.setattr(telegram_service, "send_document", fake_send_document)
    alice, bob, guest = login(client, tg_id=840003), login(client, tg_id=840004), login(client)
    card_id = _card(client, alice)
    assert client.post(f"/api/cards/{card_id}/send", headers=auth(alice)).status_code == 200
    assert sent == [(840003, f"oqila-{card_id}.jpg", "image/jpeg", b"\xff\xd8\xff")]
    assert client.post(f"/api/cards/{card_id}/send", headers=auth(bob)).status_code == 404
    assert client.post(f"/api/cards/{card_id}/send", headers=auth(guest)).status_code == 400
    assert client.post(f"/api/cards/{card_id}/send").status_code == 401

    async def failing(*a, **k):
        return False

    monkeypatch.setattr(telegram_service, "send_document", failing)
    assert client.post(f"/api/cards/{card_id}/send", headers=auth(alice)).status_code == 502


def test_label_downloads_have_attachment_headers(client):
    alice = login(client, tg_id=840005)
    client.post("/api/uzum/settings", json={"is_demo": True}, headers=auth(alice))
    order_id = client.get("/api/uzum/orders", headers=auth(alice)).json()["orders"][0]["order_id"]
    qs = media_qs(client, alice)
    png = client.get(f"/api/uzum/orders/{order_id}/label.png?download=1&{qs}")
    assert png.headers["content-disposition"] == f'attachment; filename="uzum-label-{order_id}.png"' and png.content[:4] == b"\x89PNG"
    assert "content-disposition" not in client.get(f"/api/uzum/orders/{order_id}/label.png?{qs}").headers
    assert "attachment" in client.get(f"/api/uzum/orders/{order_id}/label.svg?download=1&{qs}").headers["content-disposition"]


def test_admin_csv_by_export_token(client):
    from services import session_service

    admin = {"X-Admin-Key": ADMIN_KEY}
    assert client.post("/api/admin/export-token").status_code == 403
    token = client.post("/api/admin/export-token", headers=admin).json()["export_token"]
    ok = client.get(f"/api/admin/export/users.csv?et={token}")
    assert ok.status_code == 200 and "attachment" in ok.headers["content-disposition"]
    assert client.get(f"/api/admin/export/cards.csv?et={token}").status_code == 200
    assert client.get("/api/admin/export/users.csv").status_code == 403
    assert client.get("/api/admin/export/users.csv?et=garbage").status_code == 403
    assert client.get("/api/admin/export/users.csv", headers=admin).status_code == 200, "the admin key still works"
    # tokens are made for one purpose: a picture token does not open the CSV, an export token does not open a picture
    who = login(client, tg_id=840006)
    media = client.post("/api/media-token", headers=auth(who)).json()["media_token"]
    assert client.get(f"/api/admin/export/users.csv?et={media}").status_code == 403
    card_id = _card(client, who)
    assert client.get(f"/api/cards/{card_id}/photo?mt={token}").status_code == 401
    expired = session_service.create_media_token(1, ttl_seconds=-1, aud="admin_export")
    assert client.get(f"/api/admin/export/users.csv?et={expired}").status_code == 403


def test_the_language_can_be_saved_on_its_own(client):
    who = login(client, tg_id=840007)
    res = client.put("/api/profile", json={"lang": "ru"}, headers=auth(who))
    assert res.status_code == 200 and res.json()["profile"]["lang"] == "ru"
    assert client.get("/api/profile", headers=auth(who)).json()["lang"] == "ru"
    client.put("/api/profile", json={"lang": "uz"}, headers=auth(who))
    again = client.post("/api/auth/login", json={"init_data": __import__("conftest").make_init_data(840007), "profile": {}}).json()
    assert again["profile"]["lang"] == "uz" and again["profile"]["name"] == "Tester"
