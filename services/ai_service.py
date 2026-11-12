"""
ai_service.py — AI pipeline for Oqila AI (Gemini Multimodal Vision + Studio Photoshoot + Mock fallback)

Supports:
  - Real Gemini API (google-genai SDK >= 2.3.0) with multimodal image understanding
  - AI Studio Photoshoot generation (gemini-2.5-flash-image) with configurable presets
  - Content tone and format customization (Instagram, Telegram, Uzum)
  - Mock mode: rich hardcoded Uzbek/Russian demo data for offline/hackathon stage use
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from services.imaging import finalize_card, to_data_url
from services.info_photo import InfoSpec, build_info_prompt, build_spec, expected_strings, find_missing, find_unexpected
from services.copy_utils import default_copy
from services.presets import ASPECTS, DEFAULT_ASPECT, STYLES_BY_ID, STYLES, build_scene_prompt, style_kind

from services.rate_limit import record_ai_call

logger = logging.getLogger(__name__)

# Gemini calls are blocking HTTP requests: they get their own small pool instead of the default executor,
# so a burst of slow generations cannot starve everything else that uses run_in_executor.
AI_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="gemini")


def _unique(models: List[str]) -> List[str]:
    return [m for i, m in enumerate(models) if m and m not in models[:i]]


def fallback_reason(exc: BaseException) -> str:
    """"quota" when Gemini refused because of limits or billing, otherwise "error"."""
    text = str(exc)
    return "quota" if any(k in text for k in ("RESOURCE_EXHAUSTED", "402", "429", "quota")) else "error"

# ---------------------------------------------------------------------------
# Photoshoot Style Presets
# ---------------------------------------------------------------------------
# Photo styles live in services/presets.py (one registry for backend, frontend and poster layouts).
# This id -> prompt mapping is kept for backward compatibility.
PHOTOSHOOT_PRESETS = {style["id"]: style["prompt"] for style in STYLES if style["prompt"]}

TONE_PRESETS = {
    "luxury": "Tone: exclusive, high-end, premium luxury. Emphasize top-notch materials, prestige and bespoke elegance.",
    "friendly": "Tone: warm, soulful, emotional storytelling. Connect with the customer's heart and comfort.",
    "sales": "Tone: dynamic, high-converting, direct sales with strong call-to-action and urgency.",
    "craft": "Tone: authentic handmade craftsmanship, heritage value, traditional masters' love and dedication.",
}

FORMAT_PRESETS = {
    "instagram": "Format: Instagram post / carousel text with engaging hook, aesthetic emojis, clear value bullets, and call-to-action to DM/comment.",
    "telegram": "Format: Telegram channel showcase post with bold title, item specs, transparent pricing, and instant order instructions.",
    "uzum": "Format: Marketplace catalog description highlighting key benefits, exact specs, care instructions, and customer satisfaction guarantee.",
}

# ---------------------------------------------------------------------------
# Mock data — realistic demo responses (hackathon safety net)
# ---------------------------------------------------------------------------
MOCK_RESPONSE_UZ = {
    "title": "«Anor» — Milliy uslubdagi premium buyum",
    "description": (
        "🌸 O'zbekistonning boy madaniy merosi va an'anaviy san'atidan ilhomlangan eksklyuziv mahsulot. "
        "Mohir ustalar tomonidan mehr bilan yaratilgan bo'lib, har bir detalida sifat va nafislik aks etadi.\n\n"
        "✨ Asosiy afzalliklari:\n"
        "• Yuqori sifatli va tabiiy xomashyo\n"
        "• Har bir buyum — cheklangan nusxadagi mualliflik ishi\n"
        "• Uyingizga fayz va iliqlik bag'ishlaydi\n"
        "• Yaqinlaringiz uchun munosib va unutilmas sovg'a\n\n"
        "📦 O'zbekiston bo'ylab tezkor yetkazib berish xizmati mavjud."
    ),
    "price_tag": "💰 Narx: 380,000 – 420,000 so'm",
    "hashtags": [
        "#milliy_mahsulot", "#qo'lda_yasalgan", "#handmade", "#tadbirkor", 
        "#uzbekistan", "#oqila_ai", "#hunarmand_qizlar", "#tadbirkor_ayollar"
    ],
    "marketing_tip": (
        "💡 Savdo maslahati: Ushbu mahsulotni Instagram va Telegram'da qisqa video (Reels) "
        "shaklida ko'rsating — yaratilish jarayoni va detallarini yaqindan tasvirlash ishonchni 3 barobarga oshiradi! "
        "Cheklangan miqdorda ekanligini ta'kidlang."
    ),
    "photoshoot_style": "minimal_studio",
    "studio_photo_url": None,
}

MOCK_RESPONSE_RU = {
    "title": "«Анор» — Эксклюзивное авторское изделие",
    "description": (
        "🌸 Изысканное изделие, вдохновлённое богатыми традициями и ремесленным мастерством Узбекистана. "
        "Создано с вниманием к каждой детали и станет ярким акцентом в вашем доме или гардеробе.\n\n"
        "✨ Почему стоит выбрать:\n"
        "• Высококачественные натуральные материалы\n"
        "• Ручная работа и лимитированная серия\n"
        "• Уникальный дизайн, сочетающий традиции и современность\n"
        "• Идеальный выбор для себя или в качестве ценного подарка\n\n"
        "📦 Быстрая и бережная доставка по всему Узбекистану."
    ),
    "price_tag": "💰 Цена: 380 000 – 420 000 сум",
    "hashtags": [
        "#авторская_работа", "#ручная_работа", "#handmade", "#tadbirkor", 
        "#uzbekistan", "#oqila_ai", "#ремесленницы", "#бизнес_узбекистан"
    ],
    "marketing_tip": (
        "💡 Совет по продажам: Покажите это изделие в формате короткого видео (Reels/Shorts) — "
        "продемонстрируйте фактуру и детали крупным планом. "
        "Личная история мастера увеличивает продажи в 3 раза! Объявите предзаказ со скидкой 10%."
    ),
    "photoshoot_style": "minimal_studio",
    "studio_photo_url": None,
}


# ---------------------------------------------------------------------------
# AI Service class
# ---------------------------------------------------------------------------
class AIService:
    """
    Wraps Google Gemini API for:
      1. Multimodal product visual analysis & copywriting (gemini-2.5-flash)
      2. AI Studio Photoshoot generation (gemini-2.5-flash-image)
      3. Legal Q&A (gemini-2.5-flash)
    Falls back to mock data if GEMINI_API_KEY is absent, AI_MODE=mock, or any error occurs.
    """

    def __init__(self) -> None:
        self.api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.ai_mode: str = os.getenv("AI_MODE", "gemini").lower()
        self._client = None

        if self.api_key and self.ai_mode != "mock":
            try:
                from google import genai  # type: ignore
                from google.genai import types as gtypes  # type: ignore
                timeout_ms = int(os.getenv("GEMINI_TIMEOUT_MS", "45000"))
                self._client = genai.Client(api_key=self.api_key, http_options=gtypes.HttpOptions(timeout=timeout_ms))
                logger.info("✅ Gemini client initialized successfully.")
            except Exception as exc:  # pragma: no cover
                logger.warning("⚠️  Could not initialize Gemini client: %s", exc)
                self._client = None
        else:
            logger.info("ℹ️  Running in MOCK mode (no API key or AI_MODE=mock).")

    @property
    def is_mock(self) -> bool:
        return self._client is None or self.ai_mode == "mock"

    # -----------------------------------------------------------------------
    # Models (all from the environment) and the one place that talks to Gemini
    # -----------------------------------------------------------------------
    @staticmethod
    def _text_models() -> List[str]:
        """Text model, then its fallback (GEMINI_TEXT_MODEL, GEMINI_TEXT_FALLBACK_MODEL)."""
        return _unique([os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash"), os.getenv("GEMINI_TEXT_FALLBACK_MODEL", "")])

    @classmethod
    def _legal_models(cls) -> List[str]:
        return _unique([os.getenv("GEMINI_LEGAL_MODEL", "")] + cls._text_models())

    @classmethod
    def _ocr_models(cls) -> List[str]:
        return _unique([os.getenv("GEMINI_VERIFY_MODEL", "")] + cls._text_models())

    async def _generate(self, kind: str, models: List[str], contents: Any, config: Any,
                        accept: Optional[Callable[[Any], bool]] = None) -> Any:
        """One Gemini request off the event loop, trying `models` in order. Every attempt is counted in ai_calls.

        `accept` may reject an answer (e.g. an image response without a picture) to try the next model.
        Raises the last error when every model failed.
        """
        loop = asyncio.get_running_loop()
        last_exc: Optional[BaseException] = None
        for model in models:
            def call(m: str = model) -> Any:
                record_ai_call(kind, m)
                return self._client.models.generate_content(model=m, contents=contents, config=config)
            try:
                response = await loop.run_in_executor(AI_EXECUTOR, call)
                if accept is None or accept(response):
                    return response
                logger.warning("%s model %s returned an unusable answer", kind, model)
                last_exc = RuntimeError(f"{model} returned an unusable answer")
            except Exception as exc:
                logger.warning("%s model %s failed: %s", kind, model, exc)
                last_exc = exc
        raise last_exc or RuntimeError("no model configured")

    # -----------------------------------------------------------------------
    # Public: generate product card & studio photoshoot
    # -----------------------------------------------------------------------
    async def generate_product_card(
        self,
        image_bytes: Optional[bytes],
        image_mime: str,
        cost_price: Optional[float],
        desired_price: Optional[float],
        note: Optional[str],
        lang: str = "ru",  # "ru" | "uz"
        photoshoot_style: str = "minimal_studio",
        photoshoot_prompt: Optional[str] = None,
        content_tone: str = "luxury",
        content_format: str = "instagram",
        generate_photo: bool = True,
        force_mock: bool = False,
        aspect_ratio: str = DEFAULT_ASPECT,
        info_text: Optional[str] = None,
    ) -> dict:
        """
        Generate a product marketing card using Gemini Vision & optional AI Photoshoot.
        force_mock=True returns the offline demo answer without calling Gemini.
        """
        if self.is_mock or force_mock:
            # Sample text that is not about the seller's product: always flagged, never saved as a real card
            result = self._mock_response(lang, cost_price, desired_price, note)
            result["ai_fallback"] = "no_key" if self.is_mock else "quota"
            return result

        try:
            return await self._call_gemini_multimodal(
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
                aspect_ratio=aspect_ratio,
                info_text=info_text,
            )
        except Exception as exc:
            logger.error("Gemini API error, falling back to mock: %s", exc)
            result = self._mock_response(lang, cost_price, desired_price, note)
            # The sample text is not about the seller's product: tell the client, so it can say so
            result["ai_fallback"] = fallback_reason(exc)
            return result

    def demo_card(self, lang: str, desired_price: Optional[float] = None, note: Optional[str] = None) -> dict:
        """The built-in sample card of the "quick demo" button: no AI call, and openly a sample."""
        return self._mock_response(lang, None, desired_price, note)

    # -----------------------------------------------------------------------
    # Public: legal Q&A chat
    # -----------------------------------------------------------------------
    async def legal_qa(
        self,
        question: str,
        lang: str = "ru",
        user_profile: Optional[dict] = None,
        force_mock: bool = False,
    ) -> tuple:
        """Answer a legal/business question about Uzbekistan regulations, personalized with user profile.

        Returns (answer, fallback_reason): the reason is None for a real AI answer and "no_key" / "quota" / "error"
        when the built-in template text is returned instead.
        """
        if self.is_mock or force_mock:
            return self._mock_legal_answer(question, lang, user_profile), ("no_key" if self.is_mock else "quota")

        lang_instruction = (
            "Respond in Uzbek (O'zbek tili, lotin alifbosi)."
            if lang == "uz"
            else "Respond in Russian (Russian language)."
        )

        profile_section = ""
        if user_profile:
            status_map = {
                "self_employed": "Самозанятая (O'z-o'zini band qilgan, 1% налог с оборота до 1 млрд сум)",
                "yatt": "ЯТТ (Индивидуальный предприниматель / Yakka tartibdagi tadbirkor, 1% налог с оборота)",
                "planning": "Планирует регистрацию / еще выбирает статус",
            }
            category_map = {
                "sewing": "Пошив одежды / текстиль (Tikuvchilik)",
                "crafts": "Хэндмейд / ремёсла (Hunarmandchilik)",
                "food": "Домашняя кулинария / выпечка (Pazandachilik)",
                "resale": "Торговля и перепродажа (товары из Китая, опт / Qayta sotish)",
                "services": "Услуги / сервис (Xizmatlar)",
            }
            channel_map = {
                "uzum": "Uzum Market",
                "instagram": "Instagram / Соцсети",
                "telegram": "Telegram",
                "offline": "Офлайн-магазин / точка продаж",
            }
            u_name = str(user_profile.get("name") or "").strip() or "Предпринимательница"
            u_first = (u_name.split() or ["Tadbirkor"])[0]
            u_status = status_map.get(user_profile.get("status"), user_profile.get("status", "Не указан"))
            u_cat = category_map.get(user_profile.get("category"), user_profile.get("category", "Не указана"))
            u_chan = channel_map.get(user_profile.get("salesChannel"), user_profile.get("salesChannel", "Не указан"))

            profile_section = f"""
