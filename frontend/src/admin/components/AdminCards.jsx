import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Search, 
  Tag, 
  ExternalLink, 
  User, 
  RefreshCw,
  Heart,
  Lightbulb,
  Download
} from 'lucide-react';
import { fetchAdminCards, downloadCardsCsv } from '../utils/adminApi';

export default function AdminCards({ onSelectUser }) {
  const [cards, setCards] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');

  const loadCards = async () => {
    setIsLoading(true);
    try {
      const res = await fetchAdminCards({ limit: 100 });
      setCards(res.cards || []);
    } catch (err) {
      console.error('Failed to load admin cards:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCards();
  }, []);

  const filteredCards = cards.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (c.title || '').toLowerCase().includes(q) ||
      (c.description || '').toLowerCase().includes(q) ||
      (c.user_name || '').toLowerCase().includes(q) ||
      (c.tg_username || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      {/* Header */}
      <div className="bg-slate-900 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <span>Сгенерированные AI карточки ({cards.length})</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Каталог созданных карточек товаров, рекламных текстов и фотосессий
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск по товару или автору..."
              className="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
            />
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <button
            onClick={loadCards}
            className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
            title="Обновить список"
          >
            <RefreshCw className="w-4 h-4 text-amber-400" />
          </button>

          <button
            onClick={async () => {
              try {
                await downloadCardsCsv();
              } catch (e) {
                alert('Ошибка при скачивании CSV: ' + e.message);
              }
            }}
            className="px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-medium flex items-center space-x-1.5 transition-colors"
            title="Скачать карточки товаров в CSV"
          >
            <Download className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">CSV Экспорт</span>
          </button>
        </div>
      </div>

      {/* Cards Grid */}
      {isLoading ? (
        <div className="py-24 text-center text-slate-400 text-xs">
          <div className="w-5 h-5 border-2 border-amber-500/20 border-t-amber-400 rounded-full animate-spin mx-auto mb-2" />
          <span>Загрузка каталога карточек...</span>
        </div>
      ) : filteredCards.length === 0 ? (
        <div className="py-16 text-center text-slate-500 text-xs bg-slate-900 rounded-2xl border border-slate-800">
          Карточки не найдены
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCards.map((card) => (
            <div
              key={card.id}
              className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden flex flex-col justify-between hover:border-slate-700 transition-all shadow-sm"
            >
              {/* Studio photo if available */}
              {card.studio_photo_url && (
                <div className="relative h-44 w-full bg-slate-950 overflow-hidden border-b border-slate-800">
                  <img
                    src={card.studio_photo_url}
                    alt={card.title}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  <div className="absolute top-2 right-2 px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-xs text-[10px] text-white font-mono">
                    {card.photoshoot_style || 'studio'}
                  </div>
                </div>
              )}

              <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-bold text-sm text-white line-clamp-1">{card.title}</h3>
                    {card.price_tag && (
                      <span className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 font-bold text-[11px] whitespace-nowrap border border-amber-500/20">
                        {card.price_tag}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                    {card.description}
                  </p>

                  {/* Marketing tip */}
                  {card.marketing_tip && (
                    <div className="p-2 rounded-xl bg-slate-950/70 border border-slate-800/80 text-[11px] text-slate-300 flex items-start space-x-1.5">
                      <Lightbulb className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                      <span className="line-clamp-2">{card.marketing_tip}</span>
                    </div>
                  )}

                  {/* Hashtags */}
                  {card.hashtags && card.hashtags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {card.hashtags.slice(0, 4).map((h, idx) => (
                        <span key={idx} className="text-[10px] text-teal-400 bg-teal-500/10 px-1.5 py-0.5 rounded">
                          {h.startsWith('#') ? h : `#${h}`}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer with Author info */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                  <button
                    onClick={() => card.user_id && onSelectUser(card.user_id)}
                    className="flex items-center space-x-1.5 text-slate-400 hover:text-teal-300 transition-colors"
                  >
                    <User className="w-3.5 h-3.5 text-teal-400" />
                    <span className="font-medium truncate max-w-[120px]">
                      {card.user_name || card.tg_username || (card.user_id ? `Юзер #${card.user_id}` : 'Аноним')}
                    </span>
                  </button>

                  <span className="text-slate-500 font-mono text-[10px]">
                    {card.created_at ? card.created_at.slice(0, 10) : ''}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
