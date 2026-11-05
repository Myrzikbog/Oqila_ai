"""
legal_calc.py — Kalkulyator va Soliq/Huquqiy qoidalar (O'zbekiston Respublikasi)
Финансово-налоговый калькулятор и официальная правовая база Республики Узбекистан (ред. 2026 г.).

Нормативно-правовая база (сверено с публикациями lex.uz, norma.uz, gov.uz/soliq — ноябрь 2026 г.):
1. Закон РУз № ЗРУ-1108 от 25.12.2025 г. (действует с 1 января 2026 г.):
   - ставка налога с оборота 1% для индивидуальных предпринимателей (ЯТТ) и самозанятых
     (закон установил её для годового дохода до 1 млрд сум);
   - отменено освобождение самозанятых от налога с оборота при доходе до 100 млн сум;
   - отменён налог с оборота в фиксированной сумме (ст. 470¹ НК утратила силу);
   - по доходам, полученным через цифровые платформы платёжных организаций, налог за самозанятых
     перечисляет платёжная организация как налоговый агент. Маркетплейс Uzum Market — комиссионер,
     налог с оборота продавец платит сам со всей суммы продажи (комиссия базу не уменьшает).

2. Указ Президента РУз № УП-100 от 26.05.2026 г. (с 1 июня 2026 г.):
   - предельный размер дохода для обязательного перехода на общеустановленный порядок
     (НДС и налог на прибыль) — 12 000 БРВ в год (≈5,28 млрд сум при БРВ 440 000 сум).

3. Самозанятость: ПП-4742 от 08.06.2020 г. и Указ № УП-50 от 19.03.2025 г.:
   - с 1 января 2026 г. перечень разрешённых видов деятельности сокращён со 104 до 72 пунктов;
   - обычная розничная торговля, парикмахерские, косметологические услуги, фото- и видеосъёмка исключены;
   - разрешена розничная продажа товаров (работ, услуг) на электронных торговых площадках (п. 33 перечня);
   - нанимать работников по трудовому договору нельзя.
   Сама площадка может ставить более строгие условия: по правилам Uzum самозанятые продают
   только товары собственного производства.

4. Налоговый кодекс РУз:
   - ст. 467 — ставки налога с оборота; ст. 470 — отчётный период месяц, уплата до 15 числа следующего месяца;
   - ст. 408 ч. 1 — социальный налог ЯТТ не менее 1 БРВ в месяц (до 15 числа текущего месяца);
   - ст. 408 ч. 2 — самозанятые добровольно платят не менее 1 БРВ в год для трудового стажа.

5. Регистрация и прочее:
   - Закон «О гарантиях свободы предпринимательской деятельности» (в ред. ЗРУ-328 от 02.05.2012 г.);
   - ПКМ № 66 от 09.02.2017 г. (государственная регистрация субъектов предпринимательства);
   - Закон № ЗРУ-793 от 12.10.2022 г. «Об электронной цифровой подписи»;
   - Закон № ЗРУ-792 от 29.09.2022 г. «Об электронной коммерции»;
   - Закон № ЗРУ-580 от 05.11.2019 г. «О банках и банковской деятельности»;
   - Инструкция ЦБ о порядке открытия, ведения и закрытия банковских счетов (рег. МЮ № 3420 от 08.02.2023 г.);
   - ПКМ № 943 от 23.11.2019 г. «О мерах по обеспечению применения онлайн-ККМ и системы виртуальной кассы»;
   - Закон № ЗРУ-578 от 01.11.2019 г. «О платежах и платежных системах».

БРВ = 440 000 сум с 1 сентября 2026 г. (Указ № УП-115 от 23.06.2026 г.).
Тарифы Uzum (комиссии, логистика) и эквайринга — коммерческие условия, а не нормы права;
в расчётах это ориентиры, актуальные значения — в кабинете продавца.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants — Uzbekistan Legal & Tax Rates (2026 г., ЗРУ-1108, УП-100)
# ---------------------------------------------------------------------------
BRV_UZS = 440_000                            # 1 БРВ = 440 000 сум с 01.09.2026 (УП-115 от 23.06.2026)

# Ставка налога с оборота для ЯТТ и самозанятых (ст. 467 НК в ред. ЗРУ-1108)
UNIFIED_TURNOVER_TAX_RATE = 0.01             # 1% налог с оборота для ИП и самозанятых
SELF_EMPLOYED_TAX_RATE = 0.01                # 1% налог с оборота (освобождение до 100 млн сум отменено с 01.01.2026)
TAX_RATE_TRADE_STANDARD = 0.01               # 1% налог с оборота для ЯТТ (до 1 млрд сум)
TAX_RATE_TRADE_ECOMMERCE = 0.01              # 1% налог с оборота для e-commerce / Uzum Market (до 1 млрд сум)
TAX_RATE_PRODUCTION_YATT = 0.01              # 1% производство и ремесла для ЯТТ
TAX_RATE_SERVICES_YATT = 0.01                # 1% сфера услуг для ЯТТ

# Порог обязательного перехода на НДС и налог на прибыль: 12 000 БРВ с 01.06.2026 (УП-100); до этого 1 млрд сум
GENERAL_REGIME_THRESHOLD_BRV = 12_000
ANNUAL_TURNOVER_LIMIT = GENERAL_REGIME_THRESHOLD_BRV * BRV_UZS   # ≈5,28 млрд сум
YATT_ANNUAL_TURNOVER_LIMIT = ANNUAL_TURNOVER_LIMIT
YATT_MANDATORY_SOCIAL_TAX = BRV_UZS          # 1 БРВ/месяц обязательно для ЯТТ (ст. 408 ч. 1)
SELF_EMPLOYED_PENSION_TAX = BRV_UZS          # 1 БРВ/год добровольно для самозанятых (ст. 408 ч. 2)

# Uzum Market category commissions: approximate commercial tariffs (not law), check the seller cabinet
UZUM_CATEGORY_RATES: Dict[str, Dict[str, Any]] = {
    "craft": {
        "rate": 0.12,
        "name_ru": "Ремесло и хэндмейд",
        "name_uz": "Hunarmandchilik va handmade",
        "label": "12%",
    },
    "clothing": {
        "rate": 0.14,
        "name_ru": "Одежда и текстиль",
        "name_uz": "Kiyim va to'qimachilik",
        "label": "14%",
    },
    "food": {
        "rate": 0.10,
        "name_ru": "Еда и сладости",
        "name_uz": "Oziq-ovqat va shirinliklar",
        "label": "10%",
    },
    "beauty": {
        "rate": 0.12,
        "name_ru": "Красота и косметика",
        "name_uz": "Go'zallik va parvarish",
        "label": "12%",
    },
    "decor": {
        "rate": 0.13,
        "name_ru": "Декор и сувениры",
        "name_uz": "Uy bezaklari va sovg'alar",
        "label": "13%",
    },
    "electronics": {
        "rate": 0.08,
        "name_ru": "Электроника и аксессуары (Китай)",
        "name_uz": "Elektronika va aksessuarlar",
        "label": "8%",
    },
    "other": {
        "rate": 0.15,
        "name_ru": "Стандартная категория (перепродажа)",
        "name_uz": "Standart toifa (qayta sotish)",
        "label": "15%",
    },
}

UZUM_LOGISTICS_BASE_UZS = 5_250              # 5 250 сум до 1 литра (Uzum Market)
PAYMENT_GATEWAY_RATE = 0.015                 # 1.5% эквайринг Click / Payme
DELIVERY_DIRECT_UZS = 25_000                 # 25 000 сум средняя курьерская доставка по городу (Yandex/BTS)


@dataclass
class CalcResult:
    sale_price: float
    cost_price: float
    gross_profit: float
    margin_pct: float
    # Business type and legality
    business_type: str                       # 'resale', 'production', 'services'
    self_employed_allowed: bool
    self_employed_warning_ru: str
    self_employed_warning_uz: str
    # Tax amounts
    tax_name: str
    tax_rate_effective_pct: float
    tax_payable_item: float                  # Точная сумма налога с этой единицы товара
    tax_payable_100: float                   # Сумма налога со 100 единиц
    social_tax_monthly: float                # Обязательный соцналог в месяц (440 000 сум для ЯТТ)
    # Self-employed mode (if allowed)
    self_employed_tax: float
    self_employed_net: float
    # YaTT mode (НК РУз ст. 467 & 408)
    yatt_type: str
    yatt_rate_pct: float
    yatt_turnover_tax: float
    yatt_social_tax_monthly: float
    yatt_net: float
    # Uzum Marketplace
    uzum_category: str
    uzum_category_name: str
    uzum_commission_rate: float
    uzum_commission_amount: float
    uzum_logistics_fee: float
    uzum_net: float
    min_price_uzum: float
    # Telegram / Instagram sales
    telegram_acquiring_fee: float
    telegram_net: float
    min_price_direct: float
    # Break-even analysis (if fixed costs provided)
    fixed_costs: float
    break_even_units_self: Optional[int]
    break_even_units_uzum: Optional[int]
    # Ratios for visual progress bar
    cost_share_pct: float
    tax_share_pct: float
    uzum_share_pct: float
    net_share_pct: float
    # China import hints
    china_import_tip_ru: str
    china_import_tip_uz: str
    # Compatibility
    tax_mode: str
    tax_amount: float
    net_profit: float
    tip_uz: str
    tip_ru: str


def calculate(
    sale_price: float,
    cost_price: float,
    lang: str = "ru",
    category: str = "craft",
    business_type: str = "resale",           # 'resale' (Китай/опт), 'production' (своё), 'services'
    trade_regime: str = "ecommerce",         # 'ecommerce' (1% маркетплейс), 'standard' (1% розница)
    yatt_type: str = "production",           # legacy fallback
    fixed_costs: float = 0.0,
) -> CalcResult:
    """
    Calculate profits, exact taxes under Uzbekistan Tax Code across business types.
    """
    if cost_price < 0:
        cost_price = 0.0
    if sale_price < 0:
        sale_price = 0.0

    gross_profit = sale_price - cost_price
    margin_pct = round((gross_profit / sale_price) * 100, 1) if sale_price > 0 else 0.0

    # 1. Определение налогового режима в зависимости от вида бизнеса:
    # -------------------------------------------------------------
    # А. Перепродажа товаров (Торговля из Китая, опт, маркетплейсы, розница):
    if business_type == "resale":
        self_employed_allowed = False
        self_employed_warning_ru = (
            "⚠️ С 1 января 2026 г. обычная розничная торговля исключена из перечня видов деятельности самозанятых "
            "(Указ № УП-50). Самозанятым разрешена только розничная продажа на электронных торговых площадках "
            "(п. 33 перечня), но Uzum по своим правилам допускает самозанятых лишь с товарами собственного производства. "
            "Для перепродажи (Китай, опт, рынок, магазин, Telegram) надёжнее открыть ЯТТ. "
            "Ставка налога с оборота для ЯТТ — 1% (ст. 467 НК, Закон № ЗРУ-1108)."
        )
        self_employed_warning_uz = (
            "⚠️ 2026-yil 1-yanvardan oddiy chakana savdo o'z-o'zini band qilganlar faoliyat turlari ro'yxatidan "
            "chiqarildi (PF-50-son Farmon). Ular faqat elektron savdo maydonchalarida chakana sotishi mumkin "
            "(ro'yxatning 33-bandi), biroq Uzum o'z qoidalariga ko'ra o'z-o'zini band qilganlarga faqat o'zi ishlab "
            "chiqargan mahsulotni sotishga ruxsat beradi. Qayta sotish (Xitoy, ulgurji, bozor, do'kon, Telegram) uchun "
            "YaTT ochish ishonchliroq. YaTT uchun aylanmadan soliq stavkasi — 1% (SK 467-modda, O'RQ-1108-son qonun)."
        )

        yatt_rate = UNIFIED_TURNOVER_TAX_RATE
        yatt_rate_pct = 1.0
        tax_name_ru = "Налог с оборота 1% (ст. 467 НК РУз, ЗРУ-1108)"  # resale
        tax_name_uz = "Aylanmadan soliq 1% (SK 467-modda, O'RQ-1108)"

        # Для сравнения считаем и вариант самозанятого (1%), хотя для перепродажи он ограничен
        self_employed_tax = round(sale_price * SELF_EMPLOYED_TAX_RATE, 0)
        self_employed_net = round(gross_profit - self_employed_tax, 0)

    # Б. Собственное производство / ремёсла / пошив:
    elif business_type == "production":
        self_employed_allowed = True
        self_employed_warning_ru = (
            "✅ Изделия собственного производства (ремёсла, текстиль, пошив, выпечка) — подходят для самозанятости, "
            "если ваш вид деятельности есть в перечне из 72 пунктов, действующем с 1 января 2026 г. (Указ № УП-50); "
            "проверьте его в приложении Soliq. Ставка налога с оборота — 1% (ст. 467 НК, Закон № ЗРУ-1108)."
        )
        self_employed_warning_uz = (
            "✅ O'zi ishlab chiqargan mahsulotlar (hunarmandchilik, to'qimachilik, tikuvchilik, pishiriqlar) o'z-o'zini band "
            "qilish uchun mos, agar faoliyat turingiz 2026-yil 1-yanvardan amal qiladigan 72 bandlik ro'yxatda bo'lsa "
            "(PF-50-son Farmon); uni Soliq ilovasida tekshiring. Aylanmadan soliq stavkasi — 1% (SK 467-modda, O'RQ-1108)."
        )
        yatt_rate = UNIFIED_TURNOVER_TAX_RATE
        yatt_rate_pct = 1.0
        tax_name_ru = "Единый налог с оборота 1% (ст. 467 НК РУз)"
        tax_name_uz = "Yagona aylanmadan soliq 1% (SK 467-modda)"
        self_employed_tax = round(sale_price * SELF_EMPLOYED_TAX_RATE, 0)
        self_employed_net = round(gross_profit - self_employed_tax, 0)

    # В. Услуги и сервис:
    else:
        self_employed_allowed = True
        self_employed_warning_ru = (
            "✅ Многие услуги доступны самозанятым, но с 1 января 2026 г. перечень сокращён до 72 видов (Указ № УП-50): "
            "например, парикмахерские, косметологические услуги, фото- и видеосъёмка из него исключены. "
            "Проверьте свой вид деятельности в приложении Soliq. Ставка налога с оборота — 1% с первого сума (ЗРУ-1108)."
        )
        self_employed_warning_uz = (
            "✅ Ko'plab xizmatlar o'z-o'zini band qilganlar uchun ochiq, biroq 2026-yil 1-yanvardan ro'yxat 72 turgacha "
            "qisqartirildi (PF-50-son Farmon): masalan, sartaroshlik, kosmetologiya, foto va videosuratga olish chiqarildi. "
            "Faoliyat turingizni Soliq ilovasida tekshiring. Aylanmadan soliq stavkasi — birinchi so'mdan 1% (O'RQ-1108)."
        )
        yatt_rate = UNIFIED_TURNOVER_TAX_RATE
        yatt_rate_pct = 1.0
        tax_name_ru = "Единый налог с оборота 1% (услуги)"
        tax_name_uz = "Yagona aylanmadan soliq 1% (xizmatlar)"
        self_employed_tax = round(sale_price * SELF_EMPLOYED_TAX_RATE, 0)
        self_employed_net = round(gross_profit - self_employed_tax, 0)

    # 2. Точный расчёт сумм налогов:
    # -----------------------------
    # Налог с оборота с одной единицы товара (1% по НК РУз ст. 467 ред. 2026 г.):
    yatt_turnover_tax = round(sale_price * yatt_rate, 0)
    tax_payable_item = yatt_turnover_tax
    tax_payable_100 = round(yatt_turnover_tax * 100, 0)
    yatt_net = round(gross_profit - yatt_turnover_tax, 0)

    # 3. Маркетплейс Uzum по категории товара:
    # ----------------------------------------
    cat_info = UZUM_CATEGORY_RATES.get(category, UZUM_CATEGORY_RATES["other"])
    uzum_rate = cat_info["rate"]
    uzum_category_name = cat_info["name_uz"] if lang == "uz" else cat_info["name_ru"]

    uzum_comm = round(sale_price * uzum_rate, 0)
    uzum_log = UZUM_LOGISTICS_BASE_UZS
    # Чистая прибыль на Uzum: Выручка − Себестоимость − Комиссия Uzum − Логистика Uzum − Налог с оборота 1%
    # (Uzum — комиссионер: налог продавец платит сам со всей суммы продажи, комиссия базу не уменьшает)
    uzum_tax = round(sale_price * UNIFIED_TURNOVER_TAX_RATE, 0)
    uzum_net = round(gross_profit - uzum_comm - uzum_log - uzum_tax, 0)

    # 4. Telegram / Instagram продажи (Click / Payme эквайринг 1.5%):
    # -------------------------------------------------------------
    telegram_fee = round(sale_price * PAYMENT_GATEWAY_RATE, 0)
    # Прибыль в Telegram: Выручка − Себестоимость − Эквайринг (1.5%) − Налог с оборота 1%
    telegram_net = round(gross_profit - telegram_fee - yatt_turnover_tax, 0)

    # 5. Минимальная безубыточная цена:
    # Uzum: (себестоимость + логистика) / (1 - комиссия - налог 1%)
    effective_uzum_deduction = uzum_rate + UNIFIED_TURNOVER_TAX_RATE
    min_price_uzum = round((cost_price + UZUM_LOGISTICS_BASE_UZS) / max(0.01, (1.0 - effective_uzum_deduction)), 0)
    min_price_direct = round(cost_price + DELIVERY_DIRECT_UZS, 0)

    # 6. Анализ точки безубыточности (Break-even):
    break_even_self = None
    break_even_uzum = None
    if fixed_costs > 0:
        if self_employed_net > 0 and self_employed_allowed:
            break_even_self = math.ceil(fixed_costs / self_employed_net)
        if uzum_net > 0:
            break_even_uzum = math.ceil(fixed_costs / uzum_net)

    # 7. Доли для визуальной диаграммы:
    if sale_price > 0:
        cost_share = round((cost_price / sale_price) * 100, 1)
        tax_share = round((yatt_turnover_tax / sale_price) * 100, 1)
        uzum_share = round(((uzum_comm + uzum_log) / sale_price) * 100, 1)
        net_share = max(0.0, round((uzum_net / sale_price) * 100, 1))
    else:
        cost_share = tax_share = uzum_share = net_share = 0.0

    # 8. Советы по импорту из Китая:
    china_import_tip_ru = (
        "🇨🇳 <b>Налоги и правила при заказе товаров из Китая для перепродажи:</b>\n"
        "• <b>Для перепродажи китайских товаров откройте ЯТТ или ООО:</b> обычная розничная торговля исключена из перечня самозанятых (УП-50), а Uzum принимает самозанятых только с товарами своего производства.\n"
        f"• <b>Налог с каждой продажи:</b> {yatt_turnover_tax:,.0f} сум (1% налог с оборота, ст. 467 НК РУз, ЗРУ-1108).\n"
        f"• <b>Соцналог ЯТТ:</b> не менее {BRV_UZS:,.0f} сум/мес (1 БРВ) независимо от объёма продаж (ст. 408 НК).\n"
        "• <b>Растаможка коммерческих партий:</b> НДС на импорт 12% + пошлина (по коду ТН ВЭД) + таможенный сбор.\n"
        "• <b>Порог 12 000 БРВ/год (≈5,28 млрд сум, УП-100):</b> при превышении — обязательный переход на НДС и налог на прибыль."
    )
    china_import_tip_uz = (
        "🇨🇳 <b>Xitoydan qayta sotish uchun tovar olib kirishdagi soliqlar va qoidalar:</b>\n"
        "• <b>Xitoy tovarlarini qayta sotish uchun YaTT yoki MChJ oching:</b> oddiy chakana savdo o'z-o'zini band qilganlar ro'yxatidan chiqarilgan (PF-50), Uzum esa ularni faqat o'z mahsuloti bilan qabul qiladi.\n"
        f"• <b>Har bir sotuvdan soliq:</b> {yatt_turnover_tax:,.0f} so'm (1% aylanmadan soliq, SK 467-modda, O'RQ-1108).\n"
        f"• <b>Oylik majburiy ijtimoiy soliq:</b> kamida {BRV_UZS:,.0f} so'm/oy (1 BHM, SK 408-modda).\n"
        "• <b>Tijorat partiyalarini bojxona rasmiylashtiruvi:</b> 12% import QQS + bojxona boji (TIF TN kodi bo'yicha) + bojxona yig'imi.\n"
        "• <b>12 000 BHM chegara (≈5,28 mlrd so'm, PF-100):</b> oshib ketsa — QQS va foyda solig'iga majburiy o'tiladi."
    )

    # Юридические подсказки со ссылками на законы РУз
    tip_ru = (
        f"⚖️ <b>Сводка налогов для вашего бизнеса ({tax_name_ru}):</b>\n\n"
        f"💰 <b>Налог с единицы товара:</b> <b>{tax_payable_item:,.0f} сум</b> (1% с выручки {sale_price:,.0f} сум).\n"
        f"📦 <b>Налог со 100 продаж:</b> <b>{tax_payable_100:,.0f} сум</b>.\n"
        f"🏛️ <b>Обязательный соцналог ЯТТ:</b> не менее <b>{BRV_UZS:,.0f} сум в месяц</b> (1 БРВ, ст. 408 НК РУз).\n"
        f"📅 <b>Сроки:</b> налог с оборота — ежемесячно до 15 числа следующего месяца (ст. 470 НК); соцналог ЯТТ — до 15 числа текущего месяца.\n"
        f"⚠️ <b>Порог 12 000 БРВ (≈5,28 млрд сум):</b> при доходе выше — переход на НДС и налог на прибыль (УП-100, с 01.06.2026).\n\n"
        + (china_import_tip_ru if business_type == "resale" else "")
    )
    tip_uz = (
        f"⚖️ <b>Biznesingiz bo'yicha soliq hisobi ({tax_name_uz}):</b>\n\n"
        f"💰 <b>Har bir donadan to'lanadigan soliq:</b> <b>{tax_payable_item:,.0f} so'm</b> (1% tushumdan {sale_price:,.0f} so'm).\n"
        f"📦 <b>100 ta sotuvdan soliq:</b> <b>{tax_payable_100:,.0f} so'm</b>.\n"
        f"🏛️ <b>YaTT majburiy ijtimoiy soliq:</b> kamida <b>{BRV_UZS:,.0f} so'm/oy</b> (1 BHM, SK 408-modda).\n"
        f"📅 <b>Muddatlar:</b> aylanmadan soliq — har oy keyingi oyning 15-sanasigacha (SK 470-modda); YaTT ijtimoiy solig'i — joriy oyning 15-sanasigacha.\n"
        f"⚠️ <b>12 000 BHM chegarasi (≈5,28 mlrd so'm):</b> daromad oshsa — QQS va foyda solig'iga o'tiladi (PF-100, 2026-yil 1-iyundan).\n\n"
        + (china_import_tip_uz if business_type == "resale" else "")
    )

    return CalcResult(
        sale_price=sale_price,
        cost_price=cost_price,
        gross_profit=round(gross_profit, 0),
        margin_pct=margin_pct,
        business_type=business_type,
        self_employed_allowed=self_employed_allowed,
        self_employed_warning_ru=self_employed_warning_ru,
        self_employed_warning_uz=self_employed_warning_uz,
        tax_name=tax_name_uz if lang == "uz" else tax_name_ru,
        tax_rate_effective_pct=yatt_rate_pct,
        tax_payable_item=tax_payable_item,
        tax_payable_100=tax_payable_100,
        social_tax_monthly=YATT_MANDATORY_SOCIAL_TAX,
        self_employed_tax=self_employed_tax,
        self_employed_net=self_employed_net,
        yatt_type=yatt_type,
        yatt_rate_pct=yatt_rate_pct,
        yatt_turnover_tax=yatt_turnover_tax,
        yatt_social_tax_monthly=YATT_MANDATORY_SOCIAL_TAX,
        yatt_net=yatt_net,
        uzum_category=category,
        uzum_category_name=uzum_category_name,
        uzum_commission_rate=uzum_rate,
        uzum_commission_amount=uzum_comm,
        uzum_logistics_fee=uzum_log,
        uzum_net=uzum_net,
        min_price_uzum=min_price_uzum,
        telegram_acquiring_fee=telegram_fee,
        telegram_net=telegram_net,
        min_price_direct=min_price_direct,
        fixed_costs=fixed_costs,
        break_even_units_self=break_even_self,
        break_even_units_uzum=break_even_uzum,
        cost_share_pct=cost_share,
        tax_share_pct=tax_share,
        uzum_share_pct=uzum_share,
        net_share_pct=net_share,
        china_import_tip_ru=china_import_tip_ru,
        china_import_tip_uz=china_import_tip_uz,
        tax_mode="yatt" if business_type == "resale" else "self_employed",
        tax_amount=tax_payable_item,
        net_profit=uzum_net if trade_regime == "ecommerce" else (yatt_net if business_type == "resale" else self_employed_net),
        tip_uz=tip_uz,
        tip_ru=tip_ru,
    )


# ---------------------------------------------------------------------------
# Legal steps reference data (100% compliant with Uzbek legislation)
# ---------------------------------------------------------------------------
LEGAL_STEPS_RU = [
    {
        "step": 1,
        "title": "Выбор формы: ЯТТ (торговля, перепродажа) или самозанятость (свои изделия и услуги)",
        "description": (
            "С 1 января 2026 г. самозанятые могут заниматься только видами деятельности из перечня в 72 пункта "
            "(Указ № УП-50 от 19.03.2025). Обычная розничная торговля, парикмахерские, косметологические услуги, "
            "фото- и видеосъёмка из него исключены; розничная продажа на электронных торговых площадках разрешена (п. 33). "
            "Если вы закупаете товар (Китай, опт, рынок) для перепродажи вне маркетплейсов — нужен ЯТТ или ООО."
        ),
        "link": "https://my.soliq.uz",
        "badge": "⚖️ ПП-4742 • УП-50",
    },
    {
        "step": 2,
        "title": "Онлайн-регистрация ЯТТ (fo.birdarcha.uz или my.gov.uz)",
        "description": (
            "ЯТТ регистрируется онлайн на fo.birdarcha.uz или my.gov.uz с ключом ЭЦП (Закон № ЗРУ-793). "
            "Выберите код ОКЭД (для интернет-торговли — 47.91). Госпошлина при онлайн-подаче — 0,9 БРВ (396 000 сум), "
            "в Центре госуслуг — 1 БРВ. Свидетельство формируется в личном кабинете (ПКМ № 66)."
        ),
        "link": "https://fo.birdarcha.uz",
        "badge": "🏢 ПКМ № 66 • birdarcha.uz",
    },
    {
        "step": 3,
        "title": "Продажи на Uzum Market: кто может продавать",
        "description": (
            "• ЯТТ и ООО продают любые разрешённые товары. "
            "• Самозанятых Uzum по своим правилам допускает только с товарами собственного производства (хэндмейд, пошив, выпечка). "
            "Регистрация — на seller.uzum.uz: документы и электронная оферта. Uzum работает как комиссионер, "
            "поэтому налог с оборота вы платите сами со всей суммы продажи."
        ),
        "link": "https://seller.uzum.uz",
        "badge": "🛍️ seller.uzum.uz",
    },
    {
        "step": 4,
        "title": "Банковский счёт: ЯТТ и самозанятые (Инструкция ЦБ, рег. № 3420)",
        "description": (
            "• ЯТТ обычно открывает расчётный счёт — он нужен для маркетплейсов и эквайринга; "
            "многие банки открывают его онлайн в бизнес-приложении. "
            "• Самозанятые, как правило, принимают оплату на личную карту Uzcard/Humo. "
            "Требования к конкретному счёту уточняйте в банке и у площадки."
        ),
        "link": "https://cbu.uz",
        "badge": "💳 Инструкция ЦБ № 3420",
    },
    {
        "step": 5,
        "title": "Налог с оборота 1% и соцналог (ЗРУ-1108, НК РУз)",
        "description": (
            "С 1 января 2026 г. ставка налога с оборота для ЯТТ и самозанятых — 1% (ст. 467 НК в ред. ЗРУ-1108). "
            "Налог считается со всей выручки, платится ежемесячно до 15 числа следующего месяца (ст. 470 НК). "
            "Соцналог: ЯТТ — не менее 1 БРВ (440 000 сум) в месяц, до 15 числа (ст. 408 ч. 1); "
            "самозанятые — добровольно не менее 1 БРВ в год для стажа (ст. 408 ч. 2). "
            "При доходе свыше 12 000 БРВ в год (≈5,28 млрд сум) — переход на НДС и налог на прибыль (УП-100, с 01.06.2026)."
        ),
        "link": "https://my.soliq.uz",
        "badge": "📊 НК РУз ст. 467, 470 • ЗРУ-1108",
    },
    {
        "step": 6,
        "title": "Фискальные чеки: онлайн-ККМ, виртуальная касса, Click/Payme (ПКМ № 943)",
        "description": (
            "По ПКМ № 943 от 23.11.2019 расчёты с покупателями сопровождаются фискальным чеком: "
            "онлайн-ККМ, виртуальная касса или электронный чек платёжной системы (Click, Payme). "
            "За торговлю без ККМ и невыдачу чека предусмотрены штрафы — уточните требования для своего вида деятельности на soliq.uz."
        ),
        "link": "https://soliq.uz",
        "badge": "🧾 ПКМ № 943 • Чеки",
    },
]

LEGAL_STEPS_UZ = [
    {
        "step": 1,
        "title": "Shaklni tanlash: YaTT (savdo, qayta sotish) yoki o'z-o'zini band qilish (o'z mahsuloti va xizmatlari)",
        "description": (
            "2026-yil 1-yanvardan o'z-o'zini band qilganlar faqat 72 bandlik ro'yxatdagi faoliyat turlari bilan shug'ullana oladi "
            "(PF-50-son Farmon, 19.03.2025). Oddiy chakana savdo, sartaroshlik, kosmetologiya xizmatlari, foto va videosuratga olish "
            "ro'yxatdan chiqarilgan; elektron savdo maydonchalarida chakana sotishga ruxsat berilgan (33-band). "
            "Agar tovarni (Xitoy, ulgurji, bozor) marketpleyslardan tashqarida qayta sotish uchun olsangiz — YaTT yoki MChJ kerak."
        ),
        "link": "https://my.soliq.uz",
        "badge": "⚖️ PQ-4742 • PF-50",
    },
    {
        "step": 2,
        "title": "YaTTni onlayn ro'yxatdan o'tkazish (fo.birdarcha.uz yoki my.gov.uz)",
        "description": (
            "YaTT fo.birdarcha.uz yoki my.gov.uz orqali ERI kaliti bilan onlayn ro'yxatdan o'tkaziladi (O'RQ-793-son qonun). "
            "IFUT kodini tanlang (internet savdo uchun — 47.91). Onlayn murojaatda davlat boji — 0,9 BHM (396 000 so'm), "
            "Davlat xizmatlari markazida — 1 BHM. Guvohnoma shaxsiy kabinetda shakllanadi (VMQ № 66)."
        ),
        "link": "https://fo.birdarcha.uz",
        "badge": "🏢 VMQ № 66 • birdarcha.uz",
    },
    {
        "step": 3,
        "title": "Uzum Market'da savdo: kim sota oladi",
        "description": (
            "• YaTT va MChJ ruxsat etilgan har qanday tovarni sotadi. "
            "• Uzum o'z qoidalariga ko'ra o'z-o'zini band qilganlarga faqat o'zi ishlab chiqargan mahsulotni (handmade, tikuvchilik, pishiriqlar) sotishga ruxsat beradi. "
            "Ro'yxatdan o'tish — seller.uzum.uz: hujjatlar va elektron oferta. Uzum komissioner sifatida ishlaydi, "
            "shuning uchun aylanmadan soliqni sotuvning to'liq summasidan o'zingiz to'laysiz."
        ),
        "link": "https://seller.uzum.uz",
        "badge": "🛍️ seller.uzum.uz",
    },
    {
        "step": 4,
        "title": "Bank hisobvarag'i: YaTT va o'z-o'zini band qilganlar (MB Yo'riqnomasi, ro'yxat № 3420)",
        "description": (
            "• YaTT odatda hisob-kitob hisobvarag'ini ochadi — u marketpleyslar va ekvayring uchun kerak; "
            "ko'plab banklar uni biznes-ilovada onlayn ochadi. "
            "• O'z-o'zini band qilganlar odatda to'lovni shaxsiy Uzcard/Humo kartasiga qabul qiladi. "
            "Aniq talablarni bank va savdo maydonchasidan so'rang."
        ),
        "link": "https://cbu.uz",
        "badge": "💳 MB 3420-sonli Yo'riqnoma",
    },
    {
        "step": 5,
        "title": "1% aylanmadan soliq va ijtimoiy soliq (O'RQ-1108, Soliq kodeksi)",
        "description": (
            "2026-yil 1-yanvardan YaTT va o'z-o'zini band qilganlar uchun aylanmadan soliq stavkasi — 1% (SK 467-modda, O'RQ-1108). "
            "Soliq butun tushumdan hisoblanadi va har oy keyingi oyning 15-sanasigacha to'lanadi (SK 470-modda). "
            "Ijtimoiy soliq: YaTT — oyiga kamida 1 BHM (440 000 so'm), 15-sanagacha (SK 408-modda 1-qism); "
            "o'z-o'zini band qilganlar — staj uchun ixtiyoriy ravishda yiliga kamida 1 BHM (408-modda 2-qism). "
            "Yillik daromad 12 000 BHMdan (≈5,28 mlrd so'm) oshsa — QQS va foyda solig'iga o'tiladi (PF-100, 2026-yil 1-iyundan)."
        ),
        "link": "https://my.soliq.uz",
        "badge": "📊 SK 467, 470 • O'RQ-1108",
    },
    {
        "step": 6,
        "title": "Fiskal cheklar: onlayn-NKM, virtual kassa, Click/Payme (VMQ № 943)",
        "description": (
            "VMQ № 943 (23.11.2019) ga ko'ra xaridor bilan hisob-kitobda fiskal chek beriladi: "
            "onlayn-NKM, virtual kassa yoki to'lov tizimining elektron cheki (Click, Payme). "
            "NKMsiz savdo va chek bermaslik uchun jarimalar nazarda tutilgan — talablarni soliq.uz saytida aniqlang."
        ),
        "link": "https://soliq.uz",
        "badge": "🧾 VMQ № 943 • Cheklar",
    },
]
