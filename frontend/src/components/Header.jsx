import React from 'react';
import { Sparkles, Sun, Moon, History, User } from 'lucide-react';
import { hapticImpact } from '../utils/telegram';

export default function Header({ 
  lang, 
  setLang, 
  theme, 
  toggleTheme, 
  onOpenHistory, 
  onOpenProfile,
  profile,
  t 
}) {
  const toggleLang = (newLang) => {
    if (newLang !== lang) {
      hapticImpact('light');
      setLang(newLang);
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-200/80 dark:border-slate-800/80 px-4 py-3 transition-colors duration-200">
      <div className="max-w-md mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-700 via-brand-600 to-teal-400 flex items-center justify-center shadow-soft text-white">
            <Sparkles className="w-5 h-5 text-teal-100" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h1 className="font-extrabold text-base tracking-tight text-slate-900 dark:text-white leading-none">
                {t.app_title}
              </h1>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium tracking-tight mt-0.5">
              {t.app_subtitle}
            </p>
          </div>
        </div>

        {/* Right actions: Profile + History + Theme toggle + Language Segmented Control */}
        <div className="flex items-center space-x-1.5">
          {/* Profile / Business settings button */}
          <button
            type="button"
            onClick={() => {
              hapticImpact('light');
              onOpenProfile?.();
            }}
            className="p-1.5 rounded-xl bg-brand-50/80 dark:bg-teal-950/40 hover:bg-brand-100 dark:hover:bg-teal-950/70 text-brand-700 dark:text-teal-300 border border-brand-200/80 dark:border-teal-800 transition-all active:scale-95 flex items-center space-x-1"
            title={lang === 'uz' ? 'Tadbirkor profili' : 'Профиль бизнеса'}
          >
            <User className="w-4 h-4 text-brand-700 dark:text-teal-300" />
            {profile?.name && (
              <span className="text-[11px] font-bold max-w-[60px] truncate hidden xs:inline">
                {profile.name.split(' ')[0]}
              </span>
            )}
          </button>

          {/* History Button */}
          <button
            type="button"
            onClick={() => {
              hapticImpact('light');
              onOpenHistory?.();
            }}
            className="p-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60 transition-all active:scale-95"
            title={t.history_title}
          >
            <History className="w-4 h-4 text-slate-600 dark:text-slate-300" />
          </button>

          {/* Theme Toggle Button (Light -> Eastern -> Dark) */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60 transition-all active:scale-95"
            title={theme === 'eastern' ? "Sharqona tema" : theme === 'dark' ? "Tungi rejim" : "Kunduzgi rejim"}
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : theme === 'eastern' ? (
              <Sparkles className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-600" />
            )}
          </button>

          {/* Language Segmented Control */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-0.5 rounded-xl border border-slate-200/60 dark:border-slate-700/60">
            <button
              type="button"
              onClick={() => toggleLang('ru')}
              className={`px-2 py-1 text-xs font-bold rounded-lg transition-all ${
                lang === 'ru'
                  ? 'bg-white dark:bg-slate-700 text-brand-800 dark:text-teal-300 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              RU
            </button>
            <button
              type="button"
              onClick={() => toggleLang('uz')}
              className={`px-2 py-1 text-xs font-bold rounded-lg transition-all ${
                lang === 'uz'
                  ? 'bg-white dark:bg-slate-700 text-brand-800 dark:text-teal-300 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              UZ
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
