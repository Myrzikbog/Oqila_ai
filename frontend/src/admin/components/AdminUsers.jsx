import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Filter, 
  Download, 
  Eye, 
  CheckCircle, 
  XCircle, 
  Building2, 
  UserCheck, 
  HelpCircle,
  Sparkles,
  Send,
  RefreshCw,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { fetchAdminUsers, toggleAdminUserActive, downloadUsersCsv } from '../utils/adminApi';

const STATUS_CONFIG = {
  self_employed: { label: 'Самозанятая (1%)', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  yatt: { label: 'ЯТТ', badge: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  planning: { label: 'Выбор статуса', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
};

const CATEGORY_NAMES = {
  sewing: '🧵 Пошив',
  crafts: '🎨 Ремесло',
  food: '🎂 Кулинария',
  resale: '📦 Перепродажа',
  services: '💼 Услуги',
};

const CHANNEL_NAMES = {
  uzum: '🟣 Uzum',
  instagram: '📸 Instagram',
  telegram: '✈️ Telegram',
  offline: '🏬 Офлайн',
};

export default function AdminUsers({ onSelectUser }) {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 20;

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const res = await fetchAdminUsers({
        limit,
        offset: page * limit,
        search,
        status: statusFilter,
        category: categoryFilter,
      });
      setUsers(res.users || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [page, statusFilter, categoryFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(0);
    loadUsers();
  };

  const handleToggleActive = async (user) => {
    const confirmMsg = user.is_active
      ? `Деактивировать аккаунт ${user.name || user.tg_first_name}?`
      : `Активировать аккаунт ${user.name || user.tg_first_name}?`;

    if (!window.confirm(confirmMsg)) return;

    try {
      const res = await toggleAdminUserActive(user.user_id);
      setUsers((prev) =>
        prev.map((u) => (u.user_id === user.user_id ? { ...u, is_active: res.is_active ? 1 : 0 } : u))
      );
    } catch (err) {
      alert('Ошибка при изменении статуса: ' + err.message);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      {/* Header & Controls */}
      <div className="bg-slate-900 p-4 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <Users className="w-5 h-5 text-teal-400" />
              <span>База предпринимателей ({total})</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Управление профилями, статусами активности и историей действий
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => downloadUsersCsv()}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center space-x-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-teal-400" />
              <span>CSV Экспорт</span>
            </button>

            <button
              onClick={loadUsers}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
              title="Обновить список"
            >
              <RefreshCw className="w-4 h-4 text-teal-400" />
            </button>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5 pt-1">
          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} className="sm:col-span-2 relative">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск по имени, @username или Telegram ID..."
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30"
            />
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </form>

          {/* Status Filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-teal-500"
            >
              <option value="">Все статусы</option>
              <option value="self_employed">Самозанятые</option>
              <option value="yatt">ЯТТ</option>
              <option value="planning">Выбирают статус</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(0);
              }}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-teal-500"
            >
              <option value="">Все ниши</option>
              <option value="sewing">🧵 Пошив одежды</option>
              <option value="crafts">🎨 Ремесло / Handmade</option>
              <option value="food">🎂 Кулинария</option>
              <option value="resale">📦 Перепродажа</option>
              <option value="services">💼 Услуги</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                <th className="py-3 px-4">Пользователь</th>
                <th className="py-3 px-4">Telegram</th>
                <th className="py-3 px-4">Правовой статус</th>
                <th className="py-3 px-4">Ниша & Канал</th>
                <th className="py-3 px-4 text-center">Карточек</th>
                <th className="py-3 px-4 text-center">Подписка</th>
                <th className="py-3 px-4">Регистрация</th>
                <th className="py-3 px-4">Последний визит</th>
                <th className="py-3 px-4 text-center">Статус</th>
                <th className="py-3 px-4 text-right">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan="10" className="py-12 text-center text-slate-400">
                    <div className="inline-flex items-center space-x-2">
                      <div className="w-4 h-4 border-2 border-teal-500/20 border-t-teal-400 rounded-full animate-spin" />
                      <span>Загрузка списка пользователей...</span>
                    </div>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan="10" className="py-12 text-center text-slate-500">
                    Пользователи по заданным критериям не найдены
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const statusConf = STATUS_CONFIG[u.status] || {
                    label: u.status,
                    badge: 'bg-slate-800 text-slate-300 border-slate-700',
                  };
                  return (
                    <tr
                      key={u.user_id}
                      className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                      onClick={() => onSelectUser(u.user_id)}
                    >
                      {/* Name / Brand */}
                      <td className="py-3 px-4">
                        <div className="font-bold text-white group-hover:text-teal-300 transition-colors">
                          {u.name || u.tg_first_name || 'Без имени'}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono">ID #{u.user_id}</div>
                      </td>

                      {/* Telegram Info */}
                      <td className="py-3 px-4">
                        {u.tg_username ? (
                          <span className="text-teal-400 font-medium">@{u.tg_username}</span>
                        ) : (
                          <span className="text-slate-400">{u.tg_first_name || '—'}</span>
                        )}
                        <div className="text-[10px] text-slate-500 font-mono">TG: {u.tg_id || 'Веб-гость'}</div>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-md border text-[10px] font-semibold whitespace-nowrap ${statusConf.badge}`}>
                          {statusConf.label}
                        </span>
                      </td>

                      {/* Niche & Channel */}
                      <td className="py-3 px-4 space-y-0.5">
                        <div className="text-slate-200 font-medium whitespace-nowrap">
                          {CATEGORY_NAMES[u.category] || u.category || '—'}
                        </div>
                        <div className="text-[10px] text-slate-400 whitespace-nowrap">
                          {CHANNEL_NAMES[u.sales_channel] || u.sales_channel || '—'}
                        </div>
                      </td>

                      {/* Cards Count */}
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 font-mono font-bold text-[11px] border border-amber-500/20">
                          {u.cards_count || 0}
                        </span>
                      </td>

                      {/* Bot Subscriber */}
                      <td className="py-3 px-4 text-center">
                        {u.is_subscriber ? (
                          <span className="inline-flex items-center text-teal-400 text-[10px] font-medium" title="Подписан на бота">
                            <CheckCircle className="w-3.5 h-3.5 mr-1" /> Да
                          </span>
                        ) : (
                          <span className="text-slate-600 text-[10px]">Нет</span>
                        )}
                      </td>

                      {/* Created At */}
                      <td className="py-3 px-4 text-slate-400 text-[11px] whitespace-nowrap font-mono">
                        {u.created_at ? u.created_at.slice(0, 10) : '—'}
                      </td>

                      {/* Last Seen */}
                      <td className="py-3 px-4 text-slate-300 text-[11px] whitespace-nowrap font-mono">
                        {u.last_seen_at ? u.last_seen_at.slice(0, 16) : '—'}
                      </td>

                      {/* Active Status */}
                      <td className="py-3 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleToggleActive(u)}
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border transition-colors ${
                            u.is_active
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-400 border-rose-500/20 hover:bg-rose-500/20'
                          }`}
                        >
                          {u.is_active ? 'Активен' : 'Заблокирован'}
                        </button>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => onSelectUser(u.user_id)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                          title="Просмотреть детали и карточки"
                        >
                          <Eye className="w-3.5 h-3.5 text-teal-400" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-3 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div>
            Показано {users.length} из {total} предпринимателей
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-[11px]">
              {page + 1} / {totalPages || 1}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page + 1 >= totalPages}
              className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
