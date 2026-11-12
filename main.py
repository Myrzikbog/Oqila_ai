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
from typing import List, Optional

from dotenv import load_dotenv

# Load .env FIRST — before any service module is imported
load_dotenv(override=True)

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Import services (after env is loaded)
from services.ai_service import ai_service
from services.auth_service import resolve_auth_user, verify_telegram_init_data
from services.session_service import (
    MEDIA_TOKEN_TTL_SECONDS,
    check_admin_key,
    create_media_token,
    create_session_token,
    get_admin_secret_key,
    get_webhook_secret,
    new_guest_tg_id,
    verify_media_token,
    verify_session_token,
)
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
    get_brand,
    get_card,
    get_stats,
    get_user,
    get_user_by_tg_id,
    get_users_count,
    init_db,
    log_event,
    remember_telegram_update,
    save_brand,
    save_generated_card,
    set_brand_logo,
    update_card_render,
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
from services.media_storage import delete_photo, resolve_photo, store_bytes
from services.info_photo import CopySpec, apply_slots, too_long_fields
from services.presets import STYLES_BY_ID, pick_aspect, public_registry, style_kind
from services.imaging import ImageRejected, normalize_logo, normalize_source
from services.rate_limit import (
    LimitExceeded,
    check_user_limit,
    finish as finish_reservation,
    global_ai_budget_exhausted,
    limits_status,
    register_guest,
    reserve,
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


def _acquire_poller_lock():
    """Only one uvicorn worker may run the Uzum poller, otherwise every notification is sent N times."""
    try:
        import fcntl
    except ImportError:  # non-POSIX platform: single process assumed
        return True
    lock_path = Path(os.getenv("OQILA_POLLER_LOCK") or (Path(__file__).parent / ".uzum_poller.lock"))
    try:
        handle = open(lock_path, "w")
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle  # keep the handle open for the lifetime of the process
    except OSError:
        return None


async def uzum_background_poller():
    """Periodic worker to sync live orders and dispatch Telegram push notifications."""
    lock = _acquire_poller_lock()
    if not lock:
        logger.info("Uzum poller is already running in another worker; skipping in this one.")
        return
    await asyncio.sleep(8)
    while True:
        try:
            from services.uzum_service import uzum_service
            await uzum_service.sync_all_users()
            await uzum_service.notify_all_users()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Uzum background poller failed: %s", exc)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Oqila AI application...")
    init_db()
    if not get_admin_secret_key():
        logger.warning(
            "ADMIN_SECRET_KEY is not set (or shorter than 16 chars): admin API key access is disabled."
        )
    poller_task = asyncio.create_task(uzum_background_poller())
    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    if webapp_url and telegram_service.is_configured:
        try:
            res = await telegram_service.set_webhook(webapp_url, secret_token=get_webhook_secret())
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
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# ---------------------------------------------------------------------------
# Static files & React Frontend (SPA)
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


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
    user_id: Optional[int] = None  # ignored: the user always comes from the session token
    name: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    sales_channel: Optional[str] = None
    lang: Optional[str] = None


# ---------------------------------------------------------------------------
# Security: user sessions and administrator access
# ---------------------------------------------------------------------------
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def _bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _active_user(user_id: Optional[int]) -> dict:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.get("is_active", 1):
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user


def current_user(request: Request) -> dict:
    """Resolve the signed-in user from the `Authorization: Bearer <session token>` header."""
    return _active_user(verify_session_token(_bearer_token(request)))


def current_user_for_media(request: Request, mt: Optional[str] = None) -> dict:
    """For URLs loaded by <img>/<a> tags, which cannot send an Authorization header: they carry a short-lived
    media token in `?mt=` (POST /api/media-token). The 30-day session token is never accepted in a URL:
    URLs end up in nginx logs, browser history and Referer headers."""
    bearer = _bearer_token(request)
    if bearer:
        return _active_user(verify_session_token(bearer))
    return _active_user(verify_media_token(mt))


def _trusted_proxies() -> set:
    return {p.strip() for p in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if p.strip()}


def client_ip(request: Request) -> str:
    """The caller's address. X-Real-IP is only believed when the request comes from our own reverse proxy."""
    peer = request.client.host if request.client else ""
    if peer in _trusted_proxies():
        real = request.headers.get("x-real-ip", "").strip()
        if real:
            return real[:64]
    return peer or "unknown"


async def run_blocking(func, *args):
    """Run CPU-bound or blocking code (PIL, file I/O) off the event loop."""
    return await asyncio.get_running_loop().run_in_executor(None, func, *args)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_UPLOAD_ERRORS = {
    "format": (415, {"ru": "Этот формат не поддерживается. Загрузите фото в JPG, PNG или WEBP (HEIC с iPhone пока не поддерживается).",
                     "uz": "Bu format qo'llab-quvvatlanmaydi. JPG, PNG yoki WEBP rasm yuklang (iPhone HEIC hozircha qo'llab-quvvatlanmaydi)."}),
    "too_large": (413, {"ru": "Слишком большое изображение: не больше 40 мегапикселей.",
                        "uz": "Rasm juda katta: 40 megapikseldan oshmasligi kerak."}),
    "broken": (415, {"ru": "Файл повреждён и не открывается как изображение.",
                     "uz": "Fayl buzilgan, rasm sifatida ochilmadi."}),
    "bytes": (413, {"ru": "Размер изображения превышает 10 МБ.", "uz": "Rasm hajmi 10 MB dan oshmasligi kerak."}),
}


def _upload_error(reason: str, lang: str) -> HTTPException:
    status, text = _UPLOAD_ERRORS.get(reason, _UPLOAD_ERRORS["format"])
    return HTTPException(status_code=status, detail=text["uz" if lang == "uz" else "ru"])


async def read_product_photo(image: Optional[UploadFile], lang: str) -> Optional[bytes]:
    """The uploaded product photo as a normalized JPEG (<= 2048 px), or None when no file was sent.

    At most 10 MB + 1 byte is read; the type is taken from the file's magic bytes and the pixel count is checked
    before decoding. The same normalized JPEG is stored and sent to the AI."""
    if not image or not image.filename:
        return None
    raw = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise _upload_error("bytes", lang)
    if not raw:
        return None
    try:
        return await run_blocking(normalize_source, raw)
    except ImageRejected as exc:
        raise _upload_error(exc.reason, lang)


def take_reservation(action: str, user_id: int, lang: str) -> int:
    try:
        return reserve(action, user_id, lang)
    except LimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))


