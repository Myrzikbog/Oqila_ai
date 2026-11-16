"""Phase 6: cleanups that changed behaviour."""
import io

from PIL import Image

from conftest import auth, login


def _png(color):
    buf = io.BytesIO()
    Image.new("RGB", (600, 800), color).save(buf, format="PNG")
    return buf.getvalue()


def test_clean_uzum_card_reports_whether_the_background_is_white(client, monkeypatch):
    from services import ai_service as ai_module
    from services.imaging import finalize_card, to_data_url

    service = ai_module.ai_service
    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")

    async def text_ok(kind, models, contents, config, accept=None):
        import json
        import types

        return types.SimpleNamespace(text=json.dumps({"title": "t", "description": "", "price_tag": "", "hashtags": [], "marketing_tip": ""}))

    async def white(self, **kw):
        return to_data_url(finalize_card(_png((255, 255, 255)), whiten=True))

    async def grey(self, **kw):
        return to_data_url(finalize_card(_png((120, 120, 120))))

    monkeypatch.setattr(service, "_generate", text_ok)
    who = login(client, tg_id=860001)
    for maker, expected in ((white, True), (grey, False)):
        monkeypatch.setattr(ai_module.AIService, "generate_studio_photo", maker)
        res = client.post("/api/generate-card", data={"note": "x", "photoshoot_style": "uzum_clean"},
                          files={"image": ("p.png", _png((200, 200, 200)), "image/png")}, headers=auth(who)).json()
        assert res["uzum_ready"] == {"white_background": expected}
    scene = client.post("/api/generate-card", data={"note": "x", "photoshoot_style": "flat_lay"},
                        files={"image": ("p.png", _png((200, 200, 200)), "image/png")}, headers=auth(who)).json()
    assert "uzum_ready" not in scene


def test_the_bot_link_comes_from_the_environment(monkeypatch):
    from services.bot_link import bot_url, bot_username

    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)
    assert bot_url() == "https://t.me/oqila_ai_bot"
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "@my_shop_bot")
    assert bot_username() == "my_shop_bot" and bot_url() == "https://t.me/my_shop_bot"
    import inspect

    from services import uzum_service

    assert "t.me/oqila_ai_bot" not in inspect.getsource(uzum_service)


def test_calculator_writes_at_most_one_log_row_per_address_and_ten_seconds(client):
    from main import _should_log_calculation
    from services.database import DB_PATH

    assert _should_log_calculation("203.0.113.1", now=1000.0) is True
    assert _should_log_calculation("203.0.113.1", now=1005.0) is False
    assert _should_log_calculation("203.0.113.2", now=1005.0) is True
    assert _should_log_calculation("203.0.113.1", now=1011.0) is True

    import sqlite3

    def count():
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute("SELECT COUNT(*) FROM usage_logs WHERE event_type = 'calculate'").fetchone()[0]

    before = count()
    for _ in range(5):
        assert client.post("/api/calculate", json={"sale_price": 380000, "cost_price": 120000}).status_code == 200
    assert count() - before <= 1


def test_dead_code_is_gone():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    assert "PHOTOSHOOT_PRESETS" not in (root / "services" / "ai_service.py").read_text(encoding="utf-8")
    assert "def get_subscribers" not in (root / "services" / "database.py").read_text(encoding="utf-8")
    assert "_get_loop" not in (root / "services" / "ai_service.py").read_text(encoding="utf-8")
