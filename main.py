"""
main.py — Oqila AI FastAPI Server
Digital ecosystem & Telegram Mini App for women entrepreneurs in Uzbekistan.

Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env FIRST — before any service module is imported
load_dotenv(override=True)

from fastapi import FastAPI, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import services (after env is loaded)
from services.ai_service import ai_service
from services.auth_service import resolve_auth_user, verify_telegram_init_data
from services.database import (
    clear_history,
    delete_history_item,
    get_admin_cards,
    get_admin_dashboard_metrics,
    get_admin_events,
    get_admin_events_count,
    get_all_users,
    get_history,
    get_history_count,
    get_stats,
    get_user,
    get_user_by_tg_id,
    get_users_count,
    init_db,
    log_event,
    save_generated_card,
    toggle_favorite,
    toggle_user_active,
    update_user_profile,
    upsert_user,
)
from services.legal_calc import (
    LEGAL_STEPS_RU,
    LEGAL_STEPS_UZ,
    calculate,
)
from services.telegram_service import telegram_service

from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("oqila_ai")


async def uzum_background_poller():
    """Periodic worker to sync live orders and dispatch Telegram push notifications."""
    await asyncio.sleep(8)
    while True:
        try:
            from services.uzum_service import uzum_service
            await uzum_service.sync_live_orders_and_stocks()
            await uzum_service.check_and_send_notifications()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.debug("Uzum background poller check: %s", exc)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Oqila AI application...")
    init_db()
    poller_task = asyncio.create_task(uzum_background_poller())
    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    if webapp_url and telegram_service.is_configured:
        try:
            res = await telegram_service.set_webhook(webapp_url)
            logger.info("Telegram webhook auto-registration on startup: %s", res)
        except Exception as exc:
            logger.warning("Failed to auto-register telegram webhook on startup: %s", exc)
    yield
    # Shutdown
    logger.info("Shutting down Oqila AI application...")
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Oqila AI — Tadbirkor Qizlar",
    description="AI-powered business assistant for Uzbekistan women entrepreneurs",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Telegram Mini App iframe, mobile clients, and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add standard security headers while keeping Telegram WebApp compatibility."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ---------------------------------------------------------------------------
# Static files & React Frontend (SPA)
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class CalcRequest(BaseModel):
    sale_price: float
    cost_price: float
    lang: str = "ru"
    category: str = "craft"
    business_type: str = "resale"
    trade_regime: str = "ecommerce"
    yatt_type: str = "production"
    fixed_costs: float = 0.0


class LegalQARequest(BaseModel):
    question: str
    lang: str = "ru"
    user_profile: Optional[dict] = None


class SetWebhookRequest(BaseModel):
    url: Optional[str] = None


class UzumSettingsRequest(BaseModel):
    api_key: Optional[str] = None
    is_demo: Optional[bool] = False
    notifications_enabled: Optional[bool] = True
    low_stock_threshold: Optional[int] = 3
    telegram_chat_id: Optional[int] = None


class UzumCancelOrderRequest(BaseModel):
    reason: str = "Отсутствует на складе"


class UzumUpdateStockRequest(BaseModel):
    sku_id: int
    amount: int


class UzumUpdatePriceRequest(BaseModel):
    sku_id: int
    price: float


class UzumTestPushRequest(BaseModel):
    chat_id: Optional[int] = None
    lang: str = "uz"


class UzumUpdateCostPriceRequest(BaseModel):
    sku_id: int
    cost_price: float


class UzumFboAlertRequest(BaseModel):
    sku_id: int
    chat_id: Optional[int] = None


class AuthLoginRequest(BaseModel):
    init_data: Optional[str] = None
    profile: Optional[dict] = None


class UpdateProfileRequest(BaseModel):
    user_id: int
    name: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    sales_channel: Optional[str] = None
    lang: Optional[str] = None


# ---------------------------------------------------------------------------
# Security: Admin API Key Dependency
# ---------------------------------------------------------------------------
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def verify_admin_key(
    header_key: Optional[str] = Security(admin_key_header),
    admin_key: Optional[str] = None,
    key: Optional[str] = None,
) -> bool:
    """Verify administrator access key via X-Admin-Key header or query parameters (?admin_key= or ?key=)."""
    configured_key = os.getenv("ADMIN_SECRET_KEY", "").strip() or "oqila_admin_2026"
    provided_key = (header_key or "").strip() or (admin_key or "").strip() or (key or "").strip()
    if not provided_key or provided_key != configured_key:
        raise HTTPException(status_code=403, detail="Invalid administrator secret key.")
    return True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root():
    """Serve the React SPA (or legacy index)."""
    from fastapi.responses import FileResponse
    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return FileResponse(str(react_index))
    legacy_index = STATIC_DIR / "index.html"
    if legacy_index.exists():
        return FileResponse(str(legacy_index))
    return JSONResponse({"status": "ok", "message": "Oqila AI API is running"})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "ai_mode": "mock" if ai_service.is_mock else "gemini",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# User Authentication & Profile API
# ---------------------------------------------------------------------------
@app.post("/api/auth/login")
async def auth_login(req: AuthLoginRequest):
    """Authenticate via Telegram WebApp initData or fallback browser profile."""
    import time
    resolved = resolve_auth_user(init_data=req.init_data, dev_profile=req.profile)
    tg_id = resolved.get("tg_id")

    if not tg_id:
        client_guest_id = (req.profile or {}).get("guest_id") or (900000000 + int(time.time()) % 10000000)
        tg_id = int(client_guest_id)

    user = upsert_user(
        tg_id=tg_id,
        tg_username=resolved.get("tg_username", ""),
        tg_first_name=resolved.get("tg_first_name", ""),
        name=(req.profile or {}).get("name") or resolved.get("name", ""),
        status=(req.profile or {}).get("status") or resolved.get("status", "self_employed"),
        category=(req.profile or {}).get("category") or resolved.get("category", "sewing"),
        sales_channel=(req.profile or {}).get("salesChannel") or resolved.get("sales_channel", "uzum"),
        lang=(req.profile or {}).get("lang") or resolved.get("lang", "uz"),
    )
    user_with_stats = get_user(user["user_id"])
    if user_with_stats:
        user_with_stats["is_admin"] = telegram_service.is_admin_user(user_with_stats.get("tg_id"))
    log_event(
        event_type="auth_login",
        lang=user.get("lang", "uz"),
        is_mock=False,
        details={"user_id": user["user_id"], "is_telegram": resolved.get("is_authenticated", False)},
        user_id=user["user_id"],
    )
    return JSONResponse(content={
        "status": "ok",
        "user_id": user["user_id"],
        "is_telegram": resolved.get("is_authenticated", False),
        "profile": user_with_stats,
    })


@app.get("/api/profile")
async def get_profile(user_id: Optional[int] = None, tg_id: Optional[int] = None):
    """Retrieve full user profile with statistics."""
    user = None
    if user_id:
        user = get_user(user_id)
    elif tg_id:
        user = get_user_by_tg_id(tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["is_admin"] = telegram_service.is_admin_user(user.get("tg_id"))
    return JSONResponse(content=user)


@app.put("/api/profile")
async def update_profile(req: UpdateProfileRequest):
    """Update user business profile attributes."""
    updated = update_user_profile(
        user_id=req.user_id,
        name=req.name,
        status=req.status,
        category=req.category,
        sales_channel=req.sales_channel,
        lang=req.lang,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    updated["is_admin"] = telegram_service.is_admin_user(updated.get("tg_id"))
    log_event(
        event_type="profile_update",
        lang=updated.get("lang", "uz"),
        details={"user_id": req.user_id},
        user_id=req.user_id,
    )
    return JSONResponse(content={"status": "ok", "profile": updated})


# ---------------------------------------------------------------------------
# Tab 1: AI Studio — Product Card Generation
# ---------------------------------------------------------------------------
@app.post("/api/generate-card")
async def generate_card(
    image: Optional[UploadFile] = File(None),
    cost_price: Optional[float] = Form(None),
    desired_price: Optional[float] = Form(None),
    note: Optional[str] = Form(None),
    lang: str = Form("ru"),
    photoshoot_style: str = Form("minimal_studio"),
    photoshoot_prompt: Optional[str] = Form(None),
    content_tone: str = Form("luxury"),
    content_format: str = Form("instagram"),
    generate_photo: bool = Form(True),
    user_id: Optional[int] = Form(None),
):
    """
    Generate a product marketing card.
    Accepts multipart form with optional image + metadata and photoshoot options.
    Supports generation from image or text description and custom prompts.
    Returns JSON with title, description, price_tag, hashtags, marketing_tip, and studio_photo_url.
    """
    image_bytes: Optional[bytes] = None
    image_mime = "image/jpeg"

    if image and image.filename:
        try:
            image_bytes = await image.read()
            image_mime = image.content_type or "image/jpeg"
            # Validate image size (max 10MB)
            if len(image_bytes) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail="Размер изображения превышает 10 МБ / Rasm hajmi 10 MB dan oshmasligi kerak",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Could not read uploaded image: %s", exc)
            image_bytes = None

    logger.info(
        "generate_card — lang=%s, has_image=%s, style=%s, custom_prompt=%s, tone=%s, format=%s, gen_photo=%s",
        lang,
        image_bytes is not None,
        photoshoot_style,
        bool(photoshoot_prompt),
        content_tone,
        content_format,
        generate_photo,
    )

    result = await ai_service.generate_product_card(
        image_bytes=image_bytes,
        image_mime=image_mime,
        cost_price=cost_price,
        desired_price=desired_price,
        note=note,
        lang=lang,
        photoshoot_style=photoshoot_style,
        photoshoot_prompt=photoshoot_prompt,
        content_tone=content_tone,
        content_format=content_format,
        generate_photo=generate_photo,
    )

    # Save to history database
    card_id = save_generated_card(
        title=result.get("title", ""),
        description=result.get("description", ""),
        price_tag=result.get("price_tag", ""),
        hashtags=result.get("hashtags", []),
        marketing_tip=result.get("marketing_tip", ""),
        studio_photo_url=result.get("studio_photo_url"),
        photoshoot_style=photoshoot_style,
        content_tone=content_tone,
        content_format=content_format,
        cost_price=cost_price,
        desired_price=desired_price,
        note=note,
        lang=lang,
        user_id=user_id,
    )
    result["id"] = card_id

    log_event(
        event_type="generate_card",
        lang=lang,
        is_mock=ai_service.is_mock,
        details={
            "card_id": card_id,
            "title": result.get("title", ""),
            "has_image": image_bytes is not None,
            "style": photoshoot_style,
            "tone": content_tone,
            "format": content_format,
            "has_studio_photo": bool(result.get("studio_photo_url")),
        },
        user_id=user_id,
    )

    return JSONResponse(content=result)


@app.get("/api/demo-card")
async def demo_card(lang: str = "ru"):
    """
    Return a pre-built demo product card (no image processing).
    Used for the «✨ Быстрое демо» button for stage presentations.
    """
    result = await ai_service.generate_product_card(
        image_bytes=None,
        image_mime="image/jpeg",
        cost_price=120_000,
        desired_price=380_000,
        note="Национальный атласный халат/ko'ylak, ручная вышивка",
        lang=lang,
    )

    card_id = save_generated_card(
        title=result.get("title", ""),
        description=result.get("description", ""),
        price_tag=result.get("price_tag", ""),
        hashtags=result.get("hashtags", []),
        marketing_tip=result.get("marketing_tip", ""),
        studio_photo_url=result.get("studio_photo_url"),
        photoshoot_style="minimal_studio",
        content_tone="luxury",
        content_format="instagram",
        cost_price=120_000,
        desired_price=380_000,
        note="Демонстрационный образец",
        lang=lang,
    )
    result["id"] = card_id

    log_event(
        event_type="demo_card",
        lang=lang,
        is_mock=True,
        details={"card_id": card_id, "title": result.get("title", "")},
    )

    return JSONResponse(content=result)


@app.get("/api/photoshoot-presets")
async def get_photoshoot_presets():
    """Return available photoshoot presets and their default prompts."""
    from services.ai_service import PHOTOSHOOT_PRESETS, TONE_PRESETS, FORMAT_PRESETS
    return {
        "styles": PHOTOSHOOT_PRESETS,
        "tones": TONE_PRESETS,
        "formats": FORMAT_PRESETS,
    }


# ---------------------------------------------------------------------------
# History & Catalog API
# ---------------------------------------------------------------------------
@app.get("/api/history")
async def get_cards_history(
    limit: int = 50,
    offset: int = 0,
    favorites_only: bool = False,
    search: str = "",
    user_id: Optional[int] = None,
):
    """Retrieve history of generated product cards with search, favorites, user isolation, and pagination."""
    items = get_history(limit=limit, offset=offset, favorites_only=favorites_only, search=search, user_id=user_id)
    total = get_history_count(favorites_only=favorites_only, search=search, user_id=user_id)
    return {
        "items": items,
        "count": len(items),
        "total": total,
        "total_count": total,
        "limit": limit,
        "offset": offset,
        "favorites_only": favorites_only,
        "search": search,
        "user_id": user_id,
    }


@app.post("/api/history/{card_id}/favorite")
async def toggle_card_favorite(card_id: int):
    """Toggle star/favorite flag on a generated card."""
    new_status = toggle_favorite(card_id)
    if new_status is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"status": "ok", "card_id": card_id, "is_favorite": new_status}


@app.delete("/api/history/{card_id}")
async def delete_card_history_item(card_id: int):
    """Delete a single card from history."""
    success = delete_history_item(card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"status": "ok", "deleted_id": card_id}


@app.get("/api/cards/{card_id}/photo")
async def get_card_photo(card_id: int):
    """Serve card studio photo on-demand with high-performance caching."""
    from services.database import get_db_connection
    import base64
    from fastapi.responses import RedirectResponse

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT studio_photo_url FROM generated_cards WHERE id = ?", (card_id,))
        row = cursor.fetchone()
        if not row or not row["studio_photo_url"]:
            raise HTTPException(status_code=404, detail="Photo not found")

        photo_val = row["studio_photo_url"]
        if photo_val.startswith("data:"):
            try:
                header, b64_data = photo_val.split(",", 1)
                mime = "image/jpeg"
                if "image/png" in header:
                    mime = "image/png"
                elif "image/webp" in header:
                    mime = "image/webp"
                raw_bytes = base64.b64decode(b64_data)
                return Response(
                    content=raw_bytes,
                    media_type=mime,
                    headers={"Cache-Control": "public, max-age=604800, immutable"},
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Failed to decode photo: {exc}")
        elif photo_val.startswith("http"):
            return RedirectResponse(url=photo_val)
        else:
            raise HTTPException(status_code=404, detail="Invalid photo URL")


@app.delete("/api/history")
async def clear_all_cards_history():
    """Clear all card history."""
    clear_history()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# CBU (Central Bank of Uzbekistan) Exchange Rates API (Item 21)
# ---------------------------------------------------------------------------
_cbu_rates_cache = {
    "data": {
        "USD": {"code": "USD", "rate": 12850.0, "diff": "+12.0", "date": "2026-09-27"},
        "EUR": {"code": "EUR", "rate": 13950.0, "diff": "-5.5", "date": "2026-09-27"},
        "RUB": {"code": "RUB", "rate": 138.5, "diff": "+0.4", "date": "2026-09-27"},
        "CNY": {"code": "CNY", "rate": 1780.0, "diff": "+2.1", "date": "2026-09-27"},
    },
    "timestamp": 0.0,
}


@app.get("/api/exchange-rate")
async def get_cbu_exchange_rate():
    """Get official exchange rates from Central Bank of Uzbekistan (CBU) with in-memory caching."""
    import time
    import httpx

    now = time.time()
    # Cache for 1 hour (3600 seconds)
    if now - _cbu_rates_cache["timestamp"] > 3600:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get("https://cbu.uz/ru/arkhiv-kursov-valyut/json/")
                if res.status_code == 200:
                    raw_data = res.json()
                    target_codes = {"USD", "EUR", "RUB", "CNY"}
                    parsed = {}
                    for item in raw_data:
                        code = item.get("Ccy")
                        if code in target_codes:
                            parsed[code] = {
                                "code": code,
                                "name": item.get("CcyNm_RU", code),
                                "rate": float(item.get("Rate", 0)),
                                "diff": item.get("Diff", "0"),
                                "date": item.get("Date", ""),
                            }
                    if len(parsed) >= 2:
                        _cbu_rates_cache["data"] = parsed
                        _cbu_rates_cache["timestamp"] = now
                        logger.info("Updated CBU currency exchange rates cache.")
        except Exception as exc:
            logger.warning("Could not refresh CBU rates, using cache/fallback: %s", exc)

    is_fallback = _cbu_rates_cache["timestamp"] == 0.0
    cache_age = round(now - _cbu_rates_cache["timestamp"]) if not is_fallback else None
    return {
        "rates": _cbu_rates_cache["data"],
        "source": "Марказий банк (cbu.uz)",
        "cached": not is_fallback,
        "is_fallback": is_fallback,
        "cache_age_seconds": cache_age,
    }


# ---------------------------------------------------------------------------
# Tab 2: Calculator & Soliq
# ---------------------------------------------------------------------------
@app.get("/api/finance-meta")
async def get_finance_meta():
    """Return BRV, Uzum categories and tax rates for the frontend."""
    from services.legal_calc import (
        BRV_UZS,
        UZUM_CATEGORY_RATES,
        UZUM_LOGISTICS_BASE_UZS,
        PAYMENT_GATEWAY_RATE,
        DELIVERY_DIRECT_UZS,
        YATT_TURNOVER_TAX_RATE_PROD,
        YATT_TURNOVER_TAX_RATE_SERV,
    )
    return {
        "brv": BRV_UZS,
        "uzum_categories": UZUM_CATEGORY_RATES,
        "uzum_logistics": UZUM_LOGISTICS_BASE_UZS,
        "acquiring_rate": PAYMENT_GATEWAY_RATE,
        "delivery_direct": DELIVERY_DIRECT_UZS,
        "yatt_rate_prod": YATT_TURNOVER_TAX_RATE_PROD,
        "yatt_rate_serv": YATT_TURNOVER_TAX_RATE_SERV,
    }


@app.post("/api/calculate")
async def calculate_profit(req: CalcRequest):
    """
    Calculate profit, margin, taxes and pricing recommendations across sales channels.
    """
    if req.sale_price < 0 or req.cost_price < 0 or req.fixed_costs < 0:
        raise HTTPException(status_code=400, detail="Prices and costs must be non-negative")
    if req.sale_price > 100_000_000_000 or req.cost_price > 100_000_000_000 or req.fixed_costs > 100_000_000_000:
        raise HTTPException(status_code=400, detail="Values exceed allowed maximum limit")

    lang = "uz" if req.lang == "uz" else "ru"

    result = calculate(
        sale_price=req.sale_price,
        cost_price=req.cost_price,
        lang=lang,
        category=req.category,
        business_type=req.business_type,
        trade_regime=req.trade_regime,
        yatt_type=req.yatt_type,
        fixed_costs=req.fixed_costs,
    )

    log_event(
        event_type="calculate",
        lang=req.lang,
        is_mock=False,
        details={
            "sale_price": req.sale_price,
            "cost_price": req.cost_price,
            "net_profit": result.net_profit,
            "margin_pct": result.margin_pct,
            "business_type": req.business_type,
            "trade_regime": req.trade_regime,
            "category": req.category,
        },
    )

    return JSONResponse(
        content={
            "sale_price": result.sale_price,
            "cost_price": result.cost_price,
            "gross_profit": result.gross_profit,
            "margin_pct": result.margin_pct,
            # Business type & Tax details
            "business_type": result.business_type,
            "self_employed_allowed": result.self_employed_allowed,
            "self_employed_warning": result.self_employed_warning_uz if req.lang == "uz" else result.self_employed_warning_ru,
            "tax_name": result.tax_name,
            "tax_rate_effective_pct": result.tax_rate_effective_pct,
            "tax_payable_item": result.tax_payable_item,
            "tax_payable_100": result.tax_payable_100,
            "social_tax_monthly": result.social_tax_monthly,
            "china_import_tip": result.china_import_tip_uz if req.lang == "uz" else result.china_import_tip_ru,
            # Self-employed
            "self_employed_tax": result.self_employed_tax,
            "self_employed_net": result.self_employed_net,
            # YaTT
            "yatt_type": result.yatt_type,
            "yatt_rate_pct": result.yatt_rate_pct,
            "yatt_turnover_tax": result.yatt_turnover_tax,
            "yatt_social_tax_monthly": result.yatt_social_tax_monthly,
            "yatt_net": result.yatt_net,
            # Uzum
            "uzum_category": result.uzum_category,
            "uzum_category_name": result.uzum_category_name,
            "uzum_commission_rate": result.uzum_commission_rate,
            "uzum_commission_amount": result.uzum_commission_amount,
            "uzum_logistics_fee": result.uzum_logistics_fee,
            "uzum_net": result.uzum_net,
            "min_price_uzum": result.min_price_uzum,
            # Telegram
            "telegram_acquiring_fee": result.telegram_acquiring_fee,
            "telegram_net": result.telegram_net,
            "min_price_direct": result.min_price_direct,
            # Break-even
            "fixed_costs": result.fixed_costs,
            "break_even_units_self": result.break_even_units_self,
            "break_even_units_uzum": result.break_even_units_uzum,
            # Shares
            "cost_share_pct": result.cost_share_pct,
            "tax_share_pct": result.tax_share_pct,
            "uzum_share_pct": result.uzum_share_pct,
            "net_share_pct": result.net_share_pct,
            # Compatibility
            "tax_mode": result.tax_mode,
            "tax_amount": result.tax_amount,
            "net_profit": result.net_profit,
            "tip": result.tip_uz if req.lang == "uz" else result.tip_ru,
        }
    )


# ---------------------------------------------------------------------------
# Tab 3: Legal Guide
# ---------------------------------------------------------------------------
@app.get("/api/legal-steps")
async def legal_steps(lang: str = "ru"):
    """Return step-by-step legal guide for business registration in Uzbekistan."""
    steps = LEGAL_STEPS_UZ if lang == "uz" else LEGAL_STEPS_RU
    return JSONResponse(content={"steps": steps})


@app.post("/api/legal-qa")
async def legal_qa(req: LegalQARequest):
    """AI-powered legal Q&A for Uzbekistan business questions."""
    if not req.question or len(req.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question too short")

    answer = await ai_service.legal_qa(
        question=req.question,
        lang=req.lang,
        user_profile=req.user_profile,
    )

    log_event(
        event_type="legal_qa",
        lang=req.lang,
        is_mock=ai_service.is_mock,
        details={
            "question": req.question[:120],
            "has_profile": req.user_profile is not None,
        },
    )

    return JSONResponse(content={"answer": answer})


# ---------------------------------------------------------------------------
# Tab 4: Uzum Market OpenAPI Integration (Multi-Shop, Orders, Stocks, Finance)
# ---------------------------------------------------------------------------
@app.get("/api/uzum/settings")
async def get_uzum_settings_endpoint():
    """Retrieve Uzum API connection settings and status."""
    from services.database import get_uzum_settings
    return JSONResponse(content=get_uzum_settings())


@app.post("/api/uzum/settings")
async def save_uzum_settings_endpoint(req: UzumSettingsRequest):
    """Connect Uzum API key or initialize Demo mode."""
    from services.uzum_service import uzum_service
    res = await uzum_service.connect_and_sync(
        api_key=req.api_key,
        is_demo=bool(req.is_demo),
        telegram_chat_id=req.telegram_chat_id,
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Error connecting Uzum API"))
    return JSONResponse(content=res)


@app.delete("/api/uzum/settings")
async def disconnect_uzum_endpoint():
    """Disconnect and clear all cached Uzum data."""
    from services.database import reset_uzum_data
    reset_uzum_data()
    return JSONResponse(content={"status": "ok", "message": "Uzum API muvaffaqiyatli uzildi"})


@app.get("/api/uzum/shops")
async def get_uzum_shops_endpoint():
    """Get all shops belonging to the seller account."""
    from services.database import get_uzum_shops
    shops = get_uzum_shops()
    return JSONResponse(content={"shops": shops, "count": len(shops)})


@app.get("/api/uzum/orders")
async def get_uzum_orders_endpoint(
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """Retrieve Uzum orders filtered by shop_id and status."""
    from services.database import get_uzum_orders
    orders = get_uzum_orders(shop_id=shop_id, status=status, limit=limit)
    return JSONResponse(content={"orders": orders, "count": len(orders)})


@app.post("/api/uzum/orders/{order_id}/confirm")
async def confirm_uzum_order_endpoint(order_id: int):
    """Confirm an FBS order (transitions from CREATED to CONFIRMED)."""
    from services.uzum_service import uzum_service
    res = await uzum_service.confirm_order(order_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return JSONResponse(content=res)


@app.post("/api/uzum/orders/{order_id}/cancel")
async def cancel_uzum_order_endpoint(order_id: int, req: Optional[UzumCancelOrderRequest] = None):
    """Cancel an FBS order."""
    from services.uzum_service import uzum_service
    reason = req.reason if req else "Отсутствует на складе"
    res = await uzum_service.cancel_order(order_id, reason=reason)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return JSONResponse(content=res)


@app.get("/api/uzum/orders/{order_id}/label")
async def get_uzum_order_label(order_id: int, size: str = "LARGE"):
    """Return shipping label information and printable format (58x40 or 43x25 mm)."""
    from services.uzum_service import uzum_service
    res = await uzum_service.get_order_label(order_id, size=size)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail="Buyurtma yoki etiketka topilmadi")
    return JSONResponse(content=res)


@app.get("/api/uzum/orders/{order_id}/label.png")
async def get_uzum_order_label_png(order_id: int, size: str = "LARGE"):
    """Return shipping label as a 203 DPI monochrome PNG image (58x40 or 43x25 mm)."""
    from services.uzum_service import uzum_service
    png_bytes = uzum_service.generate_thermal_label_image(order_id, size=size)
    if not png_bytes:
        raise HTTPException(status_code=404, detail="Etiketka rasmini yaratib bo'lmadi")
    return Response(content=png_bytes, media_type="image/png")


@app.get("/api/uzum/orders/{order_id}/label.svg")
async def get_uzum_order_label_svg(order_id: int, size: str = "LARGE"):
    """Return shipping label as a pure vector SVG (58x40 or 43x25 mm)."""
    from services.uzum_service import uzum_service
    svg_content = uzum_service.generate_thermal_label_svg(order_id, size=size)
    return Response(content=svg_content, media_type="image/svg+xml")


@app.get("/api/uzum/stocks")
async def get_uzum_stocks_endpoint(shop_id: Optional[int] = None):
    """Retrieve SKU stocks and low-stock indicators."""
    from services.database import get_uzum_stocks
    stocks = get_uzum_stocks(shop_id=shop_id)
    return JSONResponse(content={"stocks": stocks, "count": len(stocks)})


@app.post("/api/uzum/stocks/update")
async def update_uzum_stock_endpoint(req: UzumUpdateStockRequest):
    """Update stock quantity for a SKU."""
    from services.database import update_uzum_stock_amount
    ok = update_uzum_stock_amount(req.sku_id, req.amount)
    if not ok:
        raise HTTPException(status_code=404, detail="SKU topilmadi")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "new_stock": req.amount})


@app.post("/api/uzum/prices/update")
async def update_uzum_price_endpoint(req: UzumUpdatePriceRequest):
    """Update selling price for a SKU."""
    from services.database import update_uzum_price
    ok = update_uzum_price(req.sku_id, req.price)
    if not ok:
        raise HTTPException(status_code=404, detail="SKU topilmadi")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "new_price": req.price})


@app.post("/api/uzum/stocks/cost-price")
async def update_uzum_cost_price_endpoint(req: UzumUpdateCostPriceRequest):
    """Update cost price (tannarxi / себестоимость) for a SKU."""
    from services.database import update_uzum_cost_price
    ok = update_uzum_cost_price(req.sku_id, req.cost_price)
    if not ok:
        raise HTTPException(status_code=404, detail="SKU topilmadi")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "cost_price": req.cost_price})


@app.get("/api/uzum/margin-guard")
async def get_uzum_margin_guard_endpoint(shop_id: Optional[int] = None):
    """Retrieve SKU-level unit economics and margin guard analytics."""
    from services.database import get_uzum_margin_analytics
    data = get_uzum_margin_analytics(shop_id=shop_id)
    return JSONResponse(content=data)


@app.get("/api/uzum/finance")
async def get_uzum_finance_endpoint(shop_id: Optional[int] = None):
    """Retrieve financial summary (gross, commission, logistics, tax 1%, net payout)."""
    from services.database import get_uzum_finance_summary
    fin = get_uzum_finance_summary(shop_id=shop_id)
    return JSONResponse(content=fin)


@app.post("/api/uzum/sync-now")
async def sync_uzum_now_endpoint():
    """Trigger manual sync and dispatch pending Telegram push notifications."""
    from services.uzum_service import uzum_service
    await uzum_service.sync_live_orders_and_stocks()
    sent = await uzum_service.check_and_send_notifications()
    return JSONResponse(content={"status": "ok", "sent_notifications": sent, "synced_at": datetime.now().isoformat()})


@app.post("/api/uzum/test-push")
async def test_uzum_push_endpoint(req: UzumTestPushRequest):
    """Send test Telegram push notification to verify delivery."""
    from services.uzum_service import uzum_service
    chat_id = req.chat_id
    if not chat_id:
        from services.database import get_subscribers, get_uzum_settings
        settings = get_uzum_settings()
        chat_id = settings.get("telegram_chat_id")
        if not chat_id:
            subs = get_subscribers()
            if subs:
                chat_id = subs[0]["chat_id"]
    if not chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram chat_id topilmadi. Avval @oqila_ai_bot ga /start bosing yoki chat_id kiriting."
        )
    ok = await uzum_service.send_test_push(chat_id=chat_id, lang=req.lang)
    if not ok:
        raise HTTPException(status_code=500, detail="Telegram'ga xabar yuborib bo'lmadi. TELEGRAM_BOT_TOKEN ni tekshiring.")
    return JSONResponse(content={"status": "ok", "chat_id": chat_id})


@app.get("/api/uzum/fbo/forecast")
async def get_uzum_fbo_forecast_endpoint(shop_id: Optional[int] = None):
    """Retrieve FBO inventory days left forecast and stockout warnings."""
    from services.database import get_uzum_fbo_forecast
    data = get_uzum_fbo_forecast(shop_id=shop_id)
    return JSONResponse(content={"forecast": data, "count": len(data)})


@app.post("/api/uzum/fbo/test-alert")
async def test_uzum_fbo_alert_endpoint(req: UzumFboAlertRequest):
    """Send proactive Telegram restock alert for an FBO SKU."""
    from services.uzum_service import uzum_service
    chat_id = req.chat_id
    if not chat_id:
        from services.database import get_subscribers, get_uzum_settings
        settings = get_uzum_settings()
        chat_id = settings.get("telegram_chat_id")
        if not chat_id:
            subs = get_subscribers()
            if subs:
                chat_id = subs[0]["chat_id"]
    if not chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram chat_id topilmadi. Avval @oqila_ai_bot ga /start bosing yoki chat_id kiriting."
        )
    ok = await uzum_service.send_fbo_restock_alert(chat_id=chat_id, sku_id=req.sku_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Telegram'ga xabar yuborib bo'lmadi.")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "chat_id": chat_id})


# ---------------------------------------------------------------------------
# Analytics & Stats (SQLite)
# ---------------------------------------------------------------------------
@app.get("/api/stats")
async def get_analytics():
    """Return platform statistics from SQLite database."""
    return JSONResponse(content=get_stats())


# ---------------------------------------------------------------------------
# Admin Panel API Endpoints (Protected by X-Admin-Key or admin_key query)
# ---------------------------------------------------------------------------
@app.get("/api/admin/dashboard")
async def admin_dashboard(admin_auth: bool = Security(verify_admin_key)):
    """Retrieve high-level dashboard metrics for the administrator."""
    metrics = get_admin_dashboard_metrics()
    return JSONResponse(content=metrics)


@app.get("/api/admin/users")
async def admin_get_users(
    limit: int = 50,
    offset: int = 0,
    search: str = "",
    status: str = "",
    category: str = "",
    admin_auth: bool = Security(verify_admin_key),
):
    """Retrieve paginated and filtered users list."""
    users = get_all_users(limit=limit, offset=offset, search=search, status=status, category=category)
    total = get_users_count(search=search, status=status, category=category)
    return JSONResponse(content={"users": users, "total": total, "limit": limit, "offset": offset})


@app.get("/api/admin/users/{user_id}")
async def admin_get_user_details(user_id: int, admin_auth: bool = Security(verify_admin_key)):
    """Retrieve detailed profile, cards, and events for a specific user."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_cards = get_admin_cards(user_id=user_id, limit=20, offset=0)
    user_events = get_admin_events(user_id=user_id, limit=50, offset=0)
    return JSONResponse(content={"user": user, "cards": user_cards, "events": user_events})