def verify_admin_key(
    request: Request,
    header_key: Optional[str] = Security(admin_key_header),
) -> bool:
    """Admin access: X-Admin-Key header matching ADMIN_SECRET_KEY, or Telegram initData
    (X-Telegram-Init-Data header) of a user who is an administrator."""
    if header_key and check_admin_key(header_key):
        return True
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if init_data:
        tg_user = verify_telegram_init_data(init_data)
        if tg_user and tg_user.get("id") and telegram_service.is_admin_user(tg_user["id"]):
            return True
    if not get_admin_secret_key() and not init_data:
        raise HTTPException(status_code=503, detail="Admin access is not configured (set ADMIN_SECRET_KEY).")
    raise HTTPException(status_code=403, detail="Invalid administrator secret key.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def root():
    """Serve the React SPA (or legacy index)."""
    from fastapi.responses import FileResponse
    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return FileResponse(str(react_index))
    return JSONResponse({"status": "ok", "message": "Oqila AI API is running"})


@app.get("/health")
def health():
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
def auth_login(req: AuthLoginRequest, request: Request):
    """Sign in and receive a session token.

    - Inside Telegram: identity comes only from verified initData.
    - Standalone browser: a server-generated guest identity; an existing guest session token
      (Authorization header) keeps the same guest account.
    """
    profile = req.profile or {}
    tg_id: Optional[int] = None
    is_telegram = False
    resolved: dict = {}

    if req.init_data:
        resolved = resolve_auth_user(init_data=req.init_data, dev_profile=profile)
        if not resolved.get("is_authenticated"):
            raise HTTPException(status_code=401, detail="Invalid or expired Telegram initData")
        tg_id = int(resolved["tg_id"])
        is_telegram = True
    else:
        existing_uid = verify_session_token(_bearer_token(request))
        existing = get_user(existing_uid) if existing_uid else None
        if existing:
            tg_id = int(existing["tg_id"])
        elif os.getenv("ALLOW_GUEST_LOGIN", "1").strip().lower() in ("0", "false", "no"):
            raise HTTPException(status_code=401, detail="Please open the app from Telegram")
        else:
            # Every new guest gets a fresh AI quota, so guests are rationed per IP (5 an hour by default)
            if not register_guest(client_ip(request)):
                raise HTTPException(
                    status_code=429,
                    detail="Слишком много новых гостевых входов с этого адреса. Откройте приложение из Telegram или попробуйте через час. / "
                           "Bu manzildan juda ko'p mehmon kirishi. Ilovani Telegram orqali oching yoki bir soatdan keyin urinib ko'ring.",
                )
            tg_id = new_guest_tg_id()
        resolved = resolve_auth_user(init_data=None, dev_profile=profile)

    user = upsert_user(
        tg_id=tg_id,
        tg_username=resolved.get("tg_username", ""),
        tg_first_name=resolved.get("tg_first_name", ""),
        name=profile.get("name") or resolved.get("name", ""),
        status=profile.get("status") or resolved.get("status", "self_employed"),
        category=profile.get("category") or resolved.get("category", "sewing"),
        sales_channel=profile.get("salesChannel") or resolved.get("sales_channel", "uzum"),
        lang=profile.get("lang") or resolved.get("lang", "uz"),
    )
    if not user.get("user_id"):
        raise HTTPException(status_code=500, detail="Could not create user")
    user_with_stats = get_user(user["user_id"]) or user
    if not user_with_stats.get("is_active", 1):
        raise HTTPException(status_code=403, detail="Account is disabled")
    user_with_stats["is_admin"] = is_telegram and telegram_service.is_admin_user(user_with_stats.get("tg_id"))
    log_event(
        event_type="auth_login",
        lang=user.get("lang", "uz"),
        is_mock=False,
        details={"user_id": user["user_id"], "is_telegram": is_telegram},
        user_id=user["user_id"],
    )
    return JSONResponse(content={
        "status": "ok",
        "user_id": user["user_id"],
        "is_telegram": is_telegram,
        "session_token": create_session_token(user["user_id"]),
        "profile": user_with_stats,
    })


@app.get("/api/profile")
def get_profile(user: dict = Depends(current_user)):
    """Retrieve the signed-in user's profile with statistics."""
    user["is_admin"] = int(user.get("tg_id") or 0) > 0 and telegram_service.is_admin_user(user.get("tg_id"))
    return JSONResponse(content=user)


@app.put("/api/profile")
def update_profile(req: UpdateProfileRequest, user: dict = Depends(current_user)):
    """Update the signed-in user's business profile attributes."""
    user_id = user["user_id"]
    updated = update_user_profile(
        user_id=user_id,
        name=req.name,
        status=req.status,
        category=req.category,
        sales_channel=req.sales_channel,
        lang=req.lang,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    updated["is_admin"] = int(updated.get("tg_id") or 0) > 0 and telegram_service.is_admin_user(updated.get("tg_id"))
    log_event(
        event_type="profile_update",
        lang=updated.get("lang", "uz"),
        details={"user_id": user_id},
        user_id=user_id,
    )
    return JSONResponse(content={"status": "ok", "profile": updated})


# ---------------------------------------------------------------------------
# Tab 1: AI Studio — Product Card Generation
# ---------------------------------------------------------------------------
TEXT_RENDER_UNAVAILABLE = {
    "ru": "Генерация картинок с текстом временно недоступна. Попробуйте позже.",
    "uz": "Matnli rasm yaratish vaqtincha mavjud emas. Keyinroq urinib ko'ring.",
}


def _msg(texts: dict, lang: Optional[str]) -> str:
    return texts["uz" if lang == "uz" else "ru"]


def _brand_for_ai(user_id: int) -> tuple:
    """(brand settings, logo PNG bytes or None): the brand goes into the prompt, the logo is a reference image."""
    brand = get_brand(user_id)
    logo_path = resolve_photo(brand.get("brand_logo"))
    logo = None
    if logo_path:
        try:
            logo = logo_path.read_bytes()
        except OSError:
            logo = None
    return brand, logo


def _photo_url(card_id: int, version: Optional[int] = None) -> str:
    return f"/api/cards/{card_id}/photo" + (f"?v={version}" if version else "")


@app.post("/api/generate-card")
async def generate_card(
    image: Optional[UploadFile] = File(None),
    cost_price: Optional[float] = Form(None),
    desired_price: Optional[float] = Form(None),
    old_price: Optional[float] = Form(None),
    note: Optional[str] = Form(None),
    lang: str = Form("ru"),
    photoshoot_style: str = Form("minimal_studio"),
    photoshoot_prompt: Optional[str] = Form(None),
    content_tone: str = Form("luxury"),
    content_format: str = Form("instagram"),
    generate_photo: bool = Form(True),
    text_only: bool = Form(False),
    aspect_ratio: str = Form(""),
    info_text: str = Form(""),
    user_id: Optional[int] = Form(None),  # ignored: the user always comes from the session token
    user: dict = Depends(current_user),
):
    """
    Generate a product marketing card: the selling text and, depending on the style, a studio photo or a picture
    with text drawn by the AI.

    For styles with text the answer carries `copy` (what is written on the picture) and `verification` (the result
    of reading the text back). `text_only=true` stops after the text, so the seller can correct it before
    POST /api/cards/{id}/render draws the picture.
    """
    user_id = user["user_id"]
    if photoshoot_style not in STYLES_BY_ID:
        photoshoot_style = "minimal_studio"
    aspect = pick_aspect(photoshoot_style, aspect_ratio)
    kind = style_kind(photoshoot_style)
    info_text = " ".join(info_text.split("\r")).strip()[:1500]
    # A bad upload is rejected before any quota is taken
    image_bytes = await read_product_photo(image, lang)
    image_mime = "image/jpeg"

    reservation = take_reservation("generate_card", user_id, lang)
    delivered = False  # True once a real AI result was produced: only then the user's quota is spent
    try:
        use_mock = ai_service.is_mock or global_ai_budget_exhausted()
        logger.info(
            "generate_card — lang=%s, has_image=%s, style=%s, custom_prompt=%s, tone=%s, format=%s, gen_photo=%s, text_only=%s",
            lang, image_bytes is not None, photoshoot_style, bool(photoshoot_prompt), content_tone, content_format,
            generate_photo, text_only,
        )
        brand, logo = (await run_blocking(_brand_for_ai, user_id)) if kind == "ai_text" else (None, None)

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
            generate_photo=generate_photo and not text_only,
            force_mock=use_mock,
            aspect_ratio=aspect,
            info_text=info_text,
            old_price=old_price,
            brand=brand,
            logo=logo,
        )

        fallback = result.get("ai_fallback")
        if fallback and result.get("ai_fallback_scope") != "text":
            # Sample text is not the seller's card: it is shown with a notice, but never saved to the history
            result["id"] = None
            result["studio_photo_url"] = None
            log_event(
                event_type="generate_card", lang=lang, is_mock=True,
                details={"ai_fallback": fallback, "style": photoshoot_style, "has_image": image_bytes is not None},
                user_id=user_id,
            )
            return JSONResponse(content=result)

        # Pictures with text and clean photos keep the seller's own photo: it is the reference for every re-render
        source_ref: Optional[str] = None
        if kind in ("ai_text", "clean") and image_bytes:
            source_ref = await run_blocking(store_bytes, "source", image_bytes, "jpg")
        info_config: Optional[dict] = None
        if kind == "ai_text":
            if not isinstance(result.get("copy"), dict):
                # the text model failed but a picture exists: there is no copy to show
                result["copy"] = apply_slots(CopySpec.from_dict({"title": result.get("title", ""), "lang": lang}), photoshoot_style).to_dict()
            info_config = {"copy": result["copy"], "verification": result.get("verification"), "aspect": aspect}

        # Save to history database
        card_id = await run_blocking(lambda: save_generated_card(
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
            source_photo_url=source_ref,
            info_config=info_config,
        ))
        if not card_id:
            delete_photo(source_ref)
            raise HTTPException(status_code=500, detail="Could not save the card. Please try again.")
        delivered = True
        result["id"] = card_id
        result["aspect"] = aspect
        result["version"] = 1
        result["has_source"] = bool(source_ref)

        log_event(
            event_type="generate_card",
            lang=lang,
            is_mock=False,
            details={
                "card_id": card_id,
                "title": result.get("title", ""),
                "has_image": image_bytes is not None,
                "style": photoshoot_style,
                "aspect": aspect,
                "tone": content_tone,
                "format": content_format,
                "has_studio_photo": bool(result.get("studio_photo_url")),
                "verified": (result.get("verification") or {}).get("verified"),
                "image_calls": result.get("image_calls"),
            },
            user_id=user_id,
        )

        return JSONResponse(content=result)
    finally:
        finish_reservation(reservation, delivered)


@app.get("/api/limits")
def get_limits(user: dict = Depends(current_user)):
    """The user's AI quota: how many card generations and legal questions are used and when a slot frees up."""
    return limits_status(user["user_id"])


@app.post("/api/media-token")
def issue_media_token(user: dict = Depends(current_user)):
    """A 10-minute token for picture and download URLs (`?mt=`), so the session token never appears in a URL."""
    return {"media_token": create_media_token(user["user_id"]), "expires_in": MEDIA_TOKEN_TTL_SECONDS}


@app.get("/api/demo-card")
def demo_card(lang: str = "ru", user: dict = Depends(current_user)):
    """
    Return a pre-built demo product card (no image processing, no Gemini call).
    Used for the «✨ Быстрое демо» button: instant and works offline on stage.
    """
    limit_error = check_user_limit("demo_card", user["user_id"], lang)
    if limit_error:
        raise HTTPException(status_code=429, detail=limit_error)
    result = ai_service.demo_card(lang, desired_price=380_000, note="Национальный атласный халат/ko'ylak, ручная вышивка")
    result["is_demo"] = True

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
        user_id=user["user_id"],
        is_demo=True,
    )
    result["id"] = card_id

    log_event(
        event_type="demo_card",
        lang=lang,
        is_mock=True,
        details={"card_id": card_id, "title": result.get("title", "")},
        user_id=user["user_id"],
    )

    return JSONResponse(content=result)


