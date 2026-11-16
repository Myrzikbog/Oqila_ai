import { useEffect } from 'react';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Behaviour of a modal dialog: Escape closes it, Tab stays inside it, focus moves in when it opens and goes back to
 * the element that opened it when it closes. `ref` is the dialog's root element.
 */
export function useDialog(isOpen, onClose, ref) {
  useEffect(() => {
    if (!isOpen || !ref.current) return undefined;
    const root = ref.current;
    const previous = document.activeElement;
    const focusables = () => [...root.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null);
    (focusables()[0] || root).focus?.();

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose?.();
        return;
      }
      if (e.key !== 'Tab') return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      previous?.focus?.();
    };
  }, [isOpen, onClose, ref]);
}
