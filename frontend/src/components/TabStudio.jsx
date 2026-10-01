import React, { useState, useRef, useEffect } from 'react';
import { 
  Sparkles, 
  ImagePlus, 
  Zap, 
  Copy, 
  Check, 
  Share2, 
  Trash2, 
  Lightbulb, 
  Tag, 
  Banknote, 
  FileText,
  Camera,
  Download,
  RotateCcw,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Layers,
  Palette,
  Sun,
  ShoppingBag,
  Crown,
  Heart,
  Send,
  Eye,
  History,
  AlertTriangle,
  X
} from 'lucide-react';
import { hapticImpact, hapticNotify, openTelegramShare } from '../utils/telegram';
import { fireConfetti } from '../utils/confetti';

const DEFAULT_PROMPTS = {
  ru: {
    minimal_studio: "Студийный свет, нейтральный светлый подиум, мягкие тени, профессиональная предметная съёмка 8k",
    uzbek_heritage: "Традиционный узбекский интерьер, резное дерево, фон с текстурой иката, теплое мягкое освещение",
    uzum_catalog: "Белоснежный изолированный фон, равномерный e-commerce свет, четкие детали, маркетплейс Uzum",
    luxury_dark: "Премиальный тёмный мрамор, драматичный акцентный свет, глубокие тени, золотистые блики",
    natural_light: "Мягкий утренний солнечный свет, фактура натурального дерева, зелень и боке на фоне",
    custom: "",
  },
  uz: {
    minimal_studio: "Studiya nuri, neytral yorug' podium, yumshoq soyalar, professional 8k katalog fotosurati",
    uzbek_heritage: "An'anaviy o'zbek milliy interyeri, o'ymakor yog'och, fonida ipak xon-atlas va ikat jilosi, iliq nur",
    uzum_catalog: "Oppoq fon, bir tekis e-commerce yorug'ligi, aniq detallar, Uzum marketpleys 1:1 standarti",
    luxury_dark: "Hashamatli qora marmar, dramatik yorug'lik nuri, chuqur soyalar, tillarang jilo, butik uslubi",
    natural_light: "Tonggi mayin quyosh nuri, tabiiy yog'och fakturasi, orqa fonda yashil barglar va boke effekti",
    custom: "",
  }
};

