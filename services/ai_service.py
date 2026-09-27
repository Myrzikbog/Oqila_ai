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
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Photoshoot Style Presets
# ---------------------------------------------------------------------------
PHOTOSHOOT_PRESETS = {
    "minimal_studio": (
        "Professional commercial studio photoshoot of this item. Placed on an elegant clean podium, "
        "soft diffused studio lighting, minimalist neutral beige/white background, ultra sharp 8k product catalog photography"
    ),
    "uzbek_heritage": (
        "Professional product photoshoot in an authentic Uzbek traditional interior. Beautiful carved wood details, "
        "subtle national silk ikat textures in background, warm ambient lighting, heritage craftsmanship aesthetic"
    ),
    "uzum_catalog": (
        "Clean e-commerce product catalog photo on pure white seamless background, soft balanced commercial lighting, "
        "subtle natural ground shadow, high commercial sharpness tailored for Uzum Market seller listing"
    ),
    "luxury_dark": (
        "Luxury editorial product photoshoot. Moody dark slate/obsidian background, warm dramatic spotlighting, "
        "polished dark marble surface, subtle gold reflections, premium high-end boutique aesthetic"
    ),
    "natural_light": (
        "Outdoor lifestyle product photography. Natural warm morning sunlight, organic wooden surface, "
        "gentle morning breeze, soft green botanical bokeh background, warm aesthetic depth of field"
    ),
}

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
                self._client = genai.Client(api_key=self.api_key)
                logger.info("✅ Gemini client initialized successfully.")
            except Exception as exc:  # pragma: no cover
                logger.warning("⚠️  Could not initialize Gemini client: %s", exc)
                self._client = None
        else:
            logger.info("ℹ️  Running in MOCK mode (no API key or AI_MODE=mock).")

    @staticmethod
    def _get_loop() -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.get_event_loop()

    @property
    def is_mock(self) -> bool:
        return self._client is None or self.ai_mode == "mock"

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
    ) -> dict:
        """
        Generate a product marketing card using Gemini Vision & optional AI Photoshoot.
        """
        if self.is_mock:
            return self._mock_response(lang, cost_price, desired_price, note)

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
            )
        except Exception as exc:
            logger.error("Gemini API error, falling back to mock: %s", exc)
            return self._mock_response(lang, cost_price, desired_price, note)

    # -----------------------------------------------------------------------
    # Public: legal Q&A chat
    # -----------------------------------------------------------------------
    async def legal_qa(self, question: str, lang: str = "ru", user_profile: Optional[dict] = None) -> str:
        """Answer a legal/business question about Uzbekistan regulations, personalized with user profile."""
        if self.is_mock:
            return self._mock_legal_answer(question, lang, user_profile)

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
            u_name = user_profile.get("name", "Предпринимательница")
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
- Address the user warmly by name ({u_name.split()[0]}) in your greeting.
- Tailor legal and tax advice to their specific status, niche, and sales channel.
- If they are self-employed and asking about trading/reselling goods from China, WARN them clearly that self-employed status strictly forbids resale, and they must register as YaTT.
- If they sell on Uzum Market, remind them that Uzum Market acts as a tax agent and withholds the 1% turnover tax (ст. 467 НК РУз в ред. ЗРУ-1108), and for self-employed only handmade/own products are allowed.
- If they are in crafts/handmade, mention potential benefits of the «Hunarmand» association.
"""

        system_prompt = f"""You are OqilaLegal — an expert AI legal assistant specializing in
Uzbekistan business law, tax regulations, and entrepreneurship for women.
{lang_instruction}
{profile_section}
OFFICIAL LEGAL FRAMEWORK OF THE REPUBLIC OF UZBEKISTAN (verified data 2026 г., Закон № ЗРУ-1108):