USER BUSINESS PROFILE (Use this to personalize your advice):
- Имя/бренд: {u_name}
- Текущий правовой статус: {u_status}
- Ниша / деятельность: {u_cat}
- Канал продаж: {u_chan}

PERSONALIZATION RULES:
- Address the user warmly by name ({u_first}) in your greeting.
- Tailor legal and tax advice to their specific status, niche, and sales channel.
- If they are self-employed and ask about reselling purchased goods (China, wholesale), explain that since 01.01.2026 ordinary retail trade is excluded from the self-employed list (УП-50), only retail sales on electronic trading platforms are allowed (item 33), and Uzum admits self-employed sellers only with their own products — so for reselling they should register as YaTT.
- If they sell on Uzum Market, remind them that Uzum is a commission agent and does NOT withhold the tax: the seller pays the 1% turnover tax (ст. 467 НК РУз в ред. ЗРУ-1108) on the full sale amount by the 15th of the next month, and Uzum admits self-employed sellers only with their own products.
- If they are in crafts/handmade, mention potential benefits of the «Hunarmand» association.
"""

        system_prompt = f"""You are OqilaLegal — an expert AI legal assistant specializing in
Uzbekistan business law, tax regulations, and entrepreneurship for women.
{lang_instruction}
{profile_section}
OFFICIAL LEGAL FRAMEWORK OF THE REPUBLIC OF UZBEKISTAN (checked against lex.uz / norma.uz / gov.uz publications, November 2026):

