import React, { useMemo, useState } from 'react';
import { CheckCircle2, AlertTriangle, Download, Loader2, Pencil, ShieldCheck, Info } from 'lucide-react';
import Collapsible from '../Collapsible';
import PosterEditor from './PosterEditor';
import { StylePicker } from './StylePicker';
import { hapticImpact, hapticNotify } from '../../utils/telegram';
import { L } from './labels';
import { mediaUrl, withToken } from '../../utils/session';
import { useMediaToken } from '../../utils/useMediaToken';

function Field({ label, children }) {
  return (
    <label className="block space-y-1">
      <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  'w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white';

const specsToText = (specs) => (specs || []).map((s) => `${s.name}: ${s.value}`).join('\n');
const textToSpecs = (text) =>
  text
    .split('\n')
    .map((line) => line.split(/:|—|–/))
    .map((parts) => ({ name: (parts[0] || '').trim(), value: parts.slice(1).join(':').trim() }))
    .filter((s) => s.name && s.value);

/**
 * An information card drawn by the AI (title, benefits, characteristics, icons) with the check result,
 * a text editor for re-drawing it, and the exact-text version drawn by the server.
 */
export default function InfoCardView({ card, registry, lang, onUpdate }) {
  useMediaToken();
  const l = L[lang] || L.ru;
  const info = card.info || {};
  const infoStyles = useMemo(() => registry.styles.filter((s) => s.group === 'info'), [registry]);
  const [style, setStyle] = useState(card.photoshoot_style && infoStyles.some((s) => s.id === card.photoshoot_style) ? card.photoshoot_style : infoStyles[0]?.id);
  const [form, setForm] = useState(() => ({
    title: info.title || '',
    tagline: info.tagline || '',
    benefits: [...(info.benefits || [])],
    specsText: specsToText(info.specs),
    badge: info.badge || '',
    usesText: (info.uses || []).join(', '),
  }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const slots = infoStyles.find((s) => s.id === style)?.slots || { tagline: 1, benefits: 4, specs: 4, badge: 1, uses: 4 };

  const regenerate = async () => {
    hapticImpact('medium');
    setBusy(true);
    setError('');
    try {
      const res = await fetch(`/api/cards/${card.id}/info-photo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          style,
          lang,
          title: form.title,
          tagline: form.tagline,
          benefits: form.benefits.filter((b) => b.trim()),
          specs: textToSpecs(form.specsText),
          badge: form.badge,
          uses: form.usesText.split(',').map((u) => u.trim()).filter(Boolean),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : l.error_regen);
      onUpdate({ studio_photo_url: data.studio_photo_url, info: data.info, poster: data.poster, photoshoot_style: data.photoshoot_style, display: 'photo' });
      hapticNotify('success');
    } catch (err) {
      setError(err.message || l.error_regen);
      hapticNotify('error');
    } finally {
      setBusy(false);
    }
  };

  const setBenefit = (i, v) => setForm((f) => {
    const benefits = [...f.benefits];
    benefits[i] = v;
    return { ...f, benefits };
  });

  const status =
    info.verified === true ? (
      <p className="flex gap-2 text-xs font-semibold text-emerald-700 dark:text-emerald-300"><CheckCircle2 className="w-4 h-4 flex-shrink-0" />{l.info_verified}</p>
    ) : info.verified === false ? (
      <p className="flex gap-2 text-xs font-semibold text-amber-800 dark:text-amber-300"><AlertTriangle className="w-4 h-4 flex-shrink-0" /><span>{l.info_unverified} {(info.missing || []).join(', ')}</span></p>
    ) : (
      <p className="flex gap-2 text-xs font-semibold text-slate-600 dark:text-slate-300"><Info className="w-4 h-4 flex-shrink-0" />{l.info_unchecked}</p>
    );

  const download = async () => {
    hapticImpact('light');
    const a = document.createElement('a');
    a.href = await mediaUrl(card.studio_photo_url);
    a.download = `oqila-card-${card.id}.jpg`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div className="space-y-3">
      <div className="relative rounded-2xl overflow-hidden border border-slate-200/80 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 shadow-sm">
        <img src={withToken(card.studio_photo_url)} alt={info.title || card.title} className={`w-full h-auto block ${busy ? 'opacity-50' : ''}`} />
        {busy && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-white/60 dark:bg-slate-900/60">
            <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-100 px-6 text-center">{l.info_wait}</span>
          </div>
        )}
      </div>

      <div className="space-y-1.5 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700">
        {status}
        <p className="flex gap-2 text-[11px] text-slate-500 dark:text-slate-400"><Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />{l.ai_check_orig}</p>
      </div>
      {error && <p role="alert" className="text-xs font-semibold text-rose-600 dark:text-rose-400">{error}</p>}

      <button type="button" onClick={download} className="w-full py-2.5 rounded-xl bg-brand-700 hover:bg-brand-800 text-white text-xs font-bold flex items-center justify-center gap-2 active:scale-[0.98]">
        <Download className="w-4 h-4" /> {l.download} (JPEG, 1080×1440)
      </button>

      <Collapsible icon={Pencil} title={l.info_edit} summary={info.title}>
        <Field label={l.f_title}>
          <input className={inputCls} value={form.title} maxLength={48} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        {slots.tagline > 0 && (
          <Field label={l.f_tagline}>
            <input className={inputCls} value={form.tagline} maxLength={56} onChange={(e) => setForm({ ...form, tagline: e.target.value })} />
          </Field>
        )}
        {slots.benefits > 0 && (
          <div className="space-y-2">
            <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.f_bullets}</div>
            {Array.from({ length: slots.benefits }).map((_, i) => (
              <input key={i} className={inputCls} value={form.benefits[i] || ''} maxLength={44} placeholder={`${l.f_bullet} ${i + 1}`} onChange={(e) => setBenefit(i, e.target.value)} />
            ))}
          </div>
        )}
        {slots.specs > 0 && (
          <Field label={l.f_specs}>
            <textarea className={`${inputCls} resize-none`} rows={4} value={form.specsText} onChange={(e) => setForm({ ...form, specsText: e.target.value })} />
          </Field>
        )}
        {slots.badge > 0 && (
          <Field label={l.f_badge}>
            <input className={inputCls} value={form.badge} maxLength={34} onChange={(e) => setForm({ ...form, badge: e.target.value })} />
          </Field>
        )}
        {slots.uses > 0 && (
          <Field label={l.f_uses}>
            <input className={inputCls} value={form.usesText} onChange={(e) => setForm({ ...form, usesText: e.target.value })} />
          </Field>
        )}
        <div className="space-y-1.5">
          <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.template}</div>
          <StylePicker styles={infoStyles} value={style} onChange={setStyle} lang={lang} showMore={false} />
        </div>
        <button type="button" disabled={busy} onClick={regenerate} className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold disabled:opacity-60 active:scale-[0.98]">
          {busy ? l.regenerating : l.regenerate}
        </button>
      </Collapsible>

      {card.poster && (
        <Collapsible icon={ShieldCheck} title={l.exact_version} summary={l.exact_hint}>
          <PosterEditor key={`exact-${card.id}-${info.title}`} card={{ ...card, poster_has_scene: false }} registry={registry} lang={lang} />
        </Collapsible>
      )}
    </div>
  );
}