@app.get("/api/photoshoot-presets")
def get_photoshoot_presets():
    """Registry of everything the studio can produce: output types, styles with their text fields and limits, aspect ratios."""
    from services.ai_service import TONE_PRESETS, FORMAT_PRESETS
    registry = public_registry()
    registry["tones"] = TONE_PRESETS
    registry["formats"] = FORMAT_PRESETS
    return registry


# ---------------------------------------------------------------------------
# History & Catalog API
# ---------------------------------------------------------------------------
@app.get("/api/history")
def get_cards_history(
    limit: int = 50,
    offset: int = 0,
    favorites_only: bool = False,
    search: str = "",
    user: dict = Depends(current_user),
):
    """Retrieve the signed-in user's generated product cards with search, favorites and pagination."""
    user_id = user["user_id"]
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
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
def toggle_card_favorite(card_id: int, user: dict = Depends(current_user)):
    """Toggle star/favorite flag on one of the user's cards."""
    new_status = toggle_favorite(card_id, user_id=user["user_id"])
    if new_status is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"status": "ok", "card_id": card_id, "is_favorite": new_status}


@app.delete("/api/history/{card_id}")
def delete_card_history_item(card_id: int, user: dict = Depends(current_user)):
    """Delete one of the user's cards from history."""
    success = delete_history_item(card_id, user_id=user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"status": "ok", "deleted_id": card_id}


