/**
 * auth.js — Telegram WebApp initData & Backend User Authentication
 */

export function getTelegramInitData() {
  if (typeof window !== 'undefined' && window.Telegram?.WebApp?.initData) {
    return window.Telegram.WebApp.initData;
  }
  return '';
}

export function getTelegramUserRaw() {
  if (typeof window !== 'undefined' && window.Telegram?.WebApp?.initDataUnsafe?.user) {
    return window.Telegram.WebApp.initDataUnsafe.user;
  }
  return null;
}

/**
 * Authenticate current user with the backend database.
 * If running inside Telegram, uses initData.
 * If running in standalone browser, uses cached profile / guest ID.
 */
export async function loginWithBackend(cachedProfile = null) {
  try {
    const initData = getTelegramInitData();
    let guestId = null;

    if (!initData) {
      // Standalone browser: persist a stable guest ID in localStorage
      guestId = localStorage.getItem('oqila_guest_id');
      if (!guestId) {
        guestId = String(900000000 + Math.floor(Math.random() * 90000000));
        localStorage.setItem('oqila_guest_id', guestId);
      }
    }

    const payload = {
      init_data: initData || null,
      profile: {
        ...(cachedProfile || {}),
        guest_id: guestId ? parseInt(guestId, 10) : undefined,
      },
    };

    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      console.warn('Backend login returned status:', res.status);
      return null;
    }

    const data = await res.json();
    return data; // { status, user_id, is_telegram, profile }
  } catch (err) {
    console.error('Failed to authenticate with backend:', err);
    return null;
  }
}

/**
 * Update user business profile on the server.
 */
export async function saveProfileToBackend(userId, profile) {
  if (!userId) return null;
  try {
    const res = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        name: profile.name,
        status: profile.status,
        category: profile.category,
        sales_channel: profile.salesChannel || profile.sales_channel,
        lang: profile.lang,
      }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.profile;
  } catch (err) {
    console.error('Failed to save profile to backend:', err);
    return null;
  }
}
