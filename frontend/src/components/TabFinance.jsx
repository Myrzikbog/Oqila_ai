import React, { useState, useEffect } from 'react';
import { 
  Calculator, 
  TrendingUp, 
  Percent, 
  Building2, 
  UserCheck, 
  ShoppingBag, 
  ShieldCheck, 
  CheckCircle2,
  Copy, 
  Check, 
  Target, 
  Send, 
  Info, 
  Layers, 
  AlertTriangle,
  Receipt,
  Coins,
  PackageCheck,
  Globe2,
  DollarSign,
  SlidersHorizontal,
  BarChart3,
  ArrowRightLeft,
  Star
} from 'lucide-react';
import { hapticImpact } from '../utils/telegram';

export default function TabFinance({ lang, t, profile, onOpenProfile }) {
  const [salePrice, setSalePrice] = useState('380000');
  const [costPrice, setCostPrice] = useState('120000');
  const [businessType, setBusinessType] = useState('resale'); // 'resale' (Китай/опт), 'production' (своё), 'services'
  const [tradeRegime, setTradeRegime] = useState('ecommerce'); // 'ecommerce' (2%), 'standard' (4%)
  const [category, setCategory] = useState('craft');
  const [fixedCosts, setFixedCosts] = useState('2500000');
  const [channelTab, setChannelTab] = useState('all'); // 'all', 'uzum', 'telegram', 'breakeven'
  const [calcData, setCalcData] = useState(null);
  const [copied, setCopied] = useState(false);

  // CBU Exchange rates state (Item 21)
  const [exchangeRates, setExchangeRates] = useState(null);
  const [showConverter, setShowConverter] = useState(false);
  const [convertVal, setConvertVal] = useState('10');
  const [convertCurrency, setConvertCurrency] = useState('USD');

  useEffect(() => {
    fetch('/api/exchange-rate')
      .then((res) => res.json())
      .then((data) => {
        if (data?.rates) setExchangeRates(data.rates);
      })
      .catch((err) => console.log('CBU fetch skipped:', err));
  }, []);

  // Sync settings when user profile is updated or loaded
  useEffect(() => {
    if (profile) {
      if (profile.status === 'self_employed') {
        setBusinessType('production');
      } else if (profile.status === 'yatt' && profile.category === 'resale') {
        setBusinessType('resale');
      }
      if (profile.salesChannel === 'uzum') {
        setTradeRegime('ecommerce');
      }
      if (profile.category === 'crafts') {
        setCategory('craft');
      } else if (profile.category === 'food') {
        setCategory('food');
      } else if (profile.category === 'sewing') {
        setCategory('clothing');
      }
    }
  }, [profile]);

  const fetchCalculation = async (sale, cost, bType, tRegime, cat, fCosts) => {
    try {
      const res = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sale_price: parseFloat(sale) || 0,
          cost_price: parseFloat(cost) || 0,
          lang,
          business_type: bType,
          trade_regime: tRegime,
          category: cat,
          fixed_costs: parseFloat(fCosts) || 0,
        }),
      });
      const data = await res.json();
      setCalcData(data);
    } catch (err) {
      console.error('Calculation error:', err);
    }
  };

  useEffect(() => {
    const sale = salePrice.replace(/\D/g, '');
    const cost = costPrice.replace(/\D/g, '');
    const fCosts = fixedCosts.replace(/\D/g, '');
    const timer = setTimeout(() => {
      fetchCalculation(sale, cost, businessType, tradeRegime, category, fCosts);
    }, 250);
    return () => clearTimeout(timer);
  }, [salePrice, costPrice, businessType, tradeRegime, category, fixedCosts, lang]);

  const formatMoney = (val) => {
    if (val === undefined || val === null) return '0';
    return Math.round(val).toLocaleString('ru-RU');
  };

  const handlePriceInput = (setter) => (e) => {
    hapticImpact('light');
    const raw = e.target.value.replace(/\D/g, '');
    setter(raw);
  };

  const copySummary = () => {
    if (!calcData) return;
    hapticImpact('medium');

    const text = lang === 'uz'
      ? `📊 Oqila AI — Moliyaviy va soliq tahlili:\n` +
        `💼 Faoliyat turi: ${businessType === 'resale' ? 'Qayta sotish (Xitoy/savdo)' : 'Ishlab chiqarish'}\n` +
        `💰 Sotish narxi: ${formatMoney(calcData.sale_price)} so'm\n` +
        `📦 Tannarx: ${formatMoney(calcData.cost_price)} so'm\n` +
        `───────────────\n` +
        `🏛️ Davlatga soliq: ${formatMoney(calcData.tax_payable_item)} so'm (${calcData.tax_rate_effective_pct}%)\n` +
        `📌 Oylik ijtimoiy soliq (YaTT): ${formatMoney(calcData.social_tax_monthly)} so'm/oy (1 BHM)\n` +
        `📈 Marjinallik: ${calcData.margin_pct}%\n` +
        `───────────────\n` +
        `🛍️ Uzum Market: Sof foyda ${formatMoney(calcData.uzum_net)} so'm (zararsiz min. narx: ${formatMoney(calcData.min_price_uzum)} so'm)\n` +
        `💬 Telegram (Click/Payme): Sof foyda ${formatMoney(calcData.telegram_net)} so'm\n` +
        `${!calcData.self_employed_allowed ? '⚠️ DIQQAT: Xitoy tovarlarini qayta sotishda o\'z-o\'zini band qilish taqiqlangan, faqat YaTT!' : ''}`
      : `📊 Oqila AI — Финансовый и налоговый анализ:\n` +
        `💼 Деятельность: ${businessType === 'resale' ? 'Перепродажа (Китай/опт)' : 'Собственное производство'}\n` +
        `💰 Цена реализации: ${formatMoney(calcData.sale_price)} сум\n` +
        `📦 Себестоимость: ${formatMoney(calcData.cost_price)} сум\n` +
        `───────────────\n` +
        `🏛️ Налог государству: ${formatMoney(calcData.tax_payable_item)} сум (${calcData.tax_rate_effective_pct}%)\n` +
        `📌 Обязательный соцналог (ЯТТ): ${formatMoney(calcData.social_tax_monthly)} сум/мес (1 БРВ)\n` +
        `📈 Маржинальность: ${calcData.margin_pct}%\n` +
        `───────────────\n` +
        `🛍️ Uzum Market: Чистая прибыль ${formatMoney(calcData.uzum_net)} сум (мин. цена: ${formatMoney(calcData.min_price_uzum)} сум)\n` +
        `💬 Telegram (Click/Payme): Чистая прибыль ${formatMoney(calcData.telegram_net)} сум\n` +
        `${!calcData.self_employed_allowed ? '⚠️ ВНИМАНИЕ: Для перепродажи товаров из Китая самозанятость ЗАПРЕЩЕНА (ПП-4742), обязателен ЯТТ!' : ''}`;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const categories = [
    { id: 'electronics', label: lang === 'uz' ? "Elektronika va aksessuarlar (Xitoy) (8%)" : "Электроника и аксессуары (Китай) (8%)" },
    { id: 'clothing', label: t.cat_clothing },
    { id: 'craft', label: t.cat_craft },
    { id: 'food', label: t.cat_food },
    { id: 'beauty', label: t.cat_beauty },
    { id: 'decor', label: t.cat_decor },
    { id: 'other', label: t.cat_other },
  ];

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="glass-card rounded-2xl p-4 border-l-4 border-l-teal-600 dark:border-l-teal-400 bg-gradient-to-r from-teal-50/60 via-white to-white dark:from-teal-950/30 dark:via-slate-900 dark:to-slate-900 transition-colors">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-brand-800 dark:text-teal-300">
            <Calculator className="w-5 h-5 text-brand-600 dark:text-teal-400 flex-shrink-0" />
            <h2 className="font-bold text-sm tracking-tight">{t.finance_title}</h2>
          </div>
          <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-300">
            {t.uzum_tariffs_badge || 'Тарифы 2026 г.'}
          </span>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
          {t.finance_subtitle}
        </p>
      </div>

      {/* CBU Exchange Rates & Converter Bar (Item 21) */}
      {exchangeRates && (
        <div className="glass-card rounded-2xl p-3 border border-amber-200/80 dark:border-amber-800/40 bg-gradient-to-r from-amber-50/50 via-white to-amber-50/20 dark:from-amber-950/20 dark:via-slate-900 dark:to-slate-900 shadow-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-amber-800 dark:text-amber-300">
              <Globe2 className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              <span>{t.cbu_rates_title || "Курсы ЦБ РУз"}</span>
            </div>
            <button
              type="button"
              onClick={() => {
                hapticImpact('light');
                setShowConverter(!showConverter);
              }}
              className="text-[11px] font-bold text-amber-700 dark:text-amber-400 hover:text-amber-900 flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-amber-100/70 dark:bg-amber-900/50"
            >
              <ArrowRightLeft className="w-3 h-3" />
              <span>{showConverter ? (lang === 'uz' ? "Yopish" : "Скрыть") : (lang === 'uz' ? "Valyuta kalkulyatori" : "Конвертер")}</span>
            </button>
          </div>

          <div className="flex items-center justify-between text-[11px] mt-2 pt-1 border-t border-amber-100 dark:border-amber-900/40">
            {['USD', 'EUR', 'CNY', 'RUB'].map((curr) => {
              const item = exchangeRates[curr];
              if (!item) return null;
              return (
                <div key={curr} className="flex flex-col items-center">
                  <span className="text-[10px] font-extrabold text-slate-500 dark:text-slate-400">{curr}</span>
                  <span className="font-extrabold text-slate-900 dark:text-white">
                    {Math.round(item.rate).toLocaleString('ru-RU')}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Quick Currency Converter Dropdown */}
          {showConverter && (
            <div className="mt-2.5 pt-2 border-t border-dashed border-amber-200 dark:border-amber-800/40 text-xs flex items-center space-x-2">
              <input
                type="tel"
                inputMode="numeric"
                value={convertVal}
                onChange={(e) => setConvertVal(e.target.value.replace(/\D/g, ''))}
                placeholder="10"
                className="w-20 px-2 py-1 rounded-lg border border-amber-300 dark:border-amber-700 text-xs bg-white dark:bg-slate-800 font-bold"
              />
              <select
                value={convertCurrency}
                onChange={(e) => setConvertCurrency(e.target.value)}
                className="px-2 py-1 rounded-lg border border-amber-300 dark:border-amber-700 text-xs bg-white dark:bg-slate-800 font-bold"
              >
                <option value="USD">USD ($)</option>
                <option value="CNY">CNY (¥)</option>
                <option value="EUR">EUR (€)</option>
                <option value="RUB">RUB (₽)</option>
              </select>
              <span className="text-slate-400 font-bold">=</span>
              <span className="font-extrabold text-brand-700 dark:text-teal-300 text-xs">
                {Math.round((parseFloat(convertVal) || 0) * (exchangeRates[convertCurrency]?.rate || 1)).toLocaleString('ru-RU')} {t.currency}
              </span>
            </div>
          )}
        </div>
      )}

      {/* User Profile Context Badge */}
      {profile && (
        <div className="flex items-center justify-between p-2.5 px-3.5 rounded-2xl bg-brand-50/80 dark:bg-teal-950/30 border border-brand-200/80 dark:border-teal-800/60 shadow-xs text-xs">
          <div className="flex items-center space-x-2 truncate">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
            <span className="font-bold text-slate-800 dark:text-slate-200 truncate">
              {profile.name} • {profile.status === 'self_employed' 
                ? (lang === 'uz' ? "O'z-o'zini band qilish (0%)" : "Самозанятая (0%)") 
                : profile.status === 'yatt'
                ? (lang === 'uz' ? "YaTT (1–4%)" : "ЯТТ (1–4%)")
                : (lang === 'uz' ? "Rejalashtirish" : "Выбор статуса")}
            </span>
          </div>
          <button
            type="button"
            onClick={onOpenProfile}
            className="text-[11px] font-bold text-brand-700 dark:text-teal-300 hover:text-brand-900 dark:hover:text-teal-100 underline decoration-dotted flex-shrink-0 ml-2"
          >
            {lang === 'uz' ? "O'zgartirish" : "Настроить"}
          </button>
        </div>
      )}

      {/* Business Model Selector */}
      <div className="glass-card rounded-2xl p-4 space-y-3 transition-colors border border-brand-200/60 dark:border-slate-800">
        <div>
          <label className="text-xs font-extrabold text-slate-900 dark:text-white flex items-center space-x-1.5 mb-1.5">
            <PackageCheck className="w-4 h-4 text-brand-600 dark:text-teal-400" />
            <span>{t.business_type_label}</span>
          </label>
          <select
            value={businessType}
            onChange={(e) => {
              hapticImpact('light');
              setBusinessType(e.target.value);
            }}
            className="w-full px-3 py-2.5 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-bold text-slate-900 dark:text-white"
          >
            <option value="resale">{t.btype_resale}</option>
            <option value="production">{t.btype_production}</option>
            <option value="services">{t.btype_services}</option>
          </select>
        </div>

        {/* If Resale (China / Trade), show Trade Regime toggle */}
        {businessType === 'resale' && (
          <div className="pt-1 space-y-2">
            <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block">
              {t.trade_regime_label}
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => { hapticImpact('light'); setTradeRegime('ecommerce'); }}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  tradeRegime === 'ecommerce'
                    ? 'border-brand-500 bg-brand-50/70 dark:bg-teal-950/40 text-brand-900 dark:text-teal-200 font-bold'
                    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400'
                }`}
              >
                <div className="text-xs font-bold flex items-center justify-between">
                  <span>Uzum / Онлайн</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-brand-600 text-white font-black">2%</span>
                </div>
                <div className="text-[10px] opacity-80 mt-0.5">Ст. 467 п. 3 НК РУз</div>
              </button>

              <button
                type="button"
                onClick={() => { hapticImpact('light'); setTradeRegime('standard'); }}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  tradeRegime === 'standard'
                    ? 'border-brand-500 bg-brand-50/70 dark:bg-teal-950/40 text-brand-900 dark:text-teal-200 font-bold'
                    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400'
                }`}
              >
                <div className="text-xs font-bold flex items-center justify-between">
                  <span>Магазин / Розница</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-600 text-white font-black">4%</span>
                </div>
                <div className="text-[10px] opacity-80 mt-0.5">Ст. 467 п. 1 НК РУз</div>
              </button>
            </div>
          </div>
        )}

        {/* Input Prices */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div>
            <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block mb-1">
              {t.calc_cost_price}
            </label>
            <div className="relative">
              <input
                type="tel"
                inputMode="numeric"
                value={formatMoney(costPrice)}
                onChange={handlePriceInput(setCostPrice)}
                className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-bold text-slate-900 dark:text-white"
              />
              <span className="absolute right-2.5 top-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase">
                {t.currency}
              </span>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block mb-1">
              {t.calc_sale_price}
            </label>
            <div className="relative">
              <input
                type="tel"
                inputMode="numeric"
                value={formatMoney(salePrice)}
                onChange={handlePriceInput(setSalePrice)}
                className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-bold text-slate-900 dark:text-white"
              />
              <span className="absolute right-2.5 top-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase">
                {t.currency}
              </span>
            </div>
          </div>
        </div>

        {/* Interactive Price Slider Scenario (Item 13) */}
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/60 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-bold">
            <span className="text-slate-700 dark:text-slate-300 flex items-center space-x-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5 text-brand-600 dark:text-teal-400" />
              <span>{t.price_slider_title}</span>
            </span>
            <span className="text-brand-700 dark:text-teal-300 font-extrabold">
              {formatMoney(salePrice)} {t.currency}
            </span>
          </div>
          <input
            type="range"
            min={Math.max(10000, Math.round((parseFloat(costPrice) || 0) * 0.5))}
            max={Math.max(1500000, (parseFloat(costPrice) || 120000) * 4)}
            step="5000"
            value={parseFloat(salePrice) || 0}
            onChange={(e) => {
              hapticImpact('light');
              setSalePrice(e.target.value);
            }}
            className="w-full accent-teal-600 cursor-pointer h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg"
          />
          <div className="flex justify-between text-[9px] font-semibold text-slate-400">
            <span>Мин: {formatMoney(Math.max(10000, Math.round((parseFloat(costPrice) || 0) * 0.5)))}</span>
            <span>Макс: {formatMoney(Math.max(1500000, (parseFloat(costPrice) || 120000) * 4))}</span>
          </div>
        </div>

        {/* Category selector for Uzum */}
        <div>
          <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block mb-1">
            {t.category_label}
          </label>
          <select
            value={category}
            onChange={(e) => {
              hapticImpact('light');
              setCategory(e.target.value);
            }}
            className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-semibold text-slate-900 dark:text-white"
          >
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Channel Navigation Pills */}
        <div className="pt-1">
          <div className="grid grid-cols-4 gap-1.5 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200/60 dark:border-slate-700/60 text-center">
            <button
              type="button"
              onClick={() => { hapticImpact('light'); setChannelTab('all'); }}
              className={`py-1.5 text-[11px] font-bold rounded-lg transition-all ${
                channelTab === 'all'
                  ? 'bg-white dark:bg-slate-700 text-brand-800 dark:text-teal-300 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800'
              }`}
            >
              {t.channel_tab_all}
            </button>
            <button
              type="button"
              onClick={() => { hapticImpact('light'); setChannelTab('uzum'); }}
              className={`py-1.5 text-[11px] font-bold rounded-lg transition-all ${
                channelTab === 'uzum'
                  ? 'bg-white dark:bg-slate-700 text-brand-800 dark:text-teal-300 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800'
              }`}
            >
              {t.channel_tab_uzum}
            </button>
            <button
              type="button"
              onClick={() => { hapticImpact('light'); setChannelTab('telegram'); }}
              className={`py-1.5 text-[11px] font-bold rounded-lg transition-all ${
                channelTab === 'telegram'
                  ? 'bg-white dark:bg-slate-700 text-brand-800 dark:text-teal-300 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800'
              }`}
            >
              {t.channel_tab_telegram}
            </button>
            <button
              type="button"
              onClick={() => { hapticImpact('light'); setChannelTab('breakeven'); }}
              className={`py-1.5 text-[11px] font-bold rounded-lg transition-all ${
                channelTab === 'breakeven'
                  ? 'bg-white dark:bg-slate-700 text-brand-800 dark:text-teal-300 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800'
              }`}
            >
              {t.channel_tab_breakeven}
            </button>
          </div>
        </div>
      </div>

      {/* CRITICAL: High-Level Metrics including TAX PAYABLE */}
      {calcData && (
        <div className="grid grid-cols-2 gap-2.5">
          {/* Card 1: Валовая прибыль */}
          <div className="glass-card rounded-2xl p-3 border border-emerald-200/80 dark:border-emerald-800/40 bg-gradient-to-br from-emerald-50/50 to-white dark:from-emerald-950/20 dark:to-slate-900">
            <div className="flex items-center justify-between text-emerald-700 dark:text-emerald-400">
              <span className="text-[11px] font-bold tracking-tight">{t.metric_gross}</span>
              <TrendingUp className="w-4 h-4" />
            </div>
            <div className="text-base font-extrabold text-slate-900 dark:text-white mt-1">
              {formatMoney(calcData.gross_profit)} <span className="text-[10px] font-semibold text-slate-500">{t.currency}</span>
            </div>
          </div>

          {/* Card 2: НАЛОГ К УПЛАТЕ (ЧЕТКО И ВИДИМО) */}
          <div className="glass-card rounded-2xl p-3 border border-red-200 dark:border-red-900/40 bg-gradient-to-br from-red-50/50 to-white dark:from-red-950/20 dark:to-slate-900">
            <div className="flex items-center justify-between text-red-600 dark:text-red-400">
              <span className="text-[11px] font-bold tracking-tight">{t.kpi_tax_payable}</span>
              <Receipt className="w-4 h-4" />
            </div>
            <div className="text-base font-extrabold text-red-600 dark:text-red-400 mt-1">
              {formatMoney(calcData.tax_payable_item)} <span className="text-[10px] font-semibold">{t.currency}</span>
              <span className="ml-1 text-[10px] px-1.5 py-0.2 rounded bg-red-100 dark:bg-red-900/60 text-red-700 dark:text-red-300 font-bold">
                {calcData.tax_rate_effective_pct}%
              </span>
            </div>
          </div>

          {/* Card 3: Чистая прибыль на Uzum */}
          <div className="glass-card rounded-2xl p-3 border border-brand-200/80 dark:border-teal-800/40 bg-gradient-to-br from-teal-50/50 to-white dark:from-teal-950/20 dark:to-slate-900">
            <div className="flex items-center justify-between text-brand-700 dark:text-teal-400">
              <span className="text-[11px] font-bold tracking-tight">{t.kpi_net_profit} (Uzum)</span>
              <Coins className="w-4 h-4" />
            </div>
            <div className="text-base font-extrabold text-brand-900 dark:text-teal-200 mt-1">
              {formatMoney(calcData.uzum_net)} <span className="text-[10px] font-semibold text-slate-500">{t.currency}</span>
            </div>
          </div>

          {/* Card 4: Маржинальность */}
          <div className="glass-card rounded-2xl p-3 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
              <span className="text-[11px] font-bold tracking-tight">{t.metric_margin}</span>
              <Percent className="w-4 h-4 text-brand-600 dark:text-teal-400" />
            </div>
            <div className="text-base font-extrabold text-slate-900 dark:text-white mt-1">
              {calcData.margin_pct}%
            </div>
          </div>
        </div>
      )}

      {/* Visual Revenue Distribution Segmented Bar (Item 12) */}
      {calcData && (
        <div className="glass-card rounded-2xl p-4 border border-brand-200/60 dark:border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-1.5">
              <BarChart3 className="w-4 h-4 text-brand-600 dark:text-teal-400" />
              <span>{t.distribution_title}</span>
            </span>
            <span className="text-[10px] font-bold text-slate-500">100% = {formatMoney(calcData.sale_price)} {t.currency}</span>
          </div>

          {/* Segmented bar */}
          <div className="h-3 w-full rounded-full overflow-hidden flex bg-slate-100 dark:bg-slate-800 shadow-inner">
            <div style={{ width: `${Math.min(100, Math.max(0, calcData.cost_share_pct))}%` }} className="bg-slate-400 dark:bg-slate-500 h-full" title="Tannarx" />
            <div style={{ width: `${Math.min(100, Math.max(0, calcData.tax_share_pct))}%` }} className="bg-rose-500 h-full" title="Soliq" />
            <div style={{ width: `${Math.min(100, Math.max(0, calcData.uzum_share_pct))}%` }} className="bg-purple-500 h-full" title="Uzum" />
            <div style={{ width: `${Math.min(100, Math.max(0, calcData.net_share_pct))}%` }} className="bg-emerald-500 h-full" title="Sof foyda" />
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 text-[10px] font-semibold text-slate-600 dark:text-slate-300 pt-1">
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-slate-400 dark:bg-slate-500 flex-shrink-0" />
              <span className="truncate">{t.calc_cost_price}: <b className="text-slate-900 dark:text-white">{calcData.cost_share_pct}%</b></span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-rose-500 flex-shrink-0" />
              <span className="truncate">{t.kpi_tax_payable}: <b className="text-slate-900 dark:text-white">{calcData.tax_share_pct}%</b></span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-purple-500 flex-shrink-0" />
              <span className="truncate">Uzum harajati: <b className="text-slate-900 dark:text-white">{calcData.uzum_share_pct}%</b></span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 flex-shrink-0" />
              <span className="truncate">{t.kpi_net_profit}: <b className="text-emerald-600 dark:text-emerald-400">{calcData.net_share_pct}%</b></span>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Channel Comparison Matrix (Item 14) */}
      {calcData && (
        <div className="glass-card rounded-2xl p-4 border border-brand-200/60 dark:border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-1.5">
              <TrendingUp className="w-4 h-4 text-brand-600 dark:text-teal-400" />
              <span>{t.channel_compare_title}</span>
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            {/* Column 1: Direct / Showroom */}
            {(() => {
              const directNet = Math.max(0, calcData.sale_price - calcData.cost_price - calcData.tax_payable_item);
              const isBest = directNet >= calcData.uzum_net && directNet >= calcData.telegram_net;
              return (
                <div className={`p-2.5 rounded-xl border relative flex flex-col justify-between ${
                  isBest 
                    ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/30 ring-1 ring-emerald-500/30' 
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900'
                }`}>
                  {isBest && (
                    <span className="absolute -top-2 left-1/2 -translate-x-1/2 px-1.5 py-0.2 rounded-full bg-emerald-600 text-[8px] font-black text-white whitespace-nowrap">
                      TOP 1
                    </span>
                  )}
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 dark:text-slate-400 truncate">Do'kon / Direct</div>
                    <div className="text-[9px] text-slate-400 mt-0.5">0% komissiya</div>
                  </div>
                  <div className="mt-2">
                    <span className="font-black text-xs text-emerald-700 dark:text-emerald-300 block">
                      {formatMoney(directNet)}
                    </span>
                    <span className="text-[8px] text-slate-400">{t.currency}</span>
                  </div>
                </div>
              );
            })()}

            {/* Column 2: Telegram / Instagram */}
            {(() => {
              const directNet = Math.max(0, calcData.sale_price - calcData.cost_price - calcData.tax_payable_item);
              const isBest = calcData.telegram_net > directNet && calcData.telegram_net >= calcData.uzum_net;
              return (
                <div className={`p-2.5 rounded-xl border relative flex flex-col justify-between ${
                  isBest 
                    ? 'border-sky-500 bg-sky-50/50 dark:bg-sky-950/30 ring-1 ring-sky-500/30' 
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900'
                }`}>
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 dark:text-slate-400 truncate">Telegram / Insta</div>
                    <div className="text-[9px] text-slate-400 mt-0.5">1.5% ekvayring</div>
                  </div>
                  <div className="mt-2">
                    <span className="font-black text-xs text-sky-700 dark:text-sky-300 block">
                      {formatMoney(calcData.telegram_net)}
                    </span>
                    <span className="text-[8px] text-slate-400">{t.currency}</span>
                  </div>
                </div>
              );
            })()}

            {/* Column 3: Uzum Market */}
            {(() => {
              const isBest = calcData.uzum_net >= calcData.telegram_net && calcData.uzum_net >= (calcData.sale_price - calcData.cost_price - calcData.tax_payable_item);
              return (
                <div className={`p-2.5 rounded-xl border relative flex flex-col justify-between ${
                  isBest 
                    ? 'border-purple-500 bg-purple-50/50 dark:bg-purple-950/30 ring-1 ring-purple-500/30' 
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900'
                }`}>
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 dark:text-slate-400 truncate">Uzum Market</div>
                    <div className="text-[9px] text-slate-400 mt-0.5">Komissiya + logistika</div>
                  </div>
                  <div className="mt-2">
                    <span className="font-black text-xs text-purple-700 dark:text-purple-300 block">
                      {formatMoney(calcData.uzum_net)}
                    </span>
                    <span className="text-[8px] text-slate-400">{t.currency}</span>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* DEDICATED TAX BREAKDOWN CARD */}
      {calcData && (
        <div className="glass-card rounded-2xl p-4 border border-red-200/80 dark:border-red-900/40 shadow-sm space-y-3 bg-gradient-to-b from-white via-red-50/20 to-white dark:from-slate-900 dark:via-red-950/10 dark:to-slate-900">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-lg bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 flex items-center justify-center">
                <Receipt className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-xs text-slate-900 dark:text-white">{t.tax_summary_title}</h3>
                <span className="text-[10px] text-slate-500 dark:text-slate-400">{calcData.tax_name}</span>
              </div>
            </div>
            <span className="text-[11px] font-extrabold px-2.5 py-0.5 rounded-full bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300">
              {calcData.tax_rate_effective_pct}% Soliq
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
            <div>
              <span className="text-slate-500 dark:text-slate-400 block text-[11px]">{t.tax_per_item}</span>
              <span className="font-black text-red-600 dark:text-red-400 text-sm">
                {formatMoney(calcData.tax_payable_item)} {t.currency}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block text-[11px]">{t.tax_per_100}</span>
              <span className="font-black text-slate-900 dark:text-white text-sm">
                {formatMoney(calcData.tax_payable_100)} {t.currency}
              </span>
            </div>
          </div>

          {/* Social Tax Fixed Monthly */}
          <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800/70 border border-slate-200/70 dark:border-slate-700 flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <Building2 className="w-4 h-4 text-brand-600 dark:text-teal-400 flex-shrink-0" />
              <span className="font-semibold text-slate-700 dark:text-slate-300">{t.social_tax_fixed_monthly}</span>
            </div>
            <span className="font-black text-slate-900 dark:text-white">
              {formatMoney(calcData.social_tax_monthly)} {t.currency} <span className="text-[10px] font-normal text-slate-500">{t.per_month}</span>
            </span>
          </div>

          {/* Self-Employed Legality Callout */}
          <div className={`p-2.5 rounded-xl border flex items-start space-x-2 text-[11px] leading-relaxed ${
            calcData.self_employed_allowed
              ? 'bg-emerald-50/60 dark:bg-emerald-950/30 border-emerald-200 text-emerald-800 dark:text-emerald-300'
              : 'bg-amber-50/80 dark:bg-amber-950/40 border-amber-300 text-amber-900 dark:text-amber-200'
          }`}>
            {calcData.self_employed_allowed ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <div className="font-bold mb-0.5">
                {t.self_employed_status_label}{' '}
                <span className={calcData.self_employed_allowed ? 'text-emerald-700 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-400'}>
                  {calcData.self_employed_allowed ? t.status_allowed : t.status_forbidden}
                </span>
              </div>
              <p className="text-[10px] opacity-90">{calcData.self_employed_warning}</p>
            </div>
          </div>
        </div>
      )}

      {/* Visual Revenue Breakdown Progress Bar */}
      {calcData && calcData.sale_price > 0 && (
        <div className="glass-card rounded-2xl p-3.5 space-y-2 border border-slate-200/70 dark:border-slate-800">
          <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
            <span className="flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
              <span>{t.breakdown_title}</span>
            </span>
            <span className="text-[11px] font-semibold text-slate-500">100%</span>
          </div>

          {/* Bar */}
          <div className="w-full h-3 rounded-full overflow-hidden flex bg-slate-100 dark:bg-slate-800">
            <div 
              style={{ width: `${Math.min(100, calcData.cost_share_pct)}%` }} 
              className="bg-amber-400 dark:bg-amber-500 transition-all duration-300"
              title={`${t.breakdown_cost}: ${calcData.cost_share_pct}%`}
            />
            <div 
              style={{ width: `${Math.min(100 - calcData.cost_share_pct, calcData.tax_share_pct)}%` }} 
              className="bg-red-500 dark:bg-red-400 transition-all duration-300"
              title={`Налог: ${calcData.tax_share_pct}%`}
            />
            <div 
              style={{ width: `${Math.min(100 - calcData.cost_share_pct - calcData.tax_share_pct, calcData.uzum_share_pct)}%` }} 
              className="bg-purple-500 dark:bg-purple-400 transition-all duration-300"
              title={`${t.breakdown_uzum}: ${calcData.uzum_share_pct}%`}
            />
            <div 
              style={{ width: `${Math.max(0, 100 - calcData.cost_share_pct - calcData.tax_share_pct - calcData.uzum_share_pct)}%` }} 
              className="bg-emerald-500 dark:bg-emerald-400 transition-all duration-300"
              title={`${t.breakdown_profit}: ${calcData.net_share_pct}%`}
            />
          </div>

          {/* Legend */}
          <div className="grid grid-cols-4 gap-1 pt-1 text-[9px] font-medium text-slate-600 dark:text-slate-400">
            <div className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
              <span className="truncate">{t.breakdown_cost} ({calcData.cost_share_pct}%)</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
              <span className="truncate">Soliq ({calcData.tax_share_pct}%)</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-purple-500 flex-shrink-0" />
              <span className="truncate">Uzum ({calcData.uzum_share_pct}%)</span>
            </div>
            <div className="flex items-center space-x-1 justify-end">
              <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
              <span className="truncate font-bold text-emerald-700 dark:text-emerald-400">{t.breakdown_profit} ({calcData.net_share_pct}%)</span>
            </div>
          </div>
        </div>
      )}

      {/* Channel Cards */}
      {calcData && (
        <div className="space-y-3">
          {/* Card 1: Uzum Marketplace */}
          {(channelTab === 'all' || channelTab === 'uzum' || channelTab === 'breakeven') && (
            <div className="glass-card rounded-2xl p-4 border border-purple-200/80 dark:border-purple-800/60 shadow-sm space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-7 h-7 rounded-lg bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 flex items-center justify-center">
                    <ShoppingBag className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xs text-slate-900 dark:text-white">{t.uzum_calc_title}</h3>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400">{calcData.uzum_category_name}</span>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                  {Math.round(calcData.uzum_commission_rate * 100)}% + {formatMoney(calcData.uzum_logistics_fee)} {t.currency}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-100 dark:border-slate-800 text-xs">
                <div>
                  <span className="text-slate-500 dark:text-slate-400 block text-[11px]">{t.uzum_min_price}:</span>
                  <span className="font-extrabold text-purple-900 dark:text-purple-300">
                    {formatMoney(calcData.min_price_uzum)} {t.currency}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 dark:text-slate-400 block text-[11px]">{t.profit_after_tax_label}</span>
                  <span className="font-extrabold text-slate-800 dark:text-slate-200">
                    {formatMoney(calcData.uzum_net)} {t.currency}
                  </span>
                </div>
              </div>

              <div className="text-[11px] text-slate-500 dark:text-slate-400 bg-purple-50/50 dark:bg-purple-950/30 p-2 rounded-lg border border-purple-100 dark:border-purple-900/40 flex items-center justify-between">
                <span>{t.uzum_commission}: {formatMoney(calcData.uzum_commission_amount)} {t.currency}</span>
                <span>{t.uzum_logistics}: {formatMoney(calcData.uzum_logistics_fee)} {t.currency}</span>
              </div>
            </div>
          )}

          {/* Card 2: Telegram / Instagram Direct sales */}
          {(channelTab === 'all' || channelTab === 'telegram') && (
            <div className="glass-card rounded-2xl p-4 border border-sky-200/80 dark:border-sky-800/60 shadow-sm space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-7 h-7 rounded-lg bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-300 flex items-center justify-center">
                    <Send className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xs text-slate-900 dark:text-white">{t.telegram_calc_title}</h3>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400">Click / Payme / Instagram Direct</span>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-50 dark:bg-sky-950/80 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                  1.5% эквайринг
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-100 dark:border-slate-800 text-xs">
                <div>
                  <span className="text-slate-500 dark:text-slate-400 block text-[11px]">{t.telegram_acquiring_label}</span>
                  <span className="font-bold text-sky-800 dark:text-sky-300">
                    {formatMoney(calcData.telegram_acquiring_fee)} {t.currency}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 dark:text-slate-400 block text-[11px]">{t.telegram_net_label}</span>
                  <span className="font-extrabold text-slate-900 dark:text-white">
                    {formatMoney(calcData.telegram_net)} {t.currency}
                  </span>
                </div>
              </div>

              <div className="text-[11px] text-slate-600 dark:text-slate-400 bg-sky-50/50 dark:bg-sky-950/30 p-2 rounded-lg border border-sky-100 dark:border-sky-900/40 flex items-start space-x-1.5">
                <Info className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400 flex-shrink-0 mt-0.5" />
                <span>{t.telegram_delivery_tip}</span>
              </div>
            </div>
          )}

          {/* Card 3: Break-even analysis */}
          {(channelTab === 'all' || channelTab === 'breakeven') && (
            <div className="glass-card rounded-2xl p-4 border border-indigo-200/80 dark:border-indigo-800/60 shadow-sm space-y-3">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 flex items-center justify-center">
                  <Target className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-xs text-slate-900 dark:text-white">{t.breakeven_title}</h3>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400">{t.breakeven_hint}</span>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block mb-1">
                  {t.fixed_costs_label}
                </label>
                <div className="relative">
                  <input
                    type="tel"
                    inputMode="numeric"
                    value={formatMoney(fixedCosts)}
                    onChange={handlePriceInput(setFixedCosts)}
                    placeholder={t.fixed_costs_placeholder}
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-bold text-slate-900 dark:text-white"
                  />
                  <span className="absolute right-2.5 top-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase">
                    {t.currency}
                  </span>
                </div>
              </div>

              {calcData.fixed_costs > 0 && (
                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-100 dark:border-slate-800 text-xs">
                  <div className="p-2 rounded-xl bg-purple-50/50 dark:bg-purple-950/30 border border-purple-100 dark:border-purple-900/40">
                    <span className="text-slate-500 dark:text-slate-400 block text-[10px]">{t.breakeven_uzum_label}</span>
                    <span className="text-base font-extrabold text-purple-700 dark:text-purple-300">
                      {calcData.break_even_units_uzum ? `${calcData.break_even_units_uzum} ${t.units_per_month}` : '—'}
                    </span>
                  </div>
                  <div className="p-2 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/40">
                    <span className="text-slate-500 dark:text-slate-400 block text-[10px]">
                      {calcData.self_employed_allowed ? t.breakeven_self_label : 'Нужно продать (ЯТТ):'}
                    </span>
                    <span className="text-base font-extrabold text-indigo-700 dark:text-indigo-300">
                      {calcData.break_even_units_self ? `${calcData.break_even_units_self} ${t.units_per_month}` : '—'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* China Import & Legal Guidelines Callout */}
          {businessType === 'resale' && (
            <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-300 dark:border-amber-800/60 text-slate-800 dark:text-slate-200 space-y-1.5">
              <div className="flex items-center space-x-2 text-amber-700 dark:text-amber-400 font-bold text-xs">
                <Globe2 className="w-4 h-4 flex-shrink-0" />
                <span>{t.china_tip_title}</span>
              </div>
              <div 
                className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: calcData.china_import_tip || '' }}
              />
            </div>
          )}

          {/* VAT Threshold Warning Notice */}
          <div className="p-3.5 rounded-2xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 flex items-start space-x-2.5">
            <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <h4 className="text-xs font-bold text-amber-900 dark:text-amber-200">
                {t.vat_threshold_notice}
              </h4>
              <p className="text-[11px] text-amber-800/90 dark:text-amber-300/80 leading-relaxed">
                {t.vat_threshold_desc}
              </p>
            </div>
          </div>

          {/* Action: Copy / Share Calculation */}
          <button
            type="button"
            onClick={copySummary}
            className="w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white font-bold text-xs flex items-center justify-center space-x-2 transition-all active:scale-[0.98] shadow-sm"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-300">{t.copied_calc}</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-teal-400" />
                <span>{t.btn_copy_calc}</span>
              </>
            )}
          </button>

          {/* Law Citations Callout */}
          <div className="p-3.5 rounded-2xl bg-slate-900 dark:bg-slate-950 text-white border border-slate-800 shadow-soft space-y-2">
            <div className="flex items-center space-x-2 text-teal-300 font-bold text-xs">
              <ShieldCheck className="w-4 h-4 flex-shrink-0" />
              <span>{t.legal_reference_title}</span>
            </div>
            <div 
              className="text-[11px] text-slate-300 leading-relaxed space-y-1.5"
              dangerouslySetInnerHTML={{ __html: calcData.tip || '' }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
