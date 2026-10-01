import React, { useState, useEffect } from 'react';
import { 
  ShoppingBag, 
  Store, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Printer, 
  XCircle, 
  TrendingUp, 
  Key, 
  Send, 
  Info, 
  Sparkles, 
  Check, 
  ChevronRight, 
  Search, 
  Eye, 
  EyeOff,
  BellRing,
  Download,
  ShieldAlert,
  Layers,
  ChevronDown,
  ChevronUp,
  Calculator,
  Zap,
  BarChart2,
  ExternalLink
} from 'lucide-react';
import { hapticImpact, hapticNotify } from '../utils/telegram';
import { fireConfetti } from '../utils/confetti';

export default function TabUzum({ lang, t, profile, onOpenCalculator }) {
  // Main state
  const [subTab, setSubTab] = useState('orders'); // 'orders' | 'stocks' | 'finance' | 'settings'
  const [selectedShopId, setSelectedShopId] = useState(0); // 0 = All shops
  const [orderStatusFilter, setOrderStatusFilter] = useState('ALL'); // 'ALL' | 'CREATED' | 'CONFIRMED' | 'DELIVERING' | 'COMPLETED'
  const [searchQuery, setSearchQuery] = useState('');

  // Data state
  const [settings, setSettings] = useState({
    is_connected: 0,
    is_demo: 0,
    api_key: '',
    masked_key: '',
    notifications_enabled: 1,
    low_stock_threshold: 3,
  });
  const [shops, setShops] = useState([]);
  const [orders, setOrders] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [finance, setFinance] = useState({
    gross_revenue: 0,
    order_count: 0,
    commission_amount: 0,
    logistics_fee: 0,
    tax_turnover: 0,
    net_payout: 0,
  });

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isCapabilitiesModalOpen, setIsCapabilitiesModalOpen] = useState(false);
  const [labelModalOrder, setLabelModalOrder] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Editing state for stocks & prices
  const [editingStock, setEditingStock] = useState({}); // { [sku_id]: number }
  const [editingPrice, setEditingPrice] = useState({}); // { [sku_id]: number }
  const [editingCost, setEditingCost] = useState({}); // { [sku_id]: number }
  const [expandedMarginSku, setExpandedMarginSku] = useState({}); // { [sku_id]: boolean }

  // Feature 3: Margin & Fee Guard
  const [marginData, setMarginData] = useState({
    items: [],
    avg_margin_pct: 0,
    healthy_count: 0,
    tight_count: 0,
    danger_count: 0,
  });

  // Feature 4: FBO Forecast
  const [fboForecast, setFboForecast] = useState([]);
  const [testingAlertSku, setTestingAlertSku] = useState(null);

  const isUz = lang === 'uz';

  // Load initial settings and data
  useEffect(() => {
    fetchUzumData();
  }, []);

  const fetchUzumData = async () => {
    setIsLoading(true);
    try {
      // 1. Settings
      const setRes = await fetch('/api/uzum/settings');
      if (setRes.ok) {
        const sData = await setRes.json();
        setSettings(sData);
        if (sData.api_key && !sData.is_demo) {
          setApiKeyInput(sData.api_key);
        }
      }

      // 2. Shops
      const shopRes = await fetch('/api/uzum/shops');
      if (shopRes.ok) {
        const shData = await shopRes.json();
        setShops(shData.shops || []);
      }

      // 3. Orders
      const ordRes = await fetch('/api/uzum/orders');
      if (ordRes.ok) {
        const oData = await ordRes.json();
        setOrders(oData.orders || []);
      }

      // 4. Stocks
      const stkRes = await fetch('/api/uzum/stocks');
      if (stkRes.ok) {
        const stData = await stkRes.json();
        setStocks(stData.stocks || []);
      }

      // 5. Finance
      const finRes = await fetch('/api/uzum/finance');
      if (finRes.ok) {
        const fData = await finRes.json();
        setFinance(fData);
      }

      // 6. Margin Guard
      const mgRes = await fetch('/api/uzum/margin-guard');
      if (mgRes.ok) {
        const mgData = await mgRes.json();
        setMarginData(mgData);
      }

      // 7. FBO Forecast
      const fboRes = await fetch('/api/uzum/fbo/forecast');
      if (fboRes.ok) {
        const fboData = await fboRes.json();
        setFboForecast(fboData.forecast || []);
      }
    } catch (err) {
      console.error('Error fetching Uzum data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncNow = async () => {
    hapticImpact('medium');
    setIsSyncing(true);
    setErrorMsg('');
    try {
      const res = await fetch('/api/uzum/sync-now', { method: 'POST' });
      if (res.ok) {
        await fetchUzumData();
        setFeedbackMsg(isUz ? "Ma'lumotlar muvaffaqiyatli yangilandi!" : 'Данные успешно синхронизированы!');
        setTimeout(() => setFeedbackMsg(''), 3000);
      }
    } catch (err) {
      setErrorMsg(isUz ? 'Sinxronlashda xatolik' : 'Ошибка синхронизации');
    } finally {
      setIsSyncing(false);
    }
  };

  // Connect API key or Demo Mode
  const handleConnectApi = async (isDemo = false) => {
    hapticImpact('heavy');
    setErrorMsg('');
    setIsLoading(true);
    try {
      const chat_id = profile?.telegram_chat_id || null;
      const res = await fetch('/api/uzum/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: isDemo ? 'uzum_demo_live_token' : apiKeyInput.trim(),
          is_demo: isDemo,
          telegram_chat_id: chat_id,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || 'Ошибка подключения');
      }
      fireConfetti();
      hapticNotify('success');
      await fetchUzumData();
      setSubTab('orders');
      setFeedbackMsg(
        isDemo
          ? (isUz ? "✨ Uzum Demo rejimi ulandi (2 ta do'kon)!" : '✨ Демо-режим Uzum подключен (2 магазина)!')
          : (isUz ? "🟢 Uzum API muvaffaqiyatli ulandi!" : '🟢 Uzum API успешно подключен!')
      );
      setTimeout(() => setFeedbackMsg(''), 4000);
    } catch (err) {
      hapticNotify('error');
      setErrorMsg(err.message || 'Ошибка');
    } finally {
      setIsLoading(false);
    }
  };

  // Disconnect
  const handleDisconnect = async () => {
    if (!window.confirm(isUz ? "Haqiqatan ham Uzum API'ni uzmoqchimisiz?" : 'Действительно отключить интеграцию Uzum?')) {
      return;
    }
    hapticImpact('medium');
    try {
      await fetch('/api/uzum/settings', { method: 'DELETE' });
      await fetchUzumData();
      setFeedbackMsg(isUz ? "Uzum API uzildi" : 'Uzum API отключен');
      setTimeout(() => setFeedbackMsg(''), 3000);
    } catch (err) {
      console.error(err);
    }
  };

  // Confirm FBS order
  const handleConfirmOrder = async (orderId) => {
    hapticImpact('heavy');
    try {
      const res = await fetch(`/api/uzum/orders/${orderId}/confirm`, { method: 'POST' });
      if (res.ok) {
        fireConfetti();
        hapticNotify('success');
        // Update local orders list state
        setOrders(prev => prev.map(o => o.order_id === orderId ? {
          ...o,
          status: 'CONFIRMED',
          status_label_ru: 'В сборке (Подтвержден)',
          status_label_uz: "Yig'ilmoqda (Tasdiqlangan)"
        } : o));
        setFeedbackMsg(isUz ? `✅ Buyurtma #${orderId} tasdiqlandi!` : `✅ Заказ #${orderId} успешно подтверждён!`);
        setTimeout(() => setFeedbackMsg(''), 3500);
      } else {
        const err = await res.json();
        alert(err.detail || 'Ошибка подтверждения');
      }
    } catch (err) {
      alert('Ошибка соединения');
    }
  };

  // Cancel FBS order
  const handleCancelOrder = async (orderId) => {
    if (!window.confirm(isUz ? `Buyurtma #${orderId} bekor qilinsinmi?` : `Отменить заказ #${orderId}?`)) {
      return;
    }
    hapticImpact('medium');
    try {
      const res = await fetch(`/api/uzum/orders/${orderId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Отсутствует на складе' }),
      });
      if (res.ok) {
        setOrders(prev => prev.map(o => o.order_id === orderId ? {
          ...o,
          status: 'CANCELLED',
          status_label_ru: 'Отменён',
          status_label_uz: 'Bekor qilindi'
        } : o));
        setFeedbackMsg(isUz ? `Buyurtma #${orderId} bekor qilindi` : `Заказ #${orderId} отменён`);
        setTimeout(() => setFeedbackMsg(''), 3000);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Update stock amount
  const handleSaveStock = async (skuId, newAmount) => {
    hapticImpact('light');
    try {
      const res = await fetch('/api/uzum/stocks/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku_id: skuId, amount: Number(newAmount) }),
      });
      if (res.ok) {
        setStocks(prev => prev.map(s => s.sku_id === skuId ? {
          ...s,
          current_stock: Number(newAmount),
          is_low_stock: Number(newAmount) <= 3 ? 1 : 0
        } : s));
        setEditingStock(prev => {
          const next = { ...prev };
          delete next[skuId];
          return next;
        });
        hapticNotify('success');
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Update selling price
  const handleSavePrice = async (skuId, newPrice) => {
    hapticImpact('light');
    try {
      const res = await fetch('/api/uzum/prices/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku_id: skuId, price: Number(newPrice) }),
      });
      if (res.ok) {
        setStocks(prev => prev.map(s => s.sku_id === skuId ? { ...s, price: Number(newPrice) } : s));
        setEditingPrice(prev => {
          const next = { ...prev };
          delete next[skuId];
          return next;
        });
        hapticNotify('success');
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Feature 3: Update SKU cost price (tannarxi / себестоимость)
  const handleSaveCostPrice = async (skuId, costPrice) => {
    hapticImpact('light');
    try {
      const res = await fetch('/api/uzum/stocks/cost-price', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku_id: skuId, cost_price: Number(costPrice) }),
      });
      if (res.ok) {
        hapticNotify('success');
        setFeedbackMsg(isUz ? "Tannarx muvaffaqiyatli saqlandi!" : 'Себестоимость обновлена!');
        setEditingCost(prev => {
          const next = { ...prev };
          delete next[skuId];
          return next;
        });
        // Refresh margin data
        const mgRes = await fetch('/api/uzum/margin-guard');
        if (mgRes.ok) setMarginData(await mgRes.json());
        setTimeout(() => setFeedbackMsg(''), 3000);
      }
    } catch (err) {
      setErrorMsg(isUz ? 'Tannarxni saqlashda xatolik' : 'Ошибка сохранения себестоимости');
    }
  };

  // Feature 3: 1-click apply recommended minimum safe price
  const handleApplyRecommendedPrice = async (skuId, recPrice) => {
    hapticImpact('medium');
    try {
      await handleSavePrice(skuId, recPrice);
      const mgRes = await fetch('/api/uzum/margin-guard');
      if (mgRes.ok) setMarginData(await mgRes.json());
      setFeedbackMsg(
        isUz
          ? `✅ Tavsiya etilgan xavfsiz narx o'rnatildi: ${recPrice.toLocaleString()} so'm`
          : `✅ Установлена безопасная цена: ${recPrice.toLocaleString()} сум`
      );
      setTimeout(() => setFeedbackMsg(''), 3500);
    } catch (err) {
      console.error(err);
    }
  };

  // Feature 4: Send proactive FBO restock alert to Telegram
  const handleSendFboAlert = async (skuId) => {
    hapticImpact('heavy');
    setTestingAlertSku(skuId);
    try {
      const res = await fetch('/api/uzum/fbo/test-alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku_id: skuId }),
      });
      const data = await res.json();
      if (res.ok) {
        fireConfetti();
        hapticNotify('success');
        setFeedbackMsg(
          isUz
            ? "🏬 Telegram'ga FBO zaxira ogohlantirishi yuborildi!"
            : '🏬 FBO-алерт успешно отправлен в Telegram!'
        );
        setTimeout(() => setFeedbackMsg(''), 4000);
      } else {
        setErrorMsg(data.detail || (isUz ? 'Xatolik yuz berdi' : 'Ошибка отправки алерта'));
      }
    } catch (err) {
      setErrorMsg(isUz ? 'Telegramga ulanish xatosi' : 'Ошибка связи с Telegram');
    } finally {
      setTestingAlertSku(null);
    }
  };

  // Feature 2: Download 58x40 mm thermal label PNG
  const handleDownloadLabelPng = (orderId, postingNumber) => {
    hapticImpact('light');
    const a = document.createElement('a');
    a.href = `/api/uzum/orders/${orderId}/label.png`;
    a.download = `uzum-label-${postingNumber || orderId}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // Send Test Push
  const handleSendTestPush = async () => {
    hapticImpact('medium');
    try {
      const chat_id = profile?.telegram_chat_id || null;
      const res = await fetch('/api/uzum/test-push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id, lang }),
      });
      if (res.ok) {
        hapticNotify('success');
        setFeedbackMsg(t.uzum_test_push_sent);
        setTimeout(() => setFeedbackMsg(''), 4000);
      } else {
        const err = await res.json();
        alert(err.detail || 'Не удалось отправить');
      }
    } catch (err) {
      alert('Ошибка соединения');
    }
  };

  // Filtered orders
  const filteredOrders = orders.filter(o => {
    if (selectedShopId !== 0 && o.shop_id !== selectedShopId) return false;
    if (orderStatusFilter !== 'ALL') {
      if (orderStatusFilter === 'CREATED' && !['CREATED', 'PENDING'].includes(o.status)) return false;
      if (orderStatusFilter === 'CONFIRMED' && o.status !== 'CONFIRMED') return false;
      if (orderStatusFilter === 'DELIVERING' && o.status !== 'DELIVERING') return false;
      if (orderStatusFilter === 'COMPLETED' && o.status !== 'COMPLETED') return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchNum = String(o.order_id).includes(q) || String(o.posting_number).toLowerCase().includes(q);
      const matchItem = (o.items || []).some(it => it.product_title.toLowerCase().includes(q));
      return matchNum || matchItem;
    }
    return true;
  });

  // Filtered stocks
  const filteredStocks = stocks.filter(s => {
    if (selectedShopId !== 0 && s.shop_id !== selectedShopId) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        s.product_title.toLowerCase().includes(q) ||
        String(s.sku_id).includes(q) ||
        String(s.barcode).includes(q)
      );
    }
    return true;
  });

  const pendingOrdersCount = orders.filter(o => ['CREATED', 'PENDING'].includes(o.status)).length;
  const lowStockCount = stocks.filter(s => s.is_low_stock).length;
  const criticalFboCount = (fboForecast || []).filter(f => f.urgency === 'CRITICAL').length;

  return (
    <div className="space-y-4 animate-fade-in pb-12">
      {/* ------------------------------------------------------------- */}
      {/* Uzum Brand Banner & Status Header                             */}
      {/* ------------------------------------------------------------- */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-700 via-indigo-700 to-purple-900 text-white p-4 shadow-float border border-purple-500/20">
        <div className="absolute -right-6 -bottom-6 opacity-10 pointer-events-none">
          <ShoppingBag className="w-36 h-36" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <div className="w-9 h-9 rounded-xl bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20 shadow-sm">
                <ShoppingBag className="w-5 h-5 text-purple-200" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="font-extrabold text-base tracking-tight">{t.uzum_title}</h1>
                </div>
                <p className="text-[11px] text-purple-200/90 leading-tight">
                  {t.uzum_subtitle}
                </p>
              </div>
            </div>

            {/* Sync Button */}
            <button
              onClick={handleSyncNow}
              disabled={isSyncing}
              className="px-2.5 py-1.5 rounded-xl bg-white/15 hover:bg-white/25 active:scale-95 text-xs font-semibold flex items-center space-x-1.5 transition-all border border-white/20 shadow-sm"
              title={t.uzum_sync_btn}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{t.uzum_sync_btn}</span>
            </button>
          </div>

          {/* Quick Info & Capabilities Button requested by USER */}
          <div className="mt-3 pt-3 border-t border-white/15 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-purple-200/80">{t.uzum_shop_label}:</span>
              {settings.is_connected ? (
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-200 border border-emerald-400/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>{settings.is_demo ? t.uzum_demo_badge : t.uzum_connected_badge}</span>
                  <span className="opacity-80">({shops.length})</span>
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/20 text-amber-200 border border-amber-400/30">
                  {t.uzum_not_connected_badge}
                </span>
              )}
            </div>

            {/* ℹ️ Small Button explaining OpenAPI capabilities */}
            <button
              onClick={() => {
                hapticImpact('light');
                setIsCapabilitiesModalOpen(true);
              }}
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-purple-500/30 hover:bg-purple-500/40 text-[11px] font-bold text-white border border-purple-300/30 shadow-sm active:scale-95 transition-all"
            >
              <Info className="w-3.5 h-3.5 text-purple-200" />
              <span>{t.uzum_api_capabilities_btn}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Feedback & Error Toast */}
      {feedbackMsg && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800/60 rounded-xl text-emerald-800 dark:text-emerald-200 text-xs font-semibold flex items-center space-x-2 animate-slide-up shadow-sm">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-600 dark:text-emerald-400" />
          <span>{feedbackMsg}</span>
        </div>
      )}
      {errorMsg && (
        <div className="p-3 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800/60 rounded-xl text-rose-800 dark:text-rose-200 text-xs font-semibold flex items-center space-x-2 animate-slide-up shadow-sm">
          <XCircle className="w-4 h-4 flex-shrink-0 text-rose-600 dark:text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* Multi-Shop Selector (Horizontal Filter Pills)                 */}
      {/* ------------------------------------------------------------- */}
      {shops.length > 0 && (
        <div className="flex items-center space-x-1.5 overflow-x-auto no-scrollbar py-0.5">
          <button
            onClick={() => {
              hapticImpact('light');
              setSelectedShopId(0);
            }}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all flex items-center space-x-1.5 shadow-sm ${
              selectedShopId === 0
                ? 'bg-purple-600 text-white shadow-purple-500/20'
                : 'bg-white dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
            }`}
          >
            <Store className="w-3.5 h-3.5" />
            <span>{t.uzum_all_shops}</span>
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-extrabold ${
              selectedShopId === 0 ? 'bg-white/20 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
            }`}>
              {orders.length}
            </span>
          </button>

          {shops.map(s => {
            const isSelected = selectedShopId === s.shop_id;
            const shopOrdersCnt = orders.filter(o => o.shop_id === s.shop_id).length;
            const pendingCnt = orders.filter(o => o.shop_id === s.shop_id && ['CREATED', 'PENDING'].includes(o.status)).length;
            return (
              <button
                key={s.shop_id}
                onClick={() => {
                  hapticImpact('light');
                  setSelectedShopId(s.shop_id);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all flex items-center space-x-1.5 shadow-sm ${
                  isSelected
                    ? 'bg-purple-600 text-white shadow-purple-500/20'
                    : 'bg-white dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
              >
                <span>{s.title}</span>
                {pendingCnt > 0 ? (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-extrabold bg-amber-500 text-white animate-pulse">
                    {pendingCnt}
                  </span>
                ) : (
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-extrabold ${
                    isSelected ? 'bg-white/20 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                  }`}>
                    {shopOrdersCnt}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* Sub-Tabs: Orders | Stocks & Margin | FBO Forecast | Finance | Settings */}
      {/* ------------------------------------------------------------- */}
      <div className="flex bg-slate-200/80 dark:bg-slate-800/80 p-1 rounded-xl gap-1 text-xs font-bold overflow-x-auto no-scrollbar">
        <button
          onClick={() => {
            hapticImpact('light');
            setSubTab('orders');
          }}
          className={`flex-1 py-2 px-1.5 rounded-lg text-center whitespace-nowrap transition-all flex items-center justify-center space-x-1 ${
            subTab === 'orders'
              ? 'bg-white dark:bg-slate-900 text-purple-700 dark:text-purple-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
          }`}
        >
          <span>{t.uzum_tab_orders}</span>
          {pendingOrdersCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-amber-500 text-white text-[10px] font-black flex items-center justify-center">
              {pendingOrdersCount}
            </span>
          )}
        </button>

        <button
          onClick={() => {
            hapticImpact('light');
            setSubTab('stocks');
          }}
          className={`flex-1 py-2 px-1.5 rounded-lg text-center whitespace-nowrap transition-all flex items-center justify-center space-x-1 ${
            subTab === 'stocks'
              ? 'bg-white dark:bg-slate-900 text-purple-700 dark:text-purple-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
          }`}
        >
          <span>{isUz ? "FBS & Marja" : "FBS & Маржа"}</span>
          {lowStockCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] font-black flex items-center justify-center">
              !
            </span>
          )}
        </button>

        <button
          onClick={() => {
            hapticImpact('light');
            setSubTab('fbo');
          }}
          className={`flex-1 py-2 px-1.5 rounded-lg text-center whitespace-nowrap transition-all flex items-center justify-center space-x-1 ${
            subTab === 'fbo'
              ? 'bg-white dark:bg-slate-900 text-purple-700 dark:text-purple-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
          }`}
        >
          <span>{isUz ? "FBO Prognoz" : "FBO Прогноз"}</span>
          {criticalFboCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-rose-500 text-white text-[9px] font-black animate-pulse">
              {criticalFboCount}
            </span>
          )}
        </button>

        <button
          onClick={() => {
            hapticImpact('light');
            setSubTab('finance');
          }}
          className={`flex-1 py-2 px-1.5 rounded-lg text-center whitespace-nowrap transition-all ${
            subTab === 'finance'
              ? 'bg-white dark:bg-slate-900 text-purple-700 dark:text-purple-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
          }`}
        >
          {t.uzum_tab_finance}
        </button>

        <button
          onClick={() => {
            hapticImpact('light');
            setSubTab('settings');
          }}
          className={`flex-1 py-2 px-1.5 rounded-lg text-center whitespace-nowrap transition-all ${
            subTab === 'settings'
              ? 'bg-white dark:bg-slate-900 text-purple-700 dark:text-purple-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
          }`}
        >
          {t.uzum_tab_settings}
        </button>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 1. ORDERS SUB-TAB                                             */}
      {/* ------------------------------------------------------------- */}
      {subTab === 'orders' && (
        <div className="space-y-3">
          {/* Status Filter Chips */}
          <div className="flex items-center space-x-1.5 overflow-x-auto no-scrollbar py-0.5">
            {[
              { id: 'ALL', label: isUz ? 'Barchasi' : 'Все' },
              { id: 'CREATED', label: isUz ? "Yangi (Tasdiqlash)" : 'Новые', badge: pendingOrdersCount },
              { id: 'CONFIRMED', label: isUz ? "Yig'ilmoqda" : 'В сборке' },
              { id: 'DELIVERING', label: isUz ? "Yetkazilmoqda" : 'В пути' },
              { id: 'COMPLETED', label: isUz ? "Yakunlangan" : 'Завершены' },
            ].map(f => {
              const isAct = orderStatusFilter === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => {
                    hapticImpact('light');
                    setOrderStatusFilter(f.id);
                  }}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold whitespace-nowrap transition-all flex items-center space-x-1 ${
                    isAct
                      ? 'bg-slate-800 dark:bg-purple-900/80 text-white shadow-sm'
                      : 'bg-white dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700'
                  }`}
                >
                  <span>{f.label}</span>
                  {f.badge > 0 && (
                    <span className="px-1.5 py-0.2 rounded-full text-[9px] font-extrabold bg-amber-500 text-white">
                      {f.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Orders List */}
          {filteredOrders.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
              <ShoppingBag className="w-10 h-10 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                {t.uzum_no_orders}
              </p>
              {!settings.is_connected && (
                <button
                  onClick={() => handleConnectApi(true)}
                  className="mt-3 inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-sm transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{t.uzum_demo_launch_btn}</span>
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredOrders.map(order => {
                const isPending = ['CREATED', 'PENDING'].includes(order.status);
                const isConfirmed = order.status === 'CONFIRMED';
                const isDelivering = order.status === 'DELIVERING';
                const isCompleted = order.status === 'COMPLETED';

                return (
                  <div
                    key={order.order_id}
                    className={`bg-white dark:bg-slate-900 border rounded-2xl p-4 shadow-card transition-all ${
                      isPending
                        ? 'border-amber-400/80 dark:border-amber-500/80 ring-1 ring-amber-400/20'
                        : 'border-slate-200/90 dark:border-slate-800/90'
                    }`}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2 pb-2.5 border-b border-slate-100 dark:border-slate-800">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-extrabold text-slate-800 dark:text-slate-200">
                            #{order.order_id}
                          </span>
                          <span className="text-[10px] font-semibold text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/80 px-2 py-0.5 rounded-md border border-purple-200 dark:border-purple-800/40">
                            {order.shop_title || "Uzum Do'kon"}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {order.posting_number} · {order.delivery_city}
                        </p>
                      </div>

                      {/* Status badge */}
                      <span className={`px-2 py-0.5 rounded-md text-[11px] font-bold ${
                        isPending
                          ? 'bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700'
                          : isConfirmed
                          ? 'bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                          : isDelivering
                          ? 'bg-purple-100 dark:bg-purple-950/80 text-purple-800 dark:text-purple-300'
                          : isCompleted
                          ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                      }`}>
                        {isUz ? order.status_label_uz : order.status_label_ru}
                      </span>
                    </div>

                    {/* Deadline warning for pending orders */}
                    {isPending && (
                      <div className="mt-2.5 p-2 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-800/60 flex items-center justify-between text-xs text-amber-900 dark:text-amber-200 font-medium">
                        <div className="flex items-center space-x-1.5">
                          <Clock className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 animate-spin" />
                          <span>{t.uzum_deadline_confirm}:</span>
                        </div>
                        <span className="font-extrabold text-amber-700 dark:text-amber-300">
                          {isUz ? "2 soat ichida" : "в течение 2 часов"}
                        </span>
                      </div>
                    )}

                    {/* Items List */}
                    <div className="mt-2.5 space-y-1.5">
                      {(order.items || []).map((it, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs">
                          <span className="text-slate-700 dark:text-slate-300 font-medium truncate pr-2">
                            • {it.product_title}
                          </span>
                          <span className="text-slate-500 dark:text-slate-400 font-bold whitespace-nowrap">
                            {it.quantity} × {it.price.toLocaleString()} {t.currency}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Total Amount & Actions */}
                    <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-bold block leading-none">
                          {isUz ? "Jami summa" : "Общая сумма"}
                        </span>
                        <span className="text-sm font-black text-purple-700 dark:text-purple-400">
                          {order.total_amount.toLocaleString()} {t.currency}
                        </span>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center space-x-1.5">
                        {isPending && (
                          <button
                            onClick={() => handleConfirmOrder(order.order_id)}
                            className="px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 active:scale-95 text-white text-xs font-bold shadow-md shadow-purple-500/20 flex items-center space-x-1 transition-all"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>{t.uzum_confirm_btn}</span>
                          </button>
                        )}

                        <button
                          onClick={() => {
                            hapticImpact('light');
                            setLabelModalOrder(order);
                          }}
                          className="px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold transition-all flex items-center space-x-1"
                          title={t.uzum_print_label_btn}
                        >
                          <Printer className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">{isUz ? "Etiketka" : "Этикетка"}</span>
                        </button>

                        {isPending && (
                          <button
                            onClick={() => handleCancelOrder(order.order_id)}
                            className="p-1.5 rounded-xl text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                            title={t.uzum_cancel_btn}
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 2. STOCKS & MARGIN GUARD SUB-TAB                              */}
      {/* ------------------------------------------------------------- */}
      {subTab === 'stocks' && (
        <div className="space-y-3">
          {/* Feature 3: Margin & Fee Guard Summary Banner */}
          <div className="p-3.5 bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-indigo-500/10 dark:from-emerald-950/40 dark:via-teal-950/40 dark:to-indigo-950/40 border border-emerald-300 dark:border-emerald-800 rounded-2xl shadow-sm space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow-sm">
                  %
                </div>
                <div>
                  <h4 className="text-xs font-black text-slate-800 dark:text-slate-100 flex items-center space-x-1.5">
                    <span>{isUz ? "Uzum Marja Nazorati (Margin & Fee Guard)" : "Контроль маржи Uzum (Margin Guard)"}</span>
                  </h4>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400">
                    {isUz ? "Uzum komissiyasi (13%), logistika (12 000) va 1% soliq hisoblangan" : "С учётом комиссии 13%, логистики 12 000 сум и налога 1%"}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[9px] uppercase tracking-wider text-slate-400 block font-bold">
                  {isUz ? "O'rtacha marja" : "Ср. маржинальность"}
                </span>
                <span className="text-sm font-black text-emerald-600 dark:text-emerald-400">
                  {marginData.avg_margin_pct || 0}%
                </span>
              </div>
            </div>

            {/* Chips */}
            <div className="grid grid-cols-3 gap-1.5 text-center text-[10px] font-bold">
              <div className="bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 py-1 px-1.5 rounded-lg">
                🟢 {isUz ? "Sog'lom" : "Здоровая"}: {marginData.healthy_count || 0}
              </div>
              <div className="bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 py-1 px-1.5 rounded-lg">
                🟡 {isUz ? "Chegara" : "Низкая"}: {marginData.tight_count || 0}
              </div>
              <div className="bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 py-1 px-1.5 rounded-lg">
                🔴 {isUz ? "Xavfli" : "Убыток"}: {marginData.danger_count || 0}
              </div>
            </div>
          </div>

          {/* Low Stock Warning Banner */}
          {lowStockCount > 0 && (
            <div className="p-3 bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-700/60 rounded-2xl flex items-center space-x-2 text-xs text-amber-900 dark:text-amber-200 font-semibold shadow-sm">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
              <span>
                {isUz 
                  ? `${lowStockCount} ta mahsulot qoldig'i 3 tadan kam qoldi! Buyurtmalar bekor bo'lmasligi uchun omborni to'ldiring.`
                  : `Внимание: по ${lowStockCount} товарам остаток ≤ 3 шт. Пополните склад, чтобы избежать отмен заказов!`
                }
              </span>
            </div>
          )}

          {/* Search bar */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={t.uzum_search_sku_placeholder}
              className="w-full pl-9 pr-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          {/* Stocks Cards List */}
          <div className="space-y-2.5">
            {filteredStocks.map(sku => {
              const currentStockVal = editingStock[sku.sku_id] !== undefined ? editingStock[sku.sku_id] : sku.current_stock;
              const currentPriceVal = editingPrice[sku.sku_id] !== undefined ? editingPrice[sku.sku_id] : sku.price;
              const isStockChanged = editingStock[sku.sku_id] !== undefined && editingStock[sku.sku_id] !== sku.current_stock;
              const isPriceChanged = editingPrice[sku.sku_id] !== undefined && editingPrice[sku.sku_id] !== sku.price;

              const mgItem = (marginData.items || []).find(m => m.sku_id === sku.sku_id) || {};
              const currentCostVal = editingCost[sku.sku_id] !== undefined ? editingCost[sku.sku_id] : (mgItem.cost_price || 0);
              const isCostChanged = editingCost[sku.sku_id] !== undefined && editingCost[sku.sku_id] !== (mgItem.cost_price || 0);
              const isMarginExpanded = !!expandedMarginSku[sku.sku_id];

              return (
                <div
                  key={sku.sku_id}
                  className={`bg-white dark:bg-slate-900 border rounded-2xl p-3.5 shadow-sm transition-all ${
                    sku.is_low_stock
                      ? 'border-amber-400/80 dark:border-amber-500/80'
                      : 'border-slate-200/90 dark:border-slate-800/90'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-[10px] font-semibold text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/80 px-2 py-0.5 rounded border border-purple-200 dark:border-purple-800/40">
                          {sku.shop_title}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          SKU #{sku.sku_id}
                        </span>
                      </div>
                      <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 mt-1">
                        {sku.product_title}
                      </h3>
                      <p className="text-[10px] text-slate-400">
                        {t.uzum_barcode}: {sku.barcode}
                      </p>
                    </div>

                    <div className="flex flex-col items-end space-y-1">
                      {sku.is_low_stock ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
                          {t.uzum_stock_low_badge}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                          OK
                        </span>
                      )}

                      {/* Margin status badge */}
                      {mgItem.margin_status === 'HEALTHY' && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                          🟢 +{mgItem.margin_pct}% {isUz ? "marja" : "маржа"}
                        </span>
                      )}
                      {mgItem.margin_status === 'TIGHT' && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                          🟡 +{mgItem.margin_pct}% {isUz ? "diqqat" : "мало"}
                        </span>
                      )}
                      {mgItem.margin_status === 'DANGER' && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800 animate-pulse">
                          🔴 {mgItem.margin_pct}% {isUz ? "zarar xavfi" : "риск убытка"}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Stock counter & Price editor & Cost editor */}
                  <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                    {/* Stock counter */}
                    <div className="bg-slate-50 dark:bg-slate-800/60 p-2 rounded-xl border border-slate-200 dark:border-slate-700/60">
                      <span className="text-[10px] text-slate-500 font-bold block mb-1">
                        {t.uzum_stock_qty}
                      </span>
                      <div className="flex items-center space-x-1.5">
                        <button
                          onClick={() => {
                            hapticImpact('light');
                            const nextVal = Math.max(0, currentStockVal - 1);
                            setEditingStock(prev => ({ ...prev, [sku.sku_id]: nextVal }));
                          }}
                          className="w-6 h-6 rounded-lg bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 flex items-center justify-center font-bold active:scale-95"
                        >
                          -
                        </button>
                        <span className="w-8 text-center font-extrabold text-sm text-slate-900 dark:text-slate-100">
                          {currentStockVal}
                        </span>
                        <button
                          onClick={() => {
                            hapticImpact('light');
                            const nextVal = currentStockVal + 1;
                            setEditingStock(prev => ({ ...prev, [sku.sku_id]: nextVal }));
                          }}
                          className="w-6 h-6 rounded-lg bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 flex items-center justify-center font-bold active:scale-95"
                        >
                          +
                        </button>

                        {isStockChanged && (
                          <button
                            onClick={() => handleSaveStock(sku.sku_id, currentStockVal)}
                            className="px-2 py-1 rounded bg-purple-600 text-white text-[10px] font-bold shadow-sm"
                          >
                            ✓
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Price editor */}
                    <div className="bg-slate-50 dark:bg-slate-800/60 p-2 rounded-xl border border-slate-200 dark:border-slate-700/60">
                      <span className="text-[10px] text-slate-500 font-bold block mb-1">
                        {t.uzum_price_label}
                      </span>
                      <div className="flex items-center space-x-1">
                        <input
                          type="number"
                          value={currentPriceVal}
                          onChange={e => {
                            const val = Number(e.target.value);
                            setEditingPrice(prev => ({ ...prev, [sku.sku_id]: val }));
                          }}
                          className="w-full px-1.5 py-0.5 rounded bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-xs font-black text-purple-700 dark:text-purple-300 focus:outline-none"
                        />
                        {isPriceChanged && (
                          <button
                            onClick={() => handleSavePrice(sku.sku_id, currentPriceVal)}
                            className="px-2 py-1 rounded bg-purple-600 text-white text-[10px] font-bold shadow-sm"
                          >
                            ✓
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Cost Price editor */}
                    <div className="bg-slate-50 dark:bg-slate-800/60 p-2 rounded-xl border border-slate-200 dark:border-slate-700/60">
                      <span className="text-[10px] text-slate-500 font-bold block mb-1">
                        {isUz ? "Tannarxi (Себест.)" : "Себестоимость"}
                      </span>
                      <div className="flex items-center space-x-1">
                        <input
                          type="number"
                          value={currentCostVal}
                          onChange={e => {
                            const val = Number(e.target.value);
                            setEditingCost(prev => ({ ...prev, [sku.sku_id]: val }));
                          }}
                          className="w-full px-1.5 py-0.5 rounded bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-xs font-black text-slate-700 dark:text-slate-200 focus:outline-none"
                        />
                        {isCostChanged && (
                          <button
                            onClick={() => handleSaveCostPrice(sku.sku_id, currentCostVal)}
                            className="px-2 py-1 rounded bg-emerald-600 text-white text-[10px] font-bold shadow-sm"
                            title={isUz ? "Saqlash" : "Сохранить"}
                          >
                            ✓
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Unit Economics Expand Button & Drawer */}
                  <div className="mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <button
                      onClick={() => {
                        hapticImpact('light');
                        setExpandedMarginSku(prev => ({ ...prev, [sku.sku_id]: !prev[sku.sku_id] }));
                      }}
                      className="w-full flex items-center justify-between text-[11px] font-bold text-slate-600 dark:text-slate-400 hover:text-purple-600 dark:hover:text-purple-300 transition-colors py-1"
                    >
                      <span className="flex items-center space-x-1.5">
                        <Calculator className="w-3.5 h-3.5 text-purple-600" />
                        <span>{isUz ? "Batafsil marja va xarajatlar" : "Юнит-экономика и комиссии"}</span>
                      </span>
                      <div className="flex items-center space-x-1">
                        <span className="text-emerald-600 dark:text-emerald-400 font-extrabold">
                          {isUz ? "Sof foyda:" : "Чистыми:"} +{(mgItem.net_profit || 0).toLocaleString()} {t.currency}
                        </span>
                        {isMarginExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </div>
                    </button>

                    {isMarginExpanded && (
                      <div className="mt-2 p-2.5 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/60 space-y-1.5 text-[11px] animate-fade-in">
                        <div className="flex justify-between text-slate-600 dark:text-slate-400">
                          <span>{isUz ? "Sotuv narxi:" : "Цена продажи:"}</span>
                          <span className="font-bold text-slate-900 dark:text-white">{(mgItem.price || sku.price).toLocaleString()} {t.currency}</span>
                        </div>
                        <div className="flex justify-between text-slate-600 dark:text-slate-400">
                          <span>{isUz ? "Tannarxi (chiqim):" : "Себестоимость:"}</span>
                          <span className="font-bold text-rose-600">-{(mgItem.cost_price || 0).toLocaleString()} {t.currency}</span>
                        </div>
                        <div className="flex justify-between text-slate-600 dark:text-slate-400">
                          <span>{isUz ? "Uzum komissiyasi (~13%):" : "Комиссия Uzum (~13%):"}</span>
                          <span className="font-bold text-rose-600">-{(mgItem.commission_est || 0).toLocaleString()} {t.currency}</span>
                        </div>
                        <div className="flex justify-between text-slate-600 dark:text-slate-400">
                          <span>{isUz ? "Uzum logistika to'lovi:" : "Логистика Uzum:"}</span>
                          <span className="font-bold text-rose-600">-{(mgItem.logistics_fee || 12000).toLocaleString()} {t.currency}</span>
                        </div>
                        <div className="flex justify-between text-slate-600 dark:text-slate-400">
                          <span>{isUz ? "1% YaTT solig'i:" : "Налог 1% (удержан):"}</span>
                          <span className="font-bold text-rose-600">-{(mgItem.tax_1pct || 0).toLocaleString()} {t.currency}</span>
                        </div>
                        <div className="pt-1.5 border-t border-slate-200 dark:border-slate-700 flex justify-between font-black text-xs">
                          <span className="text-slate-900 dark:text-white">{isUz ? "1 donadan sof foyda:" : "Чистая прибыль с 1 шт:"}</span>
                          <span className="text-emerald-600 dark:text-emerald-400">
                            +{(mgItem.net_profit || 0).toLocaleString()} {t.currency} ({mgItem.margin_pct}%)
                          </span>
                        </div>

                        {mgItem.recommended_price && mgItem.margin_status !== 'HEALTHY' && (
                          <div className="mt-2 pt-2 border-t border-dashed border-amber-300 dark:border-amber-700/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1.5 bg-amber-50 dark:bg-amber-950/40 p-2 rounded-lg">
                            <div className="text-[10px] text-amber-900 dark:text-amber-200">
                              <span className="font-bold block">
                                {isUz ? "Xavfsiz narx (25% marja uchun):" : "Безопасная цена (маржа 25%):"}
                              </span>
                              <span className="font-extrabold text-xs text-purple-700 dark:text-purple-300">
                                {mgItem.recommended_price.toLocaleString()} {t.currency}
                              </span>
                            </div>
                            <button
                              onClick={() => handleApplyRecommendedPrice(sku.sku_id, mgItem.recommended_price)}
                              className="px-2.5 py-1 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-[10px] font-bold shadow-sm active:scale-95 transition-all"
                            >
                              {isUz ? "Narxni o'rnatish" : "Установить"}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. FBO FORECAST SUB-TAB (ПОСТАВКИ НА СКЛАД UZUM)               */}
      {/* ------------------------------------------------------------- */}
      {subTab === 'fbo' && (
        <div className="space-y-3">
          {/* FBO Educational & Context Header */}
          <div className="p-3.5 bg-gradient-to-r from-purple-700 via-indigo-700 to-purple-900 rounded-2xl text-white shadow-card space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
                  <Layers className="w-4 h-4 text-purple-200" />
                </div>
                <div>
                  <h3 className="font-extrabold text-xs tracking-tight">
                    {isUz ? "🏬 Uzum FBO: Omborga Yetkazib Berish (Поставки)" : "🏬 Uzum FBO: Поставки на центральный склад"}
                  </h3>
                  <p className="text-[10px] text-purple-200/90 leading-tight">
                    {isUz 
                      ? "FBO rejimida tovarlar Uzum omborida saqlanadi. AI zaxira tugashini oldindan hisoblaydi."
                      : "Умный предиктивный расчёт остатков на складе Uzum во избежание обнуления карточки."
                    }
                  </p>
                </div>
              </div>
              <a
                href="https://seller.uzum.uz/seller/invoices"
                target="_blank"
                rel="noreferrer"
                className="px-2.5 py-1.5 rounded-xl bg-white/20 hover:bg-white/30 text-white text-[11px] font-bold flex items-center space-x-1 transition-all"
              >
                <span>{isUz ? "Nakladnaya" : "Накладная"}</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* FBO SKU Cards */}
          <div className="space-y-2.5">
            {fboForecast.map(item => {
              const daysLeft = Math.round(item.days_remaining);
              const isCritical = item.urgency === 'CRITICAL';
              const isWarning = item.urgency === 'WARNING';
              const isAlertLoading = testingAlertSku === item.sku_id;

              return (
                <div
                  key={item.sku_id}
                  className={`bg-white dark:bg-slate-900 border rounded-2xl p-4 shadow-sm space-y-3 transition-all ${
                    isCritical
                      ? 'border-rose-400 dark:border-rose-600/80 ring-1 ring-rose-400/20'
                      : isWarning
                      ? 'border-amber-400 dark:border-amber-600/80'
                      : 'border-slate-200 dark:border-slate-800'
                  }`}
                >
                  {/* Card Title & Urgency */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-[10px] font-semibold text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/80 px-2 py-0.5 rounded border border-purple-200 dark:border-purple-800/40">
                          {item.shop_title}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          SKU #{item.sku_id}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white mt-1">
                        {item.product_title}
                      </h4>
                    </div>

                    {isCritical ? (
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800 animate-pulse flex items-center space-x-1">
                        <AlertTriangle className="w-3 h-3" />
                        <span>{isUz ? "Kritik holat!" : "Критично!"}</span>
                      </span>
                    ) : isWarning ? (
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                        {isUz ? "Diqqat" : "Внимание"}
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                        {isUz ? "Zaxira yetarli" : "Оптимально"}
                      </span>
                    )}
                  </div>

                  {/* Stock, Velocity & Days left indicators */}
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                      <span className="text-[10px] text-slate-400 font-bold block">
                        {isUz ? "FBO Qoldiq" : "Остаток FBO"}
                      </span>
                      <span className="text-sm font-black text-slate-900 dark:text-white">
                        {item.fbo_stock} dona
                      </span>
                    </div>

                    <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                      <span className="text-[10px] text-slate-400 font-bold block">
                        {isUz ? "Kunlik sotuv" : "Продаж в день"}
                      </span>
                      <span className="text-sm font-black text-purple-700 dark:text-purple-300">
                        {item.daily_sales_velocity} dona
                      </span>
                    </div>

                    <div className={`p-2 rounded-xl border ${
                      isCritical
                        ? 'bg-rose-50 dark:bg-rose-950/60 border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                        : isWarning
                        ? 'bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800 text-amber-700 dark:text-amber-300'
                        : 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
                    }`}>
                      <span className="text-[10px] font-bold block opacity-80">
                        {isUz ? "Zaxira muddati" : "Хватит на"}
                      </span>
                      <span className="text-sm font-black">
                        {daysLeft} {isUz ? "kun" : "дней"}
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar of Stock depletion */}
                  <div className="space-y-1">
                    <div className="w-full h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isCritical ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, (daysLeft / 14) * 100))}%` }}
                      />
                    </div>
                  </div>

                  {/* AI Recommendation Tip */}
                  <div className="p-2.5 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800/60 text-xs space-y-1">
                    <div className="flex items-center space-x-1.5 text-purple-800 dark:text-purple-300 font-extrabold text-[11px]">
                      <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                      <span>{isUz ? "Oqila AI Tavsiyasi:" : "Рекомендация Oqila AI:"}</span>
                    </div>
                    <p className="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed">
                      {isUz ? item.tip_uz : item.tip_ru}
                    </p>
                    <div className="pt-1 text-[11px] font-extrabold text-purple-700 dark:text-purple-300 flex items-center justify-between">
                      <span>{isUz ? "Tavsiya etilgan partiya:" : "Рекомендуемая партия:"}</span>
                      <span className="px-2 py-0.5 rounded-md bg-purple-100 dark:bg-purple-900/60 font-black">
                        {item.recommended_reorder} dona
                      </span>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="pt-1 flex items-center space-x-2">
                    <button
                      onClick={() => handleSendFboAlert(item.sku_id)}
                      disabled={isAlertLoading}
                      className="flex-1 py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-700 active:scale-95 text-white text-xs font-bold shadow-md shadow-purple-500/20 flex items-center justify-center space-x-1.5 transition-all"
                    >
                      <BellRing className={`w-3.5 h-3.5 ${isAlertLoading ? 'animate-spin' : ''}`} />
                      <span>{isUz ? "Telegram'ga ogohlantirish" : "Отправить алерт в бот"}</span>
                    </button>
                    <a
                      href="https://seller.uzum.uz/seller/invoices"
                      target="_blank"
                      rel="noreferrer"
                      className="py-2 px-3 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold flex items-center space-x-1"
                    >
                      <span>{isUz ? "Накладная" : "Накладная"}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. FINANCE SUB-TAB                                            */}
      {/* ------------------------------------------------------------- */}
      {subTab === 'finance' && (
        <div className="space-y-3">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-xs font-extrabold text-slate-800 dark:text-slate-100">
                  {t.uzum_finance_title}
                </h3>
                <p className="text-[11px] text-slate-400">
                  {selectedShopId === 0 ? t.uzum_all_shops : shops.find(s => s.shop_id === selectedShopId)?.title}
                </p>
              </div>
              <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>

            {/* Net Payout Hero Card */}
            <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 via-indigo-500/10 to-purple-500/20 border border-purple-500/20 text-center">
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block uppercase tracking-wide">
                {t.uzum_net_payout}
              </span>
              <span className="text-2xl font-black text-purple-700 dark:text-purple-300 mt-1 block">
                {finance.net_payout.toLocaleString()} {t.currency}
              </span>
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold mt-0.5 block">
                {t.uzum_orders_delivered_count}: {finance.order_count} ta
              </span>
            </div>

            {/* Financial breakdown items */}
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <span className="text-slate-600 dark:text-slate-400">{t.uzum_gross_sales}:</span>
                <span className="font-extrabold text-slate-900 dark:text-slate-100">
                  {finance.gross_revenue.toLocaleString()} {t.currency}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <span className="text-slate-600 dark:text-slate-400">{t.uzum_commission_deduction}:</span>
                <span className="font-bold text-rose-600 dark:text-rose-400">
                  - {finance.commission_amount.toLocaleString()} {t.currency}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <span className="text-slate-600 dark:text-slate-400">{t.uzum_logistics_deduction}:</span>
                <span className="font-bold text-rose-600 dark:text-rose-400">
                  - {finance.logistics_fee.toLocaleString()} {t.currency}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <span className="text-slate-600 dark:text-slate-400">{t.uzum_turnover_tax_deduction}:</span>
                <span className="font-bold text-amber-600 dark:text-amber-400">
                  - {finance.tax_turnover.toLocaleString()} {t.currency}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 4. SETTINGS & API KEY SUB-TAB                                 */}
      {/* ------------------------------------------------------------- */}
      {subTab === 'settings' && (
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-xs font-extrabold text-slate-800 dark:text-slate-100 flex items-center space-x-1.5">
                <Key className="w-4 h-4 text-purple-600" />
                <span>{t.uzum_settings_title}</span>
              </h3>
            </div>

            {/* API Key Input */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block">
                {t.uzum_api_token_label}
              </label>
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKeyInput}
                  onChange={e => setApiKeyInput(e.target.value)}
                  placeholder={t.uzum_api_token_placeholder}
                  className="w-full pr-10 pl-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-xs font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                >
                  {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Connect & Demo Buttons */}
            <div className="flex flex-col sm:flex-row gap-2 pt-1">
              <button
                onClick={() => handleConnectApi(false)}
                disabled={isLoading || !apiKeyInput.trim()}
                className="flex-1 py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-purple-500/20 active:scale-95 transition-all flex items-center justify-center space-x-1.5"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{t.uzum_connect_btn}</span>
              </button>

              <button
                onClick={() => handleConnectApi(true)}
                disabled={isLoading}
                className="py-2 px-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white text-xs font-bold shadow-sm active:scale-95 transition-all flex items-center justify-center space-x-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{t.uzum_demo_launch_btn}</span>
              </button>
            </div>

            {settings.is_connected ? (
              <button
                onClick={handleDisconnect}
                className="w-full py-1.5 rounded-xl border border-rose-200 dark:border-rose-900/60 text-rose-600 dark:text-rose-400 text-xs font-bold hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
              >
                {t.uzum_disconnect_btn}
              </button>
            ) : null}

            {/* Telegram Push Notification Card */}
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/60 space-y-2">
              <div className="flex items-center space-x-2">
                <BellRing className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100">
                  {t.uzum_push_toggle_title}
                </h4>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
                {t.uzum_push_toggle_desc}
              </p>
              <button
                onClick={handleSendTestPush}
                className="mt-1 w-full py-1.5 px-3 rounded-lg bg-white dark:bg-slate-800 border border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300 text-xs font-bold hover:bg-purple-50 dark:hover:bg-purple-950/40 transition-colors flex items-center justify-center space-x-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{t.uzum_test_push_btn}</span>
              </button>
            </div>

            {/* Instructions: How to get key */}
            <div className="p-3.5 rounded-xl bg-purple-50/50 dark:bg-purple-950/30 border border-purple-200/60 dark:border-purple-800/40 space-y-1.5 text-xs">
              <span className="font-extrabold text-purple-900 dark:text-purple-200 block">
                {t.uzum_key_help_title}
              </span>
              <p className="text-slate-600 dark:text-slate-400 text-[11px]">{t.uzum_key_help_1}</p>
              <p className="text-slate-600 dark:text-slate-400 text-[11px]">{t.uzum_key_help_2}</p>
              <p className="text-slate-600 dark:text-slate-400 text-[11px]">{t.uzum_key_help_3}</p>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL: Uzum OpenAPI Capabilities (Requested by USER)          */}
      {/* ------------------------------------------------------------- */}
      {isCapabilitiesModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5 max-w-md w-full shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-xl bg-purple-100 dark:bg-purple-950 flex items-center justify-center">
                  <Info className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-extrabold text-sm text-slate-900 dark:text-white">
                    {t.uzum_api_capabilities_title}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Swagger OpenAPI: api-seller.uzum.uz
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsCapabilitiesModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs max-h-[70vh] overflow-y-auto pr-1">
              <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800/60">
                <h4 className="font-bold text-purple-900 dark:text-purple-200 mb-1 flex items-center justify-between">
                  <span>📦 1. {isUz ? "FBS/DBS Buyurtmalar va SLA Rejimi" : "Работа с заказами FBS/DBS (SLA)"}</span>
                  <span className="text-[10px] font-normal px-2 py-0.5 rounded-full bg-purple-200 dark:bg-purple-800 text-purple-800 dark:text-purple-200 font-mono">16 соат дедлайн</span>
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  {isUz
                    ? "Yangi buyurtmalarni avtomatik yuklash (GET /v2/fbs/orders). 16 soat ichida 'В сборку'ga o'tkazish shart. Telegram orqali 1 bosishda tasdiqlash (POST /confirm) va etiketka chop etish."
                    : "Автоматический приём заказов (GET /v2/fbs/orders). По регламенту Uzum у селлера есть ровно 16 часов на подтверждение («В сборку»). Подтверждение в 1 клик прямо из Telegram (POST /confirm)."
                  }
                </p>
                <div className="mt-2 text-[10px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 p-2 rounded-lg border border-amber-200 dark:border-amber-800/50">
                  ⚠️ {isUz
                    ? "24 soatdan keyin bekor qilinsa: 9% jarima (10 000 - 360 000 so'm). Tovarni almashtirib yuborish: 100% jarima!"
                    : "Штрафы Uzum: отмена заказа позже 24ч — 9% (от 10 000 до 360 000 сум). Подмена товара — 100% стоимости!"
                  }
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <h4 className="font-bold text-slate-900 dark:text-white mb-1">
                  🏷️ 2. {isUz ? "Etiketkalar va Shtrix-kodlar (58×40 / 43×25 mm)" : "Маркировка и Печать (58×40 / 43×25 мм)"}
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  {isUz
                    ? "Har bir jo'natmaga Uzum qoidasi bo'yicha markirovka yopishtiriladi (GET /v1/fbs/order/{id}/labels/print). O'lchamlari 58×40 mm yoki 43×25 mm. Belgisi / IMEI majburiy bo'lgan tovarlar uchun kod kiritish."
                    : "Формирование термоэтикеток по ГОСТ Uzum (58×40 мм или 43×25 мм). Печать прямо из браузера или скачивание. Поддержка маркировок ASL Belgisi и IMEI."
                  }
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <h4 className="font-bold text-slate-900 dark:text-white mb-1">
                  📊 3. {isUz ? "Ombor qoldiqlari (GET /v3/fbs/sku/stocks)" : "Остатки на складе (Stocks)"}
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  {isUz
                    ? "Ombordagi qoldiqlarni real vaqtda yangilash. Qoldiq 3 tadan kamayganda avtomatik ogohlantirish (Low Stock Alert), buyurtma bekor bo'lishining oldini oladi."
                    : "Синхронизация остатков по каждому SKU (GET /v3/fbs/sku/stocks), мгновенные предупреждения при остатке ≤ 3 шт. во избежание дефицита и штрафов."
                  }
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <h4 className="font-bold text-slate-900 dark:text-white mb-1">
                  🏪 4. {isUz ? "Multi-Do'kon va Alohida Moliyaviy Hisob" : "Мульти-Магазины (Multi-Shop Isolation)"}
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  {isUz
                    ? "Bitta akkauntdagi bir nechta do'konlarni (masalan, kiyim-kechak va hunarmandchilik) mustaqil boshqarish, har bir do'kon bo'yicha buyurtmalar, komissiyalar va daromadni alohida ajratish."
                    : "Раздельное управление магазинами на одном аккаунте. Независимый учёт заказов, остатков и финансов по каждому магазину + сводная аналитика."
                  }
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <h4 className="font-bold text-slate-900 dark:text-white mb-1">
                  💰 5. {isUz ? "Moliya, Komissiya va Soliq (1% YaTT)" : "Финансы, Комиссии и Налоги"}
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  {isUz
                    ? "Uzum komissiyasi (12-15%), yetkazib berish to'lovi va O'zbekiston soliq qonunchiligi bo'yicha 1% aylanma solig'i yechilganidan keyingi sof foyda prognozi."
                    : "Расчёт удержанной комиссии (12-15%), тарифов логистики и налога с оборота 1%, с выводом чистой выплаты на расчётный счёт или карту."
                  }
                </p>
              </div>

              <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/60">
                <h4 className="font-bold text-indigo-900 dark:text-indigo-200 mb-1">
                  🔔 6. {isUz ? "Telegram Push Bildirishnomalar" : "Telegram Push-уведомления"}
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  {isUz
                    ? "Yangi buyurtma tushganda @oqila_ai_bot darhol xabar yuboradi, do'kon nomi, tovarlar tarkibi, 16 soatlik taymer va tasdiqlash tugmasini taqdim etadi."
                    : "Мгновенное уведомление в Telegram при новом заказе FBS с составом, дедлайном SLA и кнопкой подтверждения без входа в кабинет."
                  }
                </p>
              </div>
            </div>

            <button
              onClick={() => setIsCapabilitiesModalOpen(false)}
              className="w-full py-2.5 rounded-xl bg-purple-600 text-white text-xs font-bold shadow-md shadow-purple-500/20 active:scale-95 transition-all"
            >
              {t.uzum_api_modal_close}
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL: Printable Barcode Label Preview                         */}
      {/* ------------------------------------------------------------- */}
      {labelModalOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5 max-w-sm w-full shadow-2xl space-y-3 text-center">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-xs font-extrabold text-slate-800 dark:text-slate-100">
                {isUz ? "Uzum FBS Markirovka (58×40 mm)" : "Этикетка Uzum FBS (58×40 мм)"}
              </span>
              <button
                onClick={() => setLabelModalOrder(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            {/* Actual 203 DPI Thermal Label PNG */}
            <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-2xl flex flex-col items-center justify-center">
              <img
                src={`/api/uzum/orders/${labelModalOrder.order_id}/label.png`}
                alt="Uzum Thermal Label 58x40 mm"
                className="w-full max-w-[320px] rounded-xl shadow-sm border border-slate-300 dark:border-slate-700 bg-white"
              />
              <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 font-mono">
                {isUz ? "Standart 58×40 mm · 203 DPI · Bluetooth & Termoprinter" : "Стандарт 58×40 мм · 203 DPI · Bluetooth & Термопринтер"}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2 pt-1">
              <button
                onClick={() => handleDownloadLabelPng(labelModalOrder.order_id, labelModalOrder.posting_number)}
                className="flex-1 py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-md shadow-purple-500/20 active:scale-95 transition-all flex items-center justify-center space-x-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>{isUz ? "PNG yuklab olish (58×40)" : "Скачать PNG (58×40)"}</span>
              </button>
              <button
                onClick={() => {
                  window.print();
                  hapticImpact('light');
                }}
                className="py-2 px-3 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-700 text-xs font-bold transition-all flex items-center justify-center space-x-1"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>{isUz ? "Chop etish" : "Печать"}</span>
              </button>
              <button
                onClick={() => setLabelModalOrder(null)}
                className="py-2 px-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs font-bold"
              >
                {isUz ? "Yopish" : "Закрыть"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

