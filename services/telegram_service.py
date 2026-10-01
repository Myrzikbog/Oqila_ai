"""
telegram_service.py — Telegram Bot Integration for Oqila AI
Features:
- WebApp integration & /start
- Bot commands menu setup (setMyCommands)
- Quick tax & price calculator (/tax, /price)
- Instant demo product packaging (/demo)
- Direct photo message handling (send photo -> AI packages item)
- Inline query mode (@bot 350000 120000 in any chat)
- Daily business tips (/tips) & subscription (/subscribe)
- Uzbekistan 2026 Tax calendar (/calendar)
"""
from __future__ import annotations

import html
import io
import json
import logging
import os
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from services.database import (
    get_all_users,
    get_user_by_tg_id,
    get_user_lang,
    get_user_terms_agreed,
    log_event,
    save_subscriber,
    set_user_admin,
    set_user_lang,
    set_user_terms_agreed,
    unsubscribe_subscriber,
    upsert_user,
)
from services.legal_calc import calculate

logger = logging.getLogger("oqila_telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"

DAILY_TIPS_UZ = [
    "💡 <b>Savdo maslahati:</b> Uzum Market'da sotayotganda, mahsulot tannarxiga kamida 25-30% ustama qo'ying. Bu marketpleysning 12% komissiyasi va 15 000 so'm logistika to'lovini qoplaydi hamda sizga sof foyda qoldiradi.",
    "🧵 <b>Hunarmand qizlar uchun:</b> «Hunarmand» uyushmasi a'zolari uchun soliq 0%! Boshqa o'z-o'zini band qilganlarda esa 2026-yildan 1% yagona aylanma solig'i amal qiladi.",
    "📸 <b>Vizual marketing:</b> Instagram va Telegram kanalda mahsulotni faqat oq fonda emas, balki 'hayotiy' muhitda (masalan, kiyimni qizlar kiygan holda, dasturxonni bezatilgan holda) ko'rsatish sotuvni 40% ga oshiradi.",
    "📦 <b>Qayta sotish (Xitoy/bozor):</b> E'tibor bering! Xitoydan yoki ulgurji bozordan olib qayta sotishda o'z-o'zini band qilish QONUN BO'YICHA TAQIQLANGAN. Jarimaga tushmaslik uchun YaTT (yagona 1% soliq) ochish shart.",
    "💳 <b>To'lov tizimlari:</b> Telegram bot yoki Instagram do'konda Click va Payme ulash — xaridor ishonchini 2 barobar oshiradi. Click/Payme ekvayring komissiyasi odatda 1.5% ni tashkil qiladi.",
    "🏷️ <b>Xaridorni jalb qilish:</b> Narxni 199 000 so'm yoki 249 000 so'm qilib belgilash (psixologik narxlash) yaxlit 200 000 yoki 250 000 so'mdan ko'ra 15% ko'proq buyurtma olib keladi.",
]

DAILY_TIPS_RU = [
    "💡 <b>Совет по продажам:</b> Продавая на Uzum Market, закладывайте в цену наценку не менее 25-30%. Это покроет комиссию маркетплейса (~12-14%) и логистику, оставляя вам чистую прибыль.",
    "🧵 <b>Для мастериц и ремесленниц:</b> Члены ассоциации «Хунарманд» полностью освобождены от налога с оборота (0%)! Для остальных самозанятых с 2026 г. действует ставка 1%.",
    "📸 <b>Визуальный маркетинг:</b> В соцсетях и Telegram показывайте товар в реальной обстановке (одежду на модели, декор в интерьере) — это повышает конверсию на 40%.",
    "📦 <b>Перепродажа (Китай/рынки):</b> Важно! Перепродавать чужие покупные товары в статусе самозанятого ЗАПРЕЩЕНО законом. Оформите ЯТТ (налог с оборота 1%), чтобы избежать штрафов.",
    "💳 <b>Приём платежей:</b> Подключение Click и Payme повышает доверие покупателей в 2 раза. Комиссия эквайринга составляет около 1.5%.",
    "🏷️ <b>Психология цен:</b> Цены 199 000 или 249 000 сум привлекают на 15% больше заказов, чем круглые суммы 200 000 или 250 000 сум.",
]

TAX_CALENDAR_TEXT_UZ = (
    "📅 <b>O'zbekiston 2026 — Kichik biznes va YaTT Soliq Taqvimi:</b>\n\n"
    "📌 <b>Har oyning 15-sanasigacha:</b>\n"
    "• YaTT uchun majburiy ijtimoiy soliq — 1 BHM (440 000 so'm). Soliq mobil ilovasi orqali to'lanadi.\n\n"
    "📌 <b>Chorak yakuni bo'yicha (har 3 oyda):</b>\n"
    "• Aylanmadan olinadigan soliq (yagona 1% stavka, SK 467-modda) — chorakdan keyingi oyning 15-sanasigacha.\n\n"
    "📌 <b>O'z-o'zini band qilganlar:</b>\n"
    "• Aylanmadan olinadigan soliq — 1% (2026-yildan joriy etilgan, SK 467-modda).\n"
    "• Pensiya staji uchun ijtimoiy soliq — yil davomida ixtiyoriy 1 BHM.\n\n"
    "⚠️ <b>Yillik aylanma 1 mlrd so'mdan oshsa:</b>\n"
    "QQS (12%) to'lovchisi sifatida ro'yxatdan o'tish majburiyati vujudga keladi."
)

TAX_CALENDAR_TEXT_RU = (
    "📅 <b>Узбекистан 2026 — Налоговый календарь для малого бизнеса и ЯТТ:</b>\n\n"
    "📌 <b>Каждый месяц до 15-го числа:</b>\n"
    "• Обязательный соцналог для ЯТТ — 1 БРВ (440 000 сум). Оплачивается через приложение Soliq.\n\n"
    "📌 <b>По итогам квартала (каждые 3 месяца):</b>\n"
    "• Налог с оборота (единая ставка 1%, ст. 467 НК РУз) — до 15-го числа месяца, следующего за кварталом.\n\n"
    "📌 <b>Самозанятые лица:</b>\n"
    "• Налог с оборота — 1% (с 1 января 2026 г., ст. 467 НК РУз).\n"
    "• Соцналог для трудового стажа — добровольно 1 БРВ в год.\n\n"
    "⚠️ <b>При годовом обороте свыше 1 млрд сум:</b>\n"
    "Возникает обязательство перехода на НДС (12%) и налог на прибыль."
)

LANG_SELECTION_TEXT = (
    "🇺🇿 <b>Oqila AI platformasiga xush kelibsiz!</b>\n"
    "Iltimos, muloqot tilini tanlang:\n\n"
    "🇷🇺 <b>Добро пожаловать в платформу Oqila AI!</b>\n"
    "Пожалуйста, выберите язык общения:"
)

TERMS_TEXT_UZ = (
    "📋 <b>Foydalanuvchi shartnomasi va javobgarlikdan cheklanish</b>\n\n"
    "«Oqila AI» xizmatidan foydalanishni boshlashdan oldin quyidagi shartlar bilan tanishib chiqing:\n\n"
    "1. <b>Tavsiyaviy xarakter:</b> «Oqila AI» sun'iy intellekt texnologiyalariga asoslangan bo'lib, "
    "taqdim etiladigan barcha ma'lumotlar, narx hisob-kitoblari, soliq konsultatsiyalari va marketing "
    "tavsiyalari faqat <i>tavsiyaviy va axborot xarakteriga</i> ega.\n\n"
    "2. <b>Moliyaviy va huquqiy xavflar:</b> Xizmat yaratuvchilari va ma'muriyati foydalanuvchining tijoriy faoliyati, "
    "daromadlari yoki zararlari, soliq organlari bilan munosabatlari, jarimalar, marketpleyslar (jumladan Uzum Market) "
    "qoidalari o'zgarishi yoki narx belgilashdagi xatoliklar uchun <i>hech qanday moddiy yoki yuridik javobgarlikni o'z zimmasiga olmaydi</i>.\n\n"
    "3. <b>Foydalanuvchi mas'uliyati:</b> O'z biznesingiz, buxgalteriya hisoboti, to'lanadigan soliqlar aniqligi hamda "
    "tovarlar sifati va savdo qonuniyligi uchun to'liq javobgarlik o'zingizda qoladi.\n\n"
    "4. <b>Ma'lumotlar xavfsizligi:</b> Tizim foydalanuvchi tajribasini yaxshilash maqsadida kiritilgan ma'lumotlarni "
    "xavfsiz qayta ishlaydi.\n\n"
    "👇 <i>Davom etish uchun quyidagi tugma orqali shartlarga rozilik bildiring:</i>"
)

TERMS_TEXT_RU = (
    "📋 <b>Пользовательское соглашение и отказ от ответственности</b>\n\n"
    "Перед началом использования сервиса «Oqila AI», пожалуйста, ознакомьтесь с условиями:\n\n"
    "1. <b>Рекомендательный характер:</b> Сервис «Oqila AI» работает на базе искусственного интеллекта. "
    "Все расчёты цен, наценок, налогов, маркетинговые тексты и юридические ответы носят <i>исключительно "
    "ознакомительный и рекомендательный характер</i>.\n\n"
    "2. <b>Отказ от ответственности:</b> Администрация и создатели платформы <i>не несут никакой финансовой или "
    "юридической ответственности</i> за коммерческие риски, недополученную прибыль, возможные убытки, налоговые штрафы "
    "или изменения регламентов сторонних маркетплейсов (включая Uzum Market).\n\n"
    "3. <b>Ответственность пользователя:</b> Пользователь самостоятельно несёт полную ответственность за ведение своего "
    "бизнеса, правильность налоговой и бухгалтерской отчётности, ценообразование и законность реализуемых товаров.\n\n"
    "4. <b>Конфиденциальность:</b> Сервис обрабатывает пользовательские данные в соответствии с установленными нормами "
    "безопасности исключительно для работы функционала.\n\n"
    "👇 <i>Для продолжения подтвердите своё согласие с условиями:</i>"
)

WELCOME_TEXT_UZ = (
    "👋 <b>Assalomu alaykum, {username}!</b>\n\n"
    "🌿 <b>«Oqila AI»</b> — O'zbekiston tadbirkor ayollari va hunarmandlari uchun "
    "sun'iy intellektga asoslangan raqamli biznes-assistent!\n\n"
    "✨ <b>Nimalar qila olaman:</b>\n"
    "• 📸 <b>Mahsulot qadoqlash:</b> Menga mahsulot rasmini yuboring — AI studiya fotosi va tayyor marketing postini yaratadi!\n"
    "• 💰 <b>Foyda va soliq hisobi:</b> /tax 380000 120000 buyrug'i orqali sof foydani hisoblang.\n"
    "• 🛍️ <b>Uzum Market:</b> /uzum orqali do'konlar va buyurtmalarni boshqaring.\n"
    "• 💡 <b>/tips:</b> Biznesni rivojlantirish bo'yicha kunlik tavsiyalar.\n"
    "• 📅 <b>/calendar:</b> O'zR soliq va hisobot muddatlari.\n"
    "• 🤖 <b>OqilaLegal:</b> Huquq va soliq bo'yicha har qanday savolingizga javob beraman.\n\n"
    "👇 <b>To'liq interaktiv ilovani ochish:</b>"
)

WELCOME_TEXT_RU = (
    "👋 <b>Здравствуйте, {username}!</b>\n\n"
    "🌿 <b>«Oqila AI»</b> — ваш умный цифровой бизнес-ассистент на базе ИИ для "
    "предпринимательниц и мастериц Узбекистана!\n\n"
    "✨ <b>Что я умею:</b>\n"
    "• 📸 <b>Упаковка товара:</b> Отправьте фото изделия в этот чат — ИИ создаст продающее студийное фото и готовый маркетинговый пост!\n"
    "• 💰 <b>Расчёт прибыли и налогов:</b> Команда /tax 380000 120000 рассчитает маржу, комиссии Uzum и чистый доход.\n"
    "• 🛍️ <b>Uzum Market:</b> Команда /uzum покажет статус магазинов, заказы и выплаты.\n"
    "• 💡 <b>/tips:</b> Ежедневные практические советы по развитию продаж.\n"
    "• 📅 <b>/calendar:</b> Налоговый календарь и сроки отчётов в РУз (2026).\n"
    "• 🤖 <b>OqilaLegal:</b> ИИ-консультант по налогам и правовым вопросам.\n\n"
    "👇 <b>Открыть интерактивное приложение:</b>"
)



class TelegramService:
    def __init__(self) -> None:
        self._verified_admin_tg_ids: set[str] = set()

    @property
    def bot_token(self) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    @property
    def webapp_url(self) -> str:
        return os.getenv("WEBAPP_URL", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token)

    def _api_url(self, method: str) -> str:
        return f"{TELEGRAM_API_BASE}/bot{self.bot_token}/{method}"

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a message to a chat."""
        if not self.is_configured:
            logger.warning("Telegram Bot Token is not configured.")
            return False

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._api_url("sendMessage"), json=payload)
                if res.status_code == 200:
                    return True
                logger.error("Telegram sendMessage error: %s - %s", res.status_code, res.text)
                # If entity parse error occurred, retry sending without parse_mode as plain text
                if "can't parse entities" in res.text and payload.get("parse_mode"):
                    payload_plain = dict(payload)
                    payload_plain.pop("parse_mode", None)
                    res_plain = await client.post(self._api_url("sendMessage"), json=payload_plain)
                    return res_plain.status_code == 200
                return False
        except Exception as exc:
            logger.error("Failed to send telegram message: %s", exc)
            return False

    async def send_photo(
        self,
        chat_id: int | str,
        photo_url_or_bytes: str | bytes,
        caption: Optional[str] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a photo by URL or binary bytes."""
        if not self.is_configured:
            return False

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                if isinstance(photo_url_or_bytes, bytes):
                    files = {"photo": ("photo.jpg", photo_url_or_bytes, "image/jpeg")}
                    data: Dict[str, Any] = {"chat_id": str(chat_id), "parse_mode": parse_mode}
                    if caption:
                        data["caption"] = caption[:1024]
                    if reply_markup:
                        data["reply_markup"] = json.dumps(reply_markup)
                    res = await client.post(self._api_url("sendPhoto"), data=data, files=files)
                elif photo_url_or_bytes.startswith("data:"):
                    # base64 data URI
                    import base64
                    header, b64_data = photo_url_or_bytes.split(",", 1)
                    raw_bytes = base64.b64decode(b64_data)
                    files = {"photo": ("photo.jpg", raw_bytes, "image/jpeg")}
                    data = {"chat_id": str(chat_id), "parse_mode": parse_mode}
                    if caption:
                        data["caption"] = caption[:1024]
                    if reply_markup:
                        data["reply_markup"] = json.dumps(reply_markup)
                    res = await client.post(self._api_url("sendPhoto"), data=data, files=files)
                else:
                    payload: Dict[str, Any] = {
                        "chat_id": chat_id,
                        "photo": photo_url_or_bytes,
                        "parse_mode": parse_mode,
                    }
                    if caption:
                        payload["caption"] = caption[:1024]
                    if reply_markup:
                        payload["reply_markup"] = reply_markup
                    res = await client.post(self._api_url("sendPhoto"), json=payload)

                return res.status_code == 200
        except Exception as exc:
            logger.error("Failed to send photo: %s", exc)
            return False

    async def send_document(
        self,
        chat_id: int | str,
        document_bytes: bytes,
        filename: str = "report.csv",
        caption: Optional[str] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a document or file directly to a Telegram chat."""
        if not self.is_configured:
            return False
        data: Dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]
            data["parse_mode"] = "HTML"
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        files = {
            "document": (filename, document_bytes, "text/csv")
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(self._api_url("sendDocument"), data=data, files=files)
                return res.status_code == 200
        except Exception as exc:
            logger.error("Failed to send document to %s: %s", chat_id, exc)
            return False

    async def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """Edit an existing Telegram message text."""
        if not self.is_configured:
            return False
        payload: Dict[str, Any] = {
            "chat_id": str(chat_id),
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._api_url("editMessageText"), json=payload)
                return res.status_code == 200
        except Exception as exc:
            logger.error("Failed to edit message in %s: %s", chat_id, exc)
            return False

    def is_admin_user(self, user_id: int | str, provided_key: Optional[str] = None) -> bool:
        """Check if Telegram user is authorized as an administrator."""
        uid_str = str(user_id).strip()
        if uid_str in self._verified_admin_tg_ids:
            return True

        secret_key = os.getenv("ADMIN_SECRET_KEY", "oqila_admin_2026").strip()
        if provided_key and provided_key.strip() == secret_key:
            self._verified_admin_tg_ids.add(uid_str)
            try:
                from services.database import set_user_admin
                set_user_admin(int(user_id), True)
            except Exception:
                pass
            return True

        admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
        if admin_ids_str:
            admin_ids = [i.strip() for i in admin_ids_str.split(",") if i.strip()]
            if uid_str in admin_ids:
                self._verified_admin_tg_ids.add(uid_str)
                return True

        # Check database persistent status
        try:
            from services.database import get_user_by_tg_id
            u = get_user_by_tg_id(int(user_id))
            if u and u.get("is_admin"):
                self._verified_admin_tg_ids.add(uid_str)
                return True
        except Exception:
            pass

        return False

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> bool:
        """Acknowledge a callback query from an inline keyboard button."""
        if not self.is_configured:
            return False
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._api_url("answerCallbackQuery"), json=payload)
                return res.status_code == 200
        except Exception as exc:
            logger.error("Failed to answer callback query: %s", exc)
            return False

    async def answer_inline_query(
        self,
        inline_query_id: str,
        results: List[Dict[str, Any]],
        cache_time: int = 10,
    ) -> bool:
        """Answer an inline query from any chat."""
        if not self.is_configured:
            return False
        payload = {
            "inline_query_id": inline_query_id,
            "results": results,
            "cache_time": cache_time,
            "is_personal": True,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._api_url("answerInlineQuery"), json=payload)
                return res.status_code == 200
        except Exception as exc:
            logger.error("Failed to answer inline query: %s", exc)
            return False

    async def download_telegram_file(self, file_id: str) -> Optional[bytes]:
        """Download file bytes sent by a user in Telegram chat."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(self._api_url("getFile"), params={"file_id": file_id})
                if res.status_code != 200:
                    return None
                file_path = res.json().get("result", {}).get("file_path")
                if not file_path:
                    return None
                file_url = f"{TELEGRAM_API_BASE}/file/bot{self.bot_token}/{file_path}"
                dl_res = await client.get(file_url)
                if dl_res.status_code == 200:
                    return dl_res.content
        except Exception as exc:
            logger.error("Failed to download Telegram file: %s", exc)
        return None

    async def set_my_commands(self) -> bool:
        """Register the official bot commands menu in Telegram (Item 1)."""
        if not self.is_configured:
            return False
        commands = [
            {"command": "start", "description": "🚀 Oqila AI ilovasi (Mini App)"},
            {"command": "lang", "description": "🌐 Tilni tanlash / Выбор языка"},
            {"command": "demo", "description": "📸 Namuna mahsulot qadoqlash"},
            {"command": "tax", "description": "💰 Soliq & marja hisobi (masalan: /tax 350000 120000)"},
            {"command": "uzum", "description": "🛍️ Uzum Market: do'konlar, buyurtmalar va qoldiqlar"},
            {"command": "price", "description": "🏷️ Narx va sof foyda hisobi"},
            {"command": "tips", "description": "💡 Kunlik biznes maslahati"},
            {"command": "calendar", "description": "📅 Soliq va hisobot taqvimi"},
            {"command": "subscribe", "description": "🔔 Soliq eslatmalariga obuna"},
            {"command": "unsubscribe", "description": "🔕 Obunani bekor qilish"},
            {"command": "help", "description": "ℹ️ Bot qo'llanmasi va yordam"},
        ]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._api_url("setMyCommands"), json={"commands": commands})
                data = res.json()
                logger.info("Configured Telegram bot commands menu: %s", data)
                return bool(data.get("ok"))
        except Exception as exc:
            logger.error("Failed to set bot commands: %s", exc)
            return False

    async def set_webhook(self, webhook_url: str, secret_token: Optional[str] = None) -> Dict[str, Any]:
        """Configure Telegram webhook with optional secret_token validation."""
        if not self.is_configured:
            return {"ok": False, "description": "TELEGRAM_BOT_TOKEN not configured"}

        url = f"{webhook_url.rstrip('/')}/api/telegram-webhook"
        token = secret_token or os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip() or None
        payload: Dict[str, Any] = {"url": url}
        if token:
            payload["secret_token"] = token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._api_url("setWebhook"), json=payload)
                data = res.json()
                logger.info("Set webhook to %s: %s", url, data)
                # Auto configure commands menu as well
                await self.set_my_commands()
                return data
        except Exception as exc:
            logger.error("Failed to set webhook: %s", exc)
            return {"ok": False, "description": str(exc)}

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook status."""
        if not self.is_configured:
            return {"ok": False, "description": "TELEGRAM_BOT_TOKEN not configured"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(self._api_url("getWebhookInfo"))
                return res.json()
        except Exception as exc:
            return {"ok": False, "description": str(exc)}

    # -----------------------------------------------------------------------
    # Main Update Dispatcher
    # -----------------------------------------------------------------------
    async def handle_update(self, update: Dict[str, Any], default_app_url: str) -> None:
        """Process incoming Telegram update with rich commands, inline query, and photo handling."""
        app_url = self.webapp_url or default_app_url

        # 1. Handle Inline Query (@bot 300000 100000) (Item 4)
        if "inline_query" in update:
            await self._handle_inline_query(update["inline_query"], app_url)
            return

        # 2. Handle Inline Button Callbacks
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb.get("id")
            cb_data = cb.get("data")
            chat_id = cb.get("message", {}).get("chat", {}).get("id")
            cb_user_id = cb.get("from", {}).get("id") or chat_id
            if cb_id:
                await self.answer_callback_query(cb_id)

            if cb_data == "cmd_change_lang" and chat_id:
                await self.send_message(
                    chat_id,
                    LANG_SELECTION_TEXT,
                    reply_markup=self._build_language_keyboard(),
                )
            elif cb_data in ("set_lang_uz", "set_lang_ru") and chat_id:
                selected_lang = "uz" if cb_data == "set_lang_uz" else "ru"
                set_user_lang(cb_user_id, selected_lang)
                terms_ok = get_user_terms_agreed(cb_user_id)
                if not terms_ok:
                    terms_text = TERMS_TEXT_UZ if selected_lang == "uz" else TERMS_TEXT_RU
                    await self.send_message(
                        chat_id,
                        terms_text,
                        reply_markup=self._build_terms_keyboard(lang=selected_lang),
                    )
                else:
                    confirm_text = (
                        "🇺🇿 <b>Muloqot tili o'zbek tiliga o'zgartirildi!</b>"
                        if selected_lang == "uz"
                        else "🇷🇺 <b>Язык общения успешно изменён на русский!</b>"
                    )
                    await self.send_message(chat_id, confirm_text)
                    from_user = cb.get("from", {})
                    uname = html.escape(from_user.get("first_name") or from_user.get("username") or "Tadbirkor")
                    w_text = (
                        WELCOME_TEXT_UZ.format(username=uname)
                        if selected_lang == "uz"
                        else WELCOME_TEXT_RU.format(username=uname)
                    )
                    await self.send_message(
                        chat_id,
                        w_text,
                        reply_markup=self._build_main_keyboard(app_url, lang=selected_lang),
                    )
            elif cb_data in ("accept_terms_uz", "accept_terms_ru") and chat_id:
                agreed_lang = "uz" if cb_data == "accept_terms_uz" else "ru"
                set_user_terms_agreed(cb_user_id, agreed=True, lang=agreed_lang)
                from_user = cb.get("from", {})
                uname = html.escape(from_user.get("first_name") or from_user.get("username") or "Tadbirkor")
                accepted_msg = (
                    "✅ <b>Foydalanuvchi shartnomasi qabul qilindi!</b>\n\n"
                    "«Oqila AI»ga xush kelibsiz. Quyidagi tugma orqali ilovani ochishingiz mumkin:"
                    if agreed_lang == "uz"
                    else "✅ <b>Пользовательское соглашение успешно принято!</b>\n\n"
                    "Добро пожаловать в «Oqila AI». Вы можете открыть приложение кнопкой ниже:"
                )
                await self.send_message(chat_id, accepted_msg)
                w_text = (
                    WELCOME_TEXT_UZ.format(username=uname)
                    if agreed_lang == "uz"
                    else WELCOME_TEXT_RU.format(username=uname)
                )
                await self.send_message(
                    chat_id,
                    w_text,
                    reply_markup=self._build_main_keyboard(app_url, lang=agreed_lang),
                )
            elif cb_data == "demo" and chat_id:
                user_lang = get_user_lang(cb_user_id, "uz")
                await self._handle_demo_command(chat_id, app_url, lang=user_lang)
            elif cb_data == "help" and chat_id:
                user_lang = get_user_lang(cb_user_id, "uz")
                if user_lang == "ru":
                    help_text = (
                        "ℹ️ <b>Справка по боту Oqila AI</b>\n\n"
                        "• 🚀 <b>Mini App:</b> Откройте полную AI-студию и калькулятор кнопкой ниже.\n"
                        "• 📸 <b>Отправьте фото:</b> ИИ создаст продающее студийное фото и готовый маркетинговый пост.\n"
                        "• 💰 <b>/tax 380000 120000:</b> Быстрый расчёт налогов и чистой прибыли на Uzum Market.\n"
                        "• 🛍️ <b>/uzum:</b> Управление магазинами, заказами и остатками.\n"
                        "• 💡 <b>/tips:</b> Полезные советы для предпринимательниц.\n"
                        "• 📅 <b>/calendar:</b> Сроки налоговых платежей и отчётов.\n"
                        "• 🌐 <b>/lang:</b> Выбор языка (O'zbekcha / Русский)."
                    )
                else:
                    help_text = (
                        "ℹ️ <b>Oqila AI Bot Qo'llanmasi</b>\n\n"
                        "• 🚀 <b>Mini App:</b> Pastdagi tugmani bosib to'liq AI Studiya va kalkulyatorni oching.\n"
                        "• 📸 <b>Rasm yuboring:</b> Mahsulot rasmini shu chatga yuborsangiz, AI uni tahlil qilib sotiq matnini tayyorlaydi.\n"
                        "• 💰 <b>/tax 380000 120000:</b> Tezkor soliq va Uzum sof foydasi hisobi.\n"
                        "• 🛍️ <b>/uzum:</b> Uzum Market do'konlari, yangi buyurtmalar va qoldiqlar.\n"
                        "• 💡 <b>/tips:</b> Ayol tadbirkorlar uchun foydali maslahat.\n"
                        "• 📅 <b>/calendar:</b> O'zR soliq muddatlari va hisobotlar.\n"
                        "• 🌐 <b>/lang:</b> Tilni tanlash (O'zbekcha / Русский)."
                    )
                await self.send_message(chat_id, help_text)
            elif cb_data == "tips" and chat_id:
                user_lang = get_user_lang(cb_user_id, "uz")
                tip = random.choice(DAILY_TIPS_RU if user_lang == "ru" else DAILY_TIPS_UZ)
                await self.send_message(chat_id, tip)
            elif cb_data and cb_data.startswith("uzum_confirm_"):
                try:
                    order_id = int(cb_data.replace("uzum_confirm_", ""))
                    from services.uzum_service import uzum_service
                    await uzum_service.confirm_order(order_id)
                    await self.send_message(
                        chat_id,
                        f"✅ <b>Buyurtma #{order_id} muvaffaqiyatli tasdiqlandi!</b>\n\n"
                        f"📦 Holat: <b>Yig'ilmoqda (В сборке)</b>\n"
                        f"🏷️ Shtrix-kod etiketkasini chiqarib, buyurtmaga yopishtiring va Uzum punktiga topshiring.",
                    )
                except Exception as exc:
                    logger.error("Error in uzum_confirm callback: %s", exc)
            elif cb_data and cb_data.startswith("uzum_label_"):
                try:
                    order_id = int(cb_data.replace("uzum_label_", ""))
                    from services.uzum_service import uzum_service
                    label_bytes = uzum_service.generate_thermal_label_image(order_id, size="LARGE")

                    caption = (
                        f"🏷️ <b>Uzum FBS Markirovka etiketkasi</b>\n\n"
                        f"📦 Buyurtma: <code>#{order_id}</code>\n"
                        f"📏 Standart o'lcham: <b>58×40 mm (203 DPI)</b>\n\n"
                        f"💡 <i>Ushbu rasmni to'g'ridan-to'g'ri Bluetooth termoprinterga yuborib chop etishingiz yoki skaner qilishingiz mumkin!</i>"
                    )

                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "✅ Tasdiqlash / Подтвердить",
                                    "callback_data": f"uzum_confirm_{order_id}",
                                }
                            ],
                            [
                                {
                                    "text": "📱 Oqila ilovasini ochish",
                                    "web_app": {"url": f"{app_url}?tab=uzum"} if app_url.startswith("https://") else None,
                                    "url": app_url if not app_url.startswith("https://") else None,
                                }
                            ]
                        ]
                    }
                    keyboard["inline_keyboard"] = [
                        [btn for btn in row if btn.get("url") or btn.get("web_app") or btn.get("callback_data")]
                        for row in keyboard["inline_keyboard"]
                    ]

                    await self.send_photo(
                        chat_id=chat_id,
                        photo_url_or_bytes=label_bytes,
                        caption=caption,
                        reply_markup=keyboard,
                    )
                except Exception as exc:
                    logger.error("Error generating label photo in Telegram: %s", exc)
                    await self.send_message(
                        chat_id,
                        f"🏷️ Buyurtma #{order_id} etiketkasi ilovada mavjud.",
                    )
            elif cb_data == "admin_refresh" and chat_id:
                cb_user_id = cb.get("from", {}).get("id")
                if not self.is_admin_user(cb_user_id):
                    await self.send_message(chat_id, "⛔ <b>Sizda admin huquqlari mavjud emas.</b>")
                else:
                    msg_id = cb.get("message", {}).get("message_id")
                    await self._handle_admin_command(
                        chat_id=chat_id,
                        app_url=app_url,
                        text="/admin",
                        user_id=cb_user_id,
                        is_refresh=True,
                        message_id=msg_id,
                    )
            elif cb_data == "admin_csv_users" and chat_id:
                cb_user_id = cb.get("from", {}).get("id")
                if not self.is_admin_user(cb_user_id):
                    await self.send_message(chat_id, "⛔ <b>Sizda admin huquqlari mavjud emas.</b>")
                else:
                    from services.database import get_all_users
                    from services.csv_service import generate_users_csv
                    from datetime import datetime
                    users = get_all_users(limit=10000, offset=0)
                    csv_bytes = generate_users_csv(users)
                    fname = f"oqila_users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                    caption = (
                        f"📊 <b>Oqila AI — Foydalanuvchilar bazasi</b>\n\n"
                        f"👥 Jami: <b>{len(users)}</b> ta tadbirkor\n"
                        f"📅 Sana: <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>\n\n"
                        f"<i>Microsoft Excel uchun to'liq moslashtirilgan (UTF-8 BOM, ';').</i>"
                    )
                    await self.send_document(chat_id, csv_bytes, filename=fname, caption=caption)
            elif cb_data == "admin_csv_cards" and chat_id:
                cb_user_id = cb.get("from", {}).get("id")
                if not self.is_admin_user(cb_user_id):
                    await self.send_message(chat_id, "⛔ <b>Sizda admin huquqlari mavjud emas.</b>")
                else:
                    from services.database import get_admin_cards
                    from services.csv_service import generate_cards_csv
                    from datetime import datetime
                    cards = get_admin_cards(limit=10000, offset=0)
                    csv_bytes = generate_cards_csv(cards)
                    fname = f"oqila_cards_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                    caption = (
                        f"📦 <b>Oqila AI — Mahsulot kartochkalari</b>\n\n"
                        f"✨ Jami: <b>{len(cards)}</b> ta kartochka\n"
                        f"📅 Sana: <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>\n\n"
                        f"<i>Microsoft Excel uchun to'liq moslashtirilgan (UTF-8 BOM, ';').</i>"
                    )
                    await self.send_document(chat_id, csv_bytes, filename=fname, caption=caption)
            return

        if "message" not in update:
            return

        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        user = msg.get("from", {})
        username = html.escape(user.get("username") or user.get("first_name", "Tadbirkor"))

        if not chat_id:
            return

        # 3. Direct Photo Message Handling (Item 7)
        if "photo" in msg:
            await self._handle_photo_message(msg, chat_id, app_url)
            return

        text = msg.get("text", "").strip()

        # 4. Command Handlers
        user_tg_id = user.get("id") or chat_id
        # Ensure user exists in database
        upsert_user(
            tg_id=user_tg_id,
            tg_username=user.get("username"),
            tg_first_name=user.get("first_name"),
        )
        user_lang = get_user_lang(user_tg_id, default="uz")
        user_agreed = get_user_terms_agreed(user_tg_id)

        if text.startswith("/lang"):
            await self.send_message(
                chat_id,
                LANG_SELECTION_TEXT,
                reply_markup=self._build_language_keyboard(),
            )
            return

        if text.startswith("/start"):
            log_event(
                event_type="telegram_start",
                lang=user_lang,
                is_mock=False,
                details={"user_id": user_tg_id, "username": username, "agreed": user_agreed},
            )

            # If user has not accepted terms yet, start onboarding by asking for language
            if not user_agreed:
                await self.send_message(
                    chat_id,
                    LANG_SELECTION_TEXT,
                    reply_markup=self._build_language_keyboard(),
                )
                return

            welcome_text = (
                WELCOME_TEXT_UZ.format(username=username)
                if user_lang == "uz"
                else WELCOME_TEXT_RU.format(username=username)
            )
            keyboard = self._build_main_keyboard(app_url, lang=user_lang)
            await self.send_message(chat_id, welcome_text, reply_markup=keyboard)

        elif text.startswith("/demo"):
            await self._handle_demo_command(chat_id, app_url, lang=user_lang)

        elif text.startswith("/tax") or text.startswith("/price"):
            await self._handle_tax_command(text, chat_id, app_url, lang=user_lang)

        elif text.startswith("/tips"):
            tip = random.choice(DAILY_TIPS_RU if user_lang == "ru" else DAILY_TIPS_UZ)
            again_btn = "🔄 Yana maslahat olish" if user_lang == "uz" else "🔄 Ещё совет"
            app_btn = "🚀 Mini App'ni ochish" if user_lang == "uz" else "🚀 Открыть Mini App"
            url_with_lang = f"{app_url}{'&' if '?' in app_url else '?'}lang={user_lang}"
            keyboard = {
                "inline_keyboard": [
                    [{"text": again_btn, "callback_data": "tips"}],
                    [{"text": app_btn, "web_app": {"url": url_with_lang}}] if app_url.startswith("https://") else []
                ]
            }
            # filter empty rows
            keyboard["inline_keyboard"] = [row for row in keyboard["inline_keyboard"] if row]
            await self.send_message(chat_id, tip, reply_markup=keyboard)

        elif text.startswith("/calendar"):
            await self.send_message(chat_id, TAX_CALENDAR_TEXT_RU if user_lang == "ru" else TAX_CALENDAR_TEXT_UZ)

        elif text.startswith("/uzum"):
            from services.database import get_uzum_shops, get_uzum_orders, get_uzum_finance_summary
            shops = get_uzum_shops()
            orders = get_uzum_orders(status="CREATED")
            fin = get_uzum_finance_summary()

            shops_str = ""
            for s in shops:
                pending_count = s.get('pending_orders_count', 0)
                if user_lang == "ru":
                    shops_str += f"• <b>{s['title']}</b> (Заказов в ожидании: {pending_count})\n"
                else:
                    shops_str += f"• <b>{s['title']}</b> (Kutilayotgan buyurtmalar: {pending_count})\n"
            if not shops_str:
                shops_str = (
                    "• <i>Магазины пока не подключены (введите API ключ Uzum в приложении Oqila).</i>\n"
                    if user_lang == "ru"
                    else "• <i>Hozircha do'konlar ulanmagan (Oqila ilovasida Uzum API kalitini kiriting).</i>\n"
                )

            if user_lang == "ru":
                uzum_status_text = (
                    "🛍️ <b>Uzum Market — Магазины и Заказы:</b>\n\n"
                    f"🏢 <b>Ваши магазины:</b>\n{shops_str}\n"
                    f"⏳ <b>Заказы, ожидающие подтверждения:</b> {len(orders)} шт\n"
                    f"💰 <b>Общая выручка:</b> {fin.get('gross_revenue', 0):,.0f} сум\n"
                    f"💳 <b>Ожидаемая чистая выплата:</b> {fin.get('net_payout', 0):,.0f} сум\n\n"
                    "👇 <i>Для подтверждения заказов откройте приложение:</i>"
                )
                open_btn_text = "🛍️ Открыть раздел Uzum"
            else:
                uzum_status_text = (
                    "🛍️ <b>Uzum Market — Do'konlar va Buyurtmalar:</b>\n\n"
                    f"🏢 <b>Do'konlaringiz:</b>\n{shops_str}\n"
                    f"⏳ <b>Tasdiqlash kutilayotgan buyurtmalar:</b> {len(orders)} ta\n"
                    f"💰 <b>Jami tushum (barcha do'konlar):</b> {fin.get('gross_revenue', 0):,.0f} so'm\n"
                    f"💳 <b>Kutilayotgan sof to'lov:</b> {fin.get('net_payout', 0):,.0f} so'm\n\n"
                    "👇 <i>Buyurtmalarni tasdiqlash va boshqarish uchun ilovani oching:</i>"
                )
                open_btn_text = "🛍️ Uzum bo'limini ochish"

            url_with_lang = f"{app_url}{'&' if '?' in app_url else '?'}tab=uzum&lang={user_lang}"
            keyboard = {
                "inline_keyboard": [
                    [{"text": open_btn_text, "web_app": {"url": url_with_lang}}] if app_url.startswith("https://") else []
                ]
            }
            keyboard["inline_keyboard"] = [row for row in keyboard["inline_keyboard"] if row]
            await self.send_message(chat_id, uzum_status_text, reply_markup=keyboard)

        elif text.startswith("/subscribe"):
            success = save_subscriber(chat_id, username=username, lang=user_lang)
            if success:
                if user_lang == "ru":
                    msg_sub = (
                        "🔔 <b>Поздравляем! Вы подписались на напоминания Oqila AI.</b>\n\n"
                        "Теперь вы будете получать напоминания о налогах до 15-го числа каждого месяца "
                        "и полезные советы по развитию вашего бизнеса!\n\n"
                        "<i>Для отмены подписки: /unsubscribe</i>"
                    )
                else:
                    msg_sub = (
                        "🔔 <b>Tabriklaymiz! Siz Oqila AI eslatmalariga obuna bo'ldingiz.</b>\n\n"
                        "Endi siz har oyning 15-sanasigacha soliq to'lovlari bo'yicha eslatmalar "
                        "hamda biznesingizni o'stiruvchi foydali tavsiyalarni olasiz!\n\n"
                        "<i>Obunani bekor qilish uchun: /unsubscribe</i>"
                    )
            else:
                msg_sub = (
                    "⚠️ Ошибка при оформлении подписки. Пожалуйста, попробуйте снова."
                    if user_lang == "ru"
                    else "⚠️ Obunani rasmiylashtirishda xatolik yuz berdi. Iltimos qayta urinib ko'ring."
                )
            await self.send_message(chat_id, msg_sub)

        elif text.startswith("/unsubscribe"):
            success = unsubscribe_subscriber(chat_id)
            if success:
                if user_lang == "ru":
                    msg_unsub = (
                        "🔕 <b>Подписка отменена.</b>\n\n"
                        "Вы больше не будете получать автоматические напоминания от бота. "
                        "Чтобы подписаться снова, отправьте /subscribe в любое время."
                    )
                else:
                    msg_unsub = (
                        "🔕 <b>Obunangiz bekor qilindi.</b>\n\n"
                        "Siz endi botdan avtomatik eslatmalarni olmaysiz. "
                        "Qayta obuna bo'lish uchun istalgan vaqtda /subscribe buyrug'ini yuborishingiz mumkin."
                    )
            else:
                msg_unsub = (
                    "ℹ️ Вы не были подписаны или подписка уже отменена."
                    if user_lang == "ru"
                    else "ℹ️ Siz avval obuna bo'lmagansiz yoki obuna allaqachon bekor qilingan."
                )
            await self.send_message(chat_id, msg_unsub)

        elif text.startswith("/admin"):
            user_id = user.get("id")
            await self._handle_admin_command(chat_id, app_url, text, user_id=user_id)

        elif text.startswith("/help"):
            if user_lang == "ru":
                help_text = (
                    "ℹ️ <b>Справка по боту Oqila AI</b>\n\n"
                    "• 📸 <b>Отправка фото:</b> Отправьте фото изделия в этот чат — ИИ проанализирует его и составит описание с ценой.\n"
                    "• 💰 <b>/tax 350000 120000:</b> Первое число — цена продажи, второе — себестоимость (расчёт налога и чистой прибыли).\n"
                    "• 🛍️ <b>/uzum:</b> Управление магазинами, заказами и печать этикеток.\n"
                    "• 📸 <b>/demo:</b> Посмотреть пример готовой карточки товара.\n"
                    "• 💡 <b>/tips:</b> Практические советы по продажам и маркетингу.\n"
                    "• 📅 <b>/calendar:</b> Налоговый календарь Узбекистана 2026.\n"
                    "• 🌐 <b>/lang:</b> Смена языка бота (O'zbekcha / Русский).\n"
                    "• 🔔 <b>/subscribe:</b> Подписка на налоговые напоминания.\n\n"
                    "Для полноценной работы нажмите кнопку <b>«Открыть приложение Oqila AI»</b>."
                )
            else:
                help_text = (
                    "ℹ️ <b>Oqila AI Bot Qo'llanmasi</b>\n\n"
                    "• 📸 <b>Rasm yuborish:</b> Mahsulot rasmini chatga yuboring — AI uni tahlil qilib, tavsif va narx chiqaradi.\n"
                    "• 💰 <b>/tax 350000 120000:</b> Birinchi son sotish narxi, ikkinchi son tannarxi — soliq va Uzum sof foydasi.\n"
                    "• 🛍️ <b>/uzum:</b> Uzum Market do'konlari, buyurtmalar va etiketkalarni chop etish.\n"
                    "• 📸 <b>/demo:</b> Tayyor mahsulot qadoqlash namunasini ko'rish.\n"
                    "• 💡 <b>/tips:</b> Kunlik marketing va savdo maslahatlari.\n"
                    "• 📅 <b>/calendar:</b> O'zR soliq to'lovlari taqvimi.\n"
                    "• 🌐 <b>/lang:</b> Bot tilini o'zgartirish (O'zbekcha / Русский).\n"
                    "• 🔔 <b>/subscribe:</b> Soliq eslatmalariga obuna bo'lish.\n\n"
                    "Ilovadan to'liq foydalanish uchun <b>«Oqila AI ilovasini ochish»</b> tugmasini bosing."
                )
            await self.send_message(chat_id, help_text)

        else:
            # Handle user question with AI Legal & Business guidance
            from services.ai_service import ai_service
            answer = await ai_service.legal_qa(text, lang=user_lang)
            consultant_title = "🤖 <b>OqilaLegal maslahatchisi:</b>" if user_lang == "uz" else "🤖 <b>Консультант OqilaLegal:</b>"
            footer_note = (
                "<i>To'liq studiya va kalkulyatordan foydalanish uchun Mini App'ni oching.</i>"
                if user_lang == "uz"
                else "<i>Откройте Mini App для доступа к фотостудии и калькулятору.</i>"
            )
            reply = f"{consultant_title}\n\n{answer}\n\n{footer_note}"
            keyboard = None
            if app_url.startswith("https://"):
                url_with_lang = f"{app_url}{'&' if '?' in app_url else '?'}lang={user_lang}"
                btn_label = "🚀 Mini App'ni ochish" if user_lang == "uz" else "🚀 Открыть Mini App"
                keyboard = {
                    "inline_keyboard": [
                        [{"text": btn_label, "web_app": {"url": url_with_lang}}]
                    ]
                }
            await self.send_message(chat_id, reply, reply_markup=keyboard)

    # -----------------------------------------------------------------------
    # Helper Handlers
    # -----------------------------------------------------------------------
    def _build_main_keyboard(self, app_url: str, lang: str = "uz") -> Dict[str, Any]:
        sep = "&" if "?" in app_url else "?"
        url_with_lang = f"{app_url}{sep}lang={lang}"
        open_app_text = "🚀 Oqila AI ilovasini ochish" if lang == "uz" else "🚀 Открыть приложение Oqila AI"
        demo_text = "📸 Namuna (/demo)" if lang == "uz" else "📸 Пример (/demo)"
        help_text = "💬 Qo'llanma" if lang == "uz" else "💬 Справка"
        change_lang_text = "🌐 Tilni o'zgartirish" if lang == "uz" else "🌐 Сменить язык"

        if app_url.startswith("https://"):
            return {
                "inline_keyboard": [
                    [
                        {
                            "text": open_app_text,
                            "web_app": {"url": url_with_lang},
                        }
                    ],
                    [
                        {"text": demo_text, "callback_data": "demo"},
                        {"text": help_text, "callback_data": "help"},
                    ],
                    [
                        {"text": change_lang_text, "callback_data": "cmd_change_lang"},
                    ],
                ]
            }
        return {
            "inline_keyboard": [
                [
                    {
                        "text": ("🌐 Veb-versiyani ochish (Brauzer)" if lang == "uz" else "🌐 Открыть веб-версию (Браузер)"),
                        "url": url_with_lang if app_url.startswith("http") else f"http://localhost:8000?lang={lang}",
                    }
                ],
                [
                    {"text": change_lang_text, "callback_data": "cmd_change_lang"},
                ]
            ]
        }

    def _build_language_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "🇺🇿 O'zbekcha", "callback_data": "set_lang_uz"},
                    {"text": "🇷🇺 Русский", "callback_data": "set_lang_ru"},
                ]
            ]
        }

    def _build_terms_keyboard(self, lang: str = "uz") -> Dict[str, Any]:
        if lang == "uz":
            return {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Roziman va qabul qilaman",
                            "callback_data": "accept_terms_uz",
                        }
                    ],
                    [
                        {
                            "text": "🇷🇺 Русский язык",
                            "callback_data": "set_lang_ru",
                        }
                    ],
                ]
            }
        else:
            return {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Принимаю условия соглашения",
                            "callback_data": "accept_terms_ru",
                        }
                    ],
                    [
                        {
                            "text": "🇺🇿 O'zbek tili",
                            "callback_data": "set_lang_uz",
                        }
                    ],
                ]
            }

    async def _handle_tax_command(self, text: str, chat_id: int, app_url: str, lang: str = "uz") -> None:
        """Parse numbers from /tax 380000 120000 and calculate profit."""
        numbers = [float(n) for n in re.findall(r"\d+", text.replace(" ", ""))]
        sale_price = 380000.0
        cost_price = 120000.0
        if len(numbers) >= 2:
            sale_price = max(numbers[0], numbers[1])
            cost_price = min(numbers[0], numbers[1])
        elif len(numbers) == 1:
            sale_price = numbers[0]
            cost_price = round(sale_price * 0.4)

        res = calculate(
            sale_price=sale_price,
            cost_price=cost_price,
            lang=lang,
            category="craft",
            business_type="resale",
            trade_regime="ecommerce",
        )

        url_with_lang = f"{app_url}{'&' if '?' in app_url else '?'}lang={lang}"

        if lang == "ru":
            resp = (
                f"📊 <b>Oqila AI — Быстрый финансовый и налоговый расчёт:</b>\n\n"
                f"💰 <b>Цена продажи:</b> {res.sale_price:,.0f} сум\n"
                f"📦 <b>Себестоимость:</b> {res.cost_price:,.0f} сум\n"
                f"📈 <b>Валовая прибыль:</b> {res.gross_profit:,.0f} сум ({res.margin_pct}%)\n"
                f"─────────────────────\n"
                f"🛍️ <b>При продаже на Uzum Market:</b>\n"
                f"• Комиссия маркетплейса: {res.uzum_commission_amount:,.0f} сум\n"
                f"• Логистический сбор: {res.uzum_logistics_fee:,.0f} сум\n"
                f"• <b>Чистая прибыль:</b> <b>{res.uzum_net:,.0f} сум</b>\n"
                f"• Минимальная безубыточная цена: {res.min_price_uzum:,.0f} сум\n"
                f"─────────────────────\n"
                f"🏛️ <b>Налог государству (1%):</b> {res.tax_payable_item:,.0f} сум\n"
                f"📌 <b>Ежемесячный соцналог ЯТТ:</b> {res.social_tax_monthly:,.0f} сум (1 БРВ)\n\n"
                f"<i>💡 Для расчёта своих цен отправьте: <code>/tax 450000 180000</code></i>"
            )
            calc_btn = "📊 Открыть полный калькулятор"
        else:
            resp = (
                f"📊 <b>Oqila AI — Tezkor Moliya va Soliq hisobi:</b>\n\n"
                f"💰 <b>Sotish narxi:</b> {res.sale_price:,.0f} so'm\n"
                f"📦 <b>Tannarx:</b> {res.cost_price:,.0f} so'm\n"
                f"📈 <b>Yalpi foyda:</b> {res.gross_profit:,.0f} so'm ({res.margin_pct}%)\n"
                f"─────────────────────\n"
                f"🛍️ <b>Uzum Market'da sotganda:</b>\n"
                f"• Marketpleys komissiyasi: {res.uzum_commission_amount:,.0f} so'm\n"
                f"• Logistika to'lovi: {res.uzum_logistics_fee:,.0f} so'm\n"
                f"• <b>Sof foyda:</b> <b>{res.uzum_net:,.0f} so'm</b>\n"
                f"• Zararsiz minimal narx: {res.min_price_uzum:,.0f} so'm\n"
                f"─────────────────────\n"
                f"🏛️ <b>Davlatga soliq (1%):</b> {res.tax_payable_item:,.0f} so'm\n"
                f"📌 <b>YaTT oylik ijtimoiy solig'i:</b> {res.social_tax_monthly:,.0f} so'm (1 BHM)\n\n"
                f"<i>💡 O'z narxlaringizni kiritish uchun: <code>/tax 450000 180000</code></i>"
            )
            calc_btn = "📊 To'liq kalkulyatorni ochish"

        keyboard = None
        if app_url.startswith("https://"):
            keyboard = {
                "inline_keyboard": [
                    [{"text": calc_btn, "web_app": {"url": url_with_lang}}]
                ]
            }
        await self.send_message(chat_id, resp, reply_markup=keyboard)

    async def _handle_demo_command(self, chat_id: int, app_url: str, lang: str = "uz") -> None:
        """Send a rich demo product packaging card."""
        url_with_lang = f"{app_url}{'&' if '?' in app_url else '?'}lang={lang}"
        if lang == "ru":
            caption = (
                "✨ <b>Пример: «Хан-атласная безрукавка с золотой вышивкой»</b>\n\n"
                "🧵 <b>Описание:</b> Натуральный шёлковый хан-атлас ручного плетения мастеров Ферганской долины "
                "в сочетании с традиционной золотой вышивкой. В каждом стежке отражены национальные традиции и тонкий вкус.\n\n"
                "💰 <b>Рекомендованная цена:</b> 420 000 сум\n"
                "📈 <b>Чистая прибыль (Uzum):</b> 235 000 сум\n"
                "🏷️ <b>Хештеги:</b> #ханатлас #национальнаяодежда #handmade #uzumbest #oqila\n\n"
                "<i>📸 Чтобы упаковать свой товар, отправьте его фото в этот чат или откройте приложение!</i>"
            )
            btn_text = "🚀 Упаковать свой товар"
        else:
            caption = (
                "✨ <b>Namuna: «Zarhal kashtali xon-atlas nimcha»</b>\n\n"
                "🧵 <b>Tavsif:</b> Farg'ona vodiysi ustalari tomonidan qo'lda to'qilgan tabiiy ipak xon-atlas va "
                "an'anaviy zarhal kashtalar uyg'unligi. Har bir chokda milliy meros va nozik did aks etgan.\n\n"
                "💰 <b>Tavsiya etilgan narx:</b> 420 000 so'm\n"
                "📈 <b>Sof foyda (Uzum):</b> 235 000 so'm\n"
                "🏷️ <b>Xeshteglar:</b> #xonatlas #milliykiyim #handmade #uzumbest #oqila\n\n"
                "<i>📸 O'z mahsulotingizni qadoqlash uchun rasmini shu chatga yuboring yoki ilovani oching!</i>"
            )
            btn_text = "🚀 O'z mahsulotingizni qadoqlash"

        demo_image = "https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=800&auto=format&fit=crop&q=80"
        keyboard = None
        if app_url.startswith("https://"):
            keyboard = {
                "inline_keyboard": [
                    [{"text": btn_text, "web_app": {"url": url_with_lang}}]
                ]
            }
        sent = await self.send_photo(chat_id, demo_image, caption=caption, reply_markup=keyboard)
        if not sent:
            await self.send_message(chat_id, caption, reply_markup=keyboard)

    async def _handle_photo_message(self, msg: Dict[str, Any], chat_id: int, app_url: str) -> None:
        """Handle product photo sent by user in Telegram chat (Item 7)."""
        photos = msg.get("photo", [])
        if not photos:
            return

        # Pick highest resolution photo
        best_photo = photos[-1]
        file_id = best_photo.get("file_id")
        user_lang = get_user_lang(chat_id, "uz")

        wait_msg = (
            "🔍 <b>Фотография товара получена!</b>\n\n"
            "Искусственный интеллект анализирует текстуру ткани, цвета и формирует описание... ⏳"
            if user_lang == "ru"
            else "🔍 <b>Mahsulot rasmi qabul qilindi!</b>\n\n"
            "Sun'iy intellekt mato fakturasi, ranglar va tavsiya etilgan narxni tahlil qilmoqda... ⏳"
        )
        await self.send_message(chat_id, wait_msg)

        file_bytes = await self.download_telegram_file(file_id)
        if not file_bytes:
            err_msg = (
                "⚠️ Не удалось загрузить фото. Пожалуйста, отправьте ещё раз."
                if user_lang == "ru"
                else "⚠️ Rasmni yuklab olishda xatolik yuz berdi. Iltimos qayta yuboring."
            )
            await self.send_message(chat_id, err_msg)
            return

        from services.ai_service import ai_service
        try:
            caption_text = msg.get("caption", "")
            default_note = "Ремесленное или национальное изделие" if user_lang == "ru" else "Hunarmandchilik yoki milliy mahsulot"
            card = await ai_service.generate_product_card(
                image_bytes=file_bytes,
                image_mime="image/jpeg",
                note=caption_text or default_note,
                lang=user_lang,
                photoshoot_style="minimal_studio",
                content_tone="sales",
                content_format="instagram",
                generate_photo=False,
            )

            title = html.escape(str(card.get("title", "")))
            desc = html.escape(str(card.get("description", "")))
            price = html.escape(str(card.get("price_tag", "")))
            tip = html.escape(str(card.get("marketing_tip", "")))
            tags = " ".join(html.escape(str(t)) for t in card.get("hashtags", []))

            if user_lang == "ru":
                reply = (
                    f"🎉 <b>Готовый маркетинговый пост для вашего товара:</b>\n\n"
                    f"🏷️ <b>{title}</b>\n\n"
                    f"{desc}\n\n"
                    f"💰 <b>Цена:</b> {price}\n\n"
                    f"📌 {tags}\n\n"
                    f"💡 <b>Совет по продажам:</b>\n{tip}"
                )
                photo_btn = "✨ Сделать AI-фотосессию (Mini App)"
            else:
                reply = (
                    f"🎉 <b>Mahsulotingiz uchun tayyor marketing posti:</b>\n\n"
                    f"🏷️ <b>{title}</b>\n\n"
                    f"{desc}\n\n"
                    f"💰 <b>Narxi:</b> {price}\n\n"
                    f"📌 {tags}\n\n"
                    f"💡 <b>Savdo strategiyasi:</b>\n{tip}"
                )
                photo_btn = "✨ AI Fotosessiya qilish (Mini App)"

            keyboard = None
            if app_url.startswith("https://"):
                url_with_lang = f"{app_url}{'&' if '?' in app_url else '?'}lang={user_lang}"
                keyboard = {
                    "inline_keyboard": [
                        [{"text": photo_btn, "web_app": {"url": url_with_lang}}]
                    ]
                }
            await self.send_message(chat_id, reply, reply_markup=keyboard)

        except Exception as exc:
            logger.error("Error generating card from telegram photo: %s", exc)
            fallback_err = (
                "⚠️ Произошла ошибка при анализе изделия. Попробуйте через Mini App:"
                if user_lang == "ru"
                else "⚠️ Mahsulotni tahlil qilishda xatolik yuz berdi. Mini App orqali urinib ko'ring:"
            )
            await self.send_message(
                chat_id,
                fallback_err,
                reply_markup=self._build_main_keyboard(app_url, lang=user_lang),
            )

    async def _handle_inline_query(self, iq: Dict[str, Any], app_url: str) -> None:
        """Handle inline query @bot 350000 120000 (Item 4)."""
        iq_id = iq.get("id")
        query = iq.get("query", "").strip()
        if not iq_id:
            return

        numbers = [float(n) for n in re.findall(r"\d+", query.replace(" ", ""))]
        if len(numbers) >= 2:
            sale = max(numbers[0], numbers[1])
            cost = min(numbers[0], numbers[1])
        elif len(numbers) == 1:
            sale = numbers[0]
            cost = round(sale * 0.4)
        else:
            sale = 350000.0
            cost = 120000.0

        res = calculate(
            sale_price=sale,
            cost_price=cost,
            lang="uz",
            category="craft",
            business_type="resale",
            trade_regime="ecommerce",
        )

        msg_text = (
            f"📊 <b>Oqila AI — Foyda va Soliq hisobi:</b>\n\n"
            f"💰 <b>Sotish narxi:</b> {res.sale_price:,.0f} so'm\n"
            f"📦 <b>Tannarx:</b> {res.cost_price:,.0f} so'm\n"
            f"🛍️ <b>Uzum Market sof foyda:</b> <b>{res.uzum_net:,.0f} so'm</b>\n"
            f"🏛️ <b>Davlatga soliq (1%):</b> {res.tax_payable_item:,.0f} so'm\n"
            f"📈 <b>Marja:</b> {res.margin_pct}%\n\n"
            f"<i>🌿 Oqila AI yordamida hisoblandi</i>"
        )

        results = [
            {
                "type": "article",
                "id": "calc_uzum",
                "title": f"💰 Sof foyda: {res.uzum_net:,.0f} so'm (Uzum)",
                "description": f"Sotish: {sale:,.0f} | Tannarx: {cost:,.0f} | Soliq: {res.tax_payable_item:,.0f}",
                "input_message_content": {
                    "message_text": msg_text,
                    "parse_mode": "HTML",
                },
            },
            {
                "type": "article",
                "id": "tips_share",
                "title": "💡 Tadbirkor ayollar uchun maslahat",
                "description": "Uzum va Instagram'da savdoni oshirish bo'yicha maslahatni ulashish",
                "input_message_content": {
                    "message_text": f"💡 <b>Oqila AI maslahati:</b>\n\n{random.choice(DAILY_TIPS_UZ)}\n\n<i>🌿 Oqila AI — Ayol tadbirkorlar assistenti</i>",
                    "parse_mode": "HTML",
                },
            },
        ]
        await self.answer_inline_query(iq_id, results)

    async def _handle_admin_command(
        self,
        chat_id: int,
        app_url: str,
        text: str,
        user_id: Optional[int] = None,
        is_refresh: bool = False,
        message_id: Optional[int] = None,
    ) -> None:
        """Handle /admin command, authenticate admin, show stats and action buttons."""
        parts = text.strip().split(maxsplit=1)
        provided_key = parts[1].strip() if len(parts) > 1 else None

        effective_uid = user_id or chat_id
        if not self.is_admin_user(effective_uid, provided_key=provided_key):
            denied_msg = (
                "⛔ <b>Kirish taqiqlangan!</b>\n\n"
                "Sizda admin huquqlari mavjud emas.\n\n"
                "Agar sizda maxfiy administrator kaliti bo'lsa, quyidagicha yuboring:\n"
                "<code>/admin MAXFIY_KALIT</code>"
            )
            await self.send_message(chat_id, denied_msg)
            return

        from services.database import get_admin_dashboard_metrics, get_uzum_shops
        metrics = get_admin_dashboard_metrics()
        shops = get_uzum_shops()
        secret_key = os.getenv("ADMIN_SECRET_KEY", "oqila_admin_2026").strip()

        total_users = metrics.get("total_users", 0)
        active_today = metrics.get("active_today", 0)
        new_this_week = metrics.get("new_this_week", 0)
        total_cards = metrics.get("total_cards", 0)
        total_subscribers = metrics.get("total_subscribers", 0)
        total_events = metrics.get("total_events", 0)

        # Build WebApp & Browser URLs with embedded secret key for instant 1-click access
        base_clean = app_url.rstrip("/")
        admin_webapp_url = f"{base_clean}/admin?key={secret_key}"

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        admin_text = (
            f"🛡️ <b>Oqila AI — Admin Boshqaruv Paneli</b>\n\n"
            f"📊 <b>Jonli ko'rsatkichlar ({now_str}):</b>\n"
            f"• 👥 <b>Foydalanuvchilar:</b> <b>{total_users:,}</b> ta (Bugun faol: <b>{active_today:,}</b> | Haftada yangi: <b>{new_this_week:,}</b>)\n"
            f"• 📦 <b>AI Kartochkalar:</b> <b>{total_cards:,}</b> ta\n"
            f"• 🔔 <b>Bot obunachilari:</b> <b>{total_subscribers:,}</b> ta\n"
            f"• 🛍️ <b>Uzum do'konlari:</b> <b>{len(shops)}</b> ta\n"
            f"• ⚡ <b>Tizim hodisalari:</b> <b>{total_events:,}</b> ta\n\n"
            f"<i>Quyidagi tugmalar orqali WebApp boshqaruv panelini ochishingiz yoki Excel/CSV hisobotlarni to'g'ridan-to'g'ri Telegram chatga yuklab olishingiz mumkin:</i>"
        )

        buttons = []
        if admin_webapp_url.startswith("https://"):
            buttons.append([
                {
                    "text": "🖥️ Admin Panelni ochish (WebApp)",
                    "web_app": {"url": admin_webapp_url},
                }
            ])
        else:
            buttons.append([
                {
                    "text": "🌐 Brauzerda ochish (Admin Panel)",
                    "url": admin_webapp_url,
                }
            ])

        buttons.append([
            {"text": "📥 Foydalanuvchilar (CSV/Excel)", "callback_data": "admin_csv_users"},
            {"text": "📦 Mahsulotlar (CSV/Excel)", "callback_data": "admin_csv_cards"},
        ])
        buttons.append([
            {"text": "🔄 Yangilash", "callback_data": "admin_refresh"},
        ])

        keyboard = {"inline_keyboard": buttons}

        if is_refresh and message_id:
            ok = await self.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=admin_text,
                reply_markup=keyboard,
            )
            if not ok:
                await self.send_message(chat_id, admin_text, reply_markup=keyboard)
        else:
            await self.send_message(chat_id, admin_text, reply_markup=keyboard)


telegram_service = TelegramService()

