import React, { useId, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { hapticImpact } from '../utils/telegram';

/**
 * Collapsible card: a one-line header (icon, title, optional short summary) that expands on tap.
 * Used to keep long screens short: the result stays on top, the details are one tap away.
 */
export default function Collapsible({ icon: Icon, title, summary, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <section className="glass-card rounded-2xl border border-slate-200/80 dark:border-slate-800 overflow-hidden">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => {
          hapticImpact('light');
          setOpen((v) => !v);
        }}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left active:bg-slate-50 dark:active:bg-slate-800/60 transition-colors"
      >
        {Icon && <Icon className="w-4 h-4 flex-shrink-0 text-brand-600 dark:text-teal-400" />}
        <span className="flex-1 min-w-0">
          <span className="block text-xs font-bold text-slate-900 dark:text-white leading-snug">{title}</span>
          {summary && !open && (
            <span className="block text-[11px] text-slate-500 dark:text-slate-400 truncate">{summary}</span>
          )}
        </span>
        <ChevronDown
          className={`w-4 h-4 flex-shrink-0 text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <div id={panelId} className="px-4 pb-4 space-y-3">
          {children}
        </div>
      )}
    </section>
  );
}

/** Small inline "details" toggle for one paragraph of fine print. */
export function Disclosure({ label, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] font-semibold text-brand-700 dark:text-teal-300 underline underline-offset-2"
      >
        {label}
      </button>
      {open && <div className="mt-1.5 text-[11px] leading-relaxed opacity-90">{children}</div>}
    </div>
  );
}
