import React, { useState } from 'react';
import {
  Camera, LayoutTemplate, Percent, ShoppingBag, Smartphone, Sparkles, Crown, Sun, Layers, Hand, Gift,
  Flower2, Heart, Utensils, User, LayoutGrid, SlidersHorizontal, Columns2, Minus, Star, Clock, ListChecks,
  Type, Moon, ChevronDown,
} from 'lucide-react';
import { hapticImpact } from '../../utils/telegram';
import { L } from './labels';

const ICONS = {
  camera: Camera, layout: LayoutTemplate, percent: Percent, shopping: ShoppingBag, smartphone: Smartphone,
  sparkles: Sparkles, crown: Crown, sun: Sun, layers: Layers, hand: Hand, gift: Gift, flower: Flower2,
  heart: Heart, utensils: Utensils, user: User, grid: LayoutGrid, sliders: SlidersHorizontal,
  columns: Columns2, minus: Minus, star: Star, clock: Clock, list: ListChecks, type: Type, moon: Moon,
};
const iconFor = (name) => ICONS[name] || Sparkles;

/**
 * Tiny wireframe of a poster layout: grey = product, teal = text plates, yellow = price/badge.
 * Shows what the result will look like before anything is generated.
 */
export function LayoutGlyph({ layout, className = '' }) {
  const product = <rect x="9" y="12" width="12" height="14" rx="2" className="fill-slate-300 dark:fill-slate-600" />;
  const plate = 'fill-brand-600 dark:fill-teal-500';
  const accent = 'fill-amber-300';
  const shapes = {
    showcase: (<><rect x="3" y="3" width="24" height="7" rx="2" className={plate} />{product}<rect x="3" y="31" width="13" height="4" rx="2" className={accent} /></>),
    magazine: (<><rect x="2" y="2" width="12" height="36" rx="2" className={plate} /><rect x="17" y="12" width="11" height="14" rx="2" className="fill-slate-300 dark:fill-slate-600" /><rect x="4" y="30" width="8" height="4" rx="2" className={accent} /></>),
    minimal: (<><rect x="9" y="4" width="12" height="16" rx="2" className="fill-slate-300 dark:fill-slate-600" /><rect x="3" y="26" width="24" height="9" rx="2" className={plate} /></>),
    sale: (<><rect x="3" y="3" width="16" height="7" rx="2" className={plate} /><circle cx="23" cy="8" r="5" className={accent} />{product}<rect x="3" y="31" width="13" height="4" rx="2" className={accent} /></>),
    new_arrival: (<><rect x="3" y="3" width="11" height="5" rx="2.5" className={accent} /><rect x="9" y="10" width="12" height="14" rx="2" className="fill-slate-300 dark:fill-slate-600" /><rect x="3" y="28" width="24" height="8" rx="2" className={plate} /></>),
    limited: (<><rect x="7" y="3" width="16" height="5" rx="2.5" className={plate} /><rect x="9" y="11" width="12" height="14" rx="2" className="fill-slate-300 dark:fill-slate-600" /><rect x="3" y="28" width="24" height="8" rx="2" className={plate} /></>),
    callouts: (<><rect x="3" y="3" width="24" height="6" rx="2" className={plate} /><rect x="10" y="13" width="10" height="14" rx="2" className="fill-slate-300 dark:fill-slate-600" /><rect x="2" y="12" width="8" height="4" rx="2" className={plate} /><rect x="20" y="19" width="8" height="4" rx="2" className={plate} /><rect x="2" y="25" width="8" height="4" rx="2" className={plate} /><rect x="9" y="32" width="12" height="4" rx="2" className={accent} /></>),
    story: (<><rect x="3" y="3" width="24" height="7" rx="2" className={plate} /><rect x="8" y="13" width="14" height="16" rx="2" className="fill-slate-300 dark:fill-slate-600" /><rect x="3" y="32" width="24" height="5" rx="2.5" className={accent} /></>),
  };
  return (
    <svg viewBox="0 0 30 40" className={className} aria-hidden="true" role="img">
      <rect x="0.5" y="0.5" width="29" height="39" rx="3" className="fill-white dark:fill-slate-900 stroke-slate-200 dark:stroke-slate-700" />
      {shapes[layout] || null}
    </svg>
  );
}

