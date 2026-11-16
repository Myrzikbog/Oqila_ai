/**
 * Telegram WebApp SDK integration: theme, haptics, back button, closing confirmation, native dialogs and file
 * downloads. Everything degrades to a plain browser: no function here throws when `Telegram.WebApp` is missing.
 */
import { readStorage } from './storage';

export const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : null;

const THEME_COLORS = { light: '#f8fafc', dark: '#090d16' };

export function getTelegramUser() {
  try {
    return tg?.initDataUnsafe?.user || null;
  } catch {
    return null;
  }
}

export function initTelegram() {
  if (!tg) return;
  try {
    tg.ready();
    tg.expand();
    tg.disableVerticalSwipes?.(); // a swipe down must scroll the page, not close the Mini App
  } catch (err) {
    console.warn('Telegram WebApp init:', err);
  }
}

/** Ask Telegram to confirm before the Mini App is closed: on only while there is work that would be lost. */
export function setClosingConfirmation(enabled) {
  try {
    if (enabled) tg?.enableClosingConfirmation?.();
    else tg?.disableClosingConfirmation?.();
  } catch { /* old client */ }
}

/**
 * Returns the current theme, 'dark' or 'light'. Priority: the user's choice, Telegram's colour scheme, the system.
 * (The former "eastern" theme is gone: a saved value of it counts as light.)
 */
export function getInitialTheme() {
  const saved = readStorage('oqila_theme');
  if (saved === 'dark') return 'dark';
  if (saved === 'light' || saved === 'eastern') return 'light';
  if (tg?.colorScheme === 'dark' || tg?.colorScheme === 'light') return tg.colorScheme;
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark';
  return 'light';
}

/** Applies the theme to <html> and to Telegram's own header and background, so the bars match the page. */
export function applyTheme(theme) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.classList.remove('dark', 'eastern');
  if (theme === 'dark') root.classList.add('dark');
  const color = THEME_COLORS[theme === 'dark' ? 'dark' : 'light'];
  try {
    tg?.setHeaderColor?.(color);
    tg?.setBackgroundColor?.(color);
  } catch { /* old client */ }
}

/** Follow Telegram's and the system's theme changes until the returned function is called. */
export function subscribeToThemeChanges(onThemeChange) {
  const cleanups = [];
  if (tg?.onEvent) {
    const handler = () => {
      if (!readStorage('oqila_theme') && tg.colorScheme) {
        applyTheme(tg.colorScheme);
        onThemeChange(tg.colorScheme);
      }
    };
    tg.onEvent('themeChanged', handler);
    cleanups.push(() => tg.offEvent?.('themeChanged', handler));
  }
  if (typeof window !== 'undefined' && window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e) => {
      if (!readStorage('oqila_theme') && !tg?.colorScheme) {
        const next = e.matches ? 'dark' : 'light';
        applyTheme(next);
        onThemeChange(next);
      }
    };
    mq.addEventListener('change', handler);
    cleanups.push(() => mq.removeEventListener('change', handler));
  }
  return () => cleanups.forEach((fn) => fn());
}

export function hapticImpact(style = 'light') {
  try {
    tg?.HapticFeedback?.impactOccurred(style);
  } catch { /* no haptics */ }
}

export function hapticNotify(type = 'success') {
  try {
    tg?.HapticFeedback?.notificationOccurred(type);
  } catch { /* no haptics */ }
}

export function openTelegramShare(text, botUsername = 'oqila_ai_bot') {
  hapticImpact('medium');
  const url = `https://t.me/${botUsername}`;
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
  if (tg?.openTelegramLink) tg.openTelegramLink(shareUrl);
  else window.open(shareUrl, '_blank');
}

// ---------------------------------------------------------------------------
// Native dialogs: Telegram's own alert / confirm, window.alert / confirm in a browser
// ---------------------------------------------------------------------------
export function showAlert(message) {
  return new Promise((resolve) => {
    if (tg?.showAlert) {
      try {
        tg.showAlert(String(message), () => resolve());
        return;
      } catch { /* fall through */ }
    }
    window.alert(String(message));
    resolve();
  });
}

export function showConfirm(message) {
  return new Promise((resolve) => {
    if (tg?.showConfirm) {
      try {
        tg.showConfirm(String(message), (ok) => resolve(Boolean(ok)));
        return;
      } catch { /* fall through */ }
    }
    resolve(window.confirm(String(message)));
  });
}

// ---------------------------------------------------------------------------
// Back button: modals push a handler; the button is shown while there is one
// ---------------------------------------------------------------------------
const backHandlers = [];
let backBound = false;

function onBackClick() {
  const top = backHandlers[backHandlers.length - 1];
  if (top) top();
}

export function pushBackHandler(handler) {
  const button = tg?.BackButton;
  if (!button) return () => {};
  backHandlers.push(handler);
  if (!backBound) {
    button.onClick(onBackClick);
    backBound = true;
  }
  button.show();
  return () => {
    const i = backHandlers.lastIndexOf(handler);
    if (i >= 0) backHandlers.splice(i, 1);
    if (backHandlers.length === 0) {
      button.hide();
      button.offClick(onBackClick);
      backBound = false;
    }
  };
}

// ---------------------------------------------------------------------------
// Downloads. `<a download>` with a data: or blob: URL does nothing inside Telegram's WebView, so a file is
// handed to Telegram itself (8.0+), else to the system share sheet, else to a plain link.
// ---------------------------------------------------------------------------
/**
 * Save the file at `url` (an https URL of this server; for protected files it carries a media token).
 * Resolves to how it was handled: 'telegram' | 'share' | 'link' | 'cancelled'.
 */
export async function downloadFile(url, fileName) {
  const absolute = new URL(url, window.location.origin).toString();
  if (tg?.isVersionAtLeast?.('8.0') && typeof tg.downloadFile === 'function') {
    try {
      tg.downloadFile({ url: absolute, file_name: fileName });
      return 'telegram';
    } catch { /* fall through */ }
  }
  try {
    if (navigator.canShare && navigator.share) {
      const res = await fetch(absolute);
      if (res.ok) {
        const blob = await res.blob();
        const file = new File([blob], fileName, { type: blob.type || 'application/octet-stream' });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ files: [file] });
          return 'share';
        }
      }
    }
  } catch (err) {
    if (err?.name === 'AbortError') return 'cancelled'; // the person closed the share sheet
  }
  const a = document.createElement('a');
  a.href = absolute;
  a.download = fileName;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
  return 'link';
}
