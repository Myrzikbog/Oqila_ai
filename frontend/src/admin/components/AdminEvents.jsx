import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Filter, 
  Search, 
  RefreshCw, 
  User, 
  Clock, 
  Code,
  X
} from 'lucide-react';
import { fetchAdminEvents } from '../utils/adminApi';

const EVENT_TYPE_BADGES = {
  auth_login: { label: 'Авторизация', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  generate_card: { label: 'Генерация карточки', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  calculate: { label: 'Расчёт налогов', color: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  legal_qa: { label: 'Юр. консультация', color: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
  profile_update: { label: 'Смена профиля', color: 'bg-teal-500/10 text-teal-400 border-teal-500/20' },
};

export default function AdminEvents({ onSelectUser }) {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [selectedDetails, setSelectedDetails] = useState(null);

  const loadEvents = async () => {
    setIsLoading(true);
    try {
      const res = await fetchAdminEvents({ limit: 100, eventType: eventTypeFilter });
      setEvents(res.events || []);
    } catch (err) {
      console.error('Failed to load events:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [eventTypeFilter]);

  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      {/* Header & Controls */}
      <div className="bg-slate-900 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <Activity className="w-5 h-5 text-purple-400" />
            <span>Журнал системных событий ({events.length})</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Аудит действий пользователей, запросов к AI и API вызовов
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-purple-500"
          >
            <option value="">Все типы событий</option>
            <option value="auth_login">Авторизация (auth_login)</option>
            <option value="generate_card">Генерация карточек (generate_card)</option>
            <option value="calculate">Калькулятор (calculate)</option>
            <option value="legal_qa">Консультации (legal_qa)</option>
            <option value="profile_update">Профиль (profile_update)</option>
          </select>

          <button
            onClick={loadEvents}
            className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-purple-400" />
          </button>
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                <th className="py-3 px-4">Событие</th>
                <th className="py-3 px-4">Пользователь</th>
                <th className="py-3 px-4">Язык</th>
                <th className="py-3 px-4">Параметры</th>
                <th className="py-3 px-4">Время</th>
                <th className="py-3 px-4 text-right">JSON</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-slate-400">
                    <div className="w-4 h-4 border-2 border-purple-500/20 border-t-purple-400 rounded-full animate-spin inline-block mr-2" />
                    Загрузка журнала...
                  </td>
                </tr>
              ) : events.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-slate-500">
                    События не найдены
                  </td>
                </tr>
              ) : (
                events.map((ev) => {
                  const badge = EVENT_TYPE_BADGES[ev.event_type] || {
                    label: ev.event_type,
                    color: 'bg-slate-800 text-slate-300 border-slate-700',
                  };
                  return (
                    <tr key={ev.id} className="hover:bg-slate-800/40 transition-colors">
                      {/* Event Type */}
                      <td className="py-2.5 px-4 font-sans">
                        <span className={`px-2 py-0.5 rounded-md border text-[10px] font-semibold ${badge.color}`}>
                          {badge.label}
                        </span>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">{ev.event_type}</div>
                      </td>

                      {/* User */}
                      <td className="py-2.5 px-4 font-sans">
                        {ev.user_id ? (
                          <button
                            onClick={() => onSelectUser(ev.user_id)}
                            className="text-teal-400 hover:underline flex items-center space-x-1"
                          >
                            <User className="w-3 h-3" />
                            <span>{ev.user_name || `@${ev.tg_username}` || `ID #${ev.user_id}`}</span>
                          </button>
                        ) : (
                          <span className="text-slate-500">Анонимный гость</span>
                        )}
                      </td>

                      {/* Language */}
                      <td className="py-2.5 px-4">
                        <span className="uppercase text-[11px] text-slate-300">{ev.lang || 'ru'}</span>
                      </td>

                      {/* Summary details */}
                      <td className="py-2.5 px-4 text-slate-400 font-sans text-[11px] max-w-xs truncate">
                        {ev.details?.title || ev.details?.niche || (ev.is_mock ? 'Mock Mode' : 'Production API')}
                      </td>

                      {/* Time */}
                      <td className="py-2.5 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                        {ev.created_at}
                      </td>

                      {/* View details JSON */}
                      <td className="py-2.5 px-4 text-right font-sans">
                        <button
                          onClick={() => setSelectedDetails(ev)}
                          className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                          title="Просмотреть JSON"
                        >
                          <Code className="w-3.5 h-3.5 text-purple-400" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* JSON Details Modal */}
      {selectedDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Code className="w-4 h-4 text-purple-400" />
                <span>Детали события #{selectedDetails.id}</span>
              </h3>
              <button
                onClick={() => setSelectedDetails(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Тип: <span className="text-purple-300 font-mono">{selectedDetails.event_type}</span></span>
                <span>Время: <span className="text-slate-300 font-mono">{selectedDetails.created_at}</span></span>
              </div>
              <pre className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-teal-300 font-mono text-[11px] overflow-x-auto max-h-80">
                {JSON.stringify(selectedDetails.details, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