@app.post("/api/admin/users/{user_id}/toggle-active")
async def admin_toggle_user_active(user_id: int, admin_auth: bool = Security(verify_admin_key)):
    """Toggle user active status (enable/disable account)."""
    new_status = toggle_user_active(user_id)
    if new_status is None:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(content={"status": "ok", "user_id": user_id, "is_active": new_status})


@app.get("/api/admin/events")
async def admin_get_events(
    user_id: Optional[int] = None,
    event_type: str = "",
    limit: int = 100,
    offset: int = 0,
    admin_auth: bool = Security(verify_admin_key),
):
    """Retrieve platform usage logs."""
    events = get_admin_events(user_id=user_id, event_type=event_type, limit=limit, offset=offset)
    total = get_admin_events_count(user_id=user_id, event_type=event_type)
    return JSONResponse(content={"events": events, "total": total, "limit": limit, "offset": offset})


@app.get("/api/admin/cards")
async def admin_get_cards(
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    admin_auth: bool = Security(verify_admin_key),
):
    """Retrieve generated cards across all users."""
    cards = get_admin_cards(user_id=user_id, limit=limit, offset=offset)
    return JSONResponse(content={"cards": cards, "limit": limit, "offset": offset})


@app.get("/api/admin/export/users.csv")
async def admin_export_users_csv(admin_auth: bool = Security(verify_admin_key)):
    """Export all users data as a beautiful, Excel-compatible CSV with UTF-8 BOM."""
    from services.csv_service import generate_users_csv

    users = get_all_users(limit=10000, offset=0)
    csv_bytes = generate_users_csv(users)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="oqila_users_{date_str}.csv"'},
    )


