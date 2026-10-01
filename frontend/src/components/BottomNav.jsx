import React from 'react';
import { Sparkles, Calculator, ShoppingBag, Scale, Info } from 'lucide-react';
import { hapticImpact } from '../utils/telegram';

export default function BottomNav({ activeTab, setActiveTab, t }) {
  const tabs = [
    { id: 'studio', label: t.nav_studio, icon: Sparkles },
    { id: 'finance', label: t.nav_finance, icon: Calculator },
    { id: 'uzum', label: t.nav_uzum, icon: ShoppingBag },
    { id: 'legal', label: t.nav_legal, icon: Scale },
    { id: 'about', label: t.nav_about, icon: Info },
  ];

  const handleTabClick = (tabId) => {
    if (activeTab !== tabId) {
      hapticImpact('light');
      setActiveTab(tabId);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <nav className="fixed bottom-3 inset-x-0 z-50 px-4 pointer-events-none">
      <div className="max-w-md mx-auto pointer-events-auto">
        <div className="glass-panel bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border border-slate-200/90 dark:border-slate-800/90 rounded-2xl shadow-float p-1.5 flex items-center justify-around transition-colors duration-200">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={`flex-1 py-2 px-1 flex flex-col items-center justify-center rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-brand-50 dark:bg-brand-950/80 text-brand-700 dark:text-teal-300 font-bold shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 font-medium'
                }`}
              >
                <Icon
                  className={`w-5 h-5 transition-transform duration-200 ${
                    isActive ? 'scale-110 text-brand-600 dark:text-teal-400' : 'text-slate-400 dark:text-slate-500'
                  }`}
                  strokeWidth={isActive ? 2.3 : 1.75}
                />
                <span className="text-[11px] mt-1 leading-tight tracking-tight">
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
