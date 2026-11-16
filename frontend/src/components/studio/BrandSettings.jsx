import React, { useEffect, useRef, useState } from 'react';
import { Upload, Trash2, Info } from 'lucide-react';
import { hapticImpact, hapticNotify } from '../../utils/telegram';
import { withToken } from '../../utils/session';
import { useMediaToken } from '../../utils/useMediaToken';
import { apiFetch } from '../../utils/api';
import { L } from './labels';

const MAX = { brand_name: 24, brand_contact: 30 };
const inputCls =
  'w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-medium text-slate-900 dark:text-white';

/**
 * The seller's brand: shop name, contacts, colour and logo. Set once; the name, contacts and colour go into
 * the prompt of every picture with text and the logo is passed to the AI as a reference image.
 */
export default function BrandSettings({ lang }) {
  useMediaToken();
  const l = L[lang] || L.ru;
  const [brand, setBrand] = useState({ brand_name: '', brand_color: '', brand_contact: '', has_logo: false });
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  useEffect(() => {
    let alive = true;
    apiFetch('/api/brand', { fallback: l.error_save })
      .then((r) => r.json())
      .then((data) => { if (alive) setBrand(data); })
      .catch((err) => { if (alive) setError(err.message); });
    return () => { alive = false; };
  }, [l.error_save]);

  const save = async () => {
    hapticImpact('light');
    setError('');
    try {
      const res = await apiFetch('/api/brand', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brand_name: brand.brand_name, brand_color: brand.brand_color, brand_contact: brand.brand_contact }),
        fallback: l.error_save,
      });
      setBrand(await res.json());
      setStatus(l.saved);
      hapticNotify('success');
      setTimeout(() => setStatus(''), 1800);
    } catch (err) {
      setError(err.message || l.error_save);
      hapticNotify('error');
    }
  };

  const upload = async (file) => {
    if (!file) return;
    setError('');
    const form = new FormData();
    form.append('logo', file);
    try {
      const res = await apiFetch('/api/brand/logo', { method: 'POST', body: form, fallback: l.error_logo });
      const saved = await res.json();
      setBrand((b) => ({ ...b, has_logo: saved.has_logo })); // do not overwrite fields still being typed
    } catch (err) {
      setError(err.message || l.error_logo);
      hapticNotify('error');
    }
  };

  const removeLogo = async () => {
    try {
      const res = await apiFetch('/api/brand/logo', { method: 'DELETE', fallback: l.error_save });
      const saved = await res.json();
      setBrand((b) => ({ ...b, has_logo: saved.has_logo }));
    } catch (err) {
      setError(err.message || l.error_save);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed flex gap-1.5">
        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <span>{l.brand_hint}</span>
      </p>
      <label className="block space-y-1">
        <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.brand_name}</span>
        <input type="text" className={inputCls} value={brand.brand_name} maxLength={MAX.brand_name}
          onChange={(e) => setBrand((b) => ({ ...b, brand_name: e.target.value }))} />
      </label>
      <label className="block space-y-1">
        <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.brand_contact}</span>
        <input type="text" className={inputCls} value={brand.brand_contact} maxLength={MAX.brand_contact}
          onChange={(e) => setBrand((b) => ({ ...b, brand_contact: e.target.value }))} />
      </label>

      <div className="flex items-start gap-4">
        <div className="flex-1 space-y-1">
          <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.brand_color}</span>
          <div className="flex items-center gap-2">
            <input type="color" value={brand.brand_color || '#0f766e'} aria-label={l.brand_color}
              onChange={(e) => setBrand((b) => ({ ...b, brand_color: e.target.value }))}
              className="w-10 h-9 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent p-0.5" />
            <span className="text-xs font-mono text-slate-500">{brand.brand_color || '—'}</span>
            {brand.brand_color && (
              <button type="button" className="text-[11px] text-slate-500 underline" aria-label="reset"
                onClick={() => setBrand((b) => ({ ...b, brand_color: '' }))}>✕</button>
            )}
          </div>
        </div>
        <div className="flex-1 space-y-1">
          <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">{l.brand_logo}</span>
          <div className="flex items-center gap-2">
            {brand.has_logo && (
              <img src={withToken('/api/brand/logo.png')} alt="" className="w-9 h-9 rounded-lg object-contain bg-white border border-slate-200 dark:border-slate-700" />
            )}
            <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
              onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ''; }} />
            <button type="button" onClick={() => fileRef.current?.click()}
              className="px-2.5 py-1.5 rounded-xl text-[11px] font-bold border bg-slate-50 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 active:scale-[0.97]">
              <Upload className="w-3 h-3 inline mr-1" aria-hidden="true" />
              {brand.has_logo ? l.replace_logo : l.upload_logo}
            </button>
            {brand.has_logo && (
              <button type="button" onClick={removeLogo} className="p-1.5 text-slate-500 hover:text-rose-500" aria-label={l.remove_logo} title={l.remove_logo}>
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
      {brand.has_logo && <p className="text-[11px] leading-snug text-amber-800 dark:text-amber-300">{l.logo_note}</p>}
      {error && <p role="alert" className="text-[11px] font-semibold text-rose-600">{error}</p>}

      <div className="flex items-center gap-3">
        <button type="button" onClick={save}
          className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold active:scale-[0.98]">
          {l.save_brand}
        </button>
        {status && <span className="text-xs font-semibold text-brand-700 dark:text-teal-300">✓ {status}</span>}
      </div>
    </div>
  );
}
