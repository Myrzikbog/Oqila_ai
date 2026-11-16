import React, { useState, useEffect, useRef } from 'react';
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
import { getTelegramUser, hapticImpact, hapticNotify, showConfirm } from '../utils/telegram';
import { useTelegramBackButton } from '../utils/useTelegram';
import { useDialog } from '../utils/useDialog';
import { clearStorage } from '../utils/storage';
import { saveProfileToBackend } from '../utils/auth';
import Collapsible from './Collapsible';
import BrandSettings from './studio/BrandSettings';

export default function ProfileModal({
  isOpen,
  onClose,
  isOnboarding = false,
  profile,
  userId,
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
      setSalesChannel(profile.salesChannel || profile.sales_channel || 'uzum');
    } else if (tgUser?.first_name) {
      setName(tgUser.first_name);
    }
  }, [profile, isOpen]);

  useTelegramBackButton(isOpen, onClose);
  const dialogRef = useRef(null);
  useDialog(isOpen, onClose, dialogRef);
  if (!isOpen) return null;

  const handleSave = async () => {
    hapticNotify('success');
    const updatedProfile = {
      name: name.trim() || (t.ui_profilemodal_1),
      status,
      category,
      salesChannel,
      lang,
      onboardingCompleted: true,
      updatedAt: new Date().toISOString(),
    };
    if (userId) {
      saveProfileToBackend(userId, updatedProfile);
    }
    onSave(updatedProfile);
    onClose();
  };

  const handleSkip = () => {
    hapticImpact('light');
    const defaultProfile = {
      name: name.trim() || (t.ui_profilemodal_2),
      status: 'self_employed',
      category: 'sewing',
      salesChannel: 'uzum',
      lang,
      onboardingCompleted: true,
      updatedAt: new Date().toISOString(),
    };
    if (userId) {
      saveProfileToBackend(userId, defaultProfile);
    }
    onSave(defaultProfile);
    onClose();
  };

  const STATUS_OPTIONS_RU = [
    {
      id: 'self_employed',
      icon: UserCheck,
      color: 'emerald',
      title: 'Самозанятая (1% налог)',
      desc: 'Свои изделия и услуги из перечня (1% налог с оборота). Нанимать работников нельзя; обычная перепродажа исключена из перечня с 2026 г.',
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
      desc: 'O\'z mahsulotlari va ro\'yxatdagi xizmatlar (1% aylanmadan soliq). Ishchi yollash mumkin emas; oddiy qayta sotish 2026-yildan ro\'yxatdan chiqarilgan.',
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
    <div ref={dialogRef} role="dialog" aria-modal="true" aria-label={t.dialog_profile} tabIndex={-1} className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-900/60 dark:bg-black/75 backdrop-blur-sm animate-in duration-200">
      <div 
        className="w-full max-w-md bg-white dark:bg-slate-900 rounded-t-3xl sm:rounded-3xl border border-slate-200/90 dark:border-slate-800 shadow-2xl overflow-hidden max-h-[92vh] flex flex-col transition-all duration-200 animate-in duration-300"
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
                  ? (t.ui_profilemodal_3)
                  : (t.ui_profilemodal_4)}
              </h3>
              <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
                {isOnboarding
                  ? (t.ui_profilemodal_5)
                  : (t.ui_profilemodal_6)}
              </p>
              {userId && (
                <div className="inline-flex items-center space-x-1 mt-1 px-2 py-0.5 rounded-full bg-teal-500/20 border border-teal-400/30 text-[9.5px] text-teal-200 font-medium">
                  <Check className="w-2.5 h-2.5 text-teal-300" />
                  <span>{t.ui_profilemodal_7}</span>
                </div>
              )}
            </div>
          </div>

          {!isOnboarding && (
            <button
              type="button"
              onClick={() => {
                hapticImpact('light');
                onClose();
              }}
              className="p-1 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors ml-2"
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
              <span>{t.ui_profilemodal_8}</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t.ui_profilemodal_9}
              className="w-full text-xs px-3.5 py-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-900 dark:text-white placeholder-slate-400 font-medium"
            />
          </div>

          {/* Section 1: Legal Status */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center justify-between">
              <span>{t.ui_profilemodal_10}</span>
              <span className="text-xs font-normal text-slate-500">
                {t.ui_profilemodal_11}
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
              {t.ui_profilemodal_12}
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
                        ? 'bg-brand-50/80 dark:bg-teal-950/40 border-brand-500 dark:border-teal-400 text-brand-900 dark:text-teal-200 font-bold ring-1 ring-brand-500/20 shadow-sm'
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
              {t.ui_profilemodal_13}
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
          {/* Brand: shop name, contacts, colour and logo for every picture with text */}
          {!isOnboarding && (
            <Collapsible icon={Store} title={t.ui_profilemodal_14}
              summary={t.ui_profilemodal_15}>
              <div className="px-4 pb-4"><BrandSettings lang={lang} /></div>
            </Collapsible>
          )}
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
                ? (t.ui_profilemodal_16)
                : (t.ui_profilemodal_17)}
            </span>
          </button>

          {!isOnboarding && (
            <button
              type="button"
              onClick={async () => {
                if (await showConfirm(t.ui_profilemodal_18)) {
                  clearStorage();
                  window.location.reload();
                }
              }}
              className="w-full py-1 text-center text-xs font-semibold text-rose-500 hover:text-rose-700 transition-colors"
            >
              {t.ui_profilemodal_19}
            </button>
          )}

          {isOnboarding && (
            <button
              type="button"
              onClick={handleSkip}
              className="w-full py-1 text-center text-[11px] font-medium text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            >
              {t.ui_profilemodal_20}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
