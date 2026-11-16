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

/** Styles of the selected output type. */
export function StylePicker({ styles, value, onChange, lang, showMore = true }) {
  const l = L[lang] || L.ru;
  const [expanded, setExpanded] = useState(false);
  const featured = styles.filter((s) => s.featured);
  const hasMore = showMore && featured.length > 0 && styles.length > featured.length + 1;
  const visible = hasMore && !expanded
    ? [...featured, ...styles.filter((s) => !s.featured && s.id === value)]
    : styles;
  const withGlyph = styles.some((s) => s.preview);

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
              ) : null}
              <div className="flex items-center gap-1.5">
                {!style.preview && <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${selected ? 'text-teal-200' : 'text-slate-400 dark:text-slate-500'}`} />}
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
