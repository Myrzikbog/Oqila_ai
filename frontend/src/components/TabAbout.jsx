import React from 'react';
import { 
  Sparkles, 
  Camera, 
  Calculator, 
  Scale, 
  Users, 
  Heart, 
  ShieldCheck, 
  ShieldAlert,
  CheckCircle2, 
  Layers, 
  Laptop, 
  Globe2 
} from 'lucide-react';

export default function TabAbout({ lang, t, onOpenOnboardingTour }) {
  const audienceList = [
    t.aud_1,
    t.aud_2,
    t.aud_3,
    t.aud_4,
  ];

  return (
    <div className="w-full space-y-4">
      {/* Platform Hero Card */}
      <div className="glass-card rounded-2xl p-5 border-l-4 border-l-brand-600 dark:border-l-brand-400 bg-gradient-to-br from-teal-50/70 via-white to-white dark:from-teal-950/40 dark:via-slate-900 dark:to-slate-900 shadow-soft space-y-3 transition-colors">
        <div className="flex items-center space-x-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-700 via-brand-600 to-teal-400 flex items-center justify-center text-white shadow-soft">
            <Sparkles className="w-5 h-5 text-teal-100" />
          </div>
          <div>
            <h2 className="font-extrabold text-base text-slate-900 dark:text-white tracking-tight">
              {t.about_title}
            </h2>
            <p className="text-xs font-semibold text-brand-700 dark:text-teal-400 mt-0.5">
              {t.about_subtitle}
            </p>
          </div>
        </div>

        <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
          {t.mission_text}
        </p>

        {/* Interactive Tour CTA Button (Item 6) */}
        <button
          type="button"
          onClick={onOpenOnboardingTour}
          className="w-full py-2.5 px-4 rounded-xl bg-brand-50 hover:bg-brand-100/80 dark:bg-teal-950/60 dark:hover:bg-teal-900/60 border border-brand-200 dark:border-teal-800 text-brand-800 dark:text-teal-200 font-bold text-xs flex items-center justify-center space-x-2 transition-all active:scale-[0.98]"
        >
          <Sparkles className="w-4 h-4 text-brand-600 dark:text-teal-400" />
          <span>{lang === 'uz' ? "Ilova bo'yicha interaktiv tur (Qo'llanma)" : "Интерактивный тур по платформе"}</span>
        </button>

        <div className="flex flex-wrap gap-1.5 pt-1">
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border border-teal-200/80 dark:border-teal-800">
            {lang === 'uz' ? "Barcha funksiyalar bepul" : "Бесплатный доступ"}
          </span>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            {lang === 'uz' ? "Telegram Mini App" : "Работает в Telegram"}
          </span>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200/80 dark:border-amber-800">
            {lang === 'uz' ? "O'zbekiston qonunchiligi" : "Законы РУз (ПП-4742)"}
          </span>
        </div>
      </div>

      {/* 3 Core Platform Pillars */}
      <div className="space-y-2.5">
        <h3 className="font-extrabold text-xs text-slate-900 dark:text-white px-1 flex items-center space-x-1.5">
          <Layers className="w-4 h-4 text-brand-600 dark:text-teal-400" />
          <span>{t.about_features_title}</span>
        </h3>

        {/* Feature 1: Studio */}
        <div className="glass-card rounded-2xl p-4 border border-slate-200/80 dark:border-slate-800 space-y-2 transition-colors">
          <div className="flex items-center space-x-2 text-brand-800 dark:text-teal-300 font-bold text-xs">
            <div className="w-7 h-7 rounded-lg bg-teal-50 dark:bg-teal-950 text-brand-600 dark:text-teal-400 flex items-center justify-center flex-shrink-0">
              <Camera className="w-4 h-4" />
            </div>
            <span>{t.feat_studio_title}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            {t.feat_studio_desc}
          </p>
        </div>

        {/* Feature 2: Finance */}
        <div className="glass-card rounded-2xl p-4 border border-slate-200/80 dark:border-slate-800 space-y-2 transition-colors">
          <div className="flex items-center space-x-2 text-amber-800 dark:text-amber-300 font-bold text-xs">
            <div className="w-7 h-7 rounded-lg bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0">
              <Calculator className="w-4 h-4" />
            </div>
            <span>{t.feat_finance_title}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            {t.feat_finance_desc}
          </p>
        </div>

        {/* Feature 3: Legal */}
        <div className="glass-card rounded-2xl p-4 border border-slate-200/80 dark:border-slate-800 space-y-2 transition-colors">
          <div className="flex items-center space-x-2 text-sky-800 dark:text-sky-300 font-bold text-xs">
            <div className="w-7 h-7 rounded-lg bg-sky-50 dark:bg-sky-950 text-sky-600 dark:text-sky-400 flex items-center justify-center flex-shrink-0">
              <Scale className="w-4 h-4" />
            </div>
            <span>{t.feat_legal_title}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            {t.feat_legal_desc}
          </p>
        </div>
      </div>

      {/* Target Audience */}
      <div className="glass-card rounded-2xl p-4 border border-slate-200/80 dark:border-slate-800 space-y-2.5 transition-colors">
        <div className="flex items-center space-x-2 text-slate-900 dark:text-white font-bold text-xs">
          <Users className="w-4 h-4 text-brand-600 dark:text-teal-400" />
          <span>{t.about_audience_title}</span>
        </div>

        <div className="space-y-2">
          {audienceList.map((item, idx) => (
            <div key={idx} className="flex items-start space-x-2 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* About Creators */}
      <div className="glass-card rounded-2xl p-4 border border-slate-200/80 dark:border-slate-800 space-y-2.5 transition-colors">
        <div className="flex items-center space-x-2 text-slate-900 dark:text-white font-bold text-xs">
          <Heart className="w-4 h-4 text-rose-500" />
          <span>{t.about_team_title}</span>
        </div>

        <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
          {t.about_team_desc}
        </p>
      </div>

      {/* Legal Disclaimer & Limitation of Liability Card */}
      <div className="glass-card rounded-2xl p-4 border border-amber-200/70 dark:border-amber-900/40 bg-amber-50/40 dark:bg-amber-950/20 space-y-2.5 transition-colors">
        <div className="flex items-center space-x-2 text-amber-900 dark:text-amber-300 font-bold text-xs">
          <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
          <span>{t.about_disclaimer_title}</span>
        </div>

        <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
          {t.about_disclaimer_text}
        </p>

        <div className="pt-2 border-t border-amber-200/60 dark:border-amber-900/40 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span className="font-semibold">{t.about_version_label}:</span>
          <span className="font-bold text-slate-800 dark:text-slate-200">{t.about_version_val}</span>
        </div>
      </div>

      {/* Clean Footer */}
      <div className="text-center py-2 space-y-1">
        <p className="text-[11px] font-extrabold text-slate-500 dark:text-slate-400">
          {t.about_title} • {lang === 'uz' ? "Tadbirkor Ayollar Uchun" : "Для Предпринимательниц"}
        </p>
        <p className="text-[10px] text-slate-400 dark:text-slate-500">
          {t.about_copyright}
        </p>
      </div>
    </div>
  );
}
