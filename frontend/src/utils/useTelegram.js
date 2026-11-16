import { useEffect } from 'react';
import { pushBackHandler, setClosingConfirmation } from './telegram';

/** While `isOpen`, Telegram's back button is shown and closes this modal. */
export function useTelegramBackButton(isOpen, onClose) {
  useEffect(() => {
    if (!isOpen) return undefined;
    return pushBackHandler(onClose);
  }, [isOpen, onClose]);
}

/** Telegram asks before closing the Mini App while `active` (work in progress that would be lost). */
export function useClosingConfirmation(active) {
  useEffect(() => {
    setClosingConfirmation(Boolean(active));
    return () => setClosingConfirmation(false);
  }, [active]);
}