def _card_photo_response(card_id: int, owner_id: Optional[int], download: bool = False) -> Response:
    """Serve a card's studio photo; owner_id=None means any card (administrators only).
    download=True adds Content-Disposition: attachment with a file name whose extension matches the real type."""
    from fastapi.responses import FileResponse, RedirectResponse
    from services.database import get_db_connection
    from services.media_storage import MIME_BY_EXT, resolve_photo
    import base64

    query = "SELECT studio_photo_url FROM generated_cards WHERE id = ?"
    params: list = [card_id]
    if owner_id is not None:
        query += " AND user_id = ?"
        params.append(owner_id)
    with get_db_connection() as conn:
        row = conn.execute(query, params).fetchone()
    if not row or not row["studio_photo_url"]:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo_val = row["studio_photo_url"]
    cache = {"Cache-Control": "private, max-age=604800"}
    if photo_val.startswith("file:"):
        path = resolve_photo(photo_val)
        if not path:
            raise HTTPException(status_code=404, detail="Photo not found")
        ext = path.suffix.lstrip(".").lower()
        mime = MIME_BY_EXT.get(ext, "application/octet-stream")
        if download:
            cache = {**cache, "Content-Disposition": f'attachment; filename="oqila-{card_id}.{ext or "jpg"}"'}
        return FileResponse(str(path), media_type=mime, headers=cache)
    if photo_val.startswith("data:"):  # legacy rows stored before photos moved to files
        try:
            header, b64_data = photo_val.split(",", 1)
            mime = "image/jpeg"
            if "image/png" in header:
                mime = "image/png"
            elif "image/webp" in header:
                mime = "image/webp"
            raw_bytes = base64.b64decode(b64_data)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to decode photo")
        if download:
            cache = {**cache, "Content-Disposition": f'attachment; filename="oqila-{card_id}.{mime.split("/")[1].replace("jpeg", "jpg")}"'}
        return Response(content=raw_bytes, media_type=mime, headers=cache)
    if photo_val.startswith("https://"):
        return RedirectResponse(url=photo_val)
    raise HTTPException(status_code=404, detail="Invalid photo URL")


@app.get("/api/cards/{card_id}/photo")
def get_card_photo(card_id: int, download: bool = False, user: dict = Depends(current_user_for_media)):
    """Serve the picture of one of the user's cards (`?download=1` to save it as a file)."""
    return _card_photo_response(card_id, owner_id=user["user_id"], download=download)


# ---------------------------------------------------------------------------
# Pictures with text: edit the copy, render, fix the lettering. The seller's branding.
# ---------------------------------------------------------------------------
class BrandRequest(BaseModel):
    brand_name: str = ""
    brand_color: str = ""
    brand_contact: str = ""


class SpecItem(BaseModel):
    name: str = ""
    value: str = ""


class CopyRequest(BaseModel):
    """Either `copy` (the seller's own text: it is only cleaned and cut to the format, no AI call) or nothing
    (the AI writes the text again from the stored photo and notes)."""
    model_config = {"populate_by_name": True}

    copy_: Optional[dict] = Field(default=None, alias="copy")
    style: Optional[str] = None
    lang: Optional[str] = None
    info_text: Optional[str] = Field(default=None, max_length=1500)


class RenderRequest(BaseModel):
    model_config = {"populate_by_name": True}

    copy_: Optional[dict] = Field(default=None, alias="copy")
    style: Optional[str] = None
    aspect: Optional[str] = None
    lang: Optional[str] = None
    # Field names of the previous /info-photo API (one release of backward compatibility)
    title: Optional[str] = None
    tagline: Optional[str] = None
    benefits: Optional[List[str]] = Field(default=None, max_length=8)
    specs: Optional[List[SpecItem]] = Field(default=None, max_length=8)
    badge: Optional[str] = None
    uses: Optional[List[str]] = Field(default=None, max_length=8)


class TextProblem(BaseModel):
    expected: str = Field(default="", max_length=120)
    found: str = Field(default="", max_length=200)


class FixTextRequest(BaseModel):
    problems: Optional[List[TextProblem]] = Field(default=None, max_length=12)


def _text_card(card_id: int, user: dict, style: Optional[str] = None) -> tuple:
    """(card, style, stored text) of one of the user's cards that carries text; 404 / 400 otherwise."""
    from services.database import card_text

    card = get_card(card_id, user["user_id"])
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    style = style if style in STYLES_BY_ID else card.get("photoshoot_style")
    if style_kind(style) != "ai_text":
        raise HTTPException(status_code=400, detail="This style has no text on the picture")
    return card, style, card_text(card.get("info_config"))


def _require_ai(lang: Optional[str]) -> None:
    if ai_service.is_mock or global_ai_budget_exhausted():
        raise HTTPException(status_code=503, detail=_msg(TEXT_RENDER_UNAVAILABLE, lang))


def _render_response(card_id: int, style: str, aspect: str, rendered: dict) -> dict:
    version = int(datetime.now().timestamp())
    url = _photo_url(card_id, version)
    return {
        "id": card_id, "photo_url": url, "studio_photo_url": url, "copy": rendered["copy"],
        "verification": rendered["verification"], "photoshoot_style": style, "aspect": aspect, "version": version,
        "image_calls": rendered.get("image_calls"),
    }


@app.post("/api/cards/{card_id}/copy")
async def card_copy(card_id: int, req: CopyRequest, user: dict = Depends(current_user)):
    """The text for a picture, before anything is drawn (cheap: at most one text call, never an image call).

    With `copy` in the body the seller's text is cleaned and cut to the format's slots and limits (no AI).
    Without it the AI writes the text again from the stored photo and the seller's notes."""
    card, style, stored = _text_card(card_id, user, req.style)
    lang = req.lang or card.get("lang") or "ru"
    if req.copy_ is not None:
        raw = {**req.copy_, "lang": lang}
        return {"copy": apply_slots(CopySpec.from_dict(raw), style).to_dict(), "too_long": too_long_fields(req.copy_, style),
                "photoshoot_style": style}

    _require_ai(lang)
    source = resolve_photo(card.get("source_photo_url"))
    reservation = take_reservation("card_copy", user["user_id"], lang)
    delivered = False
    try:
        brand, _logo = await run_blocking(_brand_for_ai, user["user_id"])
        result = await ai_service.generate_product_card(
            image_bytes=(await run_blocking(source.read_bytes)) if source else None, image_mime="image/jpeg",
            cost_price=card.get("cost_price"), desired_price=card.get("desired_price"), note=card.get("note"), lang=lang,
            photoshoot_style=style, content_tone=card.get("content_tone") or "luxury",
            content_format=card.get("content_format") or "instagram", generate_photo=False,
            info_text=req.info_text or "", brand=brand,
        )
        if result.get("ai_fallback") or not isinstance(result.get("copy"), dict):
            raise HTTPException(status_code=503, detail=_msg(TEXT_RENDER_UNAVAILABLE, lang))
        delivered = True
    finally:
        finish_reservation(reservation, delivered)
    log_event(event_type="card_copy", lang=lang, is_mock=False, details={"card_id": card_id, "style": style}, user_id=user["user_id"])
    return {"copy": result["copy"], "too_long": [], "photoshoot_style": style}


