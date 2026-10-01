import React, { useState, useEffect } from 'react';
import { 
  History, 
  X, 
  Trash2, 
  Sparkles, 
  Calendar, 
  Copy, 
  Check, 
  Download,
  Tag,
  ArrowRight,
  PackageOpen,
  Search,
  Star,
  Printer,
  Filter
} from 'lucide-react';
import { hapticImpact, hapticNotify } from '../utils/telegram';

export default function HistoryModal({ isOpen, onClose, onSelectCard, t, lang, userId }) {
  const [historyItems, setHistoryItems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [onlyFavorites, setOnlyFavorites] = useState(false);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const q = searchQuery.trim() ? `&search=${encodeURIComponent(searchQuery.trim())}` : '';
      const fav = onlyFavorites ? '&favorites_only=true' : '';
      const u = userId ? `&user_id=${userId}` : '';
      const res = await fetch(`/api/history?limit=100${q}${fav}${u}`);
      const data = await res.json();
      setHistoryItems(data.items || []);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen, onlyFavorites]);

  // Debounced search
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => {
      fetchHistory();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  if (!isOpen) return null;

  const handleToggleFavorite = async (e, id) => {
    e.stopPropagation();
    hapticImpact('light');
    try {
      const res = await fetch(`/api/history/${id}/favorite`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'ok') {
        setHistoryItems((prev) =>
          prev.map((item) => (item.id === id ? { ...item, is_favorite: data.is_favorite } : item))
        );
        hapticNotify('success');
      }
    } catch (err) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  const handleDeleteItem = async (e, id) => {
    e.stopPropagation();
    hapticImpact('medium');
    try {
      await fetch(`/api/history/${id}`, { method: 'DELETE' });
      setHistoryItems((prev) => prev.filter((item) => item.id !== id));
      hapticNotify('success');
    } catch (err) {
      console.error(err);
      hapticNotify('error');
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm(t.history_clear_confirm)) return;
    hapticImpact('heavy');
    try {
      await fetch('/api/history', { method: 'DELETE' });
      setHistoryItems([]);
      hapticNotify('success');
    } catch (err) {
      console.error(err);
      hapticNotify('error');
    }
  };

  const handleCopyText = (e, item) => {
    e.stopPropagation();
    hapticImpact('light');
    const tags = (item.hashtags || []).join(' ');
    const text = `${item.title}\n\n${item.description}\n\n${item.price_tag}\n\n${tags}`;
    navigator.clipboard.writeText(text);
    setCopiedId(item.id);
    hapticNotify('success');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDownloadPhoto = (e, url) => {
    e.stopPropagation();
    hapticImpact('light');
    const a = document.createElement('a');
    a.href = url;
    a.download = `oqila-studio-${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handlePrintCatalog = (e, item) => {
    e.stopPropagation();
    hapticImpact('light');
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${item.title} — Oqila AI Katalog</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; color: #1e293b; max-width: 650px; margin: 0 auto; }
          .card { border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
          .badge { display: inline-block; background: #0d9488; color: white; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: bold; margin-bottom: 12px; }
          img { width: 100%; max-height: 420px; object-fit: cover; border-radius: 12px; margin-bottom: 16px; }
          h1 { font-size: 20px; margin: 0 0 10px 0; color: #0f172a; }
          .price { font-size: 22px; font-weight: 800; color: #0d9488; margin-bottom: 16px; }
          .desc { font-size: 14px; line-height: 1.6; color: #334155; margin-bottom: 16px; white-space: pre-wrap; }
          .tags { font-size: 12px; color: #64748b; font-weight: 600; }
          .footer { margin-top: 24px; font-size: 11px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px; display: flex; justify-content: space-between; }
          @media print {
            body { padding: 10px; }
          }
        </style>
      </head>
      <body>
        <div class="card">
          <span class="badge">Oqila AI • O'zbekiston Tadbirkorlari</span>
          ${item.studio_photo_url ? `<img src="${item.studio_photo_url}" alt="${item.title}" />` : ''}
          <h1>${item.title}</h1>
          <div class="price">${item.price_tag || ''}</div>
          <div class="desc">${item.description || ''}</div>
          <div class="tags">${(item.hashtags || []).join(' ')}</div>
          <div class="footer">
            <span>Sana: ${new Date(item.created_at).toLocaleDateString()}</span>
            <span>Oqila AI orqali qadoqlangan</span>
          </div>
        </div>
        <script>
          window.onload = function() { window.print(); }
        </script>
      </body>
      </html>
    `);
    printWindow.document.close();
  };

  const formatDate = (isoString) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(lang === 'uz' ? 'uz-UZ' : 'ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (e) {
      return isoString;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-md bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col max-h-[88vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-teal-50 dark:bg-teal-950/60 text-brand-600 dark:text-teal-400 flex items-center justify-center">
              <PackageOpen className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-extrabold text-sm text-slate-900 dark:text-white">
                {lang === 'uz' ? "Mening tovarlarim (Katalog)" : "Мои товары (Каталог)"}
              </h3>
              <p className="text-[10px] text-slate-400 dark:text-slate-500">
                {historyItems.length} {lang === 'uz' ? "ta mahsulot saqlangan" : "сохранённых товаров"}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-1">
            {historyItems.length > 0 && (
              <button
                type="button"
                onClick={handleClearAll}
                className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 hover:text-rose-700 px-2 py-1 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
              >
                {t.history_clear_all}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Search & Favorites Filter Bar (Item 22) */}
        <div className="p-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 space-y-2 flex-shrink-0">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t.catalog_search_placeholder || "Поиск по названию или хэштегам..."}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-900 dark:text-white"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center space-x-1.5 text-xs">
            <button
              type="button"
              onClick={() => {
                hapticImpact('light');
                setOnlyFavorites(false);
              }}
              className={`px-3 py-1 rounded-lg font-bold text-[11px] transition-all ${
                !onlyFavorites
                  ? 'bg-brand-600 text-white shadow-xs'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              {t.catalog_filter_all || "Все карточки"}
            </button>

            <button
              type="button"
              onClick={() => {
                hapticImpact('light');
                setOnlyFavorites(true);
              }}
              className={`px-3 py-1 rounded-lg font-bold text-[11px] flex items-center space-x-1 transition-all ${
                onlyFavorites
                  ? 'bg-amber-500 text-white shadow-xs'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              <Star className="w-3 h-3 fill-current" />
              <span>{t.catalog_filter_fav || "Избранные ⭐"}</span>
            </button>
          </div>
        </div>

        {/* List Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading && historyItems.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-2 text-slate-400">
              <div className="w-6 h-6 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs">{t.loading}</p>
            </div>
          ) : historyItems.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-2 text-slate-400">
              <PackageOpen className="w-10 h-10 stroke-[1.25] text-slate-300 dark:text-slate-600" />
              <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                {onlyFavorites
                  ? (lang === 'uz' ? "Hali sevimlilarga qo'shilgan mahsulotlar yo'q" : "Нет избранных товаров")
                  : (t.history_empty_title || "Список пуст")}
              </p>
              <p className="text-[11px] max-w-[220px]">
                {onlyFavorites
                  ? (lang === 'uz' ? "Mahsulot burchagidagi yulduzchani bosing" : "Нажмите звездочку на карточке товара")
                  : (t.history_empty_desc || "Сгенерируйте карточку в Студии")}
              </p>
            </div>
          ) : (
            historyItems.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  hapticImpact('light');
                  onSelectCard(item);
                  onClose();
                }}
                className={`group p-3 rounded-2xl border transition-all cursor-pointer relative space-y-2.5 ${
                  item.is_favorite
                    ? 'border-amber-300 dark:border-amber-700/80 bg-amber-50/20 dark:bg-amber-950/10 hover:border-amber-400'
                    : 'border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-800/60 hover:border-brand-300 dark:hover:border-teal-700'
                }`}
              >
                {/* Top Row: Date, Favorite Star, Delete */}
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <div className="flex items-center space-x-1.5">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    <span>{formatDate(item.created_at)}</span>
                  </div>

                  <div className="flex items-center space-x-1">
                    {/* Star / Favorite Button (Item 22) */}
                    <button
                      type="button"
                      onClick={(e) => handleToggleFavorite(e, item.id)}
                      className={`p-1 rounded-md transition-all ${
                        item.is_favorite
                          ? 'text-amber-500 hover:text-amber-600 bg-amber-100/70 dark:bg-amber-900/50'
                          : 'text-slate-300 dark:text-slate-600 hover:text-amber-500'
                      }`}
                      title="В избранное"
                    >
                      <Star className={`w-3.5 h-3.5 ${item.is_favorite ? 'fill-current' : ''}`} />
                    </button>

                    {item.studio_photo_url && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800 flex items-center space-x-0.5">
                        <Sparkles className="w-2.5 h-2.5" />
                        <span>AI</span>
                      </span>
                    )}

                    <button
                      type="button"
                      onClick={(e) => handleDeleteItem(e, item.id)}
                      className="p-1 rounded-md text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-all ml-1"
                      title={t.history_delete_item}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Main Content with Photo Thumbnail */}
                <div className="flex items-start space-x-3">
                  {item.studio_photo_url ? (
                    <div className="relative w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 border border-slate-100 dark:border-slate-700 bg-slate-100 dark:bg-slate-900">
                      <img
                        src={item.studio_photo_url}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="w-16 h-16 rounded-xl bg-brand-50 dark:bg-slate-800 text-brand-600 dark:text-teal-400 flex items-center justify-center flex-shrink-0 border border-slate-100 dark:border-slate-700">
                      <Tag className="w-6 h-6 stroke-[1.5]" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0 space-y-1">
                    <h4 className="font-bold text-xs text-slate-900 dark:text-white truncate">
                      {item.title}
                    </h4>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                      {item.description}
                    </p>
                    <div className="flex items-center space-x-2 pt-0.5">
                      <span className="text-[11px] font-extrabold text-brand-700 dark:text-teal-300">
                        {item.price_tag}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Bottom Actions Row: Open in studio + Print/PDF + Copy */}
                <div className="pt-1.5 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-brand-600 dark:text-teal-400 flex items-center space-x-1 group-hover:translate-x-0.5 transition-transform">
                    <span>{t.history_open_in_studio}</span>
                    <ArrowRight className="w-3 h-3" />
                  </span>

                  <div className="flex items-center space-x-1">
                    {/* Print / PDF Export Button (Item 19) */}
                    <button
                      type="button"
                      onClick={(e) => handlePrintCatalog(e, item)}
                      className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-all text-xs"
                      title={t.export_pdf_btn || "Печать / Экспорт"}
                    >
                      <Printer className="w-3.5 h-3.5" />
                    </button>

                    {item.studio_photo_url && (
                      <button
                        type="button"
                        onClick={(e) => handleDownloadPhoto(e, item.studio_photo_url)}
                        className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-all text-xs"
                        title={t.download_photo}
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={(e) => handleCopyText(e, item)}
                      className={`p-1.5 rounded-lg text-xs font-medium flex items-center space-x-1 transition-all ${
                        copiedId === item.id
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300'
                      }`}
                      title={t.copy_post}
                    >
                      {copiedId === item.id ? (
                        <Check className="w-3.5 h-3.5 text-white" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