1. САМОЗАНЯТОСТЬ (O'z-o'zini band qilish) — ПП-4742 от 08.06.2020 г. и Закон № ЗРУ-1108 от 25.12.2025 г.:
   - С 1 января 2026 года для самозанятых установлена единая ставка налога с оборота 1% (прежнее освобождение до 100 млн сум отменено).
   - 104 разрешённых вида деятельности: ремёсла, пошив одежды (№36), кулинария/выпечка (№50), услуги и др.
   - Социальный налог для пенсионного стажа: не менее 1 БРВ в год (440 000 сум) — ДОБРОВОЛЬНО (ст. 408 ч. 2 НК РУз).
   - ЗАПРЕЩЕНО нанимать работников по трудовому договору.
   - ЗАПРЕЩЕНО заниматься перепродажей покупных товаров (товары из Китая, рынков «Абу Сахий», оптовиков) — только продукция собственного изготовления!
   - ВЫХОД НА UZUM MARKET ДЛЯ САМОЗАНЯТЫХ:
     • Самозанятый ИМЕЕТ ПРАВО продавать на Uzum Market ТОЛЬКО товары СОБСТВЕННОГО ПРОИЗВОДСТВА (хэндмейд, пошив, выпечка).
     • Uzum Market выступает налоговым агентом и удерживает 1% налога с оборота у источника выплаты.
     • Перепродавать покупные товары в статусе самозанятого на Uzum Market СТРОГО ЗАПРЕЩЕНО законом!

2. ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ (ЯТТ / Yakka tartibdagi tadbirkor):
   - Регулируется Законом РУз № ЗРУ-328 от 02.05.2012 г. и Налоговым кодексом РУз в редакции Закона № ЗРУ-1108 (с 1 января 2026 г.).
   - Регистрация онлайн через fo.birdarcha.uz или my.gov.uz за 15–30 минут (госпошлина 0.9 БРВ).
   - ОБЯЗАТЕЛЕН для любой торговой деятельности (перепродажа товаров из Китая, опт, ритейл).
   - ЕДИНАЯ СТАВКА НАЛОГА С ОБОРОТА: 1% при годовом совокупном доходе до 1 млрд сум (ст. 467 таблица ставок строка 5). Прежние ставки 2%, 4% и фиксированный налог отменены.
   - Социальный налог (ст. 408 ч. 1 п. 1 НК РУз): ОБЯЗАТЕЛЬНО не менее 1 БРВ в месяц (440 000 сум/мес) независимо от дохода.
   - Срок уплаты налогов: ежемесячно до 15-го числа.
   - Порог перехода на НДС (12%) и налог на прибыль: оборот свыше 1 млрд сум в год (ст. 237 и 461 НК РУз).
   - Разрешено нанимать сотрудников по трудовому договору (до 5 человек для торговли).

3. БАНКОВСКИЕ СЧЕТА В БАНКАХ УЗБЕКИСТАНА:
   - Регулируется Законом РУз № ЗРУ-580 и Инструкцией ЦБ РУз № 3420 от 08.02.2023 г.
   - ДЛЯ ЯТТ: расчетный счет открывается на имя ЯТТ онлайн (Kapitalbank Business, Anorbank, Ipoteka, TBC) за 1–3 дня.
   - ДЛЯ САМОЗАНЯТЫХ: расчетный счет юрлица не обязателен. Выплаты от клиентов и Uzum Market приходят на личную карту Uzcard/Humo.

4. РЕМЕСЛЕННИЧЕСТВО (Ассоциация «Хунарманд»):
   - Указ Президента РУз № УП-5242 и № УП-91.
   - Члены ассоциации «Хунарманд» полностью освобождены от уплаты налога с оборота по доходам от реализации ремесленных изделий.

5. ОНЛАЙН-ККМ И ЧЕКИ:
   - ПКМ РУз № 943 от 23.11.2019 г. и ст. 221 НК РУз. Фискальные чеки обязательны (через Soliq QR-чек или Click/Payme).

