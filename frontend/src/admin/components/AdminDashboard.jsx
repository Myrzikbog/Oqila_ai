import React, { useState, useEffect } from 'react';
import { 
  Users, 
  UserCheck, 
  Sparkles, 
  Send, 
  Activity, 
  TrendingUp, 
  Building2, 
  Briefcase, 
  ShoppingBag,
  RefreshCw,
  Calendar,
  Layers,
  CheckCircle2,
  Download
} from 'lucide-react';
import { fetchAdminDashboard, downloadUsersCsv, downloadCardsCsv } from '../utils/adminApi';

const STATUS_LABELS = {
  self_employed: { label: 'Самозанятая (1% налог)', color: 'bg-emerald-500' },
  yatt: { label: 'ЯТТ (Индивидуальный предприниматель)', color: 'bg-sky-500' },
  planning: { label: 'Только выбирает статус', color: 'bg-amber-500' },
};

const CATEGORY_LABELS = {
  sewing: { label: 'Пошив одежды и текстиль', emoji: '🧵' },
  crafts: { label: 'Ремесло и Handmade', emoji: '🎨' },
  food: { label: 'Кулинария и выпечка', emoji: '🎂' },
  resale: { label: 'Перепродажа (Китай, опт)', emoji: '📦' },
  services: { label: 'Сфера услуг и бьюти', emoji: '💼' },
};

const CHANNEL_LABELS = {
  uzum: { label: 'Uzum Market', emoji: '🟣' },
  instagram: { label: 'Instagram', emoji: '📸' },
  telegram: { label: 'Telegram (канал/бот)', emoji: '✈️' },
  offline: { label: 'Офлайн точка', emoji: '🏬' },
};