@app.get("/api/admin/export/cards.csv")
async def admin_export_cards_csv(admin_auth: bool = Security(verify_admin_key)):
    """Export all generated cards data as a beautiful, Excel-compatible CSV."""
    from services.csv_service import generate_cards_csv

    cards = get_admin_cards(limit=10000, offset=0)
    csv_bytes = generate_cards_csv(cards)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="oqila_cards_{date_str}.csv"'},
    )


# ---------------------------------------------------------------------------
# Telegram Bot Webhook Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates."""
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if secret:
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header_token != secret:
            logger.warning("Rejected unauthorized Telegram webhook update")
            raise HTTPException(status_code=403, detail="Forbidden")

    try:
        update = await request.json()
        host_url = str(request.base_url).rstrip("/")
        if request.headers.get("x-forwarded-proto") == "https":
            host_url = host_url.replace("http://", "https://")
        await telegram_service.handle_update(update, default_app_url=host_url)
    except Exception as exc:
        logger.error("Error processing telegram update: %s", exc)
    return {"ok": True}


@app.post("/api/set-webhook")
async def set_telegram_webhook(req: Optional[SetWebhookRequest] = None, request: Request = None):
    """Register webhook URL with Telegram Bot API."""
    target_url = (req.url if req and req.url else None) or os.getenv("WEBAPP_URL")
    if not target_url and request:
        target_url = str(request.base_url).rstrip("/")
        if request.headers.get("x-forwarded-proto") == "https":
            target_url = target_url.replace("http://", "https://")

    if not target_url:
        raise HTTPException(status_code=400, detail="Webhook URL must be provided")

    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip() or None
    result = await telegram_service.set_webhook(target_url, secret_token=secret)
    return JSONResponse(content=result)


@app.get("/api/webhook-info")
async def get_webhook_status():
    """Get current Telegram webhook registration status."""
    info = await telegram_service.get_webhook_info()
    return JSONResponse(content=info)


# ---------------------------------------------------------------------------
# SPA Catch-all Route
# ---------------------------------------------------------------------------
@app.get("/{full_path:path}", include_in_schema=False)
async def catch_all(full_path: str):
    """Serve SPA index for deep links or static assets from dist."""
    from fastapi.responses import FileResponse
    # Do not intercept API, health, static or assets
    if full_path.startswith(("api/", "health", "static/", "assets/")):
        raise HTTPException(status_code=404, detail="Not found")

    file_in_dist = FRONTEND_DIST / full_path
    if FRONTEND_DIST.exists() and file_in_dist.is_file():
        return FileResponse(str(file_in_dist))

    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return FileResponse(str(react_index))
    legacy_index = STATIC_DIR / "index.html"
    if legacy_index.exists():
        return FileResponse(str(legacy_index))
    raise HTTPException(status_code=404, detail="Index not found")


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
