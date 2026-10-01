import React, { useState } from 'react';
import { ShieldCheck, Key, ArrowRight, AlertCircle, Eye, EyeOff, Sparkles, ExternalLink } from 'lucide-react';
import { testAdminKey, setAdminKey } from '../utils/adminApi';

export default function AdminLogin({ onLoginSuccess }) {
  const [keyInput, setKeyInput] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!keyInput.trim()) {
      setErrorMessage('Пожалуйста, введите ключ администратора');
      return;
    }

    setIsLoading(true);
    setErrorMessage('');
    try {
      const ok = await testAdminKey(keyInput.trim());
      if (ok) {
        setAdminKey(keyInput.trim());
        onLoginSuccess();
      } else {
        setErrorMessage('Неверный ключ администратора. Проверьте правильность ввода.');
      }
    } catch (err) {
      setErrorMessage('Ошибка подключения к серверу. Попробуйте снова.');
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemoKey = () => {
    setKeyInput('oqila_admin_2026');
    setErrorMessage('');
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 relative overflow-hidden selection:bg-brand-500 selection:text-white">
      {/* Background ambient glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-3xl p-8 shadow-2xl backdrop-blur-xl relative z-10 space-y-6">
        {/* Brand & Badge */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-brand-700 to-teal-500 text-white shadow-lg shadow-brand-500/20">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white tracking-tight flex items-center justify-center space-x-1.5">
              <span>Oqila AI</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-500/20 text-teal-300 border border-teal-500/30 uppercase tracking-wider font-semibold">
                Control Room
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Административная панель управления экосистемой
            </p>
          </div>
        </div>

        {/* Error notification */}
        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start space-x-2.5 animate-in fade-in">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Key Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span className="flex items-center space-x-1.5">
                <Key className="w-3.5 h-3.5 text-teal-400" />
                <span>Секретный ключ администратора</span>
              </span>
              <button
                type="button"
                onClick={fillDemoKey}
                className="text-[11px] text-teal-400 hover:text-teal-300 transition-colors underline underline-offset-2 flex items-center space-x-1"
              >
                <Sparkles className="w-3 h-3" />
                <span>Демо-ключ</span>
              </button>
            </label>

            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                placeholder="Введите ADMIN_SECRET_KEY..."
                autoFocus
                className="w-full px-4 py-3 bg-slate-950 border border-slate-700/80 rounded-xl text-white text-sm focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 pr-10 tracking-wide font-mono transition-all"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-brand-600 via-brand-700 to-teal-600 hover:from-brand-700 hover:to-teal-700 text-white font-bold text-xs shadow-lg shadow-brand-700/25 transition-all flex items-center justify-center space-x-2 disabled:opacity-60 active:scale-98"
          >
            {isLoading ? (
              <span className="inline-flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Проверка доступа...</span>
              </span>
            ) : (
              <>
                <span>Войти в панель управления</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Back Link */}
        <div className="pt-2 border-t border-slate-800/80 text-center">
          <a
            href="/"
            className="text-xs text-slate-400 hover:text-teal-300 transition-colors inline-flex items-center space-x-1"
          >
            <span>Вернуться в клиентское приложение Oqila AI</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