async def _render_card_endpoint(card_id: int, req: RenderRequest, user: dict) -> dict:
    card, style, stored = _text_card(card_id, user, req.style)
    lang = req.lang or card.get("lang") or "ru"
    _require_ai(lang)
    source = resolve_photo(card.get("source_photo_url"))
    if not source:
        raise HTTPException(status_code=409, detail="The original photo of this card is no longer stored")
    aspect = pick_aspect(style, req.aspect or stored.get("aspect"))
    if req.copy_ is not None:
        raw_copy = dict(req.copy_)
    elif any(v is not None for v in (req.title, req.tagline, req.benefits, req.specs, req.badge, req.uses)):
        raw_copy = {"title": req.title, "tagline": req.tagline, "benefits": req.benefits, "badge": req.badge, "uses": req.uses,
                    "specs": [s.model_dump() for s in (req.specs or [])]}
    else:
        raw_copy = dict(stored.get("copy") or {})
    copy = CopySpec.from_dict({**raw_copy, "lang": lang})
    if not copy.title:
        raise HTTPException(status_code=400, detail="The title is empty")

    reservation = take_reservation("generate_card", user["user_id"], lang)
    delivered = False
    try:
        brand, logo = await run_blocking(_brand_for_ai, user["user_id"])
        rendered = await ai_service.render_card(copy, style, aspect, await run_blocking(source.read_bytes), brand=brand, logo=logo)
        if not rendered["photo"]:
            # No server-drawn substitute: an honest error, the text stays in the editor
            raise HTTPException(status_code=503, detail=_msg(TEXT_RENDER_UNAVAILABLE, lang))
        from services.imaging import to_data_url

        info_config = {"copy": rendered["copy"], "verification": rendered["verification"], "aspect": aspect}
        try:
            old_photo = await run_blocking(update_card_render, card_id, user["user_id"], to_data_url(rendered["photo"]), info_config, style)
        except LookupError:
            raise HTTPException(status_code=404, detail="Card not found")
        except Exception:
            raise HTTPException(status_code=500, detail="Could not save the card. Please try again.")
        delivered = True
    finally:
        finish_reservation(reservation, delivered)
    if old_photo:
        delete_photo(old_photo)
    log_event(
        event_type="generate_card", lang=lang, is_mock=False,
        details={"card_id": card_id, "style": style, "aspect": aspect, "regenerated": True,
                 "verified": rendered["verification"].get("verified"), "image_calls": rendered.get("image_calls")},
        user_id=user["user_id"],
    )
    return _render_response(card_id, style, aspect, rendered)


@app.post("/api/cards/{card_id}/render")
async def render_card(card_id: int, req: RenderRequest, user: dict = Depends(current_user)):
    """Draw the picture of a card with the given (seller-approved) text, in any style that carries text."""
    return await _render_card_endpoint(card_id, req, user)


@app.post("/api/cards/{card_id}/info-photo", deprecated=True)
async def regenerate_info_photo(card_id: int, req: RenderRequest, user: dict = Depends(current_user)):
    """Alias of /render kept for one release (old clients send title/tagline/benefits/specs)."""
    res = await _render_card_endpoint(card_id, req, user)
    return {**res, "info": res["copy"]}


@app.post("/api/cards/{card_id}/fix-text")
async def fix_card_text(card_id: int, req: FixTextRequest, user: dict = Depends(current_user)):
    """Correct only the lettering of the existing picture (one edit by the image model), keeping everything else.
    By default the strings reported by the last check are fixed; the seller may name other lines."""
    card, style, stored = _text_card(card_id, user)
    lang = card.get("lang") or "ru"
    _require_ai(lang)
    picture = resolve_photo(card.get("studio_photo_url"))
    if not picture or not stored.get("copy"):
        raise HTTPException(status_code=409, detail="This card has no picture to correct yet")
    problems = [p.model_dump() for p in (req.problems or [])] or list((stored.get("verification") or {}).get("problems") or [])
    problems = [p for p in problems if (p.get("expected") or p.get("found"))]
    if not problems:
        raise HTTPException(status_code=400, detail="Nothing to fix: name the lines that are wrong")
    aspect = pick_aspect(style, stored.get("aspect"))
    copy = CopySpec.from_dict({**stored["copy"], "lang": lang})

    reservation = take_reservation("generate_card", user["user_id"], lang)
    delivered = False
    try:
        rendered = await ai_service.fix_card_text(await run_blocking(picture.read_bytes), problems, copy, style, aspect)
        if not rendered["photo"]:
            raise HTTPException(status_code=503, detail=_msg(TEXT_RENDER_UNAVAILABLE, lang))
        from services.imaging import to_data_url

        info_config = {"copy": rendered["copy"], "verification": rendered["verification"], "aspect": aspect}
        try:
            old_photo = await run_blocking(update_card_render, card_id, user["user_id"], to_data_url(rendered["photo"]), info_config, style)
        except LookupError:
            raise HTTPException(status_code=404, detail="Card not found")
        except Exception:
            raise HTTPException(status_code=500, detail="Could not save the card. Please try again.")
        delivered = True
    finally:
        finish_reservation(reservation, delivered)
    if old_photo:
        delete_photo(old_photo)
    log_event(event_type="generate_card", lang=lang, is_mock=False,
              details={"card_id": card_id, "style": style, "fix_text": True, "verified": rendered["verification"].get("verified")},
              user_id=user["user_id"])
    return _render_response(card_id, style, aspect, rendered)


@app.get("/api/cards/{card_id}/poster.png", deprecated=True)
def old_poster_link_redirect(card_id: int, request: Request):
    """Posters are ordinary pictures now: old links are permanently redirected to the card's photo."""
    from fastapi.responses import RedirectResponse

    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"/api/cards/{card_id}/photo{query}", status_code=301)


def _brand_response(user_id: int) -> dict:
    brand = get_brand(user_id)
    return {"brand_name": brand["brand_name"], "brand_color": brand["brand_color"],
            "brand_contact": brand["brand_contact"], "has_logo": bool(brand["brand_logo"])}


@app.get("/api/brand")
def get_brand_endpoint(user: dict = Depends(current_user)):
    """The seller's branding: shop name, brand colour, contacts, logo flag."""
    return _brand_response(user["user_id"])


