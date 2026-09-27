"""
legal_calc.py — Kalkulyator va Soliq/Huquqiy qoidalar (O'zbekiston Respublikasi)
Финансово-налоговый калькулятор и официальная правовая база Республики Узбекистан (2025–2026 гг.).

Нормативно-правовая база:
1. Постановление Президента РУз № ПП-4742 от 08.06.2020 г.
   «О мерах по упрощению государственного регулирования предпринимательской деятельности и самозанятости»:
   - 104 разрешённых вида деятельности для самозанятых лиц (включая ремёсла, пошив, кулинарию, личные услуги);
   - ⚠️ ВАЖНО: Торговля покупными товарами (перепродажа товаров из Китая, рынков «Абу Сахий»,
     оптовых баз и фабрик) СТРОГО ЗАПРЕЩЕНА в режиме самозанятости!
     Для любой перепродажи товаров закон требует регистрацию ЯТТ (индивидуального предпринимателя) или ООО (МЧЖ);
   - Для разрешённых видов доход до 100 млн сум в год НЕ облагается НДФЛ (налог 0%);
   - Запрещено нанимать работников по трудовому договору;
   - Самозанятые МОГУТ продавать на Uzum Market ТОЛЬКО изделия собственного производства.

2. Государственная регистрация предпринимательства:
   - Закон РУз от 02.05.2012 г. № ЗРУ-328 «О гарантиях свободы предпринимательской деятельности»;
   - Постановление Кабинета Министров РУз от 09.02.2017 г. № 66 (регистрация ЯТТ через fo.birdarcha.uz).

3. Налоговый кодекс Республики Узбекистан:
   - Статья 467, ч. 1, п. 1: Ставка налога с оборота для розничной торговли и услуг — 4%;
   - Статья 467, ч. 1, п. 3: Льготная ставка налога с оборота для участников электронной коммерции
     (Uzum Market, интернет-магазины, боты с онлайн-оплатой) — 2% (Закон № ЗРУ-792);
   - Статья 467, ч. 1, п. 5: Ставка налога с оборота для производителей отдельных товаров — 1%;
   - Статьи 237 & 461: Порог обязательного перехода на НДС (12%) — годовой оборот свыше 1 млрд сум;
   - Статья 408, ч. 1, п. 1: Социальный налог для ЯТТ — не менее 1 БРВ в месяц (440 000 сум/мес) ОБЯЗАТЕЛЬНО;
   - Статья 408, ч. 2: Социальный налог для самозанятых — не менее 1 БРВ в год (добровольно, для стажа);
   - Статья 221: Ответственность за нарушение порядка применения ККМ и фискальных чеков (ПКМ № 943).

4. Банковские счета:
   - Закон РУз от 05.11.2019 г. № ЗРУ-580 «О банках и банковской деятельности»;
   - Инструкция Центрального банка РУз о порядке открытия, ведения и закрытия банковских счетов (рег. МЮ № 3420 от 08.02.2023 г.).

5. Электронные платежи:
   - Закон РУз от 01.11.2019 г. № ЗРУ-578 «О платежах и платежных системах» (Click / Payme эквайринг 1.5%).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants — Uzbekistan Legal & Tax Rates (2025–2026)
# ---------------------------------------------------------------------------
BRV_UZS = 440_000                            # 1 БРВ (Базовая расчетная величина) = 440 000 сум
SELF_EMPLOYED_TAX_RATE = 0.00                # 0% НДФЛ до 100 млн сум (ПП-4742)
SELF_EMPLOYED_ANNUAL_LIMIT = 100_000_000     # 100 млн сум лимит для льготы 0%

# Ставки налога с оборота (НК РУз, ст. 467)
TAX_RATE_TRADE_STANDARD = 0.04               # 4% обычная розничная/оптовая торговля (ст. 467 п. 1)
TAX_RATE_TRADE_ECOMMERCE = 0.02              # 2% электронная торговля / маркетплейсы (ст. 467 п. 3)
TAX_RATE_PRODUCTION_YATT = 0.01              # 1% производство и ремесла для ЯТТ (ст. 467 п. 5)
TAX_RATE_SERVICES_YATT = 0.04                # 4% сфера услуг для ЯТТ (ст. 467 п. 1)

YATT_ANNUAL_TURNOVER_LIMIT = 1_000_000_000   # 1 млрд сум — порог обязательного НДС 12% (ст. 237, 461)
YATT_MANDATORY_SOCIAL_TAX = BRV_UZS          # 1 БРВ/месяц обязательно для ЯТТ (ст. 408 ч. 1)
SELF_EMPLOYED_PENSION_TAX = BRV_UZS          # 1 БРВ/год добровольно для самозанятых (ст. 408 ч. 2)

# Uzum Market Category Tariffs (ред. 2026 г.)
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
    trade_regime: str = "ecommerce",         # 'ecommerce' (2% маркетплейс), 'standard' (4% розница)
    yatt_type: str = "production",           # legacy fallback
    fixed_costs: float = 0.0,
) -> CalcResult:
    """
    Calculate profits, exact taxes under Uzbekistan Tax Code across business types.
    """
    if cost_price <= 0:
        cost_price = 1.0
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
            "⚠️ ВНИМАНИЕ: Перепродажа покупных товаров (в т.ч. из Китая, рынков «Абу Сахий», оптовиков) "
            "СТРОГО ЗАПРЕЩЕНА для самозанятых (ПП-4742)! Вы обязаны работать как ЯТТ или ООО. "
            "Ставка налога с оборота: 2% (электронная торговля Uzum/сайт) или 4% (стандартная торговля)."
        )
        self_employed_warning_uz = (
            "⚠️ DIQQAT: Xarid qilingan tovarlarni qayta sotish (jumladan Xitoy, Abu Saxiy yoki ulgurji bozorlardan) "
            "o'z-o'zini band qilgan shaxslar uchun QAT'IYAN TAQIQLANGAN (PQ-4742)! YaTT yoki MChJ ochish shart. "
            "Aylanmadan soliq stavkasi: 2% (e-tijorat / Uzum) yoki 4% (an'anaviy chakana savdo)."
        )

        if trade_regime == "standard":
            yatt_rate = TAX_RATE_TRADE_STANDARD
            yatt_rate_pct = 4.0
            tax_name_ru = "Налог с оборота (торговля) 4%"
            tax_name_uz = "Aylanmadan soliq (savdo) 4%"
        else:
            yatt_rate = TAX_RATE_TRADE_ECOMMERCE
            yatt_rate_pct = 2.0
            tax_name_ru = "Льготный налог e-commerce (Uzum/онлайн) 2%"
            tax_name_uz = "Imtiyozli e-tijorat solig'i (Uzum/onlayn) 2%"

        # Для самозанятого перепродажа не разрешена, но показываем теоретический 0 для сравнения
        self_employed_tax = 0.0
        self_employed_net = round(gross_profit, 0)

    # Б. Собственное производство / ремёсла / пошив:
    elif business_type == "production":
        self_employed_allowed = True
        self_employed_warning_ru = (
            "✅ Самозанятость РАЗРЕШЕНА: изготовление ремесленных изделий, национального текстиля, "
            "выпечки и пошива на заказ освобождено от налога на доход до 100 млн сум в год (ПП-4742)."
        )
        self_employed_warning_uz = (
            "✅ O'z-o'zini band qilishga RUXSAT ETILGAN: milliy hunarmandchilik, tikuvchilik va "
            "pazandachilik mahsulotlari yiliga 100 mln so'mgacha daromad solig'idan ozod etilgan (PQ-4742)."
        )
        yatt_rate = TAX_RATE_PRODUCTION_YATT
        yatt_rate_pct = 1.0
        tax_name_ru = "Льготный налог ЯТТ (производство) 1%"
        tax_name_uz = "YaTT imtiyozli aylanma solig'i (ishlab chiqarish) 1%"
        self_employed_tax = 0.0
        self_employed_net = round(gross_profit, 0)

    # В. Услуги и сервис:
    else:
        self_employed_allowed = True
        self_employed_warning_ru = (
            "✅ Самозанятость РАЗРЕШЕНА для 104 видов услуг (IT, дизайн, красота, репетиторство, ремонт). "
            "Доход до 100 млн сум/год — 0% налог (ПП-4742)."
        )
        self_employed_warning_uz = (
            "✅ 104 ta xizmat turi uchun o'z-o'zini band qilishga RUXSAT ETILGAN. "
            "Yiliga 100 mln so'mgacha daromad solig'i — 0% (PQ-4742)."
        )
        yatt_rate = TAX_RATE_SERVICES_YATT
        yatt_rate_pct = 4.0
        tax_name_ru = "Налог с оборота ЯТТ (услуги) 4%"
        tax_name_uz = "YaTT aylanma solig'i (xizmatlar) 4%"
        self_employed_tax = 0.0
        self_employed_net = round(gross_profit, 0)

    # 2. Точный расчёт сумм налогов:
    # -----------------------------
    # Налог с оборота с одной единицы товара:
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
    # Чистая прибыль на Uzum: Выручка − Себестоимость − Комиссия Uzum − Логистика Uzum − Налог с оборота (2% e-commerce)
    uzum_tax = round(sale_price * TAX_RATE_TRADE_ECOMMERCE, 0) if business_type == "resale" else yatt_turnover_tax
    uzum_net = round(gross_profit - uzum_comm - uzum_log - uzum_tax, 0)

    # 4. Telegram / Instagram продажи (Click / Payme эквайринг 1.5%):
    # -------------------------------------------------------------
    telegram_fee = round(sale_price * PAYMENT_GATEWAY_RATE, 0)
    # Прибыль в Telegram: Выручка − Себестоимость − Эквайринг (1.5%) − Налог с оборота
    telegram_net = round(gross_profit - telegram_fee - yatt_turnover_tax, 0)

    # 5. Минимальная безубыточная цена:
    # Uzum: (себестоимость + логистика) / (1 - комиссия - налог e-commerce)
    effective_uzum_deduction = uzum_rate + (TAX_RATE_TRADE_ECOMMERCE if business_type == "resale" else yatt_rate)
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
        "• <b>Самозанятость НЕЛЬЗЯ использовать</b> для торговли китайскими товарами — только ЯТТ или ООО!\n"
        f"• <b>Налог с каждой продажи:</b> {yatt_turnover_tax:,.0f} сум ({yatt_rate_pct:.0f}% налог с оборота).\n"
        f"• <b>Фиксированный соцналог:</b> {BRV_UZS:,.0f} сум/мес (1 БРВ) независимо от объёма продаж.\n"
        "• <b>Растаможка коммерческих партий:</b> НДС на импорт 12% + пошлина (0–20% по коду ТН ВЭД) + таможенный сбор.\n"
        "• <b>Порог 1 млрд сум/год:</b> при превышении оборотный налог отменяется, обязателен переход на НДС 12% и налог на прибыль 12%."
    )
    china_import_tip_uz = (
        "🇨🇳 <b>Xitoydan qayta sotish uchun tovar olib kirishdagi soliqlar va qoidalar:</b>\n"
        "• Xitoy tovarlarini sotishda <b>o'z-o'zini band qilish MUMKIN EMAS</b> — faqat YaTT yoki MChJ!\n"
        f"• <b>Har bir sotuvdan soliq:</b> {yatt_turnover_tax:,.0f} so'm ({yatt_rate_pct:.0f}% aylanmadan soliq).\n"
        f"• <b>Oylik majburiy ijtimoiy soliq:</b> {BRV_UZS:,.0f} so'm/oy (1 BHM).\n"
        "• <b>Tijorat partiyalarini bojxona rasmiylashtiruvi:</b> 12% QQS + bojxona boji (0–20%) + bojxona yig'imi.\n"
        "• <b>1 mlrd so'm chegara:</b> Yillik tushum 1 mlrd so'mdan oshsa, 12% QQS va 12% foyda solig'iga majburiy o'tiladi."
    )

    # Юридические подсказки со ссылками на законы РУз
    tip_ru = (
        f"⚖️ <b>Сводка налогов для вашего бизнеса ({tax_name_ru}):</b>\n\n"
        f"💰 <b>Налог с единицы товара:</b> <b>{tax_payable_item:,.0f} сум</b> ({yatt_rate_pct:.0f}% с выручки {sale_price:,.0f} сум).\n"
        f"📦 <b>Налог со 100 продаж:</b> <b>{tax_payable_100:,.0f} сум</b>.\n"
        f"🏛️ <b>Обязательный соцналог ЯТТ:</b> <b>{BRV_UZS:,.0f} сум в месяц</b> (1 БРВ, ст. 408 НК РУз).\n"
        f"⚠️ <b>Порог НДС 1 млрд сум:</b> При обороте свыше 1 млрд сум в год — переход на НДС 12% (ст. 237 НК РУз).\n\n"
        + (china_import_tip_ru if business_type == "resale" else "")
    )
    tip_uz = (
        f"⚖️ <b>Biznesingiz bo'yicha soliq hisobi ({tax_name_uz}):</b>\n\n"
        f"💰 <b>Har bir donadan to'lanadigan soliq:</b> <b>{tax_payable_item:,.0f} so'm</b> ({yatt_rate_pct:.0f}% tushumdan {sale_price:,.0f} so'm).\n"
        f"📦 <b>100 ta sotuvdan soliq:</b> <b>{tax_payable_100:,.0f} so'm</b>.\n"
        f"🏛️ <b>YaTT majburiy ijtimoiy soliq:</b> <b>{BRV_UZS:,.0f} so'm/oy</b> (1 BHM, SK 408-modda).\n"
        f"⚠️ <b>1 mlrd so'm QQS chegarasi:</b> Yillik aylanma 1 mlrd so'mdan oshganda 12% QQS to'lovchisi bo'lish shart (SK 237-modda).\n\n"
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
        "title": "Выбор формы: ЯТТ (для торговли/Китая) или Самозанятый (для хэндмейда/услуг)",
        "description": (
            "⚠️ Разделение по ПП-4742: если вы заказываете товары в Китае (1688, Taobao), на рынках или фабриках для перепродажи — "
            "закон категорически запрещает самозанятость! Необходима регистрация ЯТТ (или ООО). "
            "Самозанятость разрешена ИСКЛЮЧИТЕЛЬНО для изделий собственного изготовления (хэндмейд, пошив, кондитерка) "
            "и 104 видов личных услуг."
        ),
        "link": "https://my.soliq.uz",
        "badge": "⚖️ Разделение по ПП-4742",
    },
    {
        "step": 2,
        "title": "Онлайн регистрация ЯТТ за 15 минут (fo.birdarcha.uz)",
        "description": (
            "Регистрация индивидуального предпринимателя (ЯТТ) осуществляется онлайн на fo.birdarcha.uz или my.gov.uz. "
            "Понадобится ключ ЭЦП (Закон № ЗРУ-793). Выберите код ОКЭД (для интернет-торговли и Uzum — 47.91). "
            "Госпошлина при онлайн-оплате — 0.9 БРВ (со скидкой 10%). Свидетельство выдаётся мгновенно (ПКМ № 66)."
        ),
        "link": "https://fo.birdarcha.uz",
        "badge": "🏢 ПКМ № 66 • birdarcha.uz",
    },
    {
        "step": 3,
        "title": "Продажи на Uzum Market: кто и как может продавать (Закон № ЗРУ-792)",
        "description": (
            "• Самозанятые МОГУТ продавать на Uzum Market, но ТОЛЬКО товары собственного производства (хэндмейд, пошив, выпечка). "
            "• Для перепродажи любых покупных товаров (Китай, опт) ОБЯЗАТЕЛЕН статус ЯТТ или ООО. "
            "Для регистрации на seller.uzum.uz загружаются документы, подписывается оферта и Uzum добавляется в комиссионеры в my.soliq.uz."
        ),
        "link": "https://seller.uzum.uz",
        "badge": "🛍️ seller.uzum.uz",
    },
    {
        "step": 4,
        "title": "Открытие счёта в банке: ЯТТ vs Самозанятые (Инструкция ЦБ № 3420)",
        "description": (
            "• Для ЯТТ: открытие расчётного счёта (20208...) обязательно для маркетплейсов и эквайринга. "
            "Открывается онлайн через приложения Kapitalbank Business, Anorbank, Ipoteka, TBC за 1–3 дня. "
            "• Для самозанятых: отдельный расчётный счёт не нужен — выплаты от Uzum и клиентов поступают на личную карту Uzcard/Humo."
        ),
        "link": "https://kapitalbank.uz",
        "badge": "💳 Инструкция ЦБ № 3420",
    },
    {
        "step": 5,
        "title": "Налоги ЯТТ: 2% (Uzum) или 4% (розница) + 1 БРВ в месяц соцналог",
        "description": (
            "Налог с оборота уплачивается ежемесячно до 15-го числа (ст. 467 НК РУз): "
            "2% при электронной торговле (Uzum Market, интернет-магазины, боты) или 4% при традиционной торговле/услугах. "
            "Обязательный соцналог для ЯТТ: ровно 1 БРВ (440 000 сум) в месяц за себя (ст. 408). "
            "Порог перехода на НДС (12%) — годовой оборот свыше 1 млрд сум (ст. 237)."
        ),
        "link": "https://my.soliq.uz",
        "badge": "📊 НК РУз ст. 467, 408",
    },
    {
        "step": 6,
        "title": "Фискальные чеки и платежи: Click, Payme, Онлайн-ККМ (ПКМ № 943)",
        "description": (
            "По закону (ПКМ № 943) каждый расчет обязан сопровождаться фискальным чеком. "
            "Используйте бесплатный QR-чек в приложении «Soliq» со смартфона, либо подключите эквайринг Click Merchant / "
            "Payme Business (1.5%) — чеки формируются автоматически при каждой онлайн-оплате."
        ),
        "link": "https://click.uz",
        "badge": "🧾 ПКМ № 943 • Чеки",
    },
]

LEGAL_STEPS_UZ = [
    {
        "step": 1,
        "title": "Shaklni tanlash: YaTT (savdo/Xitoy uchun) yoki O'z-o'zini band qilish (handmade/xizmat)",
        "description": (
            "⚠️ PQ-4742 bo'yicha ajratish: agar siz tovarlarni Xitoydan (1688, Taobao), bozorlardan yoki fabrikalardan qayta sotish uchun olib kelsangiz — "
            "qonunchilik o'z-o'zini band qilishni qat'iyan taqiqlaydi! YaTT (yoki MChJ) ochish shart. "
            "O'z-o'zini band qilish FAQAT o'z mehnati bilan yaratilgan buyumlar (handmade, tikuvchilik, pazandachilik) "
            "va 104 ta xizmat turi uchun amal qiladi."
        ),
        "link": "https://my.soliq.uz",
        "badge": "⚖️ PQ-4742 bo'yicha ajratish",
    },
    {
        "step": 2,
        "title": "YaTTni 15 daqiqada onlayn ro'yxatdan o'tkazish (fo.birdarcha.uz)",
        "description": (
            "Yakka tartibdagi tadbirkorlik (YaTT) to'liq onlayn tarzda fo.birdarcha.uz yoki my.gov.uz orqali ochiladi. "
            "ERI kaliti kerak bo'ladi (O‘RQ-793-son qonun). Elektron savdo va Uzum uchun IFUT/OKED 47.91 kodini tanlang. "
            "Onlayn to'lovda davlat boji 10% chegirma bilan 0.9 BHMni tashkil etadi (VMQ № 66)."
        ),
        "link": "https://fo.birdarcha.uz",
        "badge": "🏢 VMQ № 66 • birdarcha.uz",
    },
    {
        "step": 3,
        "title": "Uzum Market'da sotuvlar: kim va qanday sota oladi (O‘RQ-792-son qonun)",
        "description": (
            "• O'z-o'zini band qilganlar Uzum Market'da sotuvchi bo'la oladi, ammo FAQAT o'zlari ishlab chiqargan buyumlarni sota oladi. "
            "• Xitoy yoki ulgurji tovarlarni qayta sotish uchun YaTT yoki MChJ maqomi SHART. "
            "seller.uzum.uz saytida ro'yxatdan o'tib, my.soliq.uz'da Uzum'ni komissioner sifatida qo'shish kerak."
        ),
        "link": "https://seller.uzum.uz",
        "badge": "🛍️ seller.uzum.uz",
    },
    {
        "step": 4,
        "title": "Bankda hisobvaraq ochish: YaTT vs O'z-o'zini band qilganlar (MB 3420-Yo'riqnoma)",
        "description": (
            "• YaTT uchun: 20208... hisobvarag'i ochish majburiy. Kapitalbank Business, Anorbank, Ipoteka, TBC ilovalarida 1-3 kunda onlayn ochiladi. "
            "• O'z-o'zini band qilganlar uchun: alohida hisob ochish shart emas — to'lovlar shaxsiy Uzcard/Humo kartasiga tushadi."
        ),
        "link": "https://kapitalbank.uz",
        "badge": "💳 MB 3420-sonli Yo'riqnomasi",
    },
    {
        "step": 5,
        "title": "YaTT soliqlari: 2% (Uzum) yoki 4% (savdo) + oyiga 1 BHM ijtimoiy soliq",
        "description": (
            "Aylanmadan soliq har oyning 15-sanasigacha to'lanadi (SK 467-modda): "
            "elektron tijoratda (Uzum, internet-do'kon, botlar) — 2%, an'anaviy savdoda — 4%. "
            "Oylik majburiy ijtimoiy soliq: qat'iy 1 BHM (440 000 so'm/oy, SK 408-modda). "
            "Yillik tushum 1 mlrd so'mdan oshsa — majburiy 12% QQS (SK 237-modda)."
        ),
        "link": "https://my.soliq.uz",
        "badge": "📊 SK 467, 408-moddalar",
    },
    {
        "step": 6,
        "title": "Fiskal cheklar va to'lovlar: Click, Payme, Onlayn-NKM (VMQ № 943)",
        "description": (
            "VMQ № 943-son qarorga ko'ra har bir savdoda xaridorga chek berilishi shart. "
            "«Soliq» ilovasidagi bepul QR-chekdan foydalaning yoki Click Merchant / Payme Business (1.5%) ulab oling — "
            "chek har bir onlayn to'lovda avtomatik tarzda shakllanadi."
        ),
        "link": "https://click.uz",
        "badge": "🧾 VMQ № 943 • Cheklar",
    },
]
