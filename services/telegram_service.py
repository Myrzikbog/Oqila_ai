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

import io
import json
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional

import httpx
from services.database import log_event, save_subscriber
from services.legal_calc import calculate

logger = logging.getLogger("oqila_telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"

DAILY_TIPS_UZ = [
    "💡 <b>Savdo maslahati:</b> Uzum Market'da sotayotganda, mahsulot tannarxiga kamida 25-30% ustama qo'ying. Bu marketpleysning 12% komissiyasi va 15 000 so'm logistika to'lovini qoplaydi hamda sizga sof foyda qoldiradi.",
    "🧵 <b>Hunarmand qizlar uchun:</b> PQ-4742 qaroriga ko'ra, o'z qo'lingiz bilan yasagan milliy buyumlarni sotsangiz, daromad solig'i 0%! Faqat pensiya staji uchun yiliga 1 marta ixtiyoriy 1 BHM (440 000 so'm) to'lash kifoya.",
    "📸 <b>Vizual marketing:</b> Instagram va Telegram kanalda mahsulotni faqat oq fonda emas, balki 'hayotiy' muhitda (masalan, kiyimni qizlar kiygan holda, dasturxonni bezatilgan holda) ko'rsatish sotuvni 40% ga oshiradi.",
    "📦 <b>Qayta sotish (Xitoy/bozor):</b> E'tibor bering! Xitoydan yoki ulgurji bozordan olib qayta sotishda o'z-o'zini band qilish QONUN BO'YICHA TAQIQLANGAN. Jarimaga tushmaslik uchun YaTT (1% yoki 2% soliq) ochish shart.",
    "💳 <b>To'lov tizimlari:</b> Telegram bot yoki Instagram do'konda Click va Payme ulash — xaridor ishonchini 2 barobar oshiradi. Click/Payme ekvayring komissiyasi odatda 1.5% ni tashkil qiladi.",
    "🏷️ <b>Xaridorni jalb qilish:</b> Narxni 199 000 so'm yoki 249 000 so'm qilib belgilash (psixologik narxlash) yaxlit 200 000 yoki 250 000 so'mdan ko'ra 15% ko'proq buyurtma olib keladi.",
]

TAX_CALENDAR_TEXT_UZ = (
    "📅 <b>O'zbekiston 2026 — Kichik biznes va YaTT Soliq Taqvimi:</b>\n\n"
    "📌 <b>Har oyning 15-sanasigacha:</b>\n"
    "• YaTT uchun majburiy ijtimoiy soliq — 1 BHM (440 000 so'm). Soliq mobil ilovasi orqali to'lanadi.\n\n"
    "📌 <b>Chorak yakuni bo'yicha (har 3 oyda):</b>\n"
    "• Aylanmadan olinadigan soliq (1% ishlab chiqarish/savdo, 2% Uzum e-tijorat, 4% xizmatlar) — chorakdan keyingi oyning 15-sanasigacha.\n\n"
    "📌 <b>O'z-o'zini band qilganlar:</b>\n"
    "• Daromad solig'i — 0% (yiliga 100 mln so'mgacha).\n"
    "• Pensiya staji uchun ijtimoiy soliq — yil davomida ixtiyoriy 1 BHM.\n\n"
    "⚠️ <b>Yillik aylanma 1 mlrd so'mdan oshsa:</b>\n"
    "QQS (12%) to'lovchisi sifatida ro'yxatdan o'tish majburiyati vujudga keladi."
)


class TelegramService:
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
            {"command": "demo", "description": "📸 Namuna mahsulot qadoqlash"},
            {"command": "tax", "description": "💰 Soliq & marja hisobi (masalan: /tax 350000 120000)"},
            {"command": "price", "description": "🏷️ Narx va sof foyda hisobi"},
            {"command": "tips", "description": "💡 Kunlik biznes maslahati"},
            {"command": "calendar", "description": "📅 Soliq va hisobot taqvimi"},
            {"command": "subscribe", "description": "🔔 Soliq eslatmalariga obuna"},
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

    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Configure Telegram webhook."""
        if not self.is_configured:
            return {"ok": False, "description": "TELEGRAM_BOT_TOKEN not configured"}

        url = f"{webhook_url.rstrip('/')}/api/telegram-webhook"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._api_url("setWebhook"), json={"url": url})
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
            if cb_id:
                await self.answer_callback_query(cb_id)
            if cb_data == "help" and chat_id:
                help_text = (
                    "ℹ️ <b>Oqila AI Bot Qo'llanmasi</b>\n\n"
                    "• 🚀 <b>Mini App:</b> Pastdagi tugmani bosib to'liq AI Studiya va kalkulyatorni oching.\n"
                    "• 📸 <b>Rasm yuboring:</b> Mahsulot rasmini shu chatga yuborsangiz, AI uni tahlil qilib sotiq matnini tayyorlaydi.\n"
                    "• 💰 <b>/tax 380000 120000:</b> Tezkor soliq va Uzum sof foydasi hisobi.\n"
                    "• 💡 <b>/tips:</b> Ayol tadbirkorlar uchun foydali maslahat.\n"
                    "• 📅 <b>/calendar:</b> O'zR soliq muddatlari va hisobotlar."
                )
                await self.send_message(chat_id, help_text)
            elif cb_data == "tips" and chat_id:
                tip = random.choice(DAILY_TIPS_UZ)
                await self.send_message(chat_id, tip)
            return

        if "message" not in update:
            return

        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        user = msg.get("from", {})
        username = user.get("username") or user.get("first_name", "Tadbirkor")

        if not chat_id:
            return

        # 3. Direct Photo Message Handling (Item 7)
        if "photo" in msg:
            await self._handle_photo_message(msg, chat_id, app_url)
            return

        text = msg.get("text", "").strip()

        # 4. Command Handlers
        if text.startswith("/start"):
            log_event(
                event_type="telegram_start",
                lang="uz",
                is_mock=False,
                details={"user_id": user.get("id"), "username": username},
            )
            welcome_text = (
                f"👋 <b>Assalomu alaykum, {username}!</b>\n\n"
                "🌿 <b>«Oqila AI»</b> — O'zbekiston tadbirkor ayollari va hunarmandlari uchun "
                "sun'iy intellektga asoslangan raqamli biznes-assistent!\n\n"
                "✨ <b>Nimalar qila olaman:</b>\n"
                "• 📸 <b>Mahsulot qadoqlash:</b> Menga mahsulot rasmini yuboring — AI studiya fotosi va tayyor marketing postini yaratadi!\n"
                "• 💰 <b>Foyda va soliq hisobi:</b> /tax 380000 120000 buyrug'i orqali sof foydani hisoblang.\n"
                "• 💡 <b>/tips:</b> Biznesni rivojlantirish bo'yicha kunlik tavsiyalar.\n"
                "• 📅 <b>/calendar:</b> O'zR soliq va hisobot muddatlari.\n"
                "• 🤖 <b>OqilaLegal:</b> Huquq va soliq bo'yicha har qanday savolingizga javob beraman.\n\n"
                "👇 <b>To'liq interaktiv ilovani ochish:</b>"
            )
            keyboard = self._build_main_keyboard(app_url)
            await self.send_message(chat_id, welcome_text, reply_markup=keyboard)

        elif text.startswith("/demo"):
            await self._handle_demo_command(chat_id, app_url)

        elif text.startswith("/tax") or text.startswith("/price"):
            await self._handle_tax_command(text, chat_id, app_url)

        elif text.startswith("/tips"):
            tip = random.choice(DAILY_TIPS_UZ)
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Yana maslahat olish", "callback_data": "tips"}],
                    [{"text": "🚀 Mini App'ni ochish", "web_app": {"url": app_url}}] if app_url.startswith("https://") else []
                ]
            }
            # filter empty rows
            keyboard["inline_keyboard"] = [row for row in keyboard["inline_keyboard"] if row]
            await self.send_message(chat_id, tip, reply_markup=keyboard)

        elif text.startswith("/calendar"):
            await self.send_message(chat_id, TAX_CALENDAR_TEXT_UZ)

        elif text.startswith("/subscribe"):
            success = save_subscriber(chat_id, username=username, lang="uz")
            if success:
                msg_sub = (
                    "🔔 <b>Tabriklaymiz! Siz Oqila AI eslatmalariga obuna bo'ldingiz.</b>\n\n"
                    "Endi siz har oyning 15-sanasigacha soliq to'lovlari bo'yicha eslatmalar "
                    "hamda biznesingizni o'stiruvchi foydali tavsiyalarni olasiz!"
                )
            else:
                msg_sub = "⚠️ Obunani rasmiylashtirishda xatolik yuz berdi. Iltimos qayta urinib ko'ring."
            await self.send_message(chat_id, msg_sub)

        elif text.startswith("/help"):
            help_text = (
                "ℹ️ <b>Oqila AI Bot Qo'llanmasi</b>\n\n"
                "• 📸 <b>Rasm yuborish:</b> Mahsulot rasmini chatga yuboring — AI uni tahlil qilib, tavsif va narx chiqaradi.\n"
                "• 💰 <b>/tax 350000 120000:</b> Birinchi son sotish narxi, ikkinchi son tannarxi — soliq va Uzum sof foydasi.\n"
                "• 📸 <b>/demo:</b> Tayyor mahsulot qadoqlash namunasini ko'rish.\n"
                "• 💡 <b>/tips:</b> Kunlik marketing va savdo maslahatlari.\n"
                "• 📅 <b>/calendar:</b> O'zR soliq to'lovlari taqvimi.\n"
                "• 🔔 <b>/subscribe:</b> Soliq eslatmalariga obuna bo'lish.\n\n"
                "Ilovadan to'liq foydalanish uchun <b>«Oqila AI ilovasini ochish»</b> tugmasini bosing."
            )
            await self.send_message(chat_id, help_text)

        else:
            # Handle user question with AI Legal & Business guidance
            from services.ai_service import ai_service
            answer = await ai_service.legal_qa(text, lang="uz")
            reply = f"🤖 <b>OqilaLegal maslahatchisi:</b>\n\n{answer}\n\n<i>To'liq studiya va kalkulyatordan foydalanish uchun Mini App'ni oching.</i>"
            keyboard = None
            if app_url.startswith("https://"):
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🚀 Mini App'ni ochish", "web_app": {"url": app_url}}]
                    ]
                }
            await self.send_message(chat_id, reply, reply_markup=keyboard)

    # -----------------------------------------------------------------------
    # Helper Handlers
    # -----------------------------------------------------------------------
    def _build_main_keyboard(self, app_url: str) -> Dict[str, Any]:
        if app_url.startswith("https://"):
            return {
                "inline_keyboard": [
                    [
                        {
                            "text": "🚀 Oqila AI ilovasini ochish",
                            "web_app": {"url": app_url},
                        }
                    ],
                    [
                        {"text": "📸 Namuna (/demo)", "callback_data": "demo"},
                        {"text": "💬 Qo'llanma", "callback_data": "help"},
                    ],
                ]
            }
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "🌐 Veb-versiyani ochish (Brauzer)",
                        "url": app_url if app_url.startswith("http") else "http://localhost:8000",
                    }
                ]
            ]
        }

    async def _handle_tax_command(self, text: str, chat_id: int, app_url: str) -> None:
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
            lang="uz",
            category="craft",
            business_type="resale",
            trade_regime="ecommerce",
        )

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
            f"🏛️ <b>Davlatga soliq (YaTT e-tijorat 2%):</b> {res.tax_payable_item:,.0f} so'm\n"
            f"📌 <b>YaTT oylik ijtimoiy solig'i:</b> {res.social_tax_monthly:,.0f} so'm (1 BHM)\n\n"
            f"<i>💡 O'z narxlaringizni kiritish uchun: <code>/tax 450000 180000</code></i>"
        )
        keyboard = None
        if app_url.startswith("https://"):
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📊 To'liq kalkulyatorni ochish", "web_app": {"url": app_url}}]
                ]
            }
        await self.send_message(chat_id, resp, reply_markup=keyboard)

    async def _handle_demo_command(self, chat_id: int, app_url: str) -> None:
        """Send a rich demo product packaging card."""
        caption = (
            "✨ <b>Namuna: «Zarhal kashtali xon-atlas nimcha»</b>\n\n"
            "🧵 <b>Tavsif:</b> Farg'ona vodiysi ustalari tomonidan qo'lda to'qilgan tabiiy ipak xon-atlas va "
            "an'anaviy zarhal kashtalar uyg'unligi. Har bir chokda milliy meros va nozik did aks etgan.\n\n"
            "💰 <b>Tavsiya etilgan narx:</b> 420 000 so'm\n"
            "📈 <b>Sof foyda (Uzum):</b> 235 000 so'm\n"
            "🏷️ <b>Xeshteglar:</b> #xonatlas #milliykiyim #handmade #uzumbest #oqila\n\n"
            "<i>📸 O'z mahsulotingizni qadoqlash uchun rasmini shu chatga yuboring yoki ilovani oching!</i>"
        )
        demo_image = "https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=800&auto=format&fit=crop&q=80"
        keyboard = None
        if app_url.startswith("https://"):
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🚀 O'z mahsulotingizni qadoqlash", "web_app": {"url": app_url}}]
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

        await self.send_message(
            chat_id,
            "🔍 <b>Mahsulot rasmi qabul qilindi!</b>\n\n"
            "Sun'iy intellekt mato fakturasi, ranglar va tavsiya etilgan narxni tahlil qilmoqda... ⏳",
        )

        file_bytes = await self.download_telegram_file(file_id)
        if not file_bytes:
            await self.send_message(chat_id, "⚠️ Rasmni yuklab olishda xatolik yuz berdi. Iltimos qayta yuboring.")
            return

        from services.ai_service import ai_service
        try:
            caption_text = msg.get("caption", "")
            card = await ai_service.generate_product_card(
                image_bytes=file_bytes,
                image_mime="image/jpeg",
                note=caption_text or "Hunarmandchilik yoki milliy mahsulot",
                lang="uz",
                photoshoot_style="minimal_studio",
                content_tone="sales",
                content_format="instagram",
                generate_photo=False,
            )

            tags = " ".join(card.get("hashtags", []))
            reply = (
                f"🎉 <b>Mahsulotingiz uchun tayyor marketing posti:</b>\n\n"
                f"🏷️ <b>{card.get('title')}</b>\n\n"
                f"{card.get('description')}\n\n"
                f"💰 <b>Narxi:</b> {card.get('price_tag')}\n\n"
                f"📌 {tags}\n\n"
                f"💡 <b>Savdo strategiyasi:</b>\n{card.get('marketing_tip')}"
            )
            keyboard = None
            if app_url.startswith("https://"):
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "✨ AI Fotosessiya qilish (Mini App)", "web_app": {"url": app_url}}]
                    ]
                }
            await self.send_message(chat_id, reply, reply_markup=keyboard)

        except Exception as exc:
            logger.error("Error generating card from telegram photo: %s", exc)
            await self.send_message(
                chat_id,
                "⚠️ Mahsulotni tahlil qilishda xatolik yuz berdi. Mini App orqali urinib ko'ring:",
                reply_markup=self._build_main_keyboard(app_url),
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
            f"🏛️ <b>Davlatga soliq (2%):</b> {res.tax_payable_item:,.0f} so'm\n"
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


telegram_service = TelegramService()
