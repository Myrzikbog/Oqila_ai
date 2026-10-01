import React from 'react';
import { 
  Shield, 
  LayoutDashboard, 
  Users, 
  Sparkles, 
  Activity, 
  LogOut, 
  Download, 
  ExternalLink 
} from 'lucide-react';
import { downloadUsersCsv } from '../utils/adminApi';

export default function AdminNavbar({ activeTab, onSelectTab, onLogout }) {
  const [isExporting, setIsExporting] = React.useState(false);

  const handleCsvExport = async () => {
    setIsExporting(true);
    try {
      await downloadUsersCsv();
    } catch (e) {
      alert('Ошибка при экспорте CSV: ' + e.message);
    } finally {
      setIsExporting(false);
    }
  };

  const navItems = [
    { id: 'dashboard', label: 'Дашборд', icon: LayoutDashboard },
    { id: 'users', label: 'Предприниматели', icon: Users },
    { id: 'cards', label: 'Карточки AI', icon: Sparkles },
    { id: 'events', label: 'Журнал событий', icon: Activity },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-30 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-700 to-teal-500 flex items-center justify-center shadow-md shadow-brand-700/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-base tracking-tight text-white">Oqila AI</span>
                <span className="px-2 py-0.5 text-[10px] rounded-md bg-teal-500/20 text-teal-300 border border-teal-500/30 uppercase tracking-wider font-semibold">
                  Admin
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Панель управления платформой</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-brand-600/30 text-teal-300 border border-teal-500/40 shadow-xs'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/80'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2">
            <button
              onClick={handleCsvExport}
              disabled={isExporting}
              title="Экспорт базы в CSV"
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5 text-teal-400" />
              <span className="hidden sm:inline">CSV Экспорт</span>
            </button>

            <button
              onClick={() => { window.location.href = '/'; }}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium border border-slate-700 flex items-center space-x-1.5 transition-colors"
              title="Перейти в приложение"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">В приложение</span>
            </button>

            <button
              onClick={onLogout}
              title="Выйти из админ-панели"
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile Navigation bar */}
        <div className="flex md:hidden overflow-x-auto py-2 space-x-1 border-t border-slate-800/60 no-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium flex-shrink-0 transition-all ${
                  isActive
                    ? 'bg-brand-600/30 text-teal-300 border border-teal-500/40'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
