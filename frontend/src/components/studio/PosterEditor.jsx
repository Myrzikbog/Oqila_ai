import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Download, Share2, Loader2, Palette, LayoutTemplate, Store, Type, Upload, Trash2, Info } from 'lucide-react';
import Collapsible from '../Collapsible';
import { hapticImpact, hapticNotify } from '../../utils/telegram';
import { withToken } from '../../utils/session';
import { LayoutGlyph } from './StylePicker';
import { L, LAYOUT_FIELDS } from './labels';

const MAX = { title: 90, price: 28, old_price: 28, bullet: 60, badge_text: 14, deadline: 36, contact: 48, cta: 32, brand_name: 32 };
const RENDER_DELAY_MS = 700;

function TextField({ label, value, onChange, max, placeholder }) {
  return (
    <label className="block space-y-1">
      <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{label}</span>
      <input
        type="text"
        value={value}
        maxLength={max}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white"
      />
    </label>
  );
}

function Chip({ selected, disabled, onClick, children, className = '' }) {
  return (
    <button
      type="button"
      disabled={disabled}
      aria-pressed={selected}
      onClick={onClick}
      className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold border transition-all active:scale-[0.97] disabled:opacity-50 ${
        selected
          ? 'bg-brand-600 text-white border-brand-600'
          : 'bg-slate-50 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
      } ${className}`}
    >
      {children}
    </button>
  );
}

/** Brand settings: shop name, contacts, colour and logo, set once and used on every poster. */
function BrandSettings({ lang, cfg, onBrandSaved, onLogoChanged }) {
  const l = L[lang] || L.ru;
  const [brand, setBrand] = useState({ brand_name: '', brand_color: '', brand_contact: '', has_logo: false });
  const [status, setStatus] = useState('');
  const [logoError, setLogoError] = useState('');
  const fileRef = useRef(null);

  useEffect(() => {
    let alive = true;
    fetch('/api/brand')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (alive && data) setBrand(data); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const save = async () => {
    hapticImpact('light');
    const res = await fetch('/api/brand', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand_name: brand.brand_name, brand_color: brand.brand_color, brand_contact: brand.brand_contact }),
    });
    if (res.ok) {
      const saved = await res.json();
      setBrand(saved);
      setStatus(l.saved);
      setTimeout(() => setStatus(''), 1800);
      onBrandSaved(saved);
    }
  };

  const upload = async (file) => {
    if (!file) return;
    setLogoError('');
    const form = new FormData();
    form.append('logo', file);
    const res = await fetch('/api/brand/logo', { method: 'POST', body: form });
    if (!res.ok) {
      setLogoError(l.error_logo);
      hapticNotify('error');
      return;
    }
    // only the logo flag comes from the server: do not overwrite the fields the seller is still typing
    const saved = await res.json();
    setBrand((b) => ({ ...b, has_logo: saved.has_logo }));
    onLogoChanged(saved.has_logo);
  };

  const removeLogo = async () => {
    const res = await fetch('/api/brand/logo', { method: 'DELETE' });
    if (res.ok) {
      const saved = await res.json();
      setBrand((b) => ({ ...b, has_logo: saved.has_logo }));
      onLogoChanged(saved.has_logo);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed flex gap-1.5">
        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        <span>{l.brand_hint}</span>
      </p>
      <TextField label={l.brand_name} value={brand.brand_name} max={MAX.brand_name} onChange={(v) => setBrand((b) => ({ ...b, brand_name: v }))} />
      <TextField label={l.brand_contact} value={brand.brand_contact} max={MAX.contact} onChange={(v) => setBrand((b) => ({ ...b, brand_contact: v }))} />

      <div className="flex items-center gap-3">
        <label className="flex-1 space-y-1">
          <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.brand_color}</span>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={brand.brand_color || '#0f766e'}
              onChange={(e) => setBrand((b) => ({ ...b, brand_color: e.target.value }))}
              className="w-10 h-9 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent p-0.5"
              aria-label={l.brand_color}
            />
            <span className="text-xs font-mono text-slate-500">{brand.brand_color || '—'}</span>
            {brand.brand_color && (
              <button type="button" className="text-[11px] text-slate-400 underline" onClick={() => setBrand((b) => ({ ...b, brand_color: '' }))}>✕</button>
            )}
          </div>
        </label>

        <div className="flex-1 space-y-1">
          <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.brand_logo}</span>
          <div className="flex items-center gap-2">
            {brand.has_logo && (
              <img src={withToken('/api/brand/logo.png')} alt="" className="w-9 h-9 rounded-lg object-contain bg-white border border-slate-200 dark:border-slate-700" />
            )}
            <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ''; }} />
            <Chip onClick={() => fileRef.current?.click()}>
              <Upload className="w-3 h-3 inline mr-1" />
              {brand.has_logo ? l.replace_logo : l.upload_logo}
            </Chip>
            {brand.has_logo && (
              <button type="button" onClick={removeLogo} className="p-1.5 text-slate-400 hover:text-rose-500" aria-label={l.remove_logo} title={l.remove_logo}>
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          {logoError && <p className="text-[11px] text-rose-600">{logoError}</p>}
        </div>
      </div>

      {brand.has_logo && (
        <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
          <input type="checkbox" checked={cfg.show_logo !== false} onChange={(e) => onBrandSaved({ ...brand, __show_logo: e.target.checked })} className="accent-teal-600" />
          {l.show_logo}
        </label>
      )}

      <div className="flex items-center gap-3">
        <button type="button" onClick={save} className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold active:scale-[0.98]">
          {l.save_brand}
        </button>
        {status && <span className="text-xs font-semibold text-brand-700 dark:text-teal-300">✓ {status}</span>}
      </div>
    </div>
  );
}

/**
 * Poster editor. The picture is drawn by the server from these settings (no AI call), so every change
 * re-renders in a moment and costs nothing. Text, colours, size and (without an AI background) layout are editable.
 */
export default function PosterEditor({ card, registry, lang }) {
  const l = L[lang] || L.ru;
  const [cfg, setCfg] = useState(() => ({ ...card.poster, bullets: [...(card.poster?.bullets || [])] }));
  const [previewUrl, setPreviewUrl] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [renderKey, setRenderKey] = useState(0);
  const blobRef = useRef(null);
  const requestRef = useRef(0);
  const urlRef = useRef(null);
  const hasScene = Boolean(card.poster_has_scene);

  const render = useCallback(async (config) => {
    const ticket = ++requestRef.current;
    setBusy(true);
    setError('');
    try {
      const res = await fetch(`/api/cards/${card.id}/poster`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (ticket !== requestRef.current) return;
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        setError(typeof detail.detail === 'string' ? detail.detail : l.error_render);
        return;
      }
      const blob = await res.blob();
      if (ticket !== requestRef.current) return;
      const url = URL.createObjectURL(blob);
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      urlRef.current = url;
      blobRef.current = blob;
      setPreviewUrl(url);
    } catch {
      if (ticket === requestRef.current) setError(l.error_render);
    } finally {
      if (ticket === requestRef.current) setBusy(false);
    }
  }, [card.id, l.error_render]);

  // debounced re-render on every change
  useEffect(() => {
    const timer = setTimeout(() => render(cfg), RENDER_DELAY_MS);
    return () => clearTimeout(timer);
  }, [cfg, renderKey, render]);

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const set = (key, value) => setCfg((c) => ({ ...c, [key]: value }));
  const setBullet = (index, value) => setCfg((c) => {
    const bullets = [...c.bullets];
    bullets[index] = value;
    return { ...c, bullets };
  });

  const layouts = useMemo(() => {
    const group = registry.layouts[cfg.layout]?.group;
    return Object.entries(registry.layouts).filter(([, info]) => info.group === group);
  }, [registry, cfg.layout]);

  const palettes = Object.entries(registry.palettes);
  const fields = LAYOUT_FIELDS[cfg.layout] || LAYOUT_FIELDS.showcase;
  const bulletSlots = 4;

  const download = () => {
    if (!previewUrl) return;
    hapticImpact('light');
    const a = document.createElement('a');
    a.href = previewUrl;
    a.download = `oqila-poster-${card.id}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const share = async () => {
    hapticImpact('light');
    const blob = blobRef.current;
    if (!blob) return;
    const file = new File([blob], `oqila-poster-${card.id}.png`, { type: 'image/png' });
    if (navigator.canShare?.({ files: [file] })) {
      try { await navigator.share({ files: [file], title: cfg.title }); return; } catch { /* user cancelled */ }
    }
    download();
  };

  const onBrandSaved = (brand) => {
    if (brand.__show_logo !== undefined) {
      set('show_logo', brand.__show_logo);
      return;
    }
    setCfg((c) => ({
      ...c,
      brand_name: brand.brand_name,
      contact: brand.brand_contact || c.contact,
      brand_color: brand.brand_color,
      palette: brand.brand_color ? 'custom' : (c.palette === 'custom' ? 'brand' : c.palette),
      show_logo: brand.has_logo ? c.show_logo : false,
    }));
  };

  const summary = `${registry.layouts[cfg.layout]?.[lang] || ''} · ${cfg.aspect}`;

  return (
    <div className="space-y-3">
      <div className="relative rounded-2xl overflow-hidden border border-slate-200/80 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 shadow-sm">
        {previewUrl ? (
          <img src={previewUrl} alt={cfg.title || l.poster_ready} className={`w-full h-auto block transition-opacity ${busy ? 'opacity-60' : 'opacity-100'}`} />
        ) : (
          <div className="aspect-[3/4] flex items-center justify-center text-slate-400"><Loader2 className="w-6 h-6 animate-spin" /></div>
        )}
        {busy && previewUrl && (
          <span className="absolute top-2.5 left-2.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-900/80 text-white">
            <Loader2 className="w-3 h-3 animate-spin" /> {l.rendering}
          </span>
        )}
      </div>
      {error && <p role="alert" className="text-xs font-semibold text-rose-600 dark:text-rose-400">{error}</p>}

      <div className="grid grid-cols-2 gap-2">
        <button type="button" onClick={download} disabled={!previewUrl || busy} className="py-2.5 rounded-xl bg-brand-700 hover:bg-brand-800 text-white text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50 active:scale-[0.98]">
          <Download className="w-4 h-4" /> {l.download}
        </button>
        <button type="button" onClick={share} disabled={!previewUrl || busy} className="py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-slate-700 text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50 active:scale-[0.98]">
          <Share2 className="w-4 h-4" /> {l.share}
        </button>
      </div>
      <p className="text-[11px] text-slate-500 dark:text-slate-400">{l.poster_hint}</p>

      <Collapsible icon={Type} title={l.texts} defaultOpen>
        {fields.includes('title') && <TextField label={l.f_title} value={cfg.title || ''} max={MAX.title} onChange={(v) => set('title', v)} />}
        {fields.includes('price') && (
          <div className="grid grid-cols-2 gap-2">
            <TextField label={l.f_price} value={cfg.price || ''} max={MAX.price} onChange={(v) => set('price', v)} />
            {fields.includes('old_price') && <TextField label={l.f_old_price} value={cfg.old_price || ''} max={MAX.old_price} onChange={(v) => set('old_price', v)} />}
          </div>
        )}
        {(fields.includes('badge_text') || fields.includes('deadline')) && (
          <div className="grid grid-cols-2 gap-2">
            {fields.includes('badge_text') && <TextField label={l.f_badge} value={cfg.badge_text || ''} max={MAX.badge_text} onChange={(v) => set('badge_text', v)} />}
            {fields.includes('deadline') && <TextField label={l.f_deadline} value={cfg.deadline || ''} max={MAX.deadline} onChange={(v) => set('deadline', v)} />}
          </div>
        )}
        {fields.includes('bullets') && (
          <div className="space-y-2">
            <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.f_bullets}</div>
            {Array.from({ length: bulletSlots }).map((_, i) => (
              <TextField key={i} label="" value={cfg.bullets?.[i] || ''} max={MAX.bullet} placeholder={`${l.f_bullet} ${i + 1}`} onChange={(v) => setBullet(i, v)} />
            ))}
          </div>
        )}
        {fields.includes('cta') && <TextField label={l.f_cta} value={cfg.cta || ''} max={MAX.cta} onChange={(v) => set('cta', v)} />}
        {fields.includes('contact') && <TextField label={l.f_contact} value={cfg.contact || ''} max={MAX.contact} onChange={(v) => set('contact', v)} />}
      </Collapsible>

      <Collapsible icon={LayoutTemplate} title={`${l.layout}, ${l.size.toLowerCase()}, ${l.colors.toLowerCase()}`} summary={summary}>
        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.layout}</div>
          <div className="flex flex-wrap gap-2">
            {layouts.map(([id, info]) => (
              <button
                key={id}
                type="button"
                disabled={hasScene && id !== cfg.layout}
                aria-pressed={cfg.layout === id}
                onClick={() => { hapticImpact('light'); set('layout', id); }}
                className={`w-20 p-1.5 rounded-xl border text-center transition-all disabled:opacity-40 ${
                  cfg.layout === id ? 'border-brand-600 ring-1 ring-brand-500/30 bg-brand-50 dark:bg-teal-950/40' : 'border-slate-200 dark:border-slate-700'
                }`}
              >
                <LayoutGlyph layout={id} className="w-full h-14" />
                <span className="block text-[10px] font-bold mt-1 text-slate-700 dark:text-slate-300 leading-tight">{info[lang] || info.ru}</span>
              </button>
            ))}
          </div>
          {hasScene && layouts.length > 1 && <p className="text-[11px] text-slate-500 dark:text-slate-400">{l.layout_locked}</p>}
        </div>

        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.size}</div>
          <div className="flex flex-wrap gap-2">
            {registry.aspects.map((a) => (
              <Chip key={a} selected={cfg.aspect === a} onClick={() => set('aspect', a)}>{a}</Chip>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 flex items-center gap-1"><Palette className="w-3 h-3" /> {l.colors}</div>
          <div className="flex flex-wrap gap-2">
            {palettes.map(([id, info]) => (
              <Chip key={id} selected={cfg.palette === id} onClick={() => setCfg((c) => ({ ...c, palette: id }))}>
                <span className="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle border border-slate-300" style={{ background: info.swatch }} />
                {info[lang] || info.ru}
              </Chip>
            ))}
            {cfg.brand_color && (
              <Chip selected={cfg.palette === 'custom'} onClick={() => set('palette', 'custom')}>
                <span className="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle border border-slate-300" style={{ background: cfg.brand_color }} />
                {l.brand_color_name}
              </Chip>
            )}
          </div>
        </div>
      </Collapsible>

      <Collapsible icon={Store} title={l.brand} summary={cfg.brand_name || l.brand_hint}>
        <BrandSettings lang={lang} cfg={cfg} onBrandSaved={onBrandSaved} onLogoChanged={(hasLogo) => { setCfg((c) => ({ ...c, show_logo: hasLogo })); setRenderKey((k) => k + 1); }} />
      </Collapsible>
    </div>
  );
}
