"""
ai_service.py — the AI pipeline of Oqila AI (Google Gemini).

What it does (every request goes through `_generate`: own thread pool, timeout, models from the environment,
each attempt counted in ai_calls):
  - the selling text of a product card (text model, from the photo and the seller's notes)
  - studio photos without text (image model, with a fallback model) and clean marketplace photos
  - pictures WITH text (information cards, posters, promos, stories): `render_card` draws, reads the text back,
    corrects only the wrong strings and never uses the fallback model; the server draws no text itself
  - the legal assistant (services/legal_ai.py) uses `_generate` from here too

Models: GEMINI_TEXT_MODEL / GEMINI_TEXT_FALLBACK_MODEL, GEMINI_IMAGE_MODEL / GEMINI_IMAGE_FALLBACK_MODEL,
GEMINI_VERIFY_MODEL (reads text from pictures), GEMINI_LEGAL_MODEL. Without a key, with AI_MODE=mock, over the daily
budget or on an error the answer is the built-in sample text flagged with `ai_fallback`; it is never saved as a card.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from services.copy_utils import default_copy
from services.imaging import finalize_card, to_data_url
from services.info_photo import (
    OCR_PROMPT,
    CopySpec,
    apply_slots,
    build_copy,
    build_edit_prompt,
    build_render_prompt,
    expected_strings,
    format_limits,
    parse_ocr,
    shorten_copy,
    verify_text,
)
from services.presets import ASPECTS, DEFAULT_ASPECT, STYLES_BY_ID, build_scene_prompt, model_aspect, style_kind

from services.rate_limit import record_ai_call

logger = logging.getLogger(__name__)

# Gemini calls are blocking HTTP requests: they get their own small pool instead of the default executor,
# so a burst of slow generations cannot starve everything else that uses run_in_executor.
AI_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="gemini")
MAX_IMAGE_CALLS = 3  # per rendered card: first picture + at most two corrections


def _mime(raw: bytes) -> str:
    return "image/png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else "image/webp" if raw[8:12] == b"WEBP" else "image/jpeg"


def _unique(models: List[str]) -> List[str]:
    return [m for i, m in enumerate(models) if m and m not in models[:i]]


def fallback_reason(exc: BaseException) -> str:
    """"quota" when Gemini refused because of limits or billing, otherwise "error"."""
    text = str(exc)
    return "quota" if any(k in text for k in ("RESOURCE_EXHAUSTED", "402", "429", "quota")) else "error"

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
    """Wraps the Google Gemini API; see the module docstring. Falls back to flagged sample data when the AI is
    unavailable (no key, AI_MODE=mock, budget spent, error)."""

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
        old_price: Optional[float] = None,
        brand: Optional[Dict[str, Any]] = None,
        logo: Optional[bytes] = None,
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
                old_price=old_price,
                brand=brand,
                logo=logo,
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
    # Internal: AI Studio Photoshoot Image Generation
    # -----------------------------------------------------------------------
    @staticmethod
    def _image_models() -> List[str]:
        """Primary image model, then a fallback: `gemini-3.1-flash-image` spells Russian/Uzbek text correctly,
        the older `gemini-2.5-flash-image` does not (it produced 'Безогсасная'), so it is only a safety net."""
        return _unique([os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
                        os.getenv("GEMINI_IMAGE_FALLBACK_MODEL", "gemini-2.5-flash-image")])

    async def _generate_image_bytes(self, contents: Any, aspect_ratio: str = DEFAULT_ASPECT, with_fallback: bool = True) -> Optional[bytes]:
        """Raw bytes of one generated picture (PNG/JPEG) or None.

        Photos without text may fall back to the older image model. Pictures WITH text may not
        (with_fallback=False): that model misspells Russian and Uzbek, and a wrong price is worse than no picture."""
        from google.genai import types as gtypes  # type: ignore

        config = gtypes.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=gtypes.ImageConfig(aspect_ratio=model_aspect(aspect_ratio)),
        )
        def picture(response: Any) -> Optional[bytes]:
            for part in response.parts or []:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
            return None

        try:
            models = self._image_models() if with_fallback else self._image_models()[:1]
            response = await self._generate("image", models, contents, config, accept=lambda r: picture(r) is not None)
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
                return to_data_url(finalize_card(raw, whiten=style_preset == "uzum_clean", size=ASPECTS["3:4"]["size"]))
            return "data:image/png;base64," + base64.b64encode(raw).decode("utf-8")

        except Exception as exc:
            logger.warning("Could not generate studio photo: %s", exc)

        return None

    # -----------------------------------------------------------------------
    # Pictures with text: the AI draws the text, a second AI call reads it back, mistakes are corrected
    # -----------------------------------------------------------------------
    async def read_image_text(self, image: bytes) -> List[List[str]]:
        """Text visible in a picture, read by a vision model, as blocks of lines."""
        from google.genai import types as gtypes  # type: ignore

        response = await self._generate(
            "ocr", self._ocr_models(),
            [gtypes.Part.from_bytes(data=image, mime_type=_mime(image)), OCR_PROMPT],
            gtypes.GenerateContentConfig(response_mime_type="application/json", temperature=0),
        )
        return parse_ocr(json.loads(response.text or "{}"))

    async def _verify_picture(self, image: bytes, expected: List[str]) -> Dict[str, Any]:
        """Check the text of a finished picture. If the reader fails it is tried once more; when it fails
        again the picture is returned unchecked (verified=None) and the seller is told so."""
        for attempt in (1, 2):
            try:
                return verify_text(await self.read_image_text(image), expected)
            except Exception as exc:
                logger.warning("Text check failed (attempt %s): %s", attempt, exc)
        return {"verified": None, "problems": [], "unexpected": []}

    async def render_card(
        self,
        copy: CopySpec,
        style: str,
        aspect: str,
        source: bytes,
        brand: Optional[Dict[str, Any]] = None,
        logo: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Draw one picture with text. At most MAX_IMAGE_CALLS image calls:
          1. generate; 2. read the text back and compare; 3. if something is wrong, ask the model to edit only the
          wrong strings on its own picture; 4. if the edit did not help, generate once more with a lighter copy.
        Returns {"photo": JPEG bytes or None, "copy": the copy that is on the picture, "verification", "image_calls"}.
        The server never draws text itself: if mistakes remain, the best picture is returned with
        verification.verified == False and the list of problems.
        """
        from google.genai import types as gtypes  # type: ignore

        loop = asyncio.get_running_loop()
        size = ASPECTS.get(aspect, ASPECTS["3:4"])["size"]
        spec = apply_slots(copy, style)
        refs = [gtypes.Part.from_bytes(data=source, mime_type=_mime(source))]
        if logo:
            refs.append(gtypes.Part.from_bytes(data=logo, mime_type=_mime(logo)))
        brand_info = {"brand_color": (brand or {}).get("brand_color"), "has_logo": bool(logo)}
        calls = 0

        async def attempt(contents: list, used: CopySpec) -> Optional[Dict[str, Any]]:
            nonlocal calls
            calls += 1
            raw = await self._generate_image_bytes(contents, aspect, with_fallback=False)
            if not raw:
                return None
            # The check runs on the finished picture (after the cut to the final size), not on the raw one
            final = await loop.run_in_executor(None, lambda: finalize_card(raw, size=size))
            check = await self._verify_picture(final, expected_strings(used))
            return {"raw": raw, "final": final, "check": check, "spec": used}

        def badness(item: Dict[str, Any]) -> int:
            return len(item["check"]["problems"])

        best = await attempt([*refs, build_render_prompt(spec, style, aspect, brand_info)], spec)
        if best is None:
            return {"photo": None, "copy": spec.to_dict(), "verification": {"verified": None, "problems": [], "unexpected": []},
                    "image_calls": calls}
        edit_helped = True
        while calls < MAX_IMAGE_CALLS and best["check"]["verified"] is False:
            if calls == 1 or edit_helped:
                # edit round-trip: the previous picture plus "replace X with exactly Y"
                before = badness(best)
                nxt = await attempt(
                    [gtypes.Part.from_bytes(data=best["raw"], mime_type=_mime(best["raw"])),
                     build_edit_prompt(best["check"]["problems"], spec.lang)],
                    best["spec"],
                )
                edit_helped = bool(nxt) and nxt["check"]["verified"] is not None and badness(nxt) < before
            else:
                # the edit did not help: one full regeneration with fewer, shorter strings
                lighter = shorten_copy(spec, style)
                nxt = await attempt([*refs, build_render_prompt(lighter, style, aspect, brand_info)], lighter)
            if nxt is None:
                continue
            if nxt["check"]["verified"] is None:
                break  # the reader is down: nothing more can be judged
            if nxt["check"]["verified"] or badness(nxt) < badness(best):
                best = nxt
        return {"photo": best["final"], "copy": best["spec"].to_dict(),
                "verification": dict(best["check"]), "image_calls": calls}

    async def fix_card_text(self, picture: bytes, problems: List[Dict[str, str]], copy: CopySpec, style: str, aspect: str) -> Dict[str, Any]:
        """One edit round-trip on an existing picture, asked for by the seller ("fix only the lettering")."""
        from google.genai import types as gtypes  # type: ignore

        loop = asyncio.get_running_loop()
        size = ASPECTS.get(aspect, ASPECTS["3:4"])["size"]
        spec = apply_slots(copy, style)
        raw = await self._generate_image_bytes(
            [gtypes.Part.from_bytes(data=picture, mime_type=_mime(picture)), build_edit_prompt(problems, spec.lang)],
            aspect, with_fallback=False,
        )
        if not raw:
            return {"photo": None, "copy": spec.to_dict(), "verification": {"verified": None, "problems": [], "unexpected": []}, "image_calls": 1}
        final = await loop.run_in_executor(None, lambda: finalize_card(raw, size=size))
        return {"photo": final, "copy": spec.to_dict(), "verification": await self._verify_picture(final, expected_strings(spec)), "image_calls": 1}

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
        old_price: Optional[float] = None,
        brand: Optional[Dict[str, Any]] = None,
        logo: Optional[bytes] = None,
    ) -> dict:
        from google.genai import types as gtypes  # type: ignore

        lim = format_limits(photoshoot_style)
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
    "title": "Plain descriptive product name for a picture heading: what it is plus one visible attribute, max {lim['title']} chars, no emoji, no quotes. NEVER invent a brand, collection or proper name",
    "tagline": "Two or three neutral words about the look or mood separated by ' · ', max {lim['subtitle']} chars, e.g. 'Нарядный · Яркий'. No superlatives, no quality claims",
    "benefits": ["3 or 4 very short benefits, max {lim['bullet']} chars each, 2-3 words"],
    "badge": "An empty string, unless the seller notes clearly support a short badge of max {lim['badge']} chars (e.g. 'Ручная работа' only if the seller says it is handmade)",
    "uses": ["up to 4 captions of 1-2 words, max {lim['use']} chars each, e.g. 'НА СТОЛ' / 'В ПОДАРОК'"]
  }}
}}