1. НАЛОГ С ОБОРОТА — Закон № ЗРУ-1108 от 25.12.2025 г. (с 1 января 2026 г.):
   - Ставка налога с оборота для ЯТТ и самозанятых — 1% (ст. 467 НК). Закон установил её для годового дохода до 1 млрд сум;
     если пользователь спрашивает про доход выше 1 млрд сум, скажи, что ставку нужно уточнить на soliq.uz.
   - Налог считается со всей выручки (расходы не вычитаются). Отчётный период — месяц, уплата до 15 числа следующего месяца (ст. 470 НК).
   - Освобождение самозанятых при доходе до 100 млн сум отменено. Налог с оборота в фиксированной сумме отменён.
   - По доходам самозанятых, полученным через цифровые платформы платёжных организаций, налог перечисляет платёжная организация (налоговый агент).
   - Uzum Market НЕ удерживает налог за продавца: Uzum — комиссионер, продавец сам платит налог со всей суммы продажи (комиссия базу не уменьшает).

2. ПОРОГ ОБЩЕГО РЕЖИМА — Указ № УП-100 от 26.05.2026 г. (с 1 июня 2026 г.):
   - Обязательный переход на НДС и налог на прибыль — при доходе свыше 12 000 БРВ в год (≈5,28 млрд сум). Прежний порог 1 млрд сум больше не действует.

