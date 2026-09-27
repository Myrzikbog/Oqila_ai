/**
 * Telegram WebApp SDK Integration, Theme Synchronization & Haptic Feedback
 */

export const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : null;

export function getTelegramUser() {
  try {
    return tg?.initDataUnsafe?.user || null;
  } catch (e) {
    return null;
  }
}

export function initTelegram() {
  if (tg) {
    try {
      tg.ready();
      tg.expand();
      if (tg.enableClosingConfirmation) {
        tg.enableClosingConfirmation();
      }
    } catch (e) {
      console.warn("Telegram WebApp init:", e);
    }
  }
}

/**
 * Returns current theme: 'dark' or 'light'
 * Priority: 
 * 1. User manual preference in localStorage
 * 2. Telegram WebApp colorScheme
 * 3. Browser system prefers-color-scheme
 */
export function getInitialTheme() {
  const saved = localStorage.getItem('oqila_theme');
  if (saved === 'dark' || saved === 'light' || saved === 'eastern') {
    return saved;
  }
  if (tg?.colorScheme) {
    return tg.colorScheme;
  }
  if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

/**
 * Applies 'dark' or 'eastern' class to <html> element
 */
export function applyTheme(theme) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.classList.remove('dark');
  root.classList.remove('eastern');

  if (theme === 'dark') {
    root.classList.add('dark');
  } else if (theme === 'eastern') {
    root.classList.add('eastern');
  }
}

export function subscribeToThemeChanges(onThemeChange) {
  // Listen for Telegram dynamic theme change event
  if (tg?.onEvent) {
    tg.onEvent('themeChanged', () => {
      // Only auto-switch if user hasn't set an explicit manual override
      const saved = localStorage.getItem('oqila_theme');
      if (!saved && tg.colorScheme) {
        applyTheme(tg.colorScheme);
        onThemeChange(tg.colorScheme);
      }
    });
  }

  // Listen for system browser change
  if (typeof window !== 'undefined' && window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', (e) => {
      const saved = localStorage.getItem('oqila_theme');
      if (!saved && !tg?.colorScheme) {
        const t = e.matches ? 'dark' : 'light';
        applyTheme(t);
        onThemeChange(t);
      }
    });
  }
}

export function hapticImpact(style = 'light') {
  if (tg?.HapticFeedback) {
    try {
      tg.HapticFeedback.impactOccurred(style);
    } catch {}
  }
}

export function hapticNotify(type = 'success') {
  if (tg?.HapticFeedback) {
    try {
      tg.HapticFeedback.notificationOccurred(type);
    } catch {}
  }
}

export function openTelegramShare(text, botUsername = 'oqila_ai_bot') {
  hapticImpact('medium');
  const url = `https://t.me/${botUsername}`;
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
  
  if (tg?.openTelegramLink) {
    tg.openTelegramLink(shareUrl);
  } else {
    window.open(shareUrl, '_blank');
  }
}
