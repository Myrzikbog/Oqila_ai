import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Scale,
  Send,
  ExternalLink,
  Bot,
  User,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  KeyRound,
  Building2,
  UserCheck,
  Award,
  Receipt,
  ShoppingBag,
  FileText,
  BookOpen,
  Sparkles,
  Clock,
  Banknote,
  AlertTriangle,
  RotateCcw
} from 'lucide-react';
import { hapticImpact, hapticNotify } from '../utils/telegram';
import { apiFetch } from '../utils/api';
import LegalAnswerCard from './legal/LegalAnswerCard';

// The FAQ comes from the server (GET /api/legal-faq): its numbers are filled in from the legal knowledge base.
const FAQ_ICONS = { KeyRound, Building2, UserCheck, Award, Receipt, ShoppingBag, FileText, Banknote };

const BRAND_COLORS = {
  bg: 'bg-brand-50 dark:bg-teal-950',
  text: 'text-brand-700 dark:text-teal-300',
  badge: 'bg-brand-50 dark:bg-teal-950 text-brand-700 dark:text-teal-300 border-brand-200 dark:border-teal-800',
  border: 'border-brand-200 dark:border-teal-800',
};

// One brand colour for every topic: the icons identify the topic, so a rainbow adds nothing.
// (item.color is kept in the data but intentionally ignored.)
const COLOR_MAP = new Proxy({}, { get: () => BRAND_COLORS });

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
import RichText from './RichText';

/** A stored chat message of the server as a message of the UI. */
function fromStored(m) {
  if (m.role === 'user') return { role: 'user', text: m.content.text || '' };
  return {
    role: 'assistant', id: m.id, answer: m.content, sources: m.sources, fallback: m.is_mock,
    conflict: m.content.conflict, calc_warning: m.content.calc_warning, rating: m.rating,
  };
}

