import React, { useState } from 'react';
import { 
  Sparkles, 
  Camera, 
  Calculator, 
  Scale, 
  ArrowRight, 
  Check, 
  X,
  ShoppingBag,
  Percent,
  FileCheck2
} from 'lucide-react';
import { hapticImpact, hapticNotify } from '../utils/telegram';

export default function OnboardingModal({ isOpen, onClose, t, lang }) {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const slides = [
    {
      id: 'studio',
      icon: Camera,
      badge: lang === 'uz' ? "1-qadam: Mahsulot qadoqlash" : "Шаг 1: Упаковка товара",
      title: t.onboarding_title_1 || "AI Студия и фотосессия",
      desc: t.onboarding_desc_1 || "Сфотографируйте товар прямо на телефон — ИИ создаст профессиональный студийный кадр и продающий пост с хэштегами.",
      color: "from-teal-500 to-emerald-600",
      bgLight: "bg-teal-50/60 dark:bg-teal-950/30 border-teal-200 dark:border-teal-800",
      preview: (
        <div className="p-3 rounded-2xl bg-white dark:bg-slate-800 border border-teal-100 dark:border-teal-900 shadow-sm flex items-center space-x-3">
          <div className="w-12 h-12 rounded-xl bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300 flex items-center justify-center flex-shrink-0">
            <Camera className="w-6 h-6" />
          </div>
          <div className="text-left text-xs space-y-0.5">
            <div className="font-bold text-slate-800 dark:text-white">
              {lang === 'uz' ? "Studiya fotosessiyasi (8K)" : "Студийное фото (8K)"}
            </div>
            <div className="text-[11px] text-teal-600 dark:text-teal-400 font-semibold">
              {lang === 'uz' ? "Instagram & Uzum uchun matn" : "Пост для Instagram & Uzum"}
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'finance',
      icon: Calculator,
      badge: lang === 'uz' ? "2-qadam: Sof foyda & Soliq" : "Шаг 2: Чистая прибыль & Налоги",
      title: t.onboarding_title_2 || "Финансы и налоги РУз",
      desc: t.onboarding_desc_2 || "Мгновенный расчёт чистой прибыли с учётом официальных льгот самозанятых (0%), ставок ЯТТ и комиссий Uzum Market.",
      color: "from-emerald-500 to-teal-600",
      bgLight: "bg-emerald-50/60 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800",
      preview: (
        <div className="p-3 rounded-2xl bg-white dark:bg-slate-800 border border-emerald-100 dark:border-emerald-900 shadow-sm grid grid-cols-2 gap-2 text-left">
          <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40">
            <div className="text-[10px] text-slate-500 dark:text-slate-400">
              {lang === 'uz' ? "O'z-o'zini band qilish" : "Самозанятые"}
            </div>
            <div className="text-xs font-black text-emerald-600 dark:text-emerald-400">1% soliq</div>
          </div>
          <div className="p-2 rounded-xl bg-purple-50 dark:bg-purple-950/40">
            <div className="text-[10px] text-slate-500 dark:text-slate-400">Uzum Market</div>
            <div className="text-xs font-black text-purple-600 dark:text-purple-400">1% soliq + tarif</div>
          </div>
        </div>
      ),
    },
    {
      id: 'legal',
      icon: Scale,
      badge: lang === 'uz' ? "3-qadam: Yuridik himoya" : "Шаг 3: Юридическая защита",
      title: t.onboarding_title_3 || "Юрист OqilaLegal",
      desc: t.onboarding_desc_3 || "Пошаговая регистрация бизнеса за 10 минут, онлайн-кассы, чеки и персональный налоговый AI-консультант.",
      color: "from-sky-500 to-teal-600",
      bgLight: "bg-sky-50/60 dark:bg-sky-950/30 border-sky-200 dark:border-sky-800",
      preview: (
        <div className="p-3 rounded-2xl bg-white dark:bg-slate-800 border border-sky-100 dark:border-sky-900 shadow-sm flex items-center space-x-2 text-left">
          <div className="w-8 h-8 rounded-lg bg-sky-100 dark:bg-sky-900 text-sky-600 dark:text-sky-300 flex items-center justify-center flex-shrink-0">
            <FileCheck2 className="w-5 h-5" />
          </div>
          <div className="text-xs font-bold text-slate-800 dark:text-slate-200">
            {lang === 'uz' ? "10 daqiqada soliq.uz orqali ro'yxatdan o'tish" : "Регистрация на soliq.uz за 10 минут"}
          </div>
        </div>
      ),
    },
  ];

  const current = slides[currentStep];

  const handleNext = () => {
    hapticImpact('light');
    if (currentStep < slides.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleFinish();
    }
  };

  const handleFinish = () => {
    hapticNotify('success');
    localStorage.setItem('oqila_onboarded', 'true');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-sm bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col p-6 text-center space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Skip button */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold px-2.5 py-0.5 rounded-full bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-teal-300">
            {current.badge}
          </span>
          <button
            type="button"
            onClick={handleFinish}
            className="text-[11px] font-bold text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          >
            {t.onboarding_skip_btn || "Пропустить"}
          </button>
        </div>

        {/* Hero Icon */}
        <div className="py-2 flex justify-center">
          <div className={`w-16 h-16 rounded-2xl bg-gradient-to-tr ${current.color} text-white flex items-center justify-center shadow-lg shadow-teal-500/20`}>
            <current.icon className="w-8 h-8 stroke-[1.75]" />
          </div>
        </div>

        {/* Title & Description */}
        <div className="space-y-1.5">
          <h3 className="text-base font-extrabold text-slate-900 dark:text-white">
            {current.title}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            {current.desc}
          </p>
        </div>

        {/* Interactive Mini Preview */}
        <div className="pt-1">
          {current.preview}
        </div>

        {/* Dots Navigator */}
        <div className="flex justify-center items-center space-x-1.5 pt-2">
          {slides.map((s, idx) => (
            <button
              key={s.id}
              type="button"
              onClick={() => {
                hapticImpact('light');
                setCurrentStep(idx);
              }}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                idx === currentStep ? 'w-6 bg-brand-600 dark:bg-teal-400' : 'w-1.5 bg-slate-200 dark:bg-slate-700'
              }`}
            />
          ))}
        </div>

        {/* Bottom CTA Button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={handleNext}
            className="w-full py-2.5 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs flex items-center justify-center space-x-2 shadow-md shadow-brand-500/20 transition-all active:scale-[0.98]"
          >
            <span>
              {currentStep === slides.length - 1
                ? (t.onboarding_start_btn || "Начать работу")
                : (t.onboarding_next_btn || "Далее")}
            </span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
