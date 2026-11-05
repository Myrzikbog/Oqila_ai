"""Access control: path traversal, per-user data isolation, admin and webhook protection."""
import pytest

from conftest import ADMIN_KEY, auth, login, make_init_data


# --- Static files / path traversal -----------------------------------------------------------

@pytest.mark.parametrize(
    "path",
    ["/..%2F..%2Fmain.py", "/..%2F..%2F.env.example", "/%2E%2E/%2E%2E/requirements.txt", "/....//main.py"],
)
def test_path_traversal_does_not_leak_files(client, path):
    res = client.get(path)
    assert "FastAPI" not in res.text and "fastapi==" not in res.text and "GEMINI_API_KEY" not in res.text


def test_spa_still_served(client):
    res = client.get("/some/deep/link")
    assert res.status_code == 200
    assert "<html" in res.text.lower()


# --- Card history isolation -------------------------------------------------------------------

def _make_card(client, who):
    res = client.get("/api/demo-card?lang=ru", headers=auth(who))
    assert res.status_code == 200, res.text
    return res.json()["id"]


def test_history_requires_auth(client):
    assert client.get("/api/history").status_code == 401
    assert client.delete("/api/history").status_code == 401
    assert client.post("/api/generate-card", data={"note": "x"}).status_code == 401
    assert client.post("/api/legal-qa", json={"question": "Qanday soliq?"}).status_code == 401


def test_users_cannot_touch_each_others_cards(client):
    alice = login(client, tg_id=880001)
    bob = login(client, tg_id=880002)
    card = _make_card(client, alice)

    # Bob's history does not contain Alice's card, even when asking for her user_id
    res = client.get(f"/api/history?user_id={alice['user_id']}", headers=auth(bob))
    assert card not in [i["id"] for i in res.json()["items"]]

    assert client.post(f"/api/history/{card}/favorite", headers=auth(bob)).status_code == 404
    assert client.delete(f"/api/history/{card}", headers=auth(bob)).status_code == 404
    assert client.get(f"/api/cards/{card}/photo", headers=auth(bob)).status_code == 404

    # Bob clearing "all" history only clears his own
    assert client.delete("/api/history", headers=auth(bob)).status_code == 200
    items = client.get("/api/history", headers=auth(alice)).json()["items"]
    assert card in [i["id"] for i in items]

    assert client.post(f"/api/history/{card}/favorite", headers=auth(alice)).json()["is_favorite"] is True
    assert client.delete(f"/api/history/{card}", headers=auth(alice)).status_code == 200


def test_generate_card_is_saved_for_token_owner(client):
    alice = login(client, tg_id=880003)
    bob = login(client, tg_id=880004)
    res = client.post(
        "/api/generate-card",
        data={"note": "Atlas ko'ylak", "user_id": str(bob["user_id"]), "generate_photo": "false"},
        headers=auth(alice),
    )
    assert res.status_code == 200, res.text
    card_id = res.json()["id"]
    assert card_id in [i["id"] for i in client.get("/api/history", headers=auth(alice)).json()["items"]]
    assert card_id not in [i["id"] for i in client.get("/api/history", headers=auth(bob)).json()["items"]]


def test_generate_card_rejects_non_image_upload(client):
    alice = login(client, tg_id=880005)
    res = client.post(
        "/api/generate-card",
        files={"image": ("x.html", b"<script>", "text/html")},
        headers=auth(alice),
    )
    assert res.status_code == 415


# --- Uzum per-user isolation -------------------------------------------------------------------

def test_uzum_requires_auth(client):
    for path in ("/api/uzum/settings", "/api/uzum/orders", "/api/uzum/stocks", "/api/uzum/finance"):
        assert client.get(path).status_code == 401, path
    assert client.delete("/api/uzum/settings").status_code == 401


def test_uzum_data_is_isolated_between_users(client):
    alice = login(client, tg_id=890001)
    bob = login(client, tg_id=890002)

    assert client.post("/api/uzum/settings", json={"is_demo": True}, headers=auth(alice)).status_code == 200
    orders = client.get("/api/uzum/orders", headers=auth(alice)).json()["orders"]
    assert orders, "demo mode loads orders"
    order_id = orders[0]["order_id"]
    sku_id = client.get("/api/uzum/stocks", headers=auth(alice)).json()["stocks"][0]["sku_id"]

    # Bob sees nothing and cannot act on Alice's shop
    assert client.get("/api/uzum/orders", headers=auth(bob)).json()["orders"] == []
    assert client.get("/api/uzum/shops", headers=auth(bob)).json()["shops"] == []
    assert client.post(f"/api/uzum/orders/{order_id}/confirm", headers=auth(bob)).status_code == 400
    assert client.post(f"/api/uzum/orders/{order_id}/cancel", headers=auth(bob)).status_code == 400
    assert client.get(f"/api/uzum/orders/{order_id}/label.svg", headers=auth(bob)).status_code == 404
    assert client.get(f"/api/uzum/orders/{order_id}/label.png", headers=auth(bob)).status_code == 404
    assert client.post("/api/uzum/stocks/update", json={"sku_id": sku_id, "amount": 0}, headers=auth(bob)).status_code == 404
    assert client.post("/api/uzum/prices/update", json={"sku_id": sku_id, "price": 1}, headers=auth(bob)).status_code == 404

    # Bob connecting demo mode and disconnecting does not affect Alice
    client.post("/api/uzum/settings", json={"is_demo": True}, headers=auth(bob))
    client.delete("/api/uzum/settings", headers=auth(bob))
    assert client.get("/api/uzum/orders", headers=auth(alice)).json()["orders"]
    assert client.get("/api/uzum/orders", headers=auth(bob)).json()["orders"] == []

    # Alice can act on her own data; the label works with ?token= for <img> tags
    assert client.post(f"/api/uzum/orders/{order_id}/confirm", headers=auth(alice)).status_code == 200
    svg = client.get(f"/api/uzum/orders/{order_id}/label.svg?token={alice['session_token']}")
    assert svg.status_code == 200 and svg.text.startswith("<svg")


