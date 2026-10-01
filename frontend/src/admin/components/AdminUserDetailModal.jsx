import React, { useState, useEffect } from 'react';
import { 
  X, 
  User, 
  Sparkles, 
  Activity, 
  Calendar, 
  Clock, 
  ShoppingBag, 
  Building2, 
  Tag, 
  ShieldCheck,
  CheckCircle,
  ExternalLink
} from 'lucide-react';
import { fetchAdminUserDetails, toggleAdminUserActive } from '../utils/adminApi';

export default function AdminUserDetailModal({ userId, onClose }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('cards'); // 'cards' | 'events'

  const loadDetails = async () => {
    if (!userId) return;
    setIsLoading(true);
    try {
      const res = await fetchAdminUserDetails(userId);
      setData(res);
    } catch (err) {
      console.error('Failed to load user details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDetails();
  }, [userId]);

  if (!userId) return null;

  const handleToggleActive = async () => {
    try {
      const res = await toggleAdminUserActive(userId);
      setData((prev) => ({
        ...prev,
        user: { ...prev.user, is_active: res.is_active ? 1 : 0 },
      }));
    } catch (err) {
      alert('Ошибка при изменении статуса: ' + err.message);
    }
  };

  const user = data?.user || {};
  const cards = data?.cards || [];
  const events = data?.events || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
      <div 
        className="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border-b border-slate-800 flex items-start justify-between flex-shrink-0">
          <div className="flex items-start space-x-3.5">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-700 to-teal-500 text-white flex items-center justify-center font-bold text-lg shadow-md">
              {(user.name || user.tg_first_name || 'U').charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-extrabold text-base text-white tracking-tight">
                  {user.name || user.tg_first_name || 'Предпринимательница'}
                </h3>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                  user.is_active
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                }`}>
                  {user.is_active ? 'Активен' : 'Заблокирован'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 flex items-center space-x-2">
                <span>TG: @{user.tg_username || 'нет_ника'}</span>
                <span>•</span>
                <span>ID #{user.user_id}</span>
                <span>•</span>
                <span className="text-teal-400 font-medium">{user.status}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleToggleActive}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
                user.is_active
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/20 hover:bg-rose-500/20'
                  : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20 hover:bg-emerald-500/20'
              }`}
            >
              {user.is_active ? 'Заблокировать' : 'Активировать'}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* User Quick Info Bar */}
        <div className="px-5 py-3 bg-slate-950/40 border-b border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs flex-shrink-0">
          <div>
            <span className="text-[10px] text-slate-500 block">Ниша бизнеса</span>
            <span className="text-slate-200 font-medium">{user.category || '—'}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Канал продаж</span>
            <span className="text-slate-200 font-medium">{user.sales_channel || '—'}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Дата регистрации</span>
            <span className="text-slate-200 font-mono text-[11px]">{user.created_at ? user.created_at.slice(0, 10) : '—'}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Последняя активность</span>
            <span className="text-slate-200 font-mono text-[11px]">{user.last_seen_at ? user.last_seen_at.slice(0, 16) : '—'}</span>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="px-5 pt-3 border-b border-slate-800 flex items-center space-x-3 flex-shrink-0">
          <button
            onClick={() => setActiveTab('cards')}
            className={`pb-2 text-xs font-semibold flex items-center space-x-1.5 border-b-2 transition-colors ${
              activeTab === 'cards'
                ? 'border-teal-400 text-teal-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Карточки пользователя ({cards.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('events')}
            className={`pb-2 text-xs font-semibold flex items-center space-x-1.5 border-b-2 transition-colors ${
              activeTab === 'events'
                ? 'border-teal-400 text-teal-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Журнал действий ({events.length})</span>
          </button>
        </div>

        {/* Body Content */}
        <div className="p-5 overflow-y-auto flex-1 space-y-4">
          {isLoading ? (
            <div className="py-16 text-center text-slate-400 text-xs">
              <div className="w-5 h-5 border-2 border-teal-500/20 border-t-teal-400 rounded-full animate-spin mx-auto mb-2" />
              <span>Загрузка профиля...</span>
            </div>
          ) : activeTab === 'cards' ? (
            cards.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                Пользователь ещё не создавал карточки товаров
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {cards.map((card) => (
                  <div key={card.id} className="p-3.5 rounded-2xl bg-slate-950/70 border border-slate-800/80 space-y-2 flex flex-col justify-between">
                    <div className="space-y-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-bold text-white text-xs line-clamp-1">{card.title}</h4>
                        {card.price_tag && (
                          <span className="px-2 py-0.5 rounded-md bg-teal-500/10 text-teal-300 font-bold text-[10px] whitespace-nowrap">
                            {card.price_tag}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                        {card.description}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>Стиль: {card.photoshoot_style || 'minimal'}</span>
                      <span>{card.created_at ? card.created_at.slice(0, 10) : ''}</span>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            /* Events Tab */
            events.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                Лог событий пуст
              </div>
            ) : (
              <div className="space-y-2">
                {events.map((ev) => (
                  <div key={ev.id} className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/70 text-xs flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-teal-400" />
                      <span className="font-mono text-teal-300 font-medium">{ev.event_type}</span>
                      <span className="text-slate-400 text-[11px]">
                        {ev.details?.title ? `«${ev.details.title}»` : ''}
                      </span>
                    </div>
                    <span className="text-slate-500 text-[10px] font-mono">{ev.created_at}</span>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
