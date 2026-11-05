"""Telegram initData verification, session tokens and login flow."""
import time

from conftest import ADMIN_KEY, auth, login, make_init_data
from services.auth_service import verify_telegram_init_data
from services.session_service import (
    check_admin_key,
    create_session_token,
    get_webhook_secret,
    verify_session_token,
)


def test_valid_init_data_is_accepted():
    user = verify_telegram_init_data(make_init_data(555001, "Malika"))
    assert user and user["id"] == 555001


def test_tampered_init_data_is_rejected():
    data = make_init_data(555002).replace("555002", "555003")
    assert verify_telegram_init_data(data) is None


def test_init_data_signed_with_other_bot_is_rejected():
    assert verify_telegram_init_data(make_init_data(555004, token="999:OTHER")) is None


def test_expired_init_data_is_rejected():
    old = int(time.time()) - 3 * 24 * 3600
    assert verify_telegram_init_data(make_init_data(555005, auth_date=old)) is None


def test_init_data_without_bot_token_is_rejected(monkeypatch):
    data = make_init_data(555006, token="")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    assert verify_telegram_init_data(data) is None


def test_session_token_roundtrip_and_tampering():
    token = create_session_token(42)
    assert verify_session_token(token) == 42
    body, sig = token.split(".")
    assert verify_session_token(f"{body}.{sig[:-2]}xx") is None
    assert verify_session_token("garbage") is None
    assert verify_session_token(None) is None


def test_expired_session_token_is_rejected():
    assert verify_session_token(create_session_token(42, ttl_seconds=-10)) is None


def test_admin_key_check(monkeypatch):
    assert check_admin_key(ADMIN_KEY)
    assert not check_admin_key("wrong")
    assert not check_admin_key("oqila_admin_2026")
    monkeypatch.setenv("ADMIN_SECRET_KEY", "short")
    assert not check_admin_key("short"), "keys under 16 chars must disable admin access"
    monkeypatch.setenv("ADMIN_SECRET_KEY", "")
    assert not check_admin_key("")


def test_webhook_secret_is_always_set_when_bot_configured(monkeypatch):
    assert get_webhook_secret()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "explicit_secret")
    assert get_webhook_secret() == "explicit_secret"


def test_telegram_login_returns_session(client):
    data = login(client, tg_id=777001)
    assert data["is_telegram"] is True
    assert data["profile"]["tg_id"] == 777001
    assert verify_session_token(data["session_token"]) == data["user_id"]


def test_invalid_init_data_login_is_rejected(client):
    res = client.post("/api/auth/login", json={"init_data": "user=%7B%22id%22%3A1%7D&hash=bad"})
    assert res.status_code == 401


def test_guest_cannot_choose_telegram_identity(client):
    victim = login(client, tg_id=777002)
    res = client.post("/api/auth/login", json={"profile": {"guest_id": 777002}})
    assert res.status_code == 200
    guest = res.json()
    assert guest["user_id"] != victim["user_id"]
    assert guest["profile"]["tg_id"] < 0, "guests get negative ids that cannot collide with Telegram ids"


def test_guest_session_is_reused(client):
    first = login(client)
    again = login(client, token=first["session_token"])
    assert again["user_id"] == first["user_id"]


def test_profile_requires_auth_and_ignores_user_id(client):
    assert client.get("/api/profile").status_code == 401
    a = login(client, tg_id=777003)
    b = login(client, tg_id=777004)
    res = client.put("/api/profile", json={"user_id": b["user_id"], "name": "Hacked"}, headers=auth(a))
    assert res.status_code == 200
    assert res.json()["profile"]["user_id"] == a["user_id"]
    b_profile = client.get("/api/profile", headers=auth(b)).json()
    assert b_profile["name"] != "Hacked"


def test_disabled_user_cannot_use_api(client):
    from services.database import toggle_user_active

    data = login(client, tg_id=777005)
    toggle_user_active(data["user_id"])
    assert client.get("/api/profile", headers=auth(data)).status_code == 403
    res = client.post("/api/auth/login", json={"init_data": make_init_data(777005)})
    assert res.status_code == 403