@app.put("/api/brand")
def save_brand_endpoint(req: BrandRequest, user: dict = Depends(current_user)):
    import re

    color = req.brand_color.strip()
    if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise HTTPException(status_code=400, detail="brand_color must look like #0f766e")
    clean = lambda v, n: " ".join(v.split())[:n]  # noqa: E731
    save_brand(user["user_id"], clean(req.brand_name, 32), color.lower(), clean(req.brand_contact, 48))
    return _brand_response(user["user_id"])


@app.post("/api/brand/logo")
async def upload_brand_logo(logo: UploadFile = File(...), user: dict = Depends(current_user)):
    raw = await logo.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo must be 2 MB or smaller")
    try:
        png = await run_blocking(normalize_logo, raw)
    except ValueError:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPG or WEBP image")
    old = set_brand_logo(user["user_id"], store_bytes("brand", png, "png"))
    delete_photo(old)
    return _brand_response(user["user_id"])


@app.delete("/api/brand/logo")
def delete_brand_logo(user: dict = Depends(current_user)):
    delete_photo(set_brand_logo(user["user_id"], None))
    return _brand_response(user["user_id"])


@app.get("/api/brand/logo.png")
def get_brand_logo(user: dict = Depends(current_user_for_media)):
    from fastapi.responses import FileResponse

    path = resolve_photo(get_brand(user["user_id"])["brand_logo"])
    if not path:
        raise HTTPException(status_code=404, detail="No logo")
    return FileResponse(str(path), media_type="image/png", headers={"Cache-Control": "private, max-age=60"})


@app.delete("/api/history")
def clear_all_cards_history(user: dict = Depends(current_user)):
    """Clear the signed-in user's card history (other users are untouched)."""
    clear_history(user_id=user["user_id"])
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
def get_finance_meta():
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
def calculate_profit(req: CalcRequest):
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
def legal_steps(lang: str = "ru"):
    """Return step-by-step legal guide for business registration in Uzbekistan."""
    steps = LEGAL_STEPS_UZ if lang == "uz" else LEGAL_STEPS_RU
    return JSONResponse(content={"steps": steps})


@app.post("/api/legal-qa")
async def legal_qa(req: LegalQARequest, user: dict = Depends(current_user)):
    """AI-powered legal Q&A for Uzbekistan business questions."""
    if not req.question or len(req.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question too short")
    if len(req.question) > 4000:
        raise HTTPException(status_code=413, detail="Question too long")

    reservation = take_reservation("legal_qa", user["user_id"], req.lang)
    reason: Optional[str] = "error"
    try:
        use_mock = ai_service.is_mock or global_ai_budget_exhausted()
        answer, reason = await ai_service.legal_qa(
            question=req.question,
            lang=req.lang,
            user_profile=req.user_profile,
            force_mock=use_mock,
        )
    finally:
        finish_reservation(reservation, reason is None)

    log_event(
        event_type="legal_qa",
        lang=req.lang,
        is_mock=reason is not None,  # what actually happened, not what was planned
        details={
            "question": req.question[:120],
            "has_profile": req.user_profile is not None,
            "ai_fallback": reason,
        },
        user_id=user["user_id"],
    )

    return JSONResponse(content={"answer": answer, "ai_fallback": reason})


# ---------------------------------------------------------------------------
# Tab 4: Uzum Market OpenAPI Integration (Multi-Shop, Orders, Stocks, Finance)
# ---------------------------------------------------------------------------
def _own_telegram_chat_id(user: dict) -> int:
    """Push notifications only go to the signed-in user's own Telegram chat."""
    tg_id = int(user.get("tg_id") or 0)
    if tg_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Telegram chat topilmadi. Ilovani @oqila_ai_bot orqali oching va /start bosing.",
        )
    return tg_id


@app.get("/api/uzum/settings")
def get_uzum_settings_endpoint(user: dict = Depends(current_user)):
    """Retrieve the user's Uzum API connection settings (the API key is returned masked only)."""
    from services.database import get_uzum_settings
    return JSONResponse(content=get_uzum_settings(user["user_id"]))


@app.post("/api/uzum/settings")
async def save_uzum_settings_endpoint(req: UzumSettingsRequest, user: dict = Depends(current_user)):
    """Connect the user's Uzum API key or initialize Demo mode."""
    from services.uzum_service import uzum_service
    tg_id = int(user.get("tg_id") or 0)
    res = await uzum_service.connect_and_sync(
        user_id=user["user_id"],
        api_key=req.api_key,
        is_demo=bool(req.is_demo),
        telegram_chat_id=tg_id if tg_id > 0 else None,
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Error connecting Uzum API"))
    return JSONResponse(content=res)


@app.delete("/api/uzum/settings")
def disconnect_uzum_endpoint(user: dict = Depends(current_user)):
    """Disconnect the user's Uzum account and clear their cached Uzum data."""
    from services.database import disconnect_uzum
    disconnect_uzum(user["user_id"])
    return JSONResponse(content={"status": "ok", "message": "Uzum API muvaffaqiyatli uzildi"})


@app.get("/api/uzum/shops")
def get_uzum_shops_endpoint(user: dict = Depends(current_user)):
    """Get all shops belonging to the user's seller account."""
    from services.database import get_uzum_shops
    shops = get_uzum_shops(user["user_id"])
    return JSONResponse(content={"shops": shops, "count": len(shops)})


@app.get("/api/uzum/orders")
def get_uzum_orders_endpoint(
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(current_user),
):
    """Retrieve the user's Uzum orders filtered by shop_id and status."""
    from services.database import get_uzum_orders
    orders = get_uzum_orders(user["user_id"], shop_id=shop_id, status=status, limit=limit)
    return JSONResponse(content={"orders": orders, "count": len(orders)})


@app.post("/api/uzum/orders/{order_id}/confirm")
async def confirm_uzum_order_endpoint(order_id: int, user: dict = Depends(current_user)):
    """Confirm one of the user's FBS orders (transitions from CREATED to CONFIRMED)."""
    from services.uzum_service import uzum_service
    res = await uzum_service.confirm_order(user["user_id"], order_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return JSONResponse(content=res)


@app.post("/api/uzum/orders/{order_id}/cancel")
async def cancel_uzum_order_endpoint(
    order_id: int,
    req: Optional[UzumCancelOrderRequest] = None,
    user: dict = Depends(current_user),
):
    """Cancel one of the user's FBS orders."""
    from services.uzum_service import uzum_service
    reason = req.reason if req else "Отсутствует на складе"
    res = await uzum_service.cancel_order(user["user_id"], order_id, reason=reason)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return JSONResponse(content=res)


@app.get("/api/uzum/orders/{order_id}/label")
async def get_uzum_order_label(order_id: int, size: str = "LARGE", user: dict = Depends(current_user)):
    """Return shipping label information and printable format (58x40 or 43x25 mm)."""
    from services.uzum_service import uzum_service
    res = await uzum_service.get_order_label(user["user_id"], order_id, size=size)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail="Buyurtma yoki etiketka topilmadi")
    return JSONResponse(content=res)


@app.get("/api/uzum/orders/{order_id}/label.png")
def get_uzum_order_label_png(order_id: int, size: str = "LARGE", user: dict = Depends(current_user_for_media)):
    """Return shipping label as a 203 DPI monochrome PNG image (58x40 or 43x25 mm)."""
    from services.uzum_service import uzum_service
    png_bytes = uzum_service.generate_thermal_label_image(user["user_id"], order_id, size=size)
    if not png_bytes:
        raise HTTPException(status_code=404, detail="Etiketka rasmini yaratib bo'lmadi")
    return Response(content=png_bytes, media_type="image/png")


@app.get("/api/uzum/orders/{order_id}/label.svg")
def get_uzum_order_label_svg(order_id: int, size: str = "LARGE", user: dict = Depends(current_user_for_media)):
    """Return shipping label as a pure vector SVG (58x40 or 43x25 mm)."""
    from services.uzum_service import uzum_service
    svg_content = uzum_service.generate_thermal_label_svg(user["user_id"], order_id, size=size)
    if not svg_content:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    return Response(content=svg_content, media_type="image/svg+xml")


@app.get("/api/uzum/stocks")
def get_uzum_stocks_endpoint(shop_id: Optional[int] = None, user: dict = Depends(current_user)):
    """Retrieve the user's SKU stocks and low-stock indicators."""
    from services.database import get_uzum_stocks
    stocks = get_uzum_stocks(user["user_id"], shop_id=shop_id)
    return JSONResponse(content={"stocks": stocks, "count": len(stocks)})


@app.post("/api/uzum/stocks/update")
def update_uzum_stock_endpoint(req: UzumUpdateStockRequest, user: dict = Depends(current_user)):
    """Update stock quantity for one of the user's SKUs."""
    from services.database import update_uzum_stock_amount
    if req.amount < 0:
        raise HTTPException(status_code=400, detail="Amount must be non-negative")
    ok = update_uzum_stock_amount(user["user_id"], req.sku_id, req.amount)
    if not ok:
        raise HTTPException(status_code=404, detail="SKU topilmadi")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "new_stock": req.amount})