6. ПЛАТЕЖИ И ЭЦП:
   - ⚠️ ЭЦП (E-IMZO) ПЛАТНАЯ: для физических лиц госпошлина составляет 7% от БРВ (~30 800 сум), для юрлиц — 10% от БРВ (~44 000 сум). Оплачивается онлайн через Click/Payme.
     • Бесплатно ЭЦП выпускается только автоматически при первом получении биометрической ID-карты в органах миграции или учащимся лицеев/колледжей.

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
            loop = self._get_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=question,
                    config=config,
                ),
            )
            return response.text or self._mock_legal_answer(question, lang, user_profile)
        except Exception as exc:
            logger.error("Gemini legal QA error: %s", exc)
            return self._mock_legal_answer(question, lang, user_profile)

    # -----------------------------------------------------------------------
    # Internal: AI Studio Photoshoot Image Generation
    # -----------------------------------------------------------------------
    async def generate_studio_photo(
        self,
        image_bytes: Optional[bytes] = None,
        image_mime: Optional[str] = "image/jpeg",
        style_preset: str = "minimal_studio",
        custom_prompt: Optional[str] = None,
        product_description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a commercial studio photoshoot image based on uploaded item or description.
        Supports both image-to-image and text-to-image with customizable prompts.
        Returns a base64 data URI (data:image/jpeg;base64,...) or None.
        """
        if self.is_mock or not self._client:
            return None

        # Need at least an image or a text description/prompt
        if not image_bytes and not custom_prompt and not product_description:
            return None

        try:
            from google.genai import types as gtypes  # type: ignore

            # Determine final prompt
            if custom_prompt and custom_prompt.strip():
                final_prompt = custom_prompt.strip()
                if product_description and not image_bytes and product_description.lower() not in final_prompt.lower():
                    final_prompt = f"Commercial product photoshoot of {product_description}. {final_prompt}"
            else:
                base_style = PHOTOSHOOT_PRESETS.get(style_preset, PHOTOSHOOT_PRESETS["minimal_studio"])
                if product_description and not image_bytes:
                    final_prompt = f"Commercial product photoshoot of {product_description}. {base_style}"
                else:
                    final_prompt = base_style

            config = gtypes.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=gtypes.ImageConfig(aspect_ratio="1:1"),
            )

            if image_bytes:
                part = gtypes.Part.from_bytes(data=image_bytes, mime_type=image_mime or "image/jpeg")
                contents = [part, final_prompt]
            else:
                contents = final_prompt

            # Run in executor to keep async loop non-blocking
            loop = self._get_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=contents,
                    config=config,
                ),
            )

            for p in response.parts:
                if p.inline_data and p.inline_data.data:
                    b64 = base64.b64encode(p.inline_data.data).decode("utf-8")
                    mime = p.inline_data.mime_type or "image/jpeg"
                    return f"data:{mime};base64,{b64}"

        except Exception as exc:
            logger.warning("Could not generate studio photo: %s", exc)

        return None

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
  "marketing_tip": "One specific actionable marketing and sales tip for Instagram/Telegram tailored to this product category (80-120 words)"
}}
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

        loop = self._get_loop()

        # Define text generation worker
        async def text_worker():
            resp = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=text_parts,
                    config=config,
                ),
            )
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
                )
            return None

        # Execute text analysis and photoshoot image generation concurrently!
        text_result, studio_photo_url = await asyncio.gather(text_worker(), photo_worker())

        # Ensure required keys exist
        for key in ("title", "description", "price_tag", "hashtags", "marketing_tip"):
            if key not in text_result:
                text_result[key] = ""

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
        if user_profile and user_profile.get("name"):
            name = user_profile.get("name", "").split()[0]
            greeting_ru = f"👤 Здравствуйте, {name}! С учётом вашего профиля:\n\n"
            greeting_uz = f"👤 Assalomu alaykum, {name}! Sizning profilingiz bo'yicha:\n\n"

        if lang == "uz":
            return (
                f"{greeting_uz}⚖️ **OqilaLegal — O'zbekiston qonunchiligi bo'yicha rasmiy maslahat (2026-yil tahriri)**\n\n"
                "📌 **1. O'z-o'zini band qilish (PQ-4742 va O'RQ-1108-son qonun):**\n"
                "• 2026-yil 1-yanvardan: yillik 1 mlrd so'mgacha aylanmaga **1% aylanmadan soliq** to'lanadi (100 mln so'mgacha 0% imtiyoz bekor qilingan).\n"
                "• Ijtimoiy soliq: pensiya staji uchun yiliga ixtiyoriy 1 BHM (440 000 so'm, SK 408-modda 2-qism).\n"
                "• ⚠️ **Uzum Market:** O'z-o'zini band qilganlar Uzum'da FAQAT o'zlari ishlab chiqargan buyumlarni sota oladi. Uzum soliq agenti sifatida 1% soliqni ushlab qoladi. Qayta sotish (Xitoy, bozor) QAT'IYAN TAQIQLANADI!\n"
                "• Bank hisobi: majburiy emas, shaxsiy Uzcard/Humo kartasiga qabul qilish mumkin.\n\n"
                "📌 **2. YaTT (Yakka tartibdagi tadbirkor — O'RQ-328-son qonun va O'RQ-1108):**\n"
                "• Tovar qayta sotish (Xitoy, ulgurji bozor) uchun YaTT OCHISH SHART!\n"
                "• **Yagona aylanmadan soliq stavkasi: 1%** (SK 467-modda 5-band, avvalgi 2% va 4% stavkalar bekor qilingan).\n"
                "• Majburiy ijtimoiy soliq: oyiga 1 BHM (440 000 so'm/oy, SK 408-modda 1-qism).\n"
                "• Bankda hisob raqam: fo.birdarcha.uz'da ro'yxatdan o'tgach, Kapitalbank, Anorbank yoki Ipotekabank orqali onlayn ochiladi (MB 3420-sonli Yo'riqnomasi).\n"
                "• Yillik tushum 1 mlrd so'mdan oshsa: majburiy 12% QQS va foyda solig'iga o'tiladi.\n\n"
                "📌 **3. Cheklar va to'lovlar (VMQ № 943 va SK 221-modda):**\n"
                "• Xaridorga Soliq ilovasi QR-cheki yoki Click/Payme integratsiyasi orqali fiskal chek berish shart.\n\n"
                "📱 Rasmiy xizmatlar: **fo.birdarcha.uz** | **my.soliq.uz** | **e-imzo.uz**"
            )
        return (
            f"{greeting_ru}⚖️ **OqilaLegal — Консультация по законодательству Узбекистана (ред. 2026 г.)**\n\n"
            "📌 **1. Самозанятость (ПП-4742 и Закон № ЗРУ-1108 с 01.01.2026 г.):**\n"
            "• С 1 января 2026 года для самозанятых действует **единая ставка налога с оборота 1%** с первого сума (льгота 0% до 100 млн сум отменена).\n"
            "• Соцналог для стажа: добровольно 1 БРВ в год (440 000 сум, ст. 408 ч. 2 НК РУз).\n"
            "• ⚠️ **Uzum Market:** Самозанятые могут продавать на Uzum ТОЛЬКО товары собственного производства (хэндмейд). Uzum удерживает 1% налога как налоговый агент. Перепродажа чужих товаров (Китай, опт) СТРОГО ЗАПРЕЩЕНА!\n"
            "• Расчётный счёт: не обязателен, выплаты принимаются на личную карту Uzcard/Humo.\n\n"
            "📌 **2. ЯТТ (Закон РУз № ЗРУ-328 и Налоговый кодекс ред. ЗРУ-1108):**\n"
            "• Для перепродажи товаров из Китая или оптовых рынков ОБЯЗАТЕЛЕН статус ЯТТ!\n"
            "• **Единая ставка налога с оборота: 1%** при доходе до 1 млрд сум (ст. 467 таблица ставок строка 5; прежние дифференцированные 2% и 4% отменены).\n"
            "• Обязательный соцналог: 1 БРВ в месяц (440 000 сум/мес, ст. 408 ч. 1 п. 1 НК РУз).\n"
            "• Расчётный счёт: открывается онлайн (Kapitalbank, Anor, Ipoteka) по Инструкции ЦБ № 3420 за 1–3 дня.\n"
            "• Порог 1 млрд сум: при превышении оборотный налог отменяется, обязателен переход на НДС 12% и налог на прибыль.\n\n"
            "📌 **3. Чеки и кассовая дисциплина (ПКМ № 943 и ст. 221 НК РУз):**\n"
            "• Онлайн-ККМ, приложение Soliq (QR-чек) или платежные сервисы Click/Payme формируют фискальные чеки автоматически.\n\n"
            "📱 Официальные сервисы: **fo.birdarcha.uz** | **my.soliq.uz** | **e-imzo.uz**"
        )



# Singleton instance
ai_service = AIService()