export default function TabLegal({ lang, t, profile, onOpenProfile }) {
  const [faqData, setFaqData] = useState([]);
  const [faqError, setFaqError] = useState('');
  const [openId, setOpenId] = useState(null);

  // Greeting: shown by the UI only (the server never receives the user's name)
  const greeting = {
    role: 'assistant',
    text: lang === 'uz'
      ? `Assalomu alaykum${profile?.name ? `, ${profile.name.split(' ')[0]}` : ''}! 👋 Men OqilaLegal — O'zbekiston qonunchiligi bo'yicha sun'iy intellekt maslahatchisiman.\n\n**Menga quyidagi mavzularda savol berishingiz mumkin:**\n• YaTT va o'z-o'zini band qilishni ochish\n• Soliqlar: stavkalar, miqdorlar, muddatlar\n• ERI (elektron imzo) olish\n• Click/Payme ulash\n• Uzum Market'da sotuvchi bo'lish\n• Hunarmand sertifikati\n\nSavolingizni yozing! ✍️`
      : `Здравствуйте${profile?.name ? `, ${profile.name.split(' ')[0]}` : ''}! 👋 Я OqilaLegal — AI-консультант по законодательству Узбекистана.\n\n**Задайте вопрос о:**\n• Открытии ЯТТ или самозанятости\n• Налогах: ставки, суммы, сроки\n• Получении ЭЦП (E-IMZO)\n• Подключении Click/Payme\n• Регистрации продавца на Uzum Market\n• Сертификате Хунарманд\n\nПишите — разберёмся вместе! ✍️`,
  };

  const [chatId, setChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    let alive = true;
    apiFetch(`/api/legal-faq?lang=${lang}`, { fallback: t.legal_faq_error })
      .then((r) => r.json())
      .then((data) => { if (alive) { setFaqData(data.items || []); setFaqError(''); } })
      .catch((err) => { if (alive) setFaqError(err.message); });
    apiFetch(`/api/legal-suggestions?lang=${lang}`, { fallback: '' })
      .then((r) => r.json())
      .then((data) => { if (alive) setSuggestions(data.suggestions || []); })
      .catch(() => {});
    return () => { alive = false; };
  }, [lang, t.legal_faq_error]);

  // Continue where the conversation was left
  useEffect(() => {
    let alive = true;
    apiFetch('/api/legal-chats/latest', { fallback: '' })
      .then((r) => r.json())
      .then((chat) => {
        if (!alive || !chat.id) return;
        setChatId(chat.id);
        setMessages(chat.messages.map(fromStored));
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const sendQuestion = useCallback(async (q, { retryOf } = {}) => {
    hapticImpact('medium');
    setInputValue('');
    setMessages((prev) => [...prev.filter((m) => m !== retryOf), ...(retryOf ? [] : [{ role: 'user', text: q }])]);
    setIsSending(true);
    try {
      const res = await apiFetch('/api/legal-qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, lang, chat_id: chatId }),
        timeout: 120000,
        fallback: t.legal_error,
      });
      const data = await res.json();
      setChatId(data.chat_id);
      setMessages((prev) => [...prev, {
        role: 'assistant', id: data.message_id, answer: data.answer, sources: data.sources, fallback: Boolean(data.ai_fallback),
        conflict: data.conflict, calc_warning: data.calc_warning, rating: null,
      }]);
      hapticNotify('success');
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', error: err.message || t.legal_error, retryQuestion: q }]);
      hapticNotify('error');
    } finally {
      setIsSending(false);
    }
  }, [chatId, lang, t.legal_error]);

  const handleSend = (questionText) => {
    const q = (questionText || inputValue).trim();
    if (!q || isSending) return;
    sendQuestion(q);
  };

  const rateAnswer = async (message, rating) => {
    try {
      await apiFetch('/api/legal-feedback', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message_id: message.id, rating }), fallback: '',
      });
      setMessages((prev) => prev.map((m) => (m === message ? { ...m, rating } : m)));
    } catch { /* a missed rating is not worth an error screen */ }
  };

  const clearChat = async () => {
    hapticImpact('medium');
    const id = chatId;
    setMessages([]);
    setChatId(null);
    if (id) apiFetch(`/api/legal-chats/${id}`, { method: 'DELETE', fallback: '' }).catch(() => {});
  };

  const lastAssistantIndex = messages.reduce((acc, m, i) => (m.role === 'assistant' && m.answer ? i : acc), -1);
  const quickQuestions = messages.length === 0 ? suggestions : [];

  return (
    <div className="space-y-4">
      {/* Header Banner */}
      <div className="glass-card rounded-2xl p-4 border-l-4 border-l-brand-600 dark:border-l-brand-400 bg-gradient-to-r from-teal-50/70 via-white to-white dark:from-teal-950/30 dark:via-slate-900 dark:to-slate-900">
        <div className="flex items-center space-x-2 text-brand-800 dark:text-teal-300">
          <Scale className="w-5 h-5 flex-shrink-0" />
          <h2 className="font-bold text-sm tracking-tight">{t.legal_title}</h2>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
          {t.legal_subtitle}
        </p>
      </div>

      {/* User Profile Context Badge */}
      {profile && (
        <div className="flex items-center justify-between p-2.5 px-3.5 rounded-2xl bg-brand-50/80 dark:bg-teal-950/30 border border-brand-200/80 dark:border-teal-800/60 shadow-sm text-xs">
          <div className="flex items-center space-x-2 truncate">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
            <span className="font-bold text-slate-800 dark:text-slate-200 truncate">
              {profile.name} • {profile.status === 'self_employed' 
                ? (t.ui_tablegal_1) 
                : profile.status === 'yatt'
                ? (t.ui_tablegal_2)
                : (t.ui_tablegal_3)}
            </span>
          </div>
          <button
            type="button"
            onClick={onOpenProfile}
            className="text-[11px] font-bold text-brand-700 dark:text-teal-300 hover:text-brand-900 dark:hover:text-teal-100 underline decoration-dotted flex-shrink-0 ml-2"
          >
            {t.ui_tablegal_4}
          </button>
        </div>
      )}

      {/* Section: FAQ Accordion */}
      <div className="space-y-2">
        <div className="flex items-center space-x-2 px-1">
          <BookOpen className="w-4 h-4 text-brand-600 dark:text-teal-400" />
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
            {t.ui_tablegal_5}
          </h3>
        </div>

        {faqError && <p role="alert" className="text-xs font-semibold text-rose-700 dark:text-rose-300 px-1">{faqError}</p>}
        {faqData.map((item) => {
          const Icon = FAQ_ICONS[item.icon] || BookOpen;
          const colors = COLOR_MAP[item.color] || COLOR_MAP.teal;
          const isOpen = openId === item.id;

          return (
            <div
              key={item.id}
              className={`glass-card rounded-2xl transition-all border ${
                isOpen ? `${colors.border} shadow-soft` : 'border-slate-200/70 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              {/* Accordion Header */}
              <button
                type="button"
                onClick={() => {
                  hapticImpact('light');
                  setOpenId(isOpen ? null : item.id);
                }}
                className="w-full p-3.5 flex items-center justify-between text-left"
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${colors.bg} ${colors.text}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-xs text-slate-900 dark:text-white leading-snug">{item.title}</h4>
                    <div className="flex items-center space-x-1.5 mt-0.5 flex-wrap gap-y-0.5">
                      <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-md border ${colors.badge}`}>
                        {item.badge}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-1.5 flex-shrink-0 ml-2">
                  {isOpen ? (
                    <ChevronUp className="w-4 h-4 text-slate-500" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-500" />
                  )}
                </div>
              </button>

              {/* Accordion Body */}
              {isOpen && (
                <div className="px-3.5 pb-4 pt-1 border-t border-slate-100 dark:border-slate-800 space-y-3">
                  {/* Meta: Timeline & Fee */}
                  <div className="flex items-center space-x-3 flex-wrap gap-y-1.5">
                    <div className="flex items-center space-x-1 text-[11px] text-slate-500 dark:text-slate-400">
                      <Clock className="w-3.5 h-3.5" />
                      <span><span className="font-bold text-slate-700 dark:text-slate-300">{t.ui_tablegal_6}</span> {item.timeline}</span>
                    </div>
                    <div className="flex items-center space-x-1 text-[11px] text-slate-500 dark:text-slate-400">
                      <Banknote className="w-3.5 h-3.5" />
                      <span><span className="font-bold text-slate-700 dark:text-slate-300">{t.ui_tablegal_7}</span> {item.fee}</span>
                    </div>
                  </div>

                  {/* Step-by-Step */}
                  <ol className="space-y-2">
                    {item.steps.map((step, idx) => (
                      <li key={idx} className="flex items-start space-x-2.5 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                        <span className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-black ${colors.bg} ${colors.text} mt-0.5`}>
                          {idx + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>

                  {/* Tip / Warning */}
                  {item.tip && (
                    <div className={`p-2.5 rounded-xl flex items-start space-x-2 text-[11px] leading-relaxed ${
                      item.tip.startsWith('⚠️')
                        ? 'bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200'
                        : item.tip.startsWith('⚡')
                        ? 'bg-teal-50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-200'
                        : 'bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200'
                    }`}>
                      <Sparkles className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                      <span>{item.tip}</span>
                    </div>
                  )}

                  {/* Legal Reference Note */}
                  {item.law && (
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 flex items-start space-x-2 text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                      <Scale className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-slate-500 dark:text-slate-400" />
                      <div>
                        <span className="font-bold text-slate-700 dark:text-slate-200">{t.ui_tablegal_8} </span>
                        <span>{item.law}</span>
                      </div>
                    </div>
                  )}

                  {/* Official Links */}
                  {item.links?.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        {t.ui_tablegal_9}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {item.links.map((link, idx) => (
                          <a
                            key={idx}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1.5 text-[11px] font-bold text-brand-700 dark:text-teal-400 hover:text-brand-800 dark:hover:text-teal-300 bg-brand-50 dark:bg-teal-950/40 hover:bg-brand-100 dark:hover:bg-teal-950/70 px-2.5 py-1 rounded-lg border border-brand-200 dark:border-teal-800 transition-all"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span>{link.label}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* AI Legal Chat */}
      <div className="glass-card rounded-2xl overflow-hidden border border-slate-200/90 dark:border-slate-800 shadow-soft">
        {/* Chat Header */}
        <div className="p-3 bg-gradient-to-r from-slate-900 via-slate-800 to-brand-950 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 flex items-center justify-center border border-teal-400/30">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-bold leading-none">{t.chat_title}</p>
              <p className="text-xs text-slate-500 mt-0.5">{t.chat_subtitle}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <button
              type="button"
              onClick={clearChat}
              title={t.ui_tablegal_10}
              aria-label={t.ui_tablegal_11}
              className="text-slate-300 hover:text-white transition-colors min-w-11 min-h-11 flex items-center justify-center rounded-lg hover:bg-white/10"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="p-3 space-y-3 max-h-80 overflow-y-auto bg-slate-50/40 dark:bg-slate-950/40">
          {/* Greeting */}
          <div className="flex items-start space-x-2">
            <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 bg-brand-100 dark:bg-brand-950 text-brand-800 dark:text-teal-300 border border-brand-200 dark:border-brand-800"><Bot className="w-3.5 h-3.5" /></div>
            <div className="p-3 rounded-2xl max-w-[87%] text-xs leading-relaxed bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200/80 dark:border-slate-700 rounded-tl-sm shadow-sm">
              <RichText text={greeting.text} />
            </div>
          </div>
          {messages.map((m, idx) => (
            <div
              key={m.id ? `a${m.id}` : idx}
              className={`flex items-start space-x-2 ${m.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
            >
              <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                m.role === 'user'
                  ? 'bg-slate-800 dark:bg-slate-700 text-white'
                  : 'bg-brand-100 dark:bg-brand-950 text-brand-800 dark:text-teal-300 border border-brand-200 dark:border-brand-800'
              }`}>
                {m.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>

              <div className={`p-3 rounded-2xl text-xs leading-relaxed ${m.answer ? 'max-w-[94%] w-full' : 'max-w-[87%]'} ${
                m.role === 'user'
                  ? 'bg-brand-700 text-white font-medium rounded-tr-sm shadow-sm'
                  : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200/80 dark:border-slate-700 rounded-tl-sm shadow-sm'
              }`}>
                {/* No raw HTML: the user's words are plain text, the answer is rendered by LegalAnswerCard */}
                {m.role === 'user' && <div className="whitespace-pre-line">{m.text}</div>}
                {m.answer && (
                  <LegalAnswerCard message={m} t={t} isLast={idx === lastAssistantIndex} onFollowUp={handleSend} onRate={rateAnswer} />
                )}
                {m.error && (
                  <div className="space-y-2">
                    <p role="alert" className="font-semibold text-rose-700 dark:text-rose-300">{m.error}</p>
                    <button type="button" onClick={() => sendQuestion(m.retryQuestion, { retryOf: m })}
                      className="min-h-11 px-4 rounded-xl bg-brand-700 text-white text-xs font-bold active:scale-95">{t.legal_retry}</button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isSending && (
            <div className="flex items-center space-x-2 text-slate-500 text-xs py-1">
              <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce" />
              <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce [animation-delay:0.2s]" />
              <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce [animation-delay:0.4s]" />
              <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                OqilaLegal {t.ui_tablegal_12}
              </span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Quick Question Chips */}
        <div className="p-2 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 flex overflow-x-auto space-x-1.5 scrollbar-none pb-2">
          {quickQuestions.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(chip)}
              className="text-[11px] font-medium px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg whitespace-nowrap border border-slate-200/60 dark:border-slate-700 transition-all flex items-center space-x-1 flex-shrink-0"
            >
              <HelpCircle className="w-3 h-3 text-brand-500 dark:text-teal-400 flex-shrink-0" />
              <span>{chip}</span>
            </button>
          ))}
        </div>

        {/* Chat Input */}
        <div className="p-2.5 bg-white dark:bg-slate-900 border-t border-slate-200/60 dark:border-slate-800 flex items-center space-x-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
            placeholder={t.chat_placeholder}
            className="flex-1 text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500"
          />
          <button
            type="button"
            disabled={isSending || !inputValue.trim()}
            onClick={() => handleSend()}
            className="p-2 rounded-xl bg-brand-700 hover:bg-brand-800 text-white transition-all disabled:opacity-40 active:scale-95"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        {/* AI Disclaimer Footer */}
        <div className="px-3 py-2 bg-amber-50/70 dark:bg-amber-950/30 border-t border-amber-200/50 dark:border-amber-900/30 flex items-start space-x-2 text-xs text-amber-900/90 dark:text-amber-200/80 leading-normal">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="flex-1">
            {t.legal_disclaimer_chat}
          </p>
        </div>
      </div>
    </div>
  );
}