export default function TabStudio({ lang, t, onOpenHistory, externalCardToLoad, userId }) {
  // Form State
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [costPrice, setCostPrice] = useState('');
  const [desiredPrice, setDesiredPrice] = useState('');
  const [note, setNote] = useState('');
  
  // Customization Presets & Custom Prompt
  const [photoshootStyle, setPhotoshootStyle] = useState('minimal_studio');
  const [photoshootPrompt, setPhotoshootPrompt] = useState(() => {
    return DEFAULT_PROMPTS[lang]?.minimal_studio || DEFAULT_PROMPTS.ru.minimal_studio;
  });
  const [contentTone, setContentTone] = useState('luxury');
  const [contentFormat, setContentFormat] = useState('instagram');
  const [generatePhoto, setGeneratePhoto] = useState(true);

  // Sync prompt default when language changes if not customized
  useEffect(() => {
    if (photoshootStyle !== 'custom') {
      const def = DEFAULT_PROMPTS[lang]?.[photoshootStyle] || DEFAULT_PROMPTS.ru[photoshootStyle] || '';
      setPhotoshootPrompt(def);
    }
  }, [lang, photoshootStyle]);

  // UI Flow State
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [isFormCollapsed, setIsFormCollapsed] = useState(false);
  const [activePhotoView, setActivePhotoView] = useState('studio'); // 'studio' | 'original'
  const [copied, setCopied] = useState(false);
  const [copiedTag, setCopiedTag] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const resultRef = useRef(null);

  // Smooth multi-step animated progress simulation (Item 10)
  useEffect(() => {
    let interval;
    if (isLoading) {
      setLoadingProgress(15);
      interval = setInterval(() => {
        setLoadingProgress((prev) => {
          if (prev < 40) return prev + 4;
          if (prev < 72) return prev + 2;
          if (prev < 94) return prev + 1;
          return prev;
        });
      }, 300);
    } else {
      setLoadingProgress(0);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  useEffect(() => {
    if (externalCardToLoad) {
      setResult(externalCardToLoad);
      setIsFormCollapsed(true);
      if (externalCardToLoad.studio_photo_url) {
        setActivePhotoView('studio');
      } else {
        setActivePhotoView('original');
      }
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [externalCardToLoad]);

  // Preset definitions with preview tags (Item 9)
  const PHOTO_STYLES = [
    { id: 'minimal_studio', label: t.style_minimal_studio || 'Студийный свет', icon: Camera, tag: 'Каталог' },
    { id: 'uzbek_heritage', label: t.style_uzbek_heritage || 'Восточный колорит', icon: Sparkles, tag: 'Икат/Атлас' },
    { id: 'uzum_catalog', label: t.style_uzum_catalog || 'Uzum (белый)', icon: ShoppingBag, tag: '100% белый' },
    { id: 'luxury_dark', label: t.style_luxury_dark || 'Luxury тёмный', icon: Crown, tag: 'Премиум' },
    { id: 'natural_light', label: t.style_natural_light || 'Природный свет', icon: Sun, tag: 'Эко/Лайф' },
    { id: 'custom', label: t.style_custom || 'Свой промпт', icon: SlidersHorizontal, tag: 'Свободный' },
  ];

  const handleStyleSelect = (styleId) => {
    hapticImpact('light');
    setPhotoshootStyle(styleId);
    if (styleId === 'custom') {
      const prevDef = DEFAULT_PROMPTS[lang]?.[photoshootStyle] || DEFAULT_PROMPTS.ru[photoshootStyle];
      if (photoshootPrompt === prevDef) {
        setPhotoshootPrompt('');
      }
    } else {
      const def = DEFAULT_PROMPTS[lang]?.[styleId] || DEFAULT_PROMPTS.ru[styleId] || '';
      setPhotoshootPrompt(def);
    }
  };

  const TONES = [
    { id: 'luxury', label: t.tone_luxury || 'Премиум', icon: Crown },
    { id: 'friendly', label: t.tone_friendly || 'Душевный', icon: Heart },
    { id: 'sales', label: t.tone_sales || 'Продающий', icon: Zap },
    { id: 'craft', label: t.tone_craft || 'Ремесленный', icon: Palette },
  ];

  const FORMATS = [
    { id: 'instagram', label: t.format_instagram || 'Instagram', icon: Sparkles },
    { id: 'telegram', label: t.format_telegram || 'Telegram', icon: Send },
    { id: 'uzum', label: t.format_uzum || 'Uzum Market', icon: ShoppingBag },
  ];

  // File upload handling
  const handleFileChange = (file) => {
    if (!file || !file.type.startsWith('image/')) return;
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage(t.file_too_large || 'Размер файла превышает 10 МБ');
      hapticNotify('error');
      return;
    }
    setErrorMessage('');
    hapticImpact('light');
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const clearImage = (e) => {
    e?.stopPropagation();
    hapticImpact('medium');
    setImageFile(null);
    setImagePreview(null);
    setErrorMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Reset entire form for next product
  const handleResetForm = () => {
    hapticImpact('medium');
    setImageFile(null);
    setImagePreview(null);
    setCostPrice('');
    setDesiredPrice('');
    setNote('');
    setPhotoshootStyle('minimal_studio');
    setPhotoshootPrompt(DEFAULT_PROMPTS[lang]?.minimal_studio || DEFAULT_PROMPTS.ru.minimal_studio);
    setResult(null);
    setErrorMessage('');
    setIsFormCollapsed(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Quick Demo Call
  const handleQuickDemo = async () => {
    hapticImpact('medium');
    setIsLoading(true);
    setResult(null);
    setErrorMessage('');
    setLoadingStep(lang === 'uz' ? "Mahsulot modeli yuklanmoqda..." : "Загрузка образца изделия...");

    try {
      const res = await fetch(`/api/demo-card?lang=${lang}`);
      if (!res.ok) {
        throw new Error(t.error_network || 'Ошибка загрузки демо');
      }
      const data = await res.json();
      setResult(data);
      setIsFormCollapsed(true);
      setLoadingProgress(100);
      if (data.studio_photo_url) {
        setActivePhotoView('studio');
      }
      hapticNotify('success');
      fireConfetti();
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err) {
      console.error(err);
      setErrorMessage(err.message || t.error_network || 'Ошибка загрузки демо');
      hapticNotify('error');
    } finally {
      setIsLoading(false);
    }
  };

  // Full AI Generation with Photoshoot
  const handleGenerate = async () => {
    hapticImpact('heavy');
    setIsLoading(true);
    setResult(null);
    
    if (generatePhoto) {
      if (imageFile) {
        setLoadingStep(
          lang === 'uz'
            ? "Oqila AI: tahlil va studiya fotosessiyasi yaratilmoqda..."
            : "Oqila AI: анализ изделия и студийная фотосессия..."
        );
      } else {
        setLoadingStep(
          lang === 'uz'
            ? "Oqila AI: tavsif bo'yicha fotosessiya va matn tayyorlanmoqda..."
            : "Oqila AI: генерация товара и студийного фото по описанию..."
        );
      }
    } else {
      setLoadingStep(
        lang === 'uz'
          ? "Oqila AI matnni tayyorlamoqda..."
          : "Oqila AI создаёт карточку..."
      );
    }

    const formData = new FormData();
    if (imageFile) formData.append('image', imageFile);
    if (costPrice) formData.append('cost_price', costPrice.replace(/\D/g, ''));
    if (desiredPrice) formData.append('desired_price', desiredPrice.replace(/\D/g, ''));
    if (note) formData.append('note', note);
    formData.append('lang', lang);
    formData.append('photoshoot_style', photoshootStyle);
    if (photoshootPrompt) formData.append('photoshoot_prompt', photoshootPrompt);
    formData.append('content_tone', contentTone);
    formData.append('content_format', contentFormat);
    formData.append('generate_photo', generatePhoto ? 'true' : 'false');
    if (userId) formData.append('user_id', userId);

    try {
      setErrorMessage('');
      const res = await fetch('/api/generate-card', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errPayload = await res.json().catch(() => ({}));
        throw new Error(errPayload.detail || t.error_network || 'Ошибка сервера при генерации');
      }
      const data = await res.json();
      setResult(data);
      setErrorMessage('');
      setLoadingProgress(100);
      setIsFormCollapsed(true);
      if (data.studio_photo_url) {
        setActivePhotoView('studio');
      } else {
        setActivePhotoView('original');
      }
      hapticNotify('success');
      fireConfetti();
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 150);
    } catch (err) {
      console.error(err);
      setErrorMessage(err.message || t.error_network || 'Не удалось сгенерировать карточку');
      hapticNotify('error');
    } finally {
      setIsLoading(false);
    }
  };

  const copyFullPost = async () => {
    if (!result) return;
    hapticImpact('medium');
    const tags = (result.hashtags || []).join(' ');
    const text = `${result.title}\n\n${result.description}\n\n${result.price_tag}\n\n${tags}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      hapticNotify('success');
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.error(err);
    }
  };

  const copySingleTag = (tag) => {
    navigator.clipboard.writeText(tag);
    hapticImpact('light');
    setCopiedTag(tag);
    setTimeout(() => setCopiedTag(null), 1500);
  };

  const downloadStudioPhoto = () => {
    if (!result?.studio_photo_url) return;
    hapticImpact('light');
    const link = document.createElement('a');
    link.href = result.studio_photo_url;
    link.download = `oqila_studio_${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full space-y-4">
      {/* Top Banner Header */}
      <div className="glass-card rounded-2xl p-4 border-l-4 border-l-brand-600 dark:border-l-brand-400 bg-gradient-to-r from-teal-50/70 via-white to-white dark:from-teal-950/30 dark:via-slate-900 dark:to-slate-900 transition-colors">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-brand-800 dark:text-teal-300">
            <Sparkles className="w-5 h-5 text-brand-600 dark:text-teal-400 flex-shrink-0" />
            <h2 className="font-bold text-sm tracking-tight">{t.studio_title}</h2>
          </div>
          <button
            type="button"
            onClick={() => {
              hapticImpact('light');
              onOpenHistory?.();
            }}
            className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-xl bg-white/80 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200/80 dark:border-slate-700/80 shadow-xs text-xs font-bold transition-all active:scale-95"
            title={t.history_title}
          >
            <History className="w-3.5 h-3.5 text-brand-600 dark:text-teal-400" />
            <span>{t.history_btn}</span>
          </button>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
          {t.studio_subtitle}
        </p>
      </div>

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="glass-card rounded-2xl p-3.5 border-l-4 border-l-rose-500 bg-rose-50/80 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-500 flex-shrink-0" />
            <span className="font-medium">{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage('')}
            className="p-1 rounded-lg text-rose-500 hover:bg-rose-100 dark:hover:bg-rose-900/40 transition-colors ml-2"
            aria-label="Close error"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Collapsed Bar (when result is present and form is collapsed) */}
      {result && isFormCollapsed && (
        <div className="glass-card rounded-2xl p-3.5 flex items-center justify-between transition-all border border-brand-200/60 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 shadow-sm">
          <div className="flex items-center space-x-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-brand-600 dark:text-teal-400 flex items-center justify-center flex-shrink-0">
              <Check className="w-4 h-4 stroke-[2.5]" />
            </div>
            <div className="truncate">
              <p className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                {result.title || t.result_title}
              </p>
              <p className="text-[11px] text-slate-400 dark:text-slate-500">
                {t.form_collapsed_hint}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-1.5 flex-shrink-0 ml-2">
            <button
              type="button"
              onClick={() => {
                hapticImpact('light');
                setIsFormCollapsed(false);
              }}
              className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all text-xs font-medium flex items-center space-x-1"
              title={t.edit_params_btn}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <ChevronDown className="w-3 h-3" />
            </button>
            <button
              type="button"
              onClick={handleResetForm}
              className="py-1.5 px-2.5 rounded-xl bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-teal-300 hover:bg-brand-100 dark:hover:bg-brand-900/60 font-semibold text-xs transition-all flex items-center space-x-1 border border-brand-200/70 dark:border-brand-800/60"
            >
              <RotateCcw className="w-3 h-3" />
              <span>{t.new_product_btn}</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Input Form (Collapsible) */}
      {(!result || !isFormCollapsed) && (
        <div className="glass-card rounded-2xl p-4 sm:p-5 space-y-4 transition-all">
          {/* Header row when expanding/collapsing */}
          {result && (
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center space-x-1.5">
                <SlidersHorizontal className="w-3.5 h-3.5 text-brand-600 dark:text-teal-400" />
                <span>{t.photoshoot_options_title}</span>
              </span>
              <button
                type="button"
                onClick={() => {
                  hapticImpact('light');
                  setIsFormCollapsed(true);
                }}
                className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 flex items-center space-x-0.5"
              >
                <span>{t.collapse_form || 'Свернуть'}</span>
                <ChevronUp className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Photo Dropzone / Preview */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files[0];
              if (f) handleFileChange(f);
            }}
            className={`relative border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all duration-200 ${
              imagePreview 
                ? 'border-brand-500 bg-brand-50/20 dark:bg-brand-950/20' 
                : 'border-slate-300 dark:border-slate-700 hover:border-brand-500 dark:hover:border-teal-400 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-white dark:hover:bg-slate-800/70'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files[0])}
            />

            {imagePreview ? (
              <div className="relative group">
                <img
                  src={imagePreview}
                  alt="Product preview"
                  className="w-full h-44 object-cover rounded-lg shadow-sm"
                />
                <button
                  type="button"
                  onClick={clearImage}
                  className="absolute top-2 right-2 bg-slate-900/80 hover:bg-slate-900 text-white p-1.5 rounded-full shadow-md transition-all active:scale-95"
                  title={t.remove_photo}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="py-4 flex flex-col items-center justify-center space-y-2 text-slate-500 dark:text-slate-400">
                <div className="w-12 h-12 rounded-full bg-brand-50 dark:bg-slate-800 text-brand-600 dark:text-teal-400 flex items-center justify-center">
                  <ImagePlus className="w-6 h-6 stroke-[1.75]" />
                </div>
                <div className="text-xs">
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{t.upload_drop}</span>
                  <span className="block text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">{t.upload_hint}</span>
                </div>
              </div>
            )}
          </div>

          {/* Direct Camera Button & Hidden Camera Input (Item 7) */}
          <div className="flex items-center justify-between text-xs pt-1">
            <button
              type="button"
              onClick={() => {
                hapticImpact('light');
                cameraInputRef.current?.click();
              }}
              className="w-full py-2 px-3 rounded-xl border border-dashed border-teal-300 dark:border-teal-800 bg-teal-50/60 dark:bg-teal-950/40 text-teal-800 dark:text-teal-300 hover:bg-teal-100/70 font-bold text-xs flex items-center justify-center space-x-2 transition-all active:scale-[0.98]"
            >
              <Camera className="w-4 h-4 text-brand-600 dark:text-teal-400" />
              <span>{lang === 'uz' ? "Kameradan rasmga olish" : "Снять на камеру прямо сейчас"}</span>
            </button>
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => handleFileChange(e.target.files?.[0])}
              className="hidden"
            />
          </div>

          {/* AI Photoshoot Toggle (when image is uploaded) */}
          <div className="p-3 rounded-xl bg-teal-50/50 dark:bg-teal-950/30 border border-teal-100 dark:border-teal-900/50 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <Camera className="w-4 h-4 text-brand-600 dark:text-teal-400 flex-shrink-0" />
              <div>
                <p className="text-xs font-bold text-slate-900 dark:text-slate-100">
                  {t.ai_photoshoot_toggle}
                </p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">
                  {t.ai_photoshoot_hint}
                </p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-3 flex-shrink-0">
              <input
                type="checkbox"
                checked={generatePhoto}
                onChange={(e) => {
                  hapticImpact('light');
                  setGeneratePhoto(e.target.checked);
                }}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-slate-600 peer-checked:bg-brand-600 dark:peer-checked:bg-teal-500"></div>
            </label>
          </div>

          {/* Photoshoot Style Selector (Pill chips) */}
          {generatePhoto && (
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1.5">
                <Palette className="w-3.5 h-3.5 text-brand-600 dark:text-teal-400" />
                <span>{t.style_label}</span>
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                {PHOTO_STYLES.map((style) => {
                  const Icon = style.icon;
                  const isSelected = photoshootStyle === style.id;
                  return (
                    <button
                      key={style.id}
                      type="button"
                      onClick={() => handleStyleSelect(style.id)}
                      className={`p-2 rounded-xl text-left flex flex-col justify-between border transition-all text-xs font-medium ${
                        isSelected
                          ? 'bg-brand-600 text-white border-brand-600 shadow-sm ring-1 ring-brand-500/30'
                          : 'bg-slate-50 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center space-x-1.5 w-full">
                        <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${isSelected ? 'text-teal-200' : 'text-slate-400 dark:text-slate-500'}`} />
                        <span className="truncate font-bold text-[11px]">{style.label}</span>
                      </div>
                      {style.tag && (
                        <span className={`text-[8.5px] font-bold mt-1 px-1.5 py-0.2 rounded w-fit ${
                          isSelected ? 'bg-brand-700/80 text-teal-100' : 'bg-slate-200/80 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                        }`}>
                          {style.tag}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Editable Photoshoot Prompt Field */}
              <div className="space-y-1 pt-1">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 flex items-center space-x-1">
                    <SlidersHorizontal className="w-3 h-3 text-brand-600 dark:text-teal-400" />
                    <span>{t.photoshoot_prompt_label}</span>
                  </label>
                  {photoshootStyle !== 'custom' && (
                    <button
                      type="button"
                      onClick={() => {
                        hapticImpact('light');
                        const def = DEFAULT_PROMPTS[lang]?.[photoshootStyle] || DEFAULT_PROMPTS.ru[photoshootStyle] || '';
                        setPhotoshootPrompt(def);
                      }}
                      className="text-[10px] text-slate-400 hover:text-brand-600 dark:hover:text-teal-400 flex items-center space-x-1 transition-colors"
                      title={t.reset_prompt}
                    >
                      <RotateCcw className="w-2.5 h-2.5" />
                      <span>{t.reset_prompt}</span>
                    </button>
                  )}
                </div>
                <textarea
                  value={photoshootPrompt}
                  onChange={(e) => setPhotoshootPrompt(e.target.value)}
                  rows={2}
                  placeholder={t.photoshoot_prompt_placeholder}
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white resize-none transition-colors"
                />
              </div>
            </div>
          )}

          {/* Content Tone & Platform Format Selectors */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Tone Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                <Crown className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />
                <span>{t.tone_label}</span>
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {TONES.map((tone) => {
                  const isSelected = contentTone === tone.id;
                  return (
                    <button
                      key={tone.id}
                      type="button"
                      onClick={() => {
                        hapticImpact('light');
                        setContentTone(tone.id);
                      }}
                      className={`py-1.5 px-2 rounded-xl text-center border text-xs font-medium transition-all ${
                        isSelected
                          ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 border-slate-900 dark:border-white shadow-sm'
                          : 'bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      {tone.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Platform Format Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                <Send className="w-3.5 h-3.5 text-sky-500 dark:text-sky-400" />
                <span>{t.format_label}</span>
              </label>
              <div className="grid grid-cols-3 gap-1">
                {FORMATS.map((fmt) => {
                  const isSelected = contentFormat === fmt.id;
                  return (
                    <button
                      key={fmt.id}
                      type="button"
                      onClick={() => {
                        hapticImpact('light');
                        setContentFormat(fmt.id);
                      }}
                      className={`py-1.5 px-1 rounded-xl text-center border text-[11px] font-semibold transition-all truncate ${
                        isSelected
                          ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                          : 'bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      {fmt.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Pricing Inputs Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1 mb-1">
                <Banknote className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                <span>{t.cost_price}</span>
              </label>
              <div className="relative">
                <input
                  type="tel"
                  inputMode="numeric"
                  value={costPrice}
                  onChange={(e) => setCostPrice(e.target.value)}
                  placeholder={t.cost_price_placeholder}
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white"
                />
                <span className="absolute right-2.5 top-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase">
                  {t.currency}
                </span>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1 mb-1">
                <Tag className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                <span>{t.desired_price}</span>
              </label>
              <div className="relative">
                <input
                  type="tel"
                  inputMode="numeric"
                  value={desiredPrice}
                  onChange={(e) => setDesiredPrice(e.target.value)}
                  placeholder={t.desired_price_placeholder}
                  className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white"
                />
                <span className="absolute right-2.5 top-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase">
                  {t.currency}
                </span>
              </div>
            </div>
          </div>

          {/* Product Note / Description Textarea */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                <FileText className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                <span>{t.product_desc_label || t.product_note}</span>
              </label>
              {!imagePreview && (
                <span className="text-[10px] font-semibold text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/60 px-2 py-0.5 rounded-full border border-teal-200/50 dark:border-teal-800/50">
                  {lang === 'uz' ? "Tavsif bo'yicha yaratish" : "Генерация по описанию"}
                </span>
              )}
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder={t.product_desc_hint || t.product_note_placeholder}
              className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white resize-none"
            />
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-1 gap-2 pt-1">
            <button
              type="button"
              disabled={isLoading || (!imageFile && !note.trim())}
              onClick={handleGenerate}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-brand-700 via-brand-600 to-teal-600 hover:from-brand-800 hover:to-teal-700 text-white font-bold text-xs shadow-md shadow-brand-700/20 flex items-center justify-center space-x-2 transition-all active:scale-[0.98] disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-teal-200" />
              <span>
                {!imageFile && note.trim()
                  ? (lang === 'uz' ? "Tavsif bo'yicha yaratish" : "Сгенерировать по описанию")
                  : t.btn_generate}
              </span>
            </button>

            <button
              type="button"
              disabled={isLoading}
              onClick={handleQuickDemo}
              className="w-full py-2 px-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 hover:bg-amber-100/80 dark:hover:bg-amber-900/60 border border-amber-200 dark:border-amber-800/60 text-amber-900 dark:text-amber-300 font-semibold text-xs flex items-center justify-center space-x-2 transition-all active:scale-[0.98]"
            >
              <Zap className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              <span>{t.btn_demo}</span>
            </button>
          </div>
        </div>
      )}

      {/* Live Animated Multi-Step Progress Bar (Item 10) */}
      {isLoading && (
        <div className="glass-card rounded-2xl p-5 space-y-4 border border-brand-300 dark:border-teal-800 shadow-md">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-extrabold text-brand-800 dark:text-teal-300 flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-brand-600 dark:text-teal-400 animate-spin" />
                <span>{loadingStep || t.generating_title}</span>
              </span>
              <span className="font-black text-brand-700 dark:text-teal-300">{loadingProgress}%</span>
            </div>

            {/* Gradient Animated Progress Bar */}
            <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden shadow-inner">
              <div 
                className="h-full bg-gradient-to-r from-teal-500 via-emerald-400 to-teal-600 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${loadingProgress}%` }}
              />
            </div>

            {/* 3 Step Indicators */}
            <div className="grid grid-cols-3 gap-1.5 pt-1 text-[10px]">
              <div className={`p-1.5 rounded-lg border text-center transition-all ${
                loadingProgress >= 20 
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/60 font-bold text-brand-900 dark:text-teal-200' 
                  : 'border-slate-200 dark:border-slate-800 text-slate-400'
              }`}>
                1. 🔍 Tahlil
              </div>
              <div className={`p-1.5 rounded-lg border text-center transition-all ${
                loadingProgress >= 55 
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/60 font-bold text-brand-900 dark:text-teal-200' 
                  : 'border-slate-200 dark:border-slate-800 text-slate-400'
              }`}>
                2. ✍️ Matn
              </div>
              <div className={`p-1.5 rounded-lg border text-center transition-all ${
                loadingProgress >= 80 
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/60 font-bold text-brand-900 dark:text-teal-200' 
                  : 'border-slate-200 dark:border-slate-800 text-slate-400'
              }`}>
                3. 📸 Fotosessiya
              </div>
            </div>
          </div>

          <div className="aspect-square w-full rounded-2xl animate-shimmer" />
        </div>
      )}

      {/* Result Card Preview */}
      {result && !isLoading && (
        <div 
          ref={resultRef}
          className="w-full glass-card rounded-2xl p-4 sm:p-5 border border-brand-200/80 dark:border-slate-800 shadow-soft space-y-4"
        >
          {/* Header Row */}
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <span className="text-xs font-bold text-brand-800 dark:text-teal-300 flex items-center space-x-1.5">
              <Check className="w-4 h-4 text-brand-600 dark:text-teal-400" />
              <span>{t.result_title}</span>
            </span>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-50 dark:bg-brand-950/80 text-brand-700 dark:text-teal-300 border border-brand-200 dark:border-brand-800">
                {t.ready_to_post || 'Ready to Post'}
              </span>
            </div>
          </div>

          {/* Photo Section: AI Studio Shoot + Original Toggle */}
          {(result.studio_photo_url || imagePreview) && (
            <div className="space-y-2">
              {/* Photo View Switcher if both are available */}
              {result.studio_photo_url && imagePreview && (
                <div className="flex items-center justify-between bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl">
                  <button
                    type="button"
                    onClick={() => {
                      hapticImpact('light');
                      setActivePhotoView('studio');
                    }}
                    className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center space-x-1.5 transition-all ${
                      activePhotoView === 'studio'
                        ? 'bg-white dark:bg-slate-900 text-brand-700 dark:text-teal-300 shadow-sm'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <Sparkles className="w-3.5 h-3.5 text-brand-600 dark:text-teal-400" />
                    <span>{t.view_studio_photo}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      hapticImpact('light');
                      setActivePhotoView('original');
                    }}
                    className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all ${
                      activePhotoView === 'original'
                        ? 'bg-white dark:bg-slate-900 text-slate-800 dark:text-white shadow-sm'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5 text-slate-400" />
                    <span>{t.view_original_photo}</span>
                  </button>
                </div>
              )}

              {/* Main Photo Display with Aspect 1:1 for Studio */}
              <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 shadow-sm group">
                <img
                  src={
                    activePhotoView === 'studio' && result.studio_photo_url
                      ? result.studio_photo_url
                      : (imagePreview || result.studio_photo_url)
                  }
                  alt={result.title}
                  className="w-full aspect-square object-cover"
                />

                {/* Badge Overlay */}
                <div className="absolute top-2.5 left-2.5">
                  {activePhotoView === 'studio' && result.studio_photo_url ? (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-900/80 backdrop-blur-md text-teal-300 border border-teal-500/30 shadow-md">
                      <Sparkles className="w-3 h-3 text-teal-400" />
                      <span>{imagePreview ? (t.studio_photo_badge || 'AI Студийное фото') : (lang === 'uz' ? "AI fotosurat (tavsif bo'yicha)" : "AI фото по описанию")}</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-900/80 backdrop-blur-md text-white/90 shadow-md">
                      <span>{t.original_photo_badge || 'Оригинал'}</span>
                    </span>
                  )}
                </div>

                {/* Download Button Overlay for Studio Photo */}
                {activePhotoView === 'studio' && result.studio_photo_url && (
                  <button
                    type="button"
                    onClick={downloadStudioPhoto}
                    className="absolute top-2.5 right-2.5 p-2 rounded-xl bg-slate-900/80 hover:bg-slate-900 backdrop-blur-md text-white shadow-md transition-all active:scale-95"
                    title={t.download_photo}
                  >
                    <Download className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Title & Description */}
          <div className="space-y-2 text-left">
            <h3 className="font-extrabold text-sm sm:text-base text-slate-900 dark:text-white leading-snug">
              {result.title}
            </h3>
            <p className="text-xs text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">
              {result.description}
            </p>
          </div>

          {/* Price Badge */}
          <div className="flex items-center space-x-2 p-2.5 rounded-xl bg-teal-50 dark:bg-teal-950/50 border border-teal-200/60 dark:border-teal-800/60">
            <Banknote className="w-4 h-4 text-brand-700 dark:text-teal-400 flex-shrink-0" />
            <span className="text-xs font-extrabold text-brand-900 dark:text-teal-200 tracking-tight">
              {result.price_tag}
            </span>
          </div>

          {/* Hashtags Chips */}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {(result.hashtags || []).map((tag, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => copySingleTag(tag)}
                className={`text-[11px] font-medium px-2.5 py-1 rounded-lg border transition-all ${
                  copiedTag === tag
                    ? 'bg-brand-600 text-white border-brand-600'
                    : 'bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-200/80 dark:border-slate-700'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>

          {/* Marketing Tip Callout */}
          {result.marketing_tip && (
            <div className="p-3 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-900/50 space-y-1 text-left">
              <div className="flex items-center space-x-1.5 text-amber-900 dark:text-amber-300 font-bold text-xs">
                <Lightbulb className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                <span>{t.marketing_tip_title}</span>
              </div>
              <p className="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                {result.marketing_tip}
              </p>
            </div>
          )}

          {/* Primary Action Buttons */}
          <div className="grid grid-cols-2 gap-2 pt-2">
            <button
              type="button"
              onClick={copyFullPost}
              className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center space-x-1.5 border transition-all active:scale-[0.98] ${
                copied
                  ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                  : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700'
              }`}
            >
              {copied ? <Check className="w-4 h-4 text-white" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? t.copied : t.copy_post}</span>
            </button>

            <button
              type="button"
              onClick={() => {
                const tags = (result.hashtags || []).join(' ');
                const text = `${result.title}\n\n${result.description}\n\n${result.price_tag}\n\n${tags}`;
                openTelegramShare(text);
              }}
              className="py-2.5 px-3 rounded-xl font-bold text-xs bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-700 hover:to-blue-700 text-white flex items-center justify-center space-x-1.5 shadow-sm transition-all active:scale-[0.98]"
            >
              <Share2 className="w-4 h-4" />
              <span>{t.share_telegram}</span>
            </button>
          </div>

          {/* Bottom helper: Create Another Product button */}
          <div className="pt-2 text-center">
            <button
              type="button"
              onClick={handleResetForm}
              className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-teal-400 transition-colors py-1.5 px-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/60"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>{t.new_product_btn}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
