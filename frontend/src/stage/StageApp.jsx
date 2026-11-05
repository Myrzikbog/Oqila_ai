import React, { useEffect, useMemo, useState } from 'react';
import QRCode from 'qrcode';

/**
 * /stage — presentation screen for a festival or pitch.
 * Big live numbers from /api/stats (aggregate only, demo data excluded),
 * a 14-day activity chart and a QR code so the audience can open the bot.
 */

const REFRESH_MS = 10_000;
const BAR_COLOR = '#14a394'; // validated: inside the dark lightness band, >= 3:1 on the surface
const SURFACE = '#0f172a';

const TEXT = {
  uz: {
    live: 'Jonli',
    subtitle: 'Tadbirkor ayollar uchun AI yordamchi',
    hero: 'Yaratilgan mahsulot kartochkalari',
    users: 'Foydalanuvchilar',
    telegram: 'Telegram orqali',
    active: 'Faol (7 kun)',
    calcs: 'Soliq va foyda hisob-kitoblari',
    legal: 'Yuridik savollar',
    uzum: 'Uzum do\'konlari ulangan',
    chartTitle: 'Kunlik yaratilgan kartochkalar',
    chartSub: 'So\'nggi 14 kun',
    table: 'Jadval',
    chart: 'Grafik',
    date: 'Sana',
    cards: 'Kartochkalar',
    newUsers: 'Yangi foydalanuvchilar',
    scan: 'Skanerlang va hoziroq sinab ko\'ring',
    honest: 'Faqat haqiqiy foydalanish: demo-hisoblar va namunalar hisobga olinmagan.',
    updated: 'Yangilandi',
    error: 'Statistikani yuklab bo\'lmadi',
  },
  ru: {
    live: 'Live',
    subtitle: 'AI-помощник для женщин-предпринимательниц',
    hero: 'Создано карточек товаров',
    users: 'Пользователи',
    telegram: 'Из Telegram',
    active: 'Активны за 7 дней',
    calcs: 'Расчётов налогов и прибыли',
    legal: 'Юридических вопросов',
    uzum: 'Подключено магазинов Uzum',
    chartTitle: 'Карточки по дням',
    chartSub: 'Последние 14 дней',
    table: 'Таблица',
    chart: 'График',
    date: 'Дата',
    cards: 'Карточки',
    newUsers: 'Новые пользователи',
    scan: 'Отсканируйте и попробуйте прямо сейчас',
    honest: 'Только реальное использование: демо-аккаунты и образцы не учитываются.',
    updated: 'Обновлено',
    error: 'Не удалось загрузить статистику',
  },
};

const formatter = new Intl.NumberFormat('ru-RU');
const compact = (n) => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
  if (n >= 10_000) return `${(n / 1_000).toFixed(1).replace(/\.0$/, '')}K`;
  return formatter.format(n);
};

function niceMax(value) {
  if (value <= 4) return 4;
  const pow = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 2.5, 5, 10]) {
    if (step * pow >= value) return step * pow;
  }
  return 10 * pow;
}

function StatTile({ label, value }) {
  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 sm:p-5">
      <div className="text-xs sm:text-sm text-slate-400">{label}</div>
      <div className="mt-1 text-2xl sm:text-4xl font-semibold text-white">{compact(value || 0)}</div>
    </div>
  );
}

function DailyChart({ days, t }) {
  const [hover, setHover] = useState(null);
  const width = 640;
  const height = 240;
  const pad = { top: 16, right: 8, bottom: 28, left: 36 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const max = niceMax(Math.max(0, ...days.map((d) => d.cards)));
  const ticks = [0, max / 2, max];
  const band = plotW / Math.max(1, days.length);
  const barW = Math.min(24, band - 2); // <= 24px thick, >= 2px surface gap between neighbours
  const y = (v) => pad.top + plotH - (v / max) * plotH;
  const r = 4;

  const barPath = (x, top, w, h) => {
    // 4px rounded data-end, square at the baseline
    const rr = Math.min(r, h, w / 2);
    if (h <= 0) return '';
    return `M${x},${top + h} V${top + rr} Q${x},${top} ${x + rr},${top} H${x + w - rr} Q${x + w},${top} ${x + w},${top + rr} V${top + h} Z`;
  };

  const shortDate = (iso) => iso.slice(5).split('-').reverse().join('.');

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" role="img" aria-label={`${t.chartTitle}, ${t.chartSub}`}>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} stroke="#1e293b" strokeWidth="1" />
            <text x={pad.left - 8} y={y(tick) + 4} textAnchor="end" fontSize="11" fill="#94a3b8" style={{ fontVariantNumeric: 'tabular-nums' }}>
              {compact(tick)}
            </text>
          </g>
        ))}
        {days.map((d, i) => {
          const x = pad.left + i * band + (band - barW) / 2;
          const top = y(d.cards);
          const h = pad.top + plotH - top;
          const isLast = i === days.length - 1;
          return (
            <g key={d.date}>
              <path d={barPath(x, top, barW, h)} fill={BAR_COLOR} opacity={hover === null || hover === i ? 1 : 0.55} />
              {isLast && d.cards > 0 && (
                <text x={x + barW / 2} y={top - 6} textAnchor="middle" fontSize="12" fill="#e2e8f0">
                  {compact(d.cards)}
                </text>
              )}
              {(i % 2 === 1 || isLast) && (
                <text x={x + barW / 2} y={height - 8} textAnchor="middle" fontSize="11" fill="#94a3b8">
                  {shortDate(d.date)}
                </text>
              )}
              {/* Hit target: the whole band, taller than the bar */}
              <rect
                x={pad.left + i * band}
                y={pad.top}
                width={band}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onTouchStart={() => setHover(i)}
              />
            </g>
          );
        })}
        <line x1={pad.left} x2={width - pad.right} y1={pad.top + plotH} y2={pad.top + plotH} stroke="#334155" strokeWidth="1" />
      </svg>
      {hover !== null && days[hover] && (
        <div
          className="pointer-events-none absolute top-0 -translate-x-1/2 rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-xs text-slate-100 shadow-lg whitespace-nowrap"
          style={{ left: `${((pad.left + hover * band + band / 2) / width) * 100}%` }}
        >
          <div className="text-slate-400">{shortDate(days[hover].date)}</div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ background: BAR_COLOR }} />
            {t.cards}: <b>{formatter.format(days[hover].cards)}</b>
          </div>
          <div className="text-slate-400">{t.newUsers}: {formatter.format(days[hover].new_users)}</div>
        </div>
      )}
    </div>
  );
}