@app.post("/api/uzum/prices/update")
def update_uzum_price_endpoint(req: UzumUpdatePriceRequest, user: dict = Depends(current_user)):
    """Update selling price for one of the user's SKUs."""
    from services.database import update_uzum_price
    if req.price < 0:
        raise HTTPException(status_code=400, detail="Price must be non-negative")
    ok = update_uzum_price(user["user_id"], req.sku_id, req.price)
    if not ok:
        raise HTTPException(status_code=404, detail="SKU topilmadi")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "new_price": req.price})


@app.post("/api/uzum/stocks/cost-price")
def update_uzum_cost_price_endpoint(req: UzumUpdateCostPriceRequest, user: dict = Depends(current_user)):
    """Update cost price (tannarxi / себестоимость) for one of the user's SKUs."""
    from services.database import update_uzum_cost_price
    if req.cost_price < 0:
        raise HTTPException(status_code=400, detail="Cost price must be non-negative")
    ok = update_uzum_cost_price(user["user_id"], req.sku_id, req.cost_price)
    if not ok:
        raise HTTPException(status_code=404, detail="SKU topilmadi")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "cost_price": req.cost_price})


@app.get("/api/uzum/margin-guard")
def get_uzum_margin_guard_endpoint(shop_id: Optional[int] = None, user: dict = Depends(current_user)):
    """Retrieve SKU-level unit economics and margin guard analytics."""
    from services.database import get_uzum_margin_analytics
    return JSONResponse(content=get_uzum_margin_analytics(user["user_id"], shop_id=shop_id))


@app.get("/api/uzum/finance")
def get_uzum_finance_endpoint(shop_id: Optional[int] = None, user: dict = Depends(current_user)):
    """Retrieve financial summary (gross, commission, logistics, tax 1%, net payout)."""
    from services.database import get_uzum_finance_summary
    return JSONResponse(content=get_uzum_finance_summary(user["user_id"], shop_id=shop_id))


@app.post("/api/uzum/sync-now")
async def sync_uzum_now_endpoint(user: dict = Depends(current_user)):
    """Trigger a manual sync of the user's account and dispatch their pending Telegram notifications."""
    from services.uzum_service import uzum_service
    await uzum_service.sync_live_orders_and_stocks(user["user_id"])
    sent = await uzum_service.check_and_send_notifications(user["user_id"])
    return JSONResponse(content={"status": "ok", "sent_notifications": sent, "synced_at": datetime.now().isoformat()})


@app.post("/api/uzum/test-push")
async def test_uzum_push_endpoint(req: UzumTestPushRequest, user: dict = Depends(current_user)):
    """Send a test Telegram push notification to the user's own chat."""
    from services.uzum_service import uzum_service
    chat_id = _own_telegram_chat_id(user)
    ok = await uzum_service.send_test_push(user["user_id"], chat_id=chat_id, lang=req.lang)
    if not ok:
        raise HTTPException(status_code=500, detail="Telegram'ga xabar yuborib bo'lmadi. TELEGRAM_BOT_TOKEN ni tekshiring.")
    return JSONResponse(content={"status": "ok", "chat_id": chat_id})


@app.get("/api/uzum/fbo/forecast")
def get_uzum_fbo_forecast_endpoint(shop_id: Optional[int] = None, user: dict = Depends(current_user)):
    """Retrieve FBO inventory days left forecast and stockout warnings."""
    from services.database import get_uzum_fbo_forecast
    data = get_uzum_fbo_forecast(user["user_id"], shop_id=shop_id)
    return JSONResponse(content={"forecast": data, "count": len(data)})


