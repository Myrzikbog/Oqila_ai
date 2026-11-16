import React, { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Download, Info, Loader2, Scissors, Sparkles, Wand2 } from 'lucide-react';
import { hapticImpact, hapticNotify } from '../../utils/telegram';
import { withToken } from '../../utils/session';
import { downloadServerFile } from '../../utils/download';
import { tg } from '../../utils/telegram';
import { useMediaToken } from '../../utils/useMediaToken';
import { apiFetch } from '../../utils/api';
import { L } from './labels';

const inputCls =
  'w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white';
const ASPECT_CLASS = { '1:1': 'aspect-square', '3:4': 'aspect-[3/4]', '4:5': 'aspect-[4/5]', '9:16': 'aspect-[9/16]' };
const RENDER_TIMEOUT = 150000;

/** Fields shown in the editor, in reading order. `list` fields repeat `count` times. */
const FIELD_ORDER = ['brand_name', 'badge', 'title', 'subtitle', 'bullets', 'specs', 'price', 'old_price', 'deadline', 'cta', 'contact', 'uses'];
const LABEL_KEY = {
  brand_name: 'f_brand_name', badge: 'f_badge', title: 'f_title', subtitle: 'f_subtitle', bullets: 'f_bullets', specs: 'f_specs',
  price: 'f_price', old_price: 'f_old_price', deadline: 'f_deadline', cta: 'f_cta', contact: 'f_contact', uses: 'f_uses',
};
const PRICE_FIELDS = new Set(['price', 'old_price']);
const digitsOf = (value) => String(value ?? '').replace(/\D/g, '');

/** Pieces of text on the picture (the same count the server limits). */
function countBlocks(c) {
  const single = ['title', 'subtitle', 'badge', 'deadline', 'cta', 'contact', 'brand_name'].filter((k) => (c[k] || '').trim()).length;
  const lists = (c.bullets || []).filter((x) => x.trim()).length + (c.specs || []).filter((s) => s.name.trim() && s.value.trim()).length + (c.uses || []).filter((x) => x.trim()).length;
  return single + lists + ((c.price || c.old_price) ? 1 : 0);
}

function formFromCopy(copy, style) {
  const c = copy || {};
  const fields = style?.fields || {};
  const pad = (arr, n) => Array.from({ length: n }, (_, i) => (arr || [])[i] || '');
  return {
    brand_name: c.brand_name || '', badge: c.badge || '', title: c.title || '', subtitle: c.subtitle || '',
    bullets: pad(c.bullets, fields.bullets?.count || 0),
    specs: Array.from({ length: fields.specs?.count || 0 }, (_, i) => ({ name: c.specs?.[i]?.name || '', value: c.specs?.[i]?.value || '' })),
    price: digitsOf(c.price), old_price: digitsOf(c.old_price), deadline: c.deadline || '', cta: c.cta || '', contact: c.contact || '',
    uses: pad(c.uses, fields.uses?.count || 0), legacy: Boolean(c.legacy),
  };
}

function copyFromForm(form) {
  return {
    brand_name: form.brand_name, badge: form.badge, title: form.title, subtitle: form.subtitle,
    bullets: form.bullets.filter((x) => x.trim()), specs: form.specs.filter((s) => s.name.trim() && s.value.trim()),
    price: form.price, old_price: form.old_price, deadline: form.deadline, cta: form.cta, contact: form.contact,
    uses: form.uses.filter((x) => x.trim()),
  };
}

function Counter({ value, limit }) {
  const over = value.length > limit;
  return <span className={`text-xs font-semibold tabular-nums ${over ? 'text-rose-600' : 'text-slate-500 dark:text-slate-400'}`}>{value.length}/{limit}</span>;
}

/**
 * A picture with text drawn by the AI: the picture in its own aspect ratio, the result of reading the text
 * back, an editor for every text slot of the format (with length limits) and the actions: draw again,
 * fix only the lettering, shorten, rewrite the text. The server never draws text itself.
 */