STRICT RULE for the "info" block: it is printed on a product photo, so it must contain ONLY facts that are clearly visible in
the image or stated in the seller's notes. Keep every string within its length limit: short text is drawn without mistakes.
NEVER invent sizes, weights, materials, certificates, guarantees, discounts, prices or any
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
            # A picture with text needs the text first, so text and picture run one after the other.
            text_result = await text_worker()
            if not isinstance(text_result, dict):
                raise ValueError("The text model did not return a JSON object")
            for key in ("title", "description", "price_tag", "marketing_tip"):
                if not isinstance(text_result.get(key), str):
                    text_result[key] = ""
            if not isinstance(text_result.get("hashtags"), list):
                text_result["hashtags"] = []
            suggestions = text_result.pop("info", None)
            defaults = default_copy(text_result, None, lang)
            if not isinstance(suggestions, dict):
                suggestions = {"benefits": defaults["bullets"]}
            # The price on the picture is the seller's form value only (never the AI's price_tag)
            copy = build_copy(suggestions, info_text, defaults["title"], lang, allowed_text=note,
                              price=desired_price, old_price=old_price, brand=brand)
            text_result["photoshoot_style"] = photoshoot_style
            text_result["aspect"] = aspect_ratio
            text_result["studio_photo_url"] = None
            text_result["verification"] = None
            text_result["copy"] = apply_slots(copy, photoshoot_style).to_dict()
            if generate_photo and image_bytes:
                rendered = await self.render_card(copy, photoshoot_style, aspect_ratio, image_bytes, brand=brand, logo=logo)
                text_result["copy"] = rendered["copy"]
                text_result["image_calls"] = rendered["image_calls"]
                if rendered["photo"]:
                    text_result["studio_photo_url"] = to_data_url(rendered["photo"])
                    text_result["verification"] = rendered["verification"]
                else:
                    text_result["render_error"] = "unavailable"  # honest: no picture, the text is still usable
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


# Singleton instance
ai_service = AIService()