export default function StageApp() {
  const [lang, setLang] = useState(() => (new URLSearchParams(window.location.search).get('lang') === 'ru' ? 'ru' : 'uz'));
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(false);
  const [qrSvg, setQrSvg] = useState('');
  const [showTable, setShowTable] = useState(false);
  const t = TEXT[lang];

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch('/api/stats', { cache: 'no-store' });
        if (!res.ok) throw new Error(String(res.status));
        const data = await res.json();
        if (alive) {
          setStats(data);
          setError(false);
        }
      } catch {
        if (alive) setError(true);
      }
    };
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const botUrl = useMemo(() => `https://t.me/${stats?.bot_username || 'oqila_ai_bot'}`, [stats?.bot_username]);

  useEffect(() => {
    // Dark modules on white with a quiet zone: the most reliable combination for phone cameras
    QRCode.toString(botUrl, { type: 'svg', margin: 2, errorCorrectionLevel: 'M', color: { dark: '#0f172a', light: '#ffffff' } })
      .then(setQrSvg)
      .catch(() => setQrSvg(''));
  }, [botUrl]);

  const days = stats?.daily_activity || [];

  return (
    <div className="min-h-screen text-slate-100 font-sans" style={{ background: SURFACE }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-6 sm:py-10 space-y-6">
        <header className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-4xl font-bold tracking-tight">Oqila AI</h1>
            <p className="text-sm sm:text-lg text-slate-400">{t.subtitle}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-2 text-sm text-slate-300">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60 animate-ping" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
              </span>
              {t.live}
            </span>
            <div className="flex rounded-lg border border-slate-700 overflow-hidden text-sm">
              {['uz', 'ru'].map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLang(code)}
                  className={`px-3 py-1.5 ${lang === code ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  {code.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </header>

        {error && !stats && <div className="rounded-xl bg-rose-500/10 border border-rose-500/30 p-4 text-rose-200">{t.error}</div>}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <section className="rounded-3xl bg-slate-900 border border-slate-800 p-6 sm:p-8">
              <div className="text-sm sm:text-lg text-slate-400">{t.hero}</div>
              <div className="mt-2 text-6xl sm:text-8xl font-semibold text-white">{compact(stats?.cards_total || 0)}</div>
            </section>

            <section className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
              <StatTile label={t.users} value={stats?.users_total} />
              <StatTile label={t.telegram} value={stats?.telegram_users} />
              <StatTile label={t.active} value={stats?.active_7d} />
              <StatTile label={t.calcs} value={stats?.calculations_total} />
              <StatTile label={t.legal} value={stats?.legal_questions_total} />
              <StatTile label={t.uzum} value={stats?.uzum_connected_users} />
            </section>

            <section className="rounded-3xl bg-slate-900 border border-slate-800 p-4 sm:p-6">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h2 className="text-base sm:text-lg font-semibold">{t.chartTitle}</h2>
                  <p className="text-xs sm:text-sm text-slate-400">{t.chartSub}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowTable((v) => !v)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:text-white"
                >
                  {showTable ? t.chart : t.table}
                </button>
              </div>
              {showTable ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" style={{ fontVariantNumeric: 'tabular-nums' }}>
                    <thead>
                      <tr className="text-slate-400 text-left">
                        <th className="py-1.5 font-medium">{t.date}</th>
                        <th className="py-1.5 font-medium text-right">{t.cards}</th>
                        <th className="py-1.5 font-medium text-right">{t.newUsers}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {days.map((d) => (
                        <tr key={d.date} className="border-t border-slate-800">
                          <td className="py-1.5">{d.date}</td>
                          <td className="py-1.5 text-right">{formatter.format(d.cards)}</td>
                          <td className="py-1.5 text-right">{formatter.format(d.new_users)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <DailyChart days={days} t={t} />
              )}
            </section>
          </div>

          <aside className="rounded-3xl bg-slate-900 border border-slate-800 p-6 flex flex-col items-center justify-center text-center gap-4">
            <div className="w-full max-w-xs aspect-square rounded-2xl bg-white p-3">
              {qrSvg ? (
                <div className="w-full h-full [&>svg]:w-full [&>svg]:h-full" dangerouslySetInnerHTML={{ __html: qrSvg }} />
              ) : (
                <div className="w-full h-full animate-pulse bg-slate-200 rounded-xl" />
              )}
            </div>
            <div className="text-lg sm:text-2xl font-semibold">{t.scan}</div>
            <a href={botUrl} className="text-teal-300 text-base sm:text-xl font-mono break-all" target="_blank" rel="noreferrer">
              @{stats?.bot_username || 'oqila_ai_bot'}
            </a>
          </aside>
        </div>

        <footer className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 text-xs text-slate-500">
          <span>{t.honest}</span>
          {stats?.generated_at && (
            <span>
              {t.updated}: {stats.generated_at.slice(11, 19)}
            </span>
          )}
        </footer>
      </div>
    </div>
  );
}
