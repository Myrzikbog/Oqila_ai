"""
main.py — Oqila AI FastAPI Server
Digital ecosystem & Telegram Mini App for women entrepreneurs in Uzbekistan.

Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env FIRST — before any service module is imported
load_dotenv(override=True)

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import services (after env is loaded)
from services.ai_service import ai_service
from services.database import (
    clear_history,
    delete_history_item,
    get_history,
    get_stats,
    log_event,
    save_generated_card,
    toggle_favorite,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Oqila AI application...")
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
):
    """Retrieve history of generated product cards with search, favorites, and pagination."""
    items = get_history(limit=limit, offset=offset, favorites_only=favorites_only, search=search)
    return {
        "items": items,
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "favorites_only": favorites_only,
        "search": search,
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

    return {
        "rates": _cbu_rates_cache["data"],
        "source": "Марказий банк (cbu.uz)",
        "cached": _cbu_rates_cache["timestamp"] > 0,
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

    result = calculate(
        sale_price=req.sale_price,
        cost_price=req.cost_price,
        lang=req.lang,
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
# Analytics & Stats (SQLite)
# ---------------------------------------------------------------------------
@app.get("/api/stats")
async def get_analytics():
    """Return platform statistics from SQLite database."""
    return JSONResponse(content=get_stats())


# ---------------------------------------------------------------------------
# Telegram Bot Webhook Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates."""
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

    result = await telegram_service.set_webhook(target_url)
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