/** Output types: Uzum photo and information card are the main ones, the rest sits under "more formats". */
export function OutputTypePicker({ groups, value, onChange, lang }) {
  const l = L[lang] || L.ru;
  const main = groups.filter((g) => g.tier !== 'extra');
  const extra = groups.filter((g) => g.tier === 'extra');
  const [open, setOpen] = useState(false);
  const extraSelected = extra.some((g) => g.id === value);
  const showExtra = open || extraSelected;

  const card = (group, big) => {
    const Icon = iconFor(group.icon);
    const selected = value === group.id;
    return (
      <button
        key={group.id}
        type="button"
        role="radio"
        aria-checked={selected}
        onClick={() => { hapticImpact('light'); onChange(group.id); }}
        className={`text-left ${big ? 'p-3.5' : 'p-3'} rounded-2xl border transition-all active:scale-[0.98] ${
          selected
            ? 'bg-brand-50 dark:bg-teal-950/50 border-brand-500 dark:border-teal-500 ring-1 ring-brand-500/30'
            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 hover:border-slate-300'
        }`}
      >
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 flex-shrink-0 ${selected ? 'text-brand-600 dark:text-teal-300' : 'text-slate-400'}`} />
          <span className={`${big ? 'text-sm' : 'text-xs'} font-bold text-slate-900 dark:text-white`}>{group[lang] || group.ru}</span>
        </div>
        <div className="mt-1 text-[11px] leading-snug text-slate-500 dark:text-slate-400">
          {group[`hint_${lang}`] || group.hint_ru}
        </div>
      </button>
    );
  };

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">{l.what_title}</div>
      <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label={l.what_title}>
        {main.map((g) => card(g, true))}
      </div>
      {extra.length > 0 && (
        <>
          <button
            type="button"
            aria-expanded={showExtra}
            onClick={() => setOpen((v) => !v)}
            className="w-full flex items-center justify-center gap-1.5 text-[11px] font-semibold text-brand-700 dark:text-teal-300 py-1"
          >
            {showExtra ? l.fewer_formats : l.more_formats}
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showExtra ? 'rotate-180' : ''}`} />
          </button>
          {showExtra && (
            <div className="grid grid-cols-2 gap-2" role="radiogroup">
              {extra.map((g) => card(g, false))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** Real example of a template (3:4); hidden if the file is missing so the tile still works. */
function StylePreview({ src }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
      className="w-full aspect-[3/4] object-cover rounded-lg mb-1.5 border border-slate-200/70 dark:border-slate-700"
    />
  );
}

/** Styles of the selected output type; posters show a wireframe of their layout. */
export function StylePicker({ styles, value, onChange, lang, showMore = true }) {
  const l = L[lang] || L.ru;
  const [expanded, setExpanded] = useState(false);
  const featured = styles.filter((s) => s.featured);
  const hasMore = showMore && featured.length > 0 && styles.length > featured.length + 1;
  const visible = hasMore && !expanded
    ? [...featured, ...styles.filter((s) => !s.featured && s.id === value)]
    : styles;
  const withGlyph = styles.some((s) => s.layout || s.preview);

  return (
    <div className="space-y-2">
      <div className={`grid gap-2 ${withGlyph ? 'grid-cols-3' : 'grid-cols-2'}`} role="radiogroup">
        {visible.map((style) => {
          const Icon = iconFor(style.icon);
          const selected = value === style.id;
          return (
            <button
              key={style.id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => { hapticImpact('light'); onChange(style.id); }}
              className={`p-2 rounded-xl border text-left transition-all active:scale-[0.98] ${
                selected
                  ? 'bg-brand-600 text-white border-brand-600 shadow-sm ring-1 ring-brand-500/30'
                  : 'bg-slate-50 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
              }`}
            >
              {style.preview ? (
                <StylePreview src={style.preview} />
              ) : style.layout ? (
                <LayoutGlyph layout={style.layout} className="w-full h-16 mb-1.5" />
              ) : null}
              <div className="flex items-center gap-1.5">
                {!style.layout && !style.preview && <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${selected ? 'text-teal-200' : 'text-slate-400 dark:text-slate-500'}`} />}
                <span className="truncate font-bold text-[11px]">{style[lang] || style.ru}</span>
              </div>
              {(style[`tag_${lang}`] || style.tag_ru) && (
                <span className={`inline-block text-[9px] font-bold mt-1 px-1.5 rounded ${
                  selected ? 'bg-brand-700/80 text-teal-100' : 'bg-slate-200/80 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                }`}>
                  {style[`tag_${lang}`] || style.tag_ru}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {hasMore && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="w-full text-[11px] font-semibold text-brand-700 dark:text-teal-300 py-1"
          aria-expanded={expanded}
        >
          {expanded ? l.fewer_styles : `${l.more_styles} (${styles.length - featured.length})`}
        </button>
      )}
    </div>
  );
}
