import { getSessionToken, runLoginOnce, setSessionToken } from './session';

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
 * Inside Telegram the server trusts only the signed initData.
 * In a standalone browser the server creates a guest account; the stored session token
 * keeps the same guest account on the next visit.
 */
export function loginWithBackend(cachedProfile = null) {
  return runLoginOnce(() => doLogin(cachedProfile));
}

async function doLogin(cachedProfile) {
  try {
    const initData = getTelegramInitData();
    const headers = { 'Content-Type': 'application/json' };
    const existingToken = getSessionToken();
    if (!initData && existingToken) headers.Authorization = `Bearer ${existingToken}`;

    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        init_data: initData || null,
        profile: { ...(cachedProfile || {}) },
      }),
    });

    if (!res.ok) {
      console.warn('Backend login returned status:', res.status);
      if (res.status === 401 || res.status === 403) setSessionToken(null);
      return null;
    }

    const data = await res.json();
    if (data.session_token) setSessionToken(data.session_token);
    return data; // { status, user_id, is_telegram, session_token, profile }
  } catch (err) {
    console.error('Failed to authenticate with backend:', err);
    return null;
  }
}

/**
 * Update the signed-in user's business profile on the server.
 */
export async function saveProfileToBackend(userId, profile) {
  if (!userId) return null;
  try {
    const res = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
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
