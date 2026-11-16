import React from 'react';
import { AlertTriangle, Banknote, BookOpen, Clock, ExternalLink, FileText, ListChecks, Scale, Shield, ThumbsDown, ThumbsUp } from 'lucide-react';
import Collapsible from '../Collapsible';
import RichText from '../RichText';
import { hapticImpact } from '../../utils/telegram';

const money = (amount, currency) => `${new Intl.NumberFormat('ru-RU').format(Math.round(amount)).replace(/ /g, ' ')} ${currency}`;

function Notice({ tone, icon: Icon, children }) {
  const tones = {
    amber: 'bg-amber-50 dark:bg-amber-950/40 border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200',
    rose: 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200',
    slate: 'bg-slate-100 dark:bg-slate-800/70 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200',
  };
  return (
    <p role="note" className={`flex gap-2 p-2.5 rounded-xl border text-[11px] font-semibold leading-snug ${tones[tone]}`}>
      <Icon className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}

/**
 * A structured answer of the legal assistant: the short answer first, details one tap away, every source with its
 * check date, honest notices (template answer, lawyer needed, check the calculation) and follow-up questions.
 * No raw HTML anywhere: text goes through RichText, links are built from server-checked URLs.
 */
export default function LegalAnswerCard({ message, t, isLast, onFollowUp, onRate }) {
  const a = message.answer;
  const isLow = a.confidence === 'low' && !message.fallback;
  const rate = (rating) => { hapticImpact('light'); onRate(message, rating); };

  return (
    <div className="space-y-2.5">
      {message.fallback && <Notice tone="amber" icon={AlertTriangle}>{t.legal_mock_notice}</Notice>}
      {a.escalate && <Notice tone="rose" icon={Shield}>{t.legal_escalate}{a.escalate_reason ? `: ${a.escalate_reason}` : ''}</Notice>}
      {message.calc_warning && <Notice tone="amber" icon={AlertTriangle}>{t.legal_check_calc}</Notice>}
      {message.conflict && <Notice tone="amber" icon={AlertTriangle}>{t.legal_conflict}</Notice>}
      {isLow && !message.calc_warning && !a.escalate && <Notice tone="slate" icon={AlertTriangle}>{t.legal_low_confidence}</Notice>}

      <RichText text={a.short_answer} className="text-[13px] font-semibold leading-snug text-slate-900 dark:text-white" />

      {a.steps.length > 0 && (
        <Collapsible icon={ListChecks} title={t.legal_steps} defaultOpen={a.steps.length <= 3}>
          <ol className="px-4 pb-3 space-y-1.5 list-decimal list-inside text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
            {a.steps.map((s, i) => <li key={i}><RichText text={s} className="inline" /></li>)}
          </ol>
        </Collapsible>
      )}
      {a.documents.length > 0 && (
        <Collapsible icon={FileText} title={t.legal_documents}>
          <ul className="px-4 pb-3 space-y-1 list-disc list-inside text-xs text-slate-700 dark:text-slate-300">{a.documents.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </Collapsible>
      )}
      {a.where_to_go.length > 0 && (
        <Collapsible icon={ExternalLink} title={t.legal_where} defaultOpen>
          <div className="px-4 pb-3 flex flex-wrap gap-2">
            {a.where_to_go.map((l, i) => (
              <a key={i} href={l.url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 min-h-11 px-3 text-[11px] font-bold text-brand-700 dark:text-teal-300 bg-brand-50 dark:bg-teal-950/40 border border-brand-200 dark:border-teal-800 rounded-lg">
                <ExternalLink className="w-3 h-3" aria-hidden="true" />{l.name || l.url}
              </a>
            ))}
          </div>
        </Collapsible>
      )}
      {a.deadlines.length > 0 && (
        <Collapsible icon={Clock} title={t.legal_deadlines}>
          <ul className="px-4 pb-3 space-y-1 text-xs text-slate-700 dark:text-slate-300">
            {a.deadlines.map((d, i) => <li key={i}><b>{d.when}</b>{d.what ? `: ${d.what}` : ''}</li>)}
          </ul>
        </Collapsible>
      )}
      {a.costs.length > 0 && (
        <Collapsible icon={Banknote} title={t.legal_costs}>
          <ul className="px-4 pb-3 space-y-1 text-xs text-slate-700 dark:text-slate-300">
            {a.costs.map((c, i) => <li key={i} className="flex justify-between gap-3"><span>{c.item}</span><b className="tabular-nums whitespace-nowrap">{money(c.amount_uzs, t.ui_legalanswercard_1)}</b></li>)}
          </ul>
        </Collapsible>
      )}
      {a.risks.length > 0 && (
        <Collapsible icon={AlertTriangle} title={t.legal_risks}>
          <ul className="px-4 pb-3 space-y-1 list-disc list-inside text-xs text-slate-700 dark:text-slate-300">{a.risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </Collapsible>
      )}
      {message.sources?.length > 0 && (
        <Collapsible icon={BookOpen} title={t.legal_sources}>
          <ul className="px-4 pb-3 space-y-2 text-xs">
            {message.sources.map((s, i) => (
              <li key={i} className="space-y-0.5">
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-brand-700 dark:text-teal-300 underline break-words">{s.title || s.url}</a>
                <div className="flex flex-wrap gap-1.5 text-xs font-bold">
                  <span className={`px-1.5 py-0.5 rounded ${s.official ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'}`}>
                    {s.official ? t.legal_official : t.legal_unofficial}
                  </span>
                  {s.verified_at && <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">{t.legal_verified_at} {s.verified_at}</span>}
                </div>
              </li>
            ))}
          </ul>
        </Collapsible>
      )}

      {isLast && a.follow_up_questions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1" aria-label={t.legal_followups}>
          {a.follow_up_questions.map((q, i) => (
            <button key={i} type="button" onClick={() => onFollowUp(q)}
              className="min-h-11 px-3 text-[11px] font-medium text-left bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg border border-slate-200 dark:border-slate-700 active:scale-95">
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between gap-2 pt-1">
        <p className="text-xs leading-snug text-slate-500 dark:text-slate-400 flex gap-1"><Scale className="w-3 h-3 flex-shrink-0 mt-0.5" aria-hidden="true" />{t.legal_disclaimer_short}</p>
        {message.id && !message.fallback && (
          <div className="flex gap-1 flex-shrink-0">
            <button type="button" aria-pressed={message.rating === 1} aria-label={t.legal_helpful} onClick={() => rate(1)}
              className={`min-w-11 min-h-11 flex items-center justify-center rounded-lg ${message.rating === 1 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button type="button" aria-pressed={message.rating === -1} aria-label={t.legal_not_helpful} onClick={() => rate(-1)}
              className={`min-w-11 min-h-11 flex items-center justify-center rounded-lg ${message.rating === -1 ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