3. САМОЗАНЯТОСТЬ — ПП-4742 от 08.06.2020 г. и Указ № УП-50 от 19.03.2025 г.:
   - С 1 января 2026 г. перечень видов деятельности сокращён со 104 до 72 пунктов. Исключены, в частности, обычная розничная торговля,
     парикмахерские и косметологические услуги, фото- и видеосъёмка. Разрешена розничная продажа на электронных торговых площадках (п. 33).
   - Нанимать работников по трудовому договору нельзя.
   - Uzum Market по своим правилам допускает самозанятых только с товарами собственного производства; для перепродажи вне маркетплейсов нужен ЯТТ или ООО.
   - Социальный налог: добровольно не менее 1 БРВ в год для трудового стажа (ст. 408 ч. 2 НК).
   - Не называй номера пунктов перечня, кроме п. 33, — советуй проверить свой вид деятельности в приложении Soliq.

4. ЯТТ (индивидуальный предприниматель):
   - Закон «О гарантиях свободы предпринимательской деятельности» (в ред. ЗРУ-328 от 02.05.2012 г.), регистрация — ПКМ № 66 от 09.02.2017 г.
   - Регистрация онлайн через fo.birdarcha.uz или my.gov.uz с ЭЦП; госпошлина онлайн 0,9 БРВ, в Центре госуслуг 1 БРВ.
   - Социальный налог: не менее 1 БРВ в месяц обязательно, до 15 числа текущего месяца (ст. 408 ч. 1 НК).

5. БРВ = 440 000 сум с 1 сентября 2026 г. (Указ № УП-115 от 23.06.2026 г.).

6. ЭЦП (E-IMZO) — Закон № ЗРУ-793 от 12.10.2022 г.:
   - Платная: для физических лиц около 7% БРВ (≈30 800 сум), для юрлиц и ЯТТ около 10% БРВ; точная сумма показывается при оплате.
   - С 2026 г. при первичном получении ID-карты ЭЦП создаётся бесплатно. Срок действия ключа — 2 года.

7. ОНЛАЙН-ККМ И ЧЕКИ — ПКМ № 943 от 23.11.2019 г.: фискальный чек выдаётся через онлайн-ККМ, виртуальную кассу
   или электронный чек платёжной системы. За торговлю без ККМ предусмотрены штрафы — не называй конкретную статью и суммы.

8. ДРУГОЕ: ЗРУ-792 от 29.09.2022 г. «Об электронной коммерции»; ЗРУ-578 от 01.11.2019 г. «О платежах и платежных системах»;
   Инструкция ЦБ о банковских счетах (рег. № 3420 от 08.02.2023 г.).
   - Ассоциация «Хунарманд» (Указ № УП-5242 от 17.11.2017 г.): у членов есть льготы, но НЕ утверждай, что они освобождены
     от налога с оборота, — советуй уточнить действующие льготы в ассоциации и на soliq.uz.
   - Тарифы Uzum, Click и Payme — коммерческие условия, а не закон; называй их ориентировочными.

If a question goes beyond these facts, say what is known, recommend checking soliq.uz, my.gov.uz or lex.uz, and do not invent article numbers, amounts or dates.