def test_uzum_settings_never_return_raw_key(client):
    alice = login(client, tg_id=890003)
    client.post("/api/uzum/settings", json={"is_demo": True}, headers=auth(alice))
    settings = client.get("/api/uzum/settings", headers=auth(alice)).json()
    assert "api_key" not in settings
    assert settings["is_connected"] == 1


def test_test_push_goes_only_to_own_chat(client, no_telegram_network):
    alice = login(client, tg_id=890004)
    res = client.post("/api/uzum/test-push", json={"chat_id": 123456789, "lang": "uz"}, headers=auth(alice))
    assert res.status_code == 200
    assert [m["chat_id"] for m in no_telegram_network] == [890004]

    guest = login(client)
    assert client.post("/api/uzum/test-push", json={"lang": "uz"}, headers=auth(guest)).status_code == 400


def test_order_notifications_go_to_owner(client, no_telegram_network):
    import asyncio

    from services.uzum_service import uzum_service

    alice = login(client, tg_id=890005)
    client.post("/api/uzum/settings", json={"is_demo": True}, headers=auth(alice))
    asyncio.run(uzum_service.notify_all_users())
    recipients = {m["chat_id"] for m in no_telegram_network}
    assert 890005 in recipients
    assert all(r > 0 for r in recipients)


def test_legacy_single_tenant_uzum_tables_are_migrated(tmp_path, monkeypatch):
    import sqlite3

    import services.database as db

    legacy = tmp_path / "legacy.db"
    conn = sqlite3.connect(legacy)
    conn.execute("CREATE TABLE uzum_settings (id INTEGER PRIMARY KEY CHECK (id = 1), api_key TEXT)")
    conn.execute("INSERT INTO uzum_settings VALUES (1, 'secret')")
    conn.execute("CREATE TABLE uzum_orders (order_id INTEGER PRIMARY KEY, shop_id INTEGER NOT NULL, status TEXT NOT NULL)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", legacy)
    db.init_db(force=True)
    conn = sqlite3.connect(legacy)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(uzum_settings)")}
    order_cols = {r[1] for r in conn.execute("PRAGMA table_info(uzum_orders)")}
    conn.close()
    assert "user_id" in cols and "user_id" in order_cols


# --- Admin API ---------------------------------------------------------------------------------

def test_admin_requires_valid_key(client):
    assert client.get("/api/admin/dashboard").status_code == 403
    assert client.get("/api/admin/dashboard", headers={"X-Admin-Key": "oqila_admin_2026"}).status_code == 403
    assert client.get("/api/admin/dashboard?key=" + ADMIN_KEY).status_code == 403, "no keys in URLs"
    assert client.get("/api/admin/dashboard", headers={"X-Admin-Key": ADMIN_KEY}).status_code == 200


def test_admin_disabled_without_configured_key(client, monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET_KEY", "")
    assert client.get("/api/admin/dashboard", headers={"X-Admin-Key": ""}).status_code == 503


def test_admin_via_telegram_init_data(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "990001")
    login(client, tg_id=990001)
    ok = client.get("/api/admin/dashboard", headers={"X-Telegram-Init-Data": make_init_data(990001)})
    assert ok.status_code == 200
    login(client, tg_id=990002)
    denied = client.get("/api/admin/dashboard", headers={"X-Telegram-Init-Data": make_init_data(990002)})
    assert denied.status_code == 403


def test_admin_flag_not_granted_to_guests(client):
    guest = login(client)
    assert guest["profile"]["is_admin"] is False


# --- Telegram webhook ---------------------------------------------------------------------------

def test_webhook_management_requires_admin(client):
    assert client.post("/api/set-webhook", json={"url": "https://evil.example"}).status_code == 403
    assert client.get("/api/webhook-info").status_code == 403


def test_webhook_rejects_requests_without_secret(client):
    update = {"update_id": 1, "message": {"chat": {"id": 1}, "from": {"id": 1}, "text": "/start"}}
    assert client.post("/api/telegram-webhook", json=update).status_code == 403
    bad = client.post("/api/telegram-webhook", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "nope"})
    assert bad.status_code == 403


def test_webhook_accepts_correct_secret(client):
    from services.session_service import get_webhook_secret

    res = client.post(
        "/api/telegram-webhook",
        json={"update_id": 2},
        headers={"X-Telegram-Bot-Api-Secret-Token": get_webhook_secret()},
    )
    assert res.status_code == 200