@app.post("/api/uzum/fbo/test-alert")
async def test_uzum_fbo_alert_endpoint(req: UzumFboAlertRequest, user: dict = Depends(current_user)):
    """Send a proactive Telegram restock alert for one of the user's FBO SKUs to their own chat."""
    from services.uzum_service import uzum_service
    chat_id = _own_telegram_chat_id(user)
    ok = await uzum_service.send_fbo_restock_alert(user["user_id"], chat_id=chat_id, sku_id=req.sku_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Telegram'ga xabar yuborib bo'lmadi.")
    return JSONResponse(content={"status": "ok", "sku_id": req.sku_id, "chat_id": chat_id})


# ---------------------------------------------------------------------------
# Analytics & Stats (SQLite)
# ---------------------------------------------------------------------------
@app.get("/api/stats")
def get_analytics():
    """Public aggregate statistics (counts only) for the /stage presentation page."""
    stats = get_stats()
    stats["bot_username"] = os.getenv("TELEGRAM_BOT_USERNAME", "oqila_ai_bot").strip().lstrip("@") or "oqila_ai_bot"
    stats["generated_at"] = datetime.now().isoformat(timespec="seconds")
    return JSONResponse(content=stats, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Admin Panel API Endpoints (Protected by X-Admin-Key or admin_key query)
# ---------------------------------------------------------------------------
@app.get("/api/admin/dashboard")
def admin_dashboard(admin_auth: bool = Security(verify_admin_key)):
    """Retrieve high-level dashboard metrics for the administrator."""
    metrics = get_admin_dashboard_metrics()
    return JSONResponse(content=metrics)


@app.get("/api/admin/users")
def admin_get_users(
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
def admin_get_user_details(user_id: int, admin_auth: bool = Security(verify_admin_key)):
    """Retrieve detailed profile, cards, and events for a specific user."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_cards = get_admin_cards(user_id=user_id, limit=20, offset=0)
    user_events = get_admin_events(user_id=user_id, limit=50, offset=0)
    return JSONResponse(content={"user": user, "cards": user_cards, "events": user_events})


@app.post("/api/admin/users/{user_id}/toggle-active")
def admin_toggle_user_active(user_id: int, admin_auth: bool = Security(verify_admin_key)):
    """Toggle user active status (enable/disable account)."""
    new_status = toggle_user_active(user_id)
    if new_status is None:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(content={"status": "ok", "user_id": user_id, "is_active": new_status})


@app.post("/api/admin/users/{user_id}/toggle-admin")
def admin_toggle_user_admin(user_id: int, admin_auth: bool = Security(verify_admin_key)):
    """Grant or revoke administrator rights of a Telegram user (the only way to set the flag by hand)."""
    from services.database import set_user_admin

    target = get_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    tg_id = int(target.get("tg_id") or 0)
    if tg_id <= 0:
        raise HTTPException(status_code=400, detail="Browser guests cannot be administrators")
    new_state = not bool(target.get("is_admin"))
    if not set_user_admin(tg_id, new_state):
        raise HTTPException(status_code=500, detail="Could not update the user")
    telegram_service.forget_admin_cache(tg_id)
    return {"status": "ok", "user_id": user_id, "is_admin": new_state}


@app.get("/api/admin/events")
def admin_get_events(
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
def admin_get_cards(
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    admin_auth: bool = Security(verify_admin_key),
):
    """Retrieve generated cards across all users."""
    cards = get_admin_cards(user_id=user_id, limit=limit, offset=offset)
    return JSONResponse(content={"cards": cards, "limit": limit, "offset": offset})


@app.get("/api/admin/cards/{card_id}/photo")
def admin_get_card_photo(card_id: int, admin_auth: bool = Security(verify_admin_key)):
    """Serve any card's studio photo to administrators."""
    return _card_photo_response(card_id, owner_id=None)


@app.get("/api/admin/export/users.csv")
def admin_export_users_csv(admin_auth: bool = Security(verify_admin_key)):
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
def admin_export_cards_csv(admin_auth: bool = Security(verify_admin_key)):
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
_webhook_tasks: set = set()  # strong references: the loop only keeps weak ones to running tasks


@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates."""
    import hmac

    secret = get_webhook_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")
    header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(header_token.encode("utf-8"), secret.encode("utf-8")):
        logger.warning("Rejected unauthorized Telegram webhook update")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        update = await request.json()
    except Exception:
        return {"ok": True}
    if not isinstance(update, dict):
        return {"ok": True}
    host_url = str(request.base_url).rstrip("/")
    if request.headers.get("x-forwarded-proto") == "https":
        host_url = host_url.replace("http://", "https://")

    # Telegram re-sends an update when the answer is slow (an AI call takes longer than its timeout), which
    # used to run the same generation several times. So: remember the update id, answer 200 at once and
    # do the work in the background.
    update_id = update.get("update_id")
    if isinstance(update_id, int) and not remember_telegram_update(update_id):
        return {"ok": True, "duplicate": True}

    async def process() -> None:
        try:
            await telegram_service.handle_update(update, default_app_url=host_url)
        except Exception as exc:
            logger.error("Error processing telegram update: %s", exc)

    task = asyncio.create_task(process())
    _webhook_tasks.add(task)
    task.add_done_callback(_webhook_tasks.discard)
    return {"ok": True}


@app.post("/api/set-webhook")
async def set_telegram_webhook(
    request: Request,
    req: Optional[SetWebhookRequest] = None,
    admin_auth: bool = Security(verify_admin_key),
):
    """Register webhook URL with Telegram Bot API (administrators only)."""
    target_url = (req.url if req and req.url else None) or os.getenv("WEBAPP_URL")
    if not target_url and request:
        target_url = str(request.base_url).rstrip("/")
        if request.headers.get("x-forwarded-proto") == "https":
            target_url = target_url.replace("http://", "https://")

    if not target_url:
        raise HTTPException(status_code=400, detail="Webhook URL must be provided")

    if not target_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Webhook URL must use https://")
    result = await telegram_service.set_webhook(target_url, secret_token=get_webhook_secret())
    return JSONResponse(content=result)


@app.get("/api/webhook-info")
async def get_webhook_status(admin_auth: bool = Security(verify_admin_key)):
    """Get current Telegram webhook registration status (administrators only)."""
    info = await telegram_service.get_webhook_info()
    return JSONResponse(content=info)


# ---------------------------------------------------------------------------
# SPA Catch-all Route
# ---------------------------------------------------------------------------
@app.get("/{full_path:path}", include_in_schema=False)
def catch_all(full_path: str):
    """Serve SPA index for deep links or static assets from dist."""
    from fastapi.responses import FileResponse
    # Do not intercept API, health, static or assets
    if full_path.startswith(("api/", "health", "assets/")):
        raise HTTPException(status_code=404, detail="Not found")

    if FRONTEND_DIST.exists() and full_path:
        dist_root = FRONTEND_DIST.resolve()
        file_in_dist = (dist_root / full_path).resolve()
        # Only serve files that really live inside frontend/dist (blocks ../ path traversal)
        if file_in_dist.is_relative_to(dist_root) and file_in_dist.is_file():
            return FileResponse(str(file_in_dist))

    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return FileResponse(str(react_index))
    raise HTTPException(status_code=404, detail="Index not found")


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=os.getenv("UVICORN_RELOAD", "0") == "1")