Rules:
- Give concise, practical, 100% legally grounded advice.
- DO NOT generate or output links, URLs, or markdown links to laws, decrees, or lex.uz. Explain all requirements and procedures in simple, plain language without web links.
- E-IMZO / ЭЦП is PAID (7% of BRV = ~30 800 UZS for physical persons). NEVER say it is free!
- Clarify the difference: self-employed CAN sell on Uzum Market ONLY their own handmade goods; for resale/China goods they MUST register as YaTT.
- Explain bank account rules accurately for both YaTT (mandatory business account) and self-employed (personal card is enough).
- Use bullet points and emojis for readability.
- Informational nature: Keep in mind this is an informational aid based on open official data. If a question involves complex corporate or customized taxation, advise consulting soliq.uz or a certified tax consultant.
"""

        try:
            from google.genai import types as gtypes  # type: ignore
            config = gtypes.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )
            response = await self._generate("legal", self._legal_models(), question, config, accept=lambda r: bool(r.text))
            return response.text, None
        except Exception as exc:
            logger.error("Gemini legal QA error: %s", exc)
            return self._mock_legal_answer(question, lang, user_profile), fallback_reason(exc)

    # -----------------------------------------------------------------------
    # Internal: AI Studio Photoshoot Image Generation
    # -----------------------------------------------------------------------
    @staticmethod
    def _image_models() -> List[str]:
        """Primary image model, then a fallback: `gemini-3.1-flash-image` spells Russian/Uzbek text correctly,
        the older `gemini-2.5-flash-image` does not (it produced 'Безогсасная'), so it is only a safety net."""
        return _unique([os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
                        os.getenv("GEMINI_IMAGE_FALLBACK_MODEL", "gemini-2.5-flash-image")])

    async def _generate_image_bytes(self, contents: Any, aspect_ratio: str = DEFAULT_ASPECT) -> Optional[bytes]:
        """Raw bytes of one generated picture (PNG/JPEG) or None; tries the fallback model if the first one fails."""
        from google.genai import types as gtypes  # type: ignore

        config = gtypes.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=gtypes.ImageConfig(aspect_ratio=ASPECTS.get(aspect_ratio, ASPECTS[DEFAULT_ASPECT])["model"]),
        )
        def picture(response: Any) -> Optional[bytes]:
            for part in response.parts or []:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
            return None

        try:
            response = await self._generate("image", self._image_models(), contents, config, accept=lambda r: picture(r) is not None)
        except Exception:
            return None
        return picture(response)

    async def generate_studio_photo(
        self,
        image_bytes: Optional[bytes] = None,
        image_mime: Optional[str] = "image/jpeg",
        style_preset: str = "minimal_studio",
        custom_prompt: Optional[str] = None,
        product_description: Optional[str] = None,
        aspect_ratio: str = DEFAULT_ASPECT,
    ) -> Optional[str]:
        """
        Generate a commercial studio photoshoot image based on uploaded item or description.
        Supports both image-to-image and text-to-image with customizable prompts.
        Returns a base64 data URI or None. "Clean" Uzum styles are finished to 1080x1440 JPEG with a pure white background.
        """
        if self.is_mock or not self._client:
            return None

        # Need at least an image or a text description/prompt
        if not image_bytes and not custom_prompt and not product_description:
            return None

        try:
            from google.genai import types as gtypes  # type: ignore

            # Determine final prompt: the style registry supplies the scene (and, for posters, the calm
            # areas left for text); wishes typed by the seller are appended, "custom" uses them as is.
            extra = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else None
            style = STYLES_BY_ID.get(style_preset)
            if extra and style and extra in (style.get("hint_ru"), style.get("hint_uz")):
                extra = None  # the UI sent the style's own description back: not a user wish
            if style_preset == "custom" and extra:
                final_prompt = extra
            else:
                final_prompt = build_scene_prompt(style_preset, extra)
            if product_description and not image_bytes and product_description.lower() not in final_prompt.lower():
                final_prompt = f"Commercial product photoshoot of {product_description}. {final_prompt}"

            if image_bytes:
                contents: Any = [gtypes.Part.from_bytes(data=image_bytes, mime_type=image_mime or "image/jpeg"), final_prompt]
            else:
                contents = final_prompt

            raw = await self._generate_image_bytes(contents, aspect_ratio)
            if not raw:
                return None
            if style_kind(style_preset) == "clean":
                return to_data_url(finalize_card(raw, whiten=style_preset == "uzum_clean"))
            return "data:image/png;base64," + base64.b64encode(raw).decode("utf-8")

        except Exception as exc:
            logger.warning("Could not generate studio photo: %s", exc)

        return None

    # -----------------------------------------------------------------------
    # Information cards: AI draws the text, a second AI call reads it back, mistakes trigger a retry
    # -----------------------------------------------------------------------
    async def read_image_text(self, image_png: bytes) -> List[str]:
        """Text visible in a picture, read by a vision model (lossless PNG and a strict prompt give complete results)."""
        from google.genai import types as gtypes  # type: ignore

        prompt = (
            "You are an OCR engine. Scan the WHOLE image systematically from top to bottom, including small captions under "
            "icons, text at the very bottom and at the edges, and text inside decorative elements. Transcribe every piece of "
            "text exactly letter by letter as written; never correct spelling, never skip anything. "
            'Return JSON: {"lines": ["..."]}.'
        )
        response = await self._generate(
            "ocr", self._ocr_models(),
            [gtypes.Part.from_bytes(data=image_png, mime_type="image/png"), prompt],
            gtypes.GenerateContentConfig(response_mime_type="application/json", temperature=0),
        )
        data = json.loads(response.text or "{}")
        lines = data.get("lines", []) if isinstance(data, dict) else data
        return [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in lines]

    async def generate_info_photo(
        self,
        image_bytes: bytes,
        image_mime: str,
        style_id: str,
        spec: InfoSpec,
        aspect_ratio: str = "3:4",
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        An information card for `spec`. Returns {"photo_url", "verified", "missing", "unexpected", "attempts"}; photo_url is None
        if no picture could be produced. verified=True means every requested string was read back from the picture,
        False means some are missing even after retries (the best attempt is returned), None means the check itself failed.
        """
        from google.genai import types as gtypes  # type: ignore

        part = gtypes.Part.from_bytes(data=image_bytes, mime_type=image_mime or "image/jpeg")
        expected = expected_strings(spec, style_id)
        best: Optional[tuple] = None
        retry_missing: Optional[List[str]] = None
        verified: Optional[bool] = None
        attempts = 0
        for attempt in range(1, max_attempts + 1):
            attempts = attempt
            raw = await self._generate_image_bytes([part, build_info_prompt(style_id, spec, aspect_ratio, retry_missing)], aspect_ratio)
            if not raw:
                continue
            try:
                lines = await self.read_image_text(raw)
                missing = find_missing(lines, expected)
                unexpected = find_unexpected(lines, expected)
                verified = not missing
            except Exception as exc:
                logger.warning("Could not verify the text of an info card: %s", exc)
                best, verified = (0, raw, [], []), None
                break
            if best is None or len(missing) < len(best[2]):
                best = (len(missing), raw, missing, unexpected)
            if not missing:
                break
            retry_missing = missing
        if best is None:
            return {"photo_url": None, "verified": False, "missing": expected, "unexpected": [], "attempts": attempts}
        _, raw, missing, unexpected = best
        return {
            "photo_url": to_data_url(finalize_card(raw)),
            "verified": verified if verified is None else not missing,
            "missing": missing,
            "unexpected": unexpected,
            "attempts": attempts,
        }

    # -----------------------------------------------------------------------
    # Internal: Concurrent Gemini Vision & Photoshoot execution
    # -----------------------------------------------------------------------
    async def _call_gemini_multimodal(
        self,
        image_bytes: Optional[bytes],
        image_mime: str,
        cost_price: Optional[float],
        desired_price: Optional[float],
        note: Optional[str],
        lang: str,
        photoshoot_style: str = "minimal_studio",
        photoshoot_prompt: Optional[str] = None,
        content_tone: str = "luxury",
        content_format: str = "instagram",
        generate_photo: bool = True,
        aspect_ratio: str = DEFAULT_ASPECT,
        info_text: Optional[str] = None,
    ) -> dict:
        from google.genai import types as gtypes  # type: ignore

        lang_instruction = (
            "Respond ONLY in Uzbek (O'zbek tili, lotin alifbosi)."
            if lang == "uz"
            else "Respond ONLY in Russian language."
        )

        tone_rule = TONE_PRESETS.get(content_tone, TONE_PRESETS["luxury"])
        format_rule = FORMAT_PRESETS.get(content_format, FORMAT_PRESETS["instagram"])

        system_prompt = f"""You are OqilaCopy — an expert AI marketing copywriter and product visual analyst for Uzbekistan's
women entrepreneurs, artisans, and small business owners.
{lang_instruction}

Your task:
1. Carefully analyze the uploaded image (or provided notes/specifications).
2. Accurately identify what the product actually is (e.g. furniture, table, chairs, clothing, ceramics, jewelry, food, etc.).
3. Under NO circumstances assume it is clothing or dress if the image shows furniture, household goods, or other categories!
4. Follow this style:
   - {tone_rule}
   - {format_rule}
5. Generate a compelling, high-converting product marketing package tailored specifically to this product.

Return ONLY valid JSON with this exact structure:
{{
  "title": "Catchy product name matching the exact item in image with emoji (max 60 chars)",
  "description": "Selling description 120-220 words. Highlight real features of this specific item, materials, durability/style, usage ideas. End with ordering info.",
  "price_tag": "Formatted price string, e.g. '💰 Narx: 380,000 so'm' or '💰 Цена: 380 000 сум'",
  "hashtags": ["#tag1", "#tag2", ...],  // 8-12 relevant hashtags
  "marketing_tip": "One specific actionable marketing and sales tip for Instagram/Telegram tailored to this product category (80-120 words)",
  "info": {{
    "title": "Plain descriptive product name for a card heading: what it is plus one visible attribute, max 40 chars, no emoji, no quotes. NEVER invent a brand, collection or proper name",
    "tagline": "Three neutral words about the look or mood separated by ' · ', e.g. 'Нарядный · Яркий · Ручной'. No superlatives, no quality claims",
    "benefits": ["3 or 4 very short benefits, max 34 chars each"],
    "badge": "An empty string, unless the seller notes clearly support a short badge (e.g. 'Ручная работа' only if the seller says it is handmade)",
    "uses": ["up to 4 captions of 1-2 words, max 14 chars each, e.g. 'НА СТОЛ' / 'В ПОДАРОК'"]
  }}
}}

STRICT RULE for the "info" block: it is printed on a product photo, so it must contain ONLY facts that are clearly visible in
the image or stated in the seller's notes. NEVER invent sizes, weights, materials, certificates, guarantees, discounts or any
other numbers, and never use promises or superlatives such as premium, best, №1, highest quality, guaranteed, exclusive, 100%.
If unsure, use general words about look and mood (colour, style, gift idea).
"""

        # Build input parts for text analysis
        text_parts: list = []
        if image_bytes:
            text_parts.append(
                gtypes.Part.from_bytes(
                    data=image_bytes,
                    mime_type=image_mime or "image/jpeg",
                )
            )

        context_parts = []
        if cost_price:
            context_parts.append(f"Себестоимость/Tannarx: {cost_price:,.0f} сум/so'm")
        if desired_price:
            context_parts.append(f"Желаемая цена/Maqsadli narx: {desired_price:,.0f} сум/so'm")
        if note:
            context_parts.append(f"Описание изделия/Tavsif: {note}")
        if info_text and info_text.strip():
            context_parts.append(f"Факты от продавца (используй только их для размеров и характеристик):\n{info_text.strip()[:1500]}")
        if photoshoot_prompt:
            context_parts.append(f"Стиль съёмки/Промпт: {photoshoot_prompt}")

        text_input = "Analyze this specific product and generate the marketing card in JSON format.\n"
        if context_parts:
            text_input += "\n".join(context_parts)
        text_parts.append(text_input)

        config = gtypes.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.7,
        )

        # Define text generation worker
        async def text_worker():
            resp = await self._generate("text", self._text_models(), text_parts, config, accept=lambda r: bool(r.text))
            raw = (resp.text or "").strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.rstrip("`").strip()
            return json.loads(raw)

        # Define studio photoshoot worker
        async def photo_worker():
            if generate_photo and (image_bytes or note or photoshoot_prompt):
                return await self.generate_studio_photo(
                    image_bytes=image_bytes,
                    image_mime=image_mime,
                    style_preset=photoshoot_style,
                    custom_prompt=photoshoot_prompt,
                    product_description=note,
                    aspect_ratio=aspect_ratio,
                )
            return None

        if style_kind(photoshoot_style) == "ai_text":
            # The card needs the text first (title, benefits), so text and picture run one after the other.
            text_result = await text_worker()
            for key in ("title", "description", "price_tag", "hashtags", "marketing_tip"):
                text_result.setdefault(key, "")
            spec = build_spec(
                text_result.get("info") or {}, info_text, default_copy(text_result, None, lang)["title"], lang, allowed_text=note
            )
            if generate_photo and image_bytes:
                info = await self.generate_info_photo(image_bytes, image_mime, photoshoot_style, spec, aspect_ratio)
            else:
                info = {"photo_url": None, "verified": None, "missing": [], "unexpected": [], "attempts": 0}
            text_result["studio_photo_url"] = info.pop("photo_url")
            text_result["info"] = {**spec.to_dict(), **info}
            text_result["photoshoot_style"] = photoshoot_style
            return text_result

        # Execute text analysis and photoshoot image generation concurrently.
        # One failing half must not throw away the other: a finished picture is kept even if the text call failed.
        text_result, studio_photo_url = await asyncio.gather(text_worker(), photo_worker(), return_exceptions=True)
        if isinstance(studio_photo_url, BaseException):
            logger.warning("Studio photo failed: %s", studio_photo_url)
            studio_photo_url = None
        if isinstance(text_result, BaseException):
            if not studio_photo_url:
                raise text_result
            logger.error("Text model failed, keeping the picture: %s", text_result)
            reason = fallback_reason(text_result)
            # No sample text here: the picture is real, so the card is saved with an honest empty description
            text_result = {
                "title": " ".join((note or "").split())[:60], "description": "", "price_tag": "", "hashtags": [],
                "marketing_tip": "", "ai_fallback": reason, "ai_fallback_scope": "text",
            }
        if not isinstance(text_result, dict):
            raise ValueError("The text model did not return a JSON object")

        # Ensure required keys exist
        for key in ("title", "description", "price_tag", "marketing_tip"):
            if not isinstance(text_result.get(key), str):
                text_result[key] = ""
        if not isinstance(text_result.get("hashtags"), list):
            text_result["hashtags"] = []

        text_result["studio_photo_url"] = studio_photo_url
        text_result["photoshoot_style"] = photoshoot_style
        text_result["photoshoot_prompt"] = photoshoot_prompt

        return text_result

    # -----------------------------------------------------------------------
    # Mock helpers
    # -----------------------------------------------------------------------
    def _mock_response(
        self,
        lang: str,
        cost_price: Optional[float],
        desired_price: Optional[float],
        note: Optional[str] = None,
    ) -> dict:
        base = dict(MOCK_RESPONSE_UZ if lang == "uz" else MOCK_RESPONSE_RU)
        
        # If user specified note about tables/chairs or furniture, adapt the mock!
        if note and any(w in note.lower() for w in ["стол", "стул", "мебель", "stol", "stul", "mebel"]):
            if lang == "uz":
                base["title"] = "«Shinam» — Qo'lda yasalgan yog'och stol va stullar"
                base["description"] = (
                    "🪵 Tabiiy yong'oq yog'ochidan tayyorlangan mustahkam va ko'rkam oshxona stoli to'plami. "
                    "Har bir stol va stul ustalarimiz tomonidan silliqlanib, ekologik toza lak bilan qoplangan.\n\n"
                    "✨ Afzalliklari:\n"
                    "• 100% tabiiy va qattiq yog'och\n"
                    "• 10 yildan ortiq xizmat qilish kafolati\n"
                    "• Klassik va zamonaviy interyerlarga mos\n\n"
                    "📦 Toshkent bo'ylab bepul yetkazib berish va o'rnatish!"
                )
                base["hashtags"] = ["#mebel", "#yogoch_stol", "#handmade", "#tadbirkor", "#uzbekistan"]
            else:
                base["title"] = "«Шинам» — Обеденный комплект из натурального дерева"
                base["description"] = (
                    "🪵 Элегантный обеденный стол и удобные стулья из массива ореха ручной работы. "
                    "Тщательная шлифовка и покрытие экологичным защитным маслом подчеркивают естественную текстуру дерева.\n\n"
                    "✨ Преимущества:\n"
                    "• 100% натуральное цельное дерево\n"
                    "• Долговечность и надёжная сборка на долгие годы\n"
                    "• Идеально вписывается в современный и классический интерьер\n\n"
                    "📦 Бесплатная доставка и сборка по Ташкенту!"
                )
                base["hashtags"] = ["#мебель", "#деревянный_стол", "#handmade", "#tadbirkor", "#uzbekistan"]

        if desired_price:
            if lang == "uz":
                base["price_tag"] = f"💰 Narx: {desired_price:,.0f} so'm"
            else:
                base["price_tag"] = f"💰 Цена: {desired_price:,.0f} сум"
        return base

    def _mock_legal_answer(self, question: str, lang: str, user_profile: Optional[dict] = None) -> str:
        greeting_ru = ""
        greeting_uz = ""
        first = (str((user_profile or {}).get("name") or "").split() or [""])[0]
        if first:
            name = first
            greeting_ru = f"👤 Здравствуйте, {name}! С учётом вашего профиля:\n\n"
            greeting_uz = f"👤 Assalomu alaykum, {name}! Sizning profilingiz bo'yicha:\n\n"

        if lang == "uz":
            return (
                f"{greeting_uz}⚖️ **OqilaLegal — O'zbekiston qonunchiligi bo'yicha qisqa ma'lumot (2026-yil)**\n\n"
                "📌 **1. Aylanmadan soliq (O'RQ-1108-son qonun):**\n"
                "• YaTT va o'z-o'zini band qilganlar uchun stavka — **1%** (SK 467-modda), butun tushumdan.\n"
                "• Har oy keyingi oyning 15-sanasigacha to'lanadi (SK 470-modda). 100 mln so'mgacha bo'lgan imtiyoz bekor qilingan.\n"
                "• Uzum komissioner: soliqni sotuvning to'liq summasidan o'zingiz to'laysiz.\n\n"
                "📌 **2. O'z-o'zini band qilish (PQ-4742, PF-50):**\n"
                "• 2026-yildan ro'yxatda 72 ta faoliyat turi; oddiy chakana savdo, sartaroshlik, foto/video xizmatlari chiqarilgan.\n"
                "• Elektron savdo maydonchalarida chakana sotish mumkin (33-band), ammo Uzum faqat o'zi ishlab chiqargan mahsulotni qabul qiladi.\n"
                "• Ijtimoiy soliq: staj uchun ixtiyoriy, yiliga kamida 1 BHM (440 000 so'm).\n\n"
                "📌 **3. YaTT:**\n"
                "• Qayta sotish (Xitoy, ulgurji, bozor) uchun YaTT oching: fo.birdarcha.uz yoki my.gov.uz, davlat boji onlayn 0,9 BHM.\n"
                "• Majburiy ijtimoiy soliq: oyiga kamida 1 BHM (440 000 so'm), 15-sanagacha.\n"
                "• Yillik daromad 12 000 BHMdan (≈5,28 mlrd so'm) oshsa — QQS va foyda solig'iga o'tiladi (PF-100).\n\n"
                "📌 **4. Cheklar (VMQ № 943):** onlayn-NKM, virtual kassa yoki Click/Payme elektron cheki.\n\n"
                "📱 Rasmiy manbalar: **soliq.uz** | **my.gov.uz** | **lex.uz**"
            )
        return (
            f"{greeting_ru}⚖️ **OqilaLegal — коротко о законодательстве Узбекистана (2026 г.)**\n\n"
            "📌 **1. Налог с оборота (Закон № ЗРУ-1108):**\n"
            "• Для ЯТТ и самозанятых ставка — **1%** (ст. 467 НК), со всей выручки.\n"
            "• Платится ежемесячно до 15 числа следующего месяца (ст. 470 НК). Освобождение до 100 млн сум отменено.\n"
            "• Uzum — комиссионер: налог вы платите сами со всей суммы продажи.\n\n"
            "📌 **2. Самозанятость (ПП-4742, УП-50):**\n"
            "• С 2026 г. в перечне 72 вида деятельности; обычная розничная торговля, парикмахерские, фото- и видеоуслуги исключены.\n"
            "• Розничная продажа на электронных площадках разрешена (п. 33), но Uzum принимает самозанятых только с товарами своего производства.\n"
            "• Соцналог: добровольно не менее 1 БРВ (440 000 сум) в год для стажа.\n\n"
            "📌 **3. ЯТТ:**\n"
            "• Для перепродажи (Китай, опт, рынок) откройте ЯТТ: fo.birdarcha.uz или my.gov.uz, госпошлина онлайн 0,9 БРВ.\n"
            "• Обязательный соцналог: не менее 1 БРВ (440 000 сум) в месяц, до 15 числа.\n"
            "• При доходе свыше 12 000 БРВ в год (≈5,28 млрд сум) — переход на НДС и налог на прибыль (УП-100).\n\n"
            "📌 **4. Чеки (ПКМ № 943):** онлайн-ККМ, виртуальная касса или электронный чек Click/Payme.\n\n"
            "📱 Официальные источники: **soliq.uz** | **my.gov.uz** | **lex.uz**"
        )



# Singleton instance
ai_service = AIService()