export default function AdminDashboard({ onSelectTab }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadMetrics = async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await fetchAdminDashboard();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <div className="w-8 h-8 border-3 border-teal-500/20 border-t-teal-400 rounded-full animate-spin" />
        <span className="text-xs text-slate-400 font-medium">Загрузка аналитики...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-center space-y-3">
        <p className="text-sm font-semibold text-rose-300">Не удалось загрузить данные дашборда</p>
        <p className="text-xs text-rose-400/80">{error}</p>
        <button
          onClick={loadMetrics}
          className="px-4 py-2 rounded-xl bg-slate-800 text-white text-xs font-semibold hover:bg-slate-700 transition-colors"
        >
          Повторить попытку
        </button>
      </div>
    );
  }

  const {
    total_users = 0,
    active_today = 0,
    new_this_week = 0,
    total_cards = 0,
    total_subscribers = 0,
    total_events = 0,
    top_categories = [],
    top_statuses = [],
    top_channels = [],
    daily_activity = [],
  } = data || {};

  // Maximum value for SVG chart scaling
  const maxActivityVal = Math.max(
    ...daily_activity.map((d) => Math.max(d.new_users, d.cards, d.events)),
    5
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner & Quick Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight flex items-center space-x-2">
            <span>Сводная панель экосистемы</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
              Live Online
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Статистика активности женщин-предпринимателей в Telegram Mini App и боте
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          <button
            onClick={async () => {
              try {
                await downloadUsersCsv();
              } catch (e) {
                alert('Ошибка при скачивании CSV пользователей: ' + e.message);
              }
            }}
            className="px-3 py-1.5 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 text-xs font-medium flex items-center space-x-1.5 transition-colors"
            title="Экспорт базы пользователей в CSV"
          >
            <Download className="w-3.5 h-3.5 text-teal-400" />
            <span>Пользователи CSV</span>
          </button>

          <button
            onClick={async () => {
              try {
                await downloadCardsCsv();
              } catch (e) {
                alert('Ошибка при скачивании CSV карточек: ' + e.message);
              }
            }}
            className="px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-medium flex items-center space-x-1.5 transition-colors"
            title="Экспорт карточек товаров в CSV"
          >
            <Download className="w-3.5 h-3.5 text-amber-400" />
            <span>Карточки CSV</span>
          </button>

          <button
            onClick={loadMetrics}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium border border-slate-700/80 flex items-center space-x-1.5 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
            <span>Обновить</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Total Users */}
        <div 
          onClick={() => onSelectTab('users')}
          className="p-4 rounded-2xl bg-slate-900 border border-slate-800/80 hover:border-slate-700 transition-all cursor-pointer group shadow-sm"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium">Предприниматели</span>
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white">{total_users}</div>
          <div className="text-[10px] text-teal-400 mt-1 flex items-center space-x-1">
            <TrendingUp className="w-3 h-3" />
            <span>База профилей</span>
          </div>
        </div>

        {/* Active Today */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium">Активных сегодня</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-emerald-400">{active_today}</div>
          <div className="text-[10px] text-slate-400 mt-1">Визитов за 24 часа</div>
        </div>

        {/* New This Week */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium">Новых за 7 дней</span>
            <div className="w-7 h-7 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-sky-400">+{new_this_week}</div>
          <div className="text-[10px] text-slate-400 mt-1">Прирост пользователей</div>
        </div>

        {/* Generated Cards */}
        <div 
          onClick={() => onSelectTab('cards')}
          className="p-4 rounded-2xl bg-slate-900 border border-slate-800/80 hover:border-slate-700 transition-all cursor-pointer group shadow-sm"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium">Карточек AI</span>
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-amber-300">{total_cards}</div>
          <div className="text-[10px] text-slate-400 mt-1">Маркетинг-карточек</div>
        </div>

        {/* Bot Subscribers */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium">Подписчиков бота</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <Send className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-indigo-300">{total_subscribers}</div>
          <div className="text-[10px] text-slate-400 mt-1">Telegram рассылки</div>
        </div>

        {/* Total Events */}
        <div 
          onClick={() => onSelectTab('events')}
          className="p-4 rounded-2xl bg-slate-900 border border-slate-800/80 hover:border-slate-700 transition-all cursor-pointer group shadow-sm"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-medium">Всего событий</span>
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-purple-300">{total_events}</div>
          <div className="text-[10px] text-slate-400 mt-1">Лог взаимодействий</div>
        </div>
      </div>

      {/* Main Analytics: Chart & Demographics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: 7-Day Activity Chart */}
        <div className="lg:col-span-2 bg-slate-900 p-5 rounded-3xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Activity className="w-4 h-4 text-teal-400" />
                <span>Динамика активности за 7 дней</span>
              </h3>
              <p className="text-[11px] text-slate-400">Регистрации, генерация карточек и взаимодействие</p>
            </div>
            <div className="flex items-center space-x-3 text-[11px]">
              <span className="flex items-center space-x-1 text-teal-400">
                <span className="w-2.5 h-2.5 rounded-full bg-teal-400" />
                <span>Юзеры</span>
              </span>
              <span className="flex items-center space-x-1 text-amber-400">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                <span>Карточки</span>
              </span>
              <span className="flex items-center space-x-1 text-purple-400">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
                <span>События</span>
              </span>
            </div>
          </div>

          {/* SVG Line / Bar visualization */}
          <div className="h-56 w-full flex items-end justify-between pt-6 px-2 gap-2">
            {daily_activity.map((day) => {
              const uHeight = Math.max((day.new_users / maxActivityVal) * 160, 4);
              const cHeight = Math.max((day.cards / maxActivityVal) * 160, 4);
              const eHeight = Math.max((day.events / maxActivityVal) * 160, 4);
              const dayLabel = day.date.slice(5); // MM-DD

              return (
                <div key={day.date} className="flex-1 flex flex-col items-center group relative">
                  {/* Tooltip on hover */}
                  <div className="absolute -top-12 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-950 border border-slate-700 text-white text-[10px] rounded-lg p-1.5 shadow-xl pointer-events-none z-20 whitespace-nowrap">
                    <div>{day.date}</div>
                    <div className="text-teal-400">Юзеры: +{day.new_users}</div>
                    <div className="text-amber-400">Карточки: {day.cards}</div>
                    <div className="text-purple-400">События: {day.events}</div>
                  </div>

                  {/* Bars stack */}
                  <div className="w-full max-w-[36px] flex items-end justify-center space-x-1 h-44 border-b border-slate-800 pb-1">
                    <div 
                      style={{ height: `${uHeight}px` }} 
                      className="w-2 rounded-t-sm bg-teal-400/90 hover:bg-teal-300 transition-colors"
                    />
                    <div 
                      style={{ height: `${cHeight}px` }} 
                      className="w-2 rounded-t-sm bg-amber-400/90 hover:bg-amber-300 transition-colors"
                    />
                    <div 
                      style={{ height: `${eHeight}px` }} 
                      className="w-2 rounded-t-sm bg-purple-400/90 hover:bg-purple-300 transition-colors"
                    />
                  </div>
                  <span className="text-[10px] text-slate-400 mt-2 font-mono">{dayLabel}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Col: Business Status Distribution */}
        <div className="bg-slate-900 p-5 rounded-3xl border border-slate-800 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <Building2 className="w-4 h-4 text-sky-400" />
              <span>Правовой статус бизнеса</span>
            </h3>
            <p className="text-[11px] text-slate-400">Распределение налоговых режимов</p>
          </div>

          <div className="space-y-3 pt-2">
            {top_statuses.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">Нет данных о пользователях</p>
            ) : (
              top_statuses.map((item) => {
                const conf = STATUS_LABELS[item.status] || { label: item.status, color: 'bg-slate-500' };
                const pct = total_users > 0 ? Math.round((item.count / total_users) * 100) : 0;
                return (
                  <div key={item.status} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 font-medium truncate max-w-[200px]">
                        {conf.label}
                      </span>
                      <span className="text-slate-400 font-mono text-[11px]">
                        {item.count} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div 
                        style={{ width: `${pct}%` }} 
                        className={`h-full rounded-full ${conf.color} transition-all duration-500`}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Niches and Sales Channels Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Niche Categories */}
        <div className="bg-slate-900 p-5 rounded-3xl border border-slate-800 space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <Briefcase className="w-4 h-4 text-teal-400" />
            <span>Сферы деятельности (Ниши)</span>
          </h3>
          <div className="space-y-2 pt-1">
            {top_categories.map((c) => {
              const meta = CATEGORY_LABELS[c.category] || { label: c.category, emoji: '✨' };
              const pct = total_users > 0 ? Math.round((c.count / total_users) * 100) : 0;
              return (
                <div key={c.category} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center space-x-2.5">
                    <span className="text-lg">{meta.emoji}</span>
                    <span className="text-xs text-slate-200 font-medium">{meta.label}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-white font-mono">{c.count}</span>
                    <span className="text-[10px] text-slate-400 ml-1.5">({pct}%)</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Sales Channels */}
        <div className="bg-slate-900 p-5 rounded-3xl border border-slate-800 space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <ShoppingBag className="w-4 h-4 text-purple-400" />
            <span>Площадки продаж</span>
          </h3>
          <div className="space-y-2 pt-1">
            {top_channels.map((ch) => {
              const meta = CHANNEL_LABELS[ch.sales_channel] || { label: ch.sales_channel, emoji: '🏬' };
              const pct = total_users > 0 ? Math.round((ch.count / total_users) * 100) : 0;
              return (
                <div key={ch.sales_channel} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center space-x-2.5">
                    <span className="text-lg">{meta.emoji}</span>
                    <span className="text-xs text-slate-200 font-medium">{meta.label}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-white font-mono">{ch.count}</span>
                    <span className="text-[10px] text-slate-400 ml-1.5">({pct}%)</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