export default function CardView({ card, registry, lang, onUpdate }) {
  useMediaToken();
  const l = L[lang] || L.ru;
  const textStyles = useMemo(() => registry.styles.filter((s) => s.kind === 'ai_text'), [registry]);
  const [styleId, setStyleId] = useState(card.photoshoot_style);
  const style = textStyles.find((s) => s.id === styleId) || textStyles[0];
  const [aspect, setAspect] = useState(card.aspect && style?.aspects?.includes(card.aspect) ? card.aspect : style?.aspect);
  const [form, setForm] = useState(() => formFromCopy(card.copy, textStyles.find((s) => s.id === card.photoshoot_style)));
  const [busy, setBusy] = useState(null); // 'render' | 'fix' | 'rewrite'
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const fields = style?.fields || {};
  const limits = useMemo(() => style?.limits || {}, [style]);
  const verification = card.verification;
  const blocks = countBlocks(form);
  const maxBlocks = style?.max_blocks || 6;
  const hasPicture = Boolean(card.studio_photo_url);

  const tooLong = useMemo(() => {
    const out = [];
    const over = (key, value, limit) => { if (limit && (value || '').length > limit) out.push(key); };
    ['title', 'subtitle', 'badge', 'deadline', 'cta', 'contact', 'brand_name'].forEach((k) => over(k, form[k], limits[k === 'badge' ? 'badge' : k]));
    form.bullets.forEach((b, i) => over(`bullets.${i}`, b, limits.bullet));
    form.specs.forEach((s, i) => { over(`specs.${i}.name`, s.name, limits.spec_name); over(`specs.${i}.value`, s.value, limits.spec_value); });
    form.uses.forEach((u, i) => over(`uses.${i}`, u, limits.use));
    return out;
  }, [form, limits]);
  const flagged = (key) => tooLong.includes(key);

  const setField = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const setItem = (key, i, value) => setForm((f) => ({ ...f, [key]: f[key].map((x, j) => (j === i ? value : x)) }));
  const setSpec = (i, part, value) => setForm((f) => ({ ...f, specs: f.specs.map((s, j) => (j === i ? { ...s, [part]: value } : s)) }));

  const changeStyle = (id) => {
    const next = textStyles.find((s) => s.id === id);
    if (!next) return;
    setStyleId(id);
    setAspect(next.aspects.includes(aspect) ? aspect : next.aspect);
    // keep what was typed; the new format shows the slots it has
    setForm(formFromCopy({ ...copyFromForm(form), legacy: form.legacy }, next));
  };

  const run = async (kind, fn) => {
    hapticImpact('medium');
    setBusy(kind);
    setError('');
    setNotice('');
    try {
      await fn();
      hapticNotify('success');
    } catch (err) {
      setError(err.timeout ? l.error_regen : (err.message || l.error_regen));
      hapticNotify('error');
    } finally {
      setBusy(null);
    }
  };

  const applyResult = (data) => {
    onUpdate({
      studio_photo_url: data.studio_photo_url, copy: data.copy, verification: data.verification, photoshoot_style: data.photoshoot_style,
      aspect: data.aspect, version: data.version, render_error: null, ai_fallback: undefined,
    });
    setForm(formFromCopy(data.copy, textStyles.find((s) => s.id === data.photoshoot_style)));
  };

  const draw = () => run('render', async () => {
    const res = await apiFetch(`/api/cards/${card.id}/render`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, timeout: RENDER_TIMEOUT, fallback: l.error_regen,
      body: JSON.stringify({ copy: copyFromForm(form), style: styleId, aspect, lang }),
    });
    applyResult(await res.json());
  });

  const fixText = () => run('fix', async () => {
    const res = await apiFetch(`/api/cards/${card.id}/fix-text`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}', timeout: RENDER_TIMEOUT, fallback: l.error_regen,
    });
    applyResult(await res.json());
  });

  const rewrite = () => run('rewrite', async () => {
    const res = await apiFetch(`/api/cards/${card.id}/copy`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, timeout: 60000, fallback: l.error_regen,
      body: JSON.stringify({ style: styleId, lang }),
    });
    const data = await res.json();
    setForm(formFromCopy(data.copy, textStyles.find((s) => s.id === data.photoshoot_style)));
  });

  const shorten = () => {
    hapticImpact('light');
    const first = tooLong[0];
    if (first) document.getElementById(`cf-${first}`)?.focus();
  };

  const download = async () => {
    hapticImpact('light');
    await downloadServerFile(`/api/cards/${card.id}/photo`, `oqila-${card.id}.jpg`);
  };

  // Fallback for clients that cannot save a file themselves: the bot sends the picture to the user's chat
  const sendToChat = () => run('send', async () => {
    await apiFetch(`/api/cards/${card.id}/send`, { method: 'POST', fallback: l.error_regen });
    setNotice(l.sent_to_chat);
  });

  const status = !hasPicture ? null : verification?.verified === true ? (
    <p className="flex gap-2 text-xs font-semibold text-emerald-700 dark:text-emerald-300"><CheckCircle2 className="w-4 h-4 flex-shrink-0" aria-hidden="true" />{l.verified}</p>
  ) : verification?.verified === false ? (
    <div role="alert" className="space-y-2 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-800">
      <p className="flex gap-2 text-xs font-bold text-amber-900 dark:text-amber-200"><AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />{l.problems_title}</p>
      <ul className="space-y-1 text-xs text-amber-900 dark:text-amber-100">
        {(verification.problems || []).map((p, i) => (
          <li key={i}>
            {p.expected ? <>«{p.expected}»{p.found ? ` — ${l.problem_found}: «${p.found}»` : ` — ${l.problem_missing}`}</> : <>{l.problem_extra}: «{p.found}»</>}
          </li>
        ))}
      </ul>
    </div>
  ) : (
    <p className="flex gap-2 text-xs font-semibold text-slate-600 dark:text-slate-300"><Info className="w-4 h-4 flex-shrink-0" aria-hidden="true" />{l.unchecked}</p>
  );

  const slotInput = (key, value, onChange, limit, label, id) => (
    <label key={id} className="block space-y-1">
      <span className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{label}</span>
        {limit ? <Counter value={value} limit={limit} /> : null}
      </span>
      <input id={`cf-${id}`} type={PRICE_FIELDS.has(key) ? 'tel' : 'text'} inputMode={PRICE_FIELDS.has(key) ? 'numeric' : undefined}
        value={value} onChange={(e) => onChange(PRICE_FIELDS.has(key) ? digitsOf(e.target.value) : e.target.value)}
        aria-invalid={flagged(id)} className={`${inputCls} ${flagged(id) ? 'border-rose-400 dark:border-rose-500 bg-rose-50 dark:bg-rose-950/30' : ''}`} />
    </label>
  );

  const busyText = busy === 'fix' ? l.fixing : busy === 'rewrite' ? l.rewriting : l.drawing;
  const canDraw = card.has_source !== false && !busy;

  return (
    <div className="space-y-3">
      <div className={`relative rounded-2xl overflow-hidden border border-slate-200/80 dark:border-slate-800 bg-white ${ASPECT_CLASS[card.aspect || aspect] || ''}`}>
        {hasPicture ? (
          <img key={`${card.id}-${card.version || 0}`} src={withToken(card.studio_photo_url)} alt={card.copy?.title || card.title}
            className={`w-full h-full object-contain ${busy ? 'opacity-50' : ''}`} />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-xs text-slate-600 bg-slate-50 dark:bg-slate-900 dark:text-slate-300">
            {card.render_error ? l.render_unavailable : l.card_no_picture}
          </div>
        )}
        {busy && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-white/60 dark:bg-slate-900/60">
            <Loader2 className="w-6 h-6 animate-spin text-brand-600" aria-hidden="true" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-100 px-6 text-center">{busyText}</span>
          </div>
        )}
        {hasPicture && !busy && (
          <button type="button" onClick={download} title={l.download} aria-label={l.download}
            className="absolute top-2.5 right-2.5 min-w-11 min-h-11 flex items-center justify-center rounded-xl bg-slate-900/80 hover:bg-slate-900 text-white shadow-md active:scale-95">
            <Download className="w-4 h-4" />
          </button>
        )}
      </div>

      {status}
      {hasPicture && tg?.initData && (
        <button type="button" onClick={sendToChat} disabled={Boolean(busy)}
          className="min-h-11 px-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-bold disabled:opacity-50">{l.send_to_chat}</button>
      )}
      {notice && <p role="status" className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">{notice}</p>}
      {hasPicture && verification?.unexpected?.length > 0 && (
        <p className="text-[11px] text-slate-600 dark:text-slate-300">{l.unexpected_title} {verification.unexpected.map((u) => `«${u}»`).join(', ')}</p>
      )}
      {form.legacy && <p className="text-[11px] leading-snug text-slate-600 dark:text-slate-300">{l.legacy_note}</p>}
      {card.has_source === false && <p className="text-[11px] leading-snug text-rose-700 dark:text-rose-300">{l.no_source}</p>}

      {hasPicture && verification?.verified === false && (
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={!canDraw} onClick={fixText}
            className="min-h-11 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 active:scale-[0.98]">
            <Wand2 className="w-4 h-4" aria-hidden="true" />{l.fix_text}
          </button>
          <button type="button" disabled={!canDraw} onClick={draw}
            className="min-h-11 px-4 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-bold disabled:opacity-50 active:scale-[0.98]">{l.redraw}</button>
        </div>
      )}

      <div className="space-y-3 p-3.5 rounded-2xl bg-white/80 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-900 dark:text-white">{l.editor_title}</h3>
          <span className={`text-[11px] font-semibold tabular-nums ${blocks > maxBlocks ? 'text-rose-600' : 'text-slate-500 dark:text-slate-400'}`}>{blocks}/{maxBlocks} {l.blocks_left}</span>
        </div>
        <p className="text-[11px] leading-snug text-slate-500 dark:text-slate-400">{l.editor_hint}</p>

        <div className="grid grid-cols-2 gap-2">
          <label className="block space-y-1">
            <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.template}</span>
            <select value={styleId} onChange={(e) => changeStyle(e.target.value)} className={inputCls}>
              {textStyles.map((s) => <option key={s.id} value={s.id}>{s[lang] || s.ru}</option>)}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.size}</span>
            <select value={aspect} onChange={(e) => setAspect(e.target.value)} className={inputCls} disabled={(style?.aspects || []).length < 2}>
              {(style?.aspects || [aspect]).map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </label>
        </div>

        {FIELD_ORDER.filter((k) => fields[k]).map((key) => {
          const label = l[LABEL_KEY[key]];
          if (key === 'bullets' || key === 'uses') {
            return form[key].map((v, i) => slotInput(key, v, (val) => setItem(key, i, val), limits[key === 'bullets' ? 'bullet' : 'use'], `${label} ${i + 1}`, `${key}.${i}`));
          }
          if (key === 'specs') {
            return form.specs.map((s, i) => (
              <div key={`specs.${i}`} className="grid grid-cols-2 gap-2">
                {slotInput('spec_name', s.name, (val) => setSpec(i, 'name', val), limits.spec_name, `${l.f_spec_name} ${i + 1}`, `specs.${i}.name`)}
                {slotInput('spec_value', s.value, (val) => setSpec(i, 'value', val), limits.spec_value, l.f_spec_value, `specs.${i}.value`)}
              </div>
            ));
          }
          return slotInput(key, form[key], (val) => setField(key, val), PRICE_FIELDS.has(key) ? 0 : limits[key], label, key);
        })}

        {error && <p role="alert" className="text-xs font-semibold text-rose-700 dark:text-rose-300">{error}</p>}
        {tooLong.length > 0 && <p className="text-[11px] font-semibold text-rose-700 dark:text-rose-300">{l.shorten_hint}</p>}

        <div className="flex flex-wrap gap-2 pt-1">
          <button type="button" disabled={!canDraw || !form.title.trim()} onClick={draw}
            className="flex-1 min-h-11 px-4 rounded-xl bg-gradient-to-r from-brand-700 to-teal-600 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-1.5 active:scale-[0.98]">
            <Sparkles className="w-4 h-4" aria-hidden="true" />{hasPicture ? l.redraw : l.draw}
          </button>
          {tooLong.length > 0 && (
            <button type="button" onClick={shorten}
              className="min-h-11 px-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 border border-rose-200 dark:border-rose-900 text-xs font-bold flex items-center gap-1.5">
              <Scissors className="w-4 h-4" aria-hidden="true" />{l.shorten}
            </button>
          )}
          <button type="button" disabled={Boolean(busy) || card.has_source === false} onClick={rewrite}
            className="min-h-11 px-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-bold disabled:opacity-50">{l.rewrite}</button>
        </div>
      </div>
    </div>
  );
}
