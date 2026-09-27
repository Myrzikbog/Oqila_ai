import React, { useState, useEffect } from 'react';
import { 
  User, 
  Building2, 
  UserCheck, 
  Sparkles, 
  X, 
  Check, 
  HelpCircle,
  ShoppingBag,
  Store,
  Send,
  Camera,
  Scissors,
  Palette,
  Cake,
  Package,
  Briefcase
} from 'lucide-react';
import { getTelegramUser, hapticImpact, hapticNotify } from '../utils/telegram';

export default function ProfileModal({
  isOpen,
  onClose,
  isOnboarding = false,
  profile,
  onSave,
  lang,
  t
}) {
  const tgUser = getTelegramUser();

  const [name, setName] = useState('');
  const [status, setStatus] = useState('self_employed'); // 'self_employed' | 'yatt' | 'planning'
  const [category, setCategory] = useState('sewing');
  const [salesChannel, setSalesChannel] = useState('uzum');

  useEffect(() => {
    if (profile) {
      setName(profile.name || tgUser?.first_name || '');
      setStatus(profile.status || 'self_employed');
      setCategory(profile.category || 'sewing');
      setSalesChannel(profile.salesChannel || 'uzum');
    } else if (tgUser?.first_name) {
      setName(tgUser.first_name);
    }
  }, [profile, isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    hapticNotify('success');
    const updatedProfile = {
      name: name.trim() || (lang === 'uz' ? 'Tadbirkor' : 'Предпринимательница'),
      status,
      category,
      salesChannel,
      onboardingCompleted: true,
      updatedAt: new Date().toISOString(),
    };
    onSave(updatedProfile);
    onClose();
  };

  const handleSkip = () => {
    hapticImpact('light');
    const defaultProfile = {
      name: name.trim() || (lang === 'uz' ? 'Tadbirkor' : 'Предпринимательница'),
      status: 'self_employed',
      category: 'sewing',
      salesChannel: 'uzum',
      onboardingCompleted: true,
      updatedAt: new Date().toISOString(),
    };
    onSave(defaultProfile);
    onClose();
  };

  const STATUS_OPTIONS_RU = [
    {
      id: 'self_employed',
      icon: UserCheck,
      color: 'emerald',
      title: 'Самозанятая (1% налог)',
      desc: 'Только свои изделия и ручной труд (1% налог с оборота). Нанимать работников и перепродавать чужой товар нельзя.',
    },
    {
      id: 'yatt',
      icon: Building2,
      color: 'sky',
      title: 'ЯТТ (Индивидуальный предприниматель)',
      desc: 'Обязательно для перепродажи товаров из Китая, рынков и магазинов (единый налог 1% с оборота + 1 БРВ соцналог).',
    },
    {
      id: 'planning',
      icon: HelpCircle,
      color: 'amber',
      title: 'Только выбираю статус',
      desc: 'Ещё не зарегистрирована, хочу понять разницу и посчитать налоги перед стартом.',
    },
  ];

  const STATUS_OPTIONS_UZ = [
    {
      id: 'self_employed',
      icon: UserCheck,
      color: 'emerald',
      title: 'O\'z-o\'zini band qilish (1% soliq)',
      desc: 'Faqat o\'z mehnati va handmade mahsulotlar (1% aylanma soliq). Qayta sotish va ishchi yollash taqiqlanadi.',
    },
    {
      id: 'yatt',
      icon: Building2,
      color: 'sky',
      title: 'YaTT (Yakka tartibdagi tadbirkor)',
      desc: 'Xitoy tovarlari va qayta sotish uchun majburiy (yagona 1% aylanma soliq + 1 BHM oylik ijtimoiy soliq).',
    },
    {
      id: 'planning',
      icon: HelpCircle,
      color: 'amber',
      title: 'Hali rejalashtiryapman',
      desc: 'Hali ro\'yxatdan o\'tmaganman, YaTT va o\'z-o\'zini band qilish farqini tushunmoqchiman.',
    },
  ];

  const CATEGORY_OPTIONS_RU = [
    { id: 'sewing', label: 'Пошив одежды и текстиль', icon: Scissors, emoji: '🧵' },
    { id: 'crafts', label: 'Ремесло и Handmade', icon: Palette, emoji: '🎨' },
    { id: 'food', label: 'Кулинария и выпечка', icon: Cake, emoji: '🎂' },
    { id: 'resale', label: 'Перепродажа (Китай, опт)', icon: Package, emoji: '📦' },
    { id: 'services', label: 'Сфера услуг и бьюти', icon: Briefcase, emoji: '💼' },
  ];

  const CATEGORY_OPTIONS_UZ = [
    { id: 'sewing', label: 'Tikuvchilik va liboslar', icon: Scissors, emoji: '🧵' },
    { id: 'crafts', label: 'Xalq hunarmandchiligi', icon: Palette, emoji: '🎨' },
    { id: 'food', label: 'Qandolatchilik va taomlar', icon: Cake, emoji: '🎂' },
    { id: 'resale', label: 'Qayta sotish (Xitoy, bozor)', icon: Package, emoji: '📦' },
    { id: 'services', label: 'Xizmat ko\'rsatish va go\'zallik', icon: Briefcase, emoji: '💼' },
  ];

  const CHANNEL_OPTIONS_RU = [
    { id: 'uzum', label: 'Uzum Market', emoji: '🟣' },
    { id: 'instagram', label: 'Instagram', emoji: '📸' },
    { id: 'telegram', label: 'Telegram (канал/бот)', emoji: '✈️' },
    { id: 'offline', label: 'Офлайн-магазин / Точка', emoji: '🏬' },
  ];

  const CHANNEL_OPTIONS_UZ = [
    { id: 'uzum', label: 'Uzum Market', emoji: '🟣' },
    { id: 'instagram', label: 'Instagram', emoji: '📸' },
    { id: 'telegram', label: 'Telegram (kanal/bot)', emoji: '✈️' },
    { id: 'offline', label: 'Do\'kon / Bozor / Shou-rum', emoji: '🏬' },
  ];

  const statusList = lang === 'uz' ? STATUS_OPTIONS_UZ : STATUS_OPTIONS_RU;
  const categoryList = lang === 'uz' ? CATEGORY_OPTIONS_UZ : CATEGORY_OPTIONS_RU;
  const channelList = lang === 'uz' ? CHANNEL_OPTIONS_UZ : CHANNEL_OPTIONS_RU;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-900/60 dark:bg-black/75 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-md bg-white dark:bg-slate-900 rounded-t-3xl sm:rounded-3xl border border-slate-200/90 dark:border-slate-800 shadow-2xl overflow-hidden max-h-[92vh] flex flex-col transition-all duration-200 animate-in slide-in-from-bottom duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 bg-gradient-to-r from-brand-900 via-brand-800 to-slate-900 text-white flex items-start justify-between border-b border-brand-950 flex-shrink-0">
          <div className="flex items-start space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-teal-400/20 text-teal-300 border border-teal-400/30 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Sparkles className="w-5 h-5 text-teal-300" />
            </div>
            <div>
              <h3 className="font-bold text-sm tracking-tight leading-snug">
                {isOnboarding 
                  ? (lang === 'uz' ? 'Oqila AI ga xush kelibsiz! 👋' : 'Добро пожаловать в Oqila AI! 👋')
                  : (lang === 'uz' ? 'Tadbirkor profili' : 'Профиль предпринимательницы')}
              </h3>
              <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
                {isOnboarding
                  ? (lang === 'uz' 
                      ? 'Profilingizni sozlang — soliqlar va AI javoblari sizga moslashtiriladi'
                      : 'Настройте профиль за 1 мин для автоматического расчёта налогов и точных ответов ИИ')
                  : (lang === 'uz'
                      ? 'Moliya va huquqiy yordamchi uchun biznes parametrlari'
                      : 'Параметры бизнеса для финансовых расчётов и консультаций ИИ')}
              </p>
            </div>
          </div>

          {!isOnboarding && (
            <button
              type="button"
              onClick={() => {
                hapticImpact('light');
                onClose();
              }}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Scrollable Form Body */}
        <div className="p-4 space-y-4 overflow-y-auto flex-1">
          {/* User Name / Brand Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-1.5">
              <User className="w-3.5 h-3.5 text-brand-600 dark:text-teal-400" />
              <span>{lang === 'uz' ? 'Ismingiz yoki brend nomi' : 'Ваше имя или название бренда'}</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={lang === 'uz' ? 'Masalan: Malika yoki «Zardo\'z Atelier»' : 'Например: Азиза или «Silk & Craft»'}
              className="w-full text-xs px-3.5 py-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-900 dark:text-white placeholder-slate-400 font-medium"
            />
          </div>

          {/* Section 1: Legal Status */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center justify-between">
              <span>{lang === 'uz' ? '1. Soliq va huquqiy maqom' : '1. Налоговый и правовой статус'}</span>
              <span className="text-[10px] font-normal text-slate-400">
                {lang === 'uz' ? 'Soliq stavkasi shunga bog\'liq' : 'Влияет на ставку налога'}
              </span>
            </label>

            <div className="space-y-2">
              {statusList.map((item) => {
                const IconComponent = item.icon;
                const isSelected = status === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => {
                      hapticImpact('light');
                      setStatus(item.id);
                    }}
                    className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-start space-x-2.5 ${
                      isSelected
                        ? 'bg-brand-50/70 dark:bg-teal-950/30 border-brand-500 dark:border-teal-500 ring-2 ring-brand-500/20 shadow-sm'
                        : 'bg-white dark:bg-slate-800/60 border-slate-200/80 dark:border-slate-700/80 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${
                      isSelected 
                        ? 'bg-brand-700 text-white shadow-soft' 
                        : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                    }`}>
                      <IconComponent className="w-4 h-4" />
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className={`text-xs font-bold ${
                          isSelected ? 'text-brand-900 dark:text-teal-200' : 'text-slate-800 dark:text-slate-200'
                        }`}>
                          {item.title}
                        </p>
                        {isSelected && (
                          <div className="w-4 h-4 rounded-full bg-brand-600 dark:bg-teal-500 text-white flex items-center justify-center">
                            <Check className="w-2.5 h-2.5" />
                          </div>
                        )}
                      </div>
                      <p className="text-[10.5px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                        {item.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 2: Business Niche / Category */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-800 dark:text-slate-200">
              {lang === 'uz' ? '2. Faoliyat yo\'nalishi (Nisha)' : '2. Сфера деятельности (Ниша)'}
            </label>

            <div className="grid grid-cols-1 gap-1.5">
              {categoryList.map((cat) => {
                const isSelected = category === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => {
                      hapticImpact('light');
                      setCategory(cat.id);
                    }}
                    className={`text-left px-3 py-2.5 rounded-xl border text-xs font-medium transition-all flex items-center space-x-2.5 ${
                      isSelected
                        ? 'bg-brand-50/80 dark:bg-teal-950/40 border-brand-500 dark:border-teal-400 text-brand-900 dark:text-teal-200 font-bold ring-1 ring-brand-500/20 shadow-xs'
                        : 'bg-white dark:bg-slate-800/60 border-slate-200/80 dark:border-slate-700/80 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <span className="text-base">{cat.emoji}</span>
                    <span className="flex-1">{cat.label}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-brand-600 dark:text-teal-400" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 3: Sales Channel */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-800 dark:text-slate-200">
              {lang === 'uz' ? '3. Asosiy savdo maydoni' : '3. Основная площадка продаж'}
            </label>

            <div className="grid grid-cols-2 gap-2">
              {channelList.map((ch) => {
                const isSelected = salesChannel === ch.id;
                return (
                  <button
                    key={ch.id}
                    type="button"
                    onClick={() => {
                      hapticImpact('light');
                      setSalesChannel(ch.id);
                    }}
                    className={`p-2.5 rounded-xl border text-xs text-center transition-all flex items-center justify-center space-x-1.5 ${
                      isSelected
                        ? 'bg-brand-700 text-white border-brand-700 font-bold shadow-soft'
                        : 'bg-white dark:bg-slate-800/60 border-slate-200/80 dark:border-slate-700/80 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <span>{ch.emoji}</span>
                    <span>{ch.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Action Footer */}
        <div className="p-4 bg-slate-50/80 dark:bg-slate-900/90 border-t border-slate-200/80 dark:border-slate-800 flex-shrink-0 space-y-2">
          <button
            type="button"
            onClick={handleSave}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-brand-700 to-brand-800 hover:from-brand-800 hover:to-brand-900 text-white font-bold text-xs shadow-soft transition-all active:scale-98 flex items-center justify-center space-x-2"
          >
            <Sparkles className="w-4 h-4 text-teal-200" />
            <span>
              {isOnboarding
                ? (lang === 'uz' ? 'Saqlash va boshlash ✨' : 'Сохранить и начать работу ✨')
                : (lang === 'uz' ? 'O\'zgarishlarni saqlash' : 'Сохранить настройки')}
            </span>
          </button>

          {!isOnboarding && (
            <button
              type="button"
              onClick={() => {
                if (window.confirm(lang === 'uz' ? "Barcha ma'lumotlarni tozalab, boshidan boshlaysizmi?" : "Очистить персонализацию и тур, чтобы начать с нуля?")) {
                  localStorage.clear();
                  window.location.reload();
                }
              }}
              className="w-full py-1 text-center text-[10px] font-semibold text-rose-500 hover:text-rose-700 transition-colors"
            >
              {lang === 'uz' ? "🔄 Holatni tozalash (Demo boshidan boshlash)" : "🔄 Сбросить состояние (начать с чистого листа)"}
            </button>
          )}

          {isOnboarding && (
            <button
              type="button"
              onClick={handleSkip}
              className="w-full py-1 text-center text-[11px] font-medium text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            >
              {lang === 'uz' ? 'Standart sozlamalar bilan davom etish' : 'Пропустить и продолжить со стандартными настройками'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
