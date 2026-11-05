/**
 * adminApi.js — Administrative API client with session key handling
 */

const KEY_STORAGE = 'oqila_admin_key';

/** Telegram initData: inside the bot's WebApp an administrator is recognised without any key. */
export function getTelegramInitData() {
  if (typeof window === 'undefined') return '';
  return window.Telegram?.WebApp?.initData || '';
}

export function getAdminKey() {
  if (typeof window === 'undefined') return '';
  // The key is never read from the URL (URLs leak into server logs and chat history).
  // Drop a legacy ?key= / ?admin_key= parameter if present.
  try {
    const url = new URL(window.location.href);
    if (url.searchParams.has('key') || url.searchParams.has('admin_key')) {
      url.searchParams.delete('key');
      url.searchParams.delete('admin_key');
      window.history.replaceState(null, '', url.toString());
    }
    localStorage.removeItem(KEY_STORAGE); // older builds persisted the key permanently
    return sessionStorage.getItem(KEY_STORAGE) || '';
  } catch {
    return '';
  }
}

export function setAdminKey(key) {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem(KEY_STORAGE, (key || '').trim());
  } catch {
    /* ignore */
  }
}

export function clearAdminKey() {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.removeItem(KEY_STORAGE);
    localStorage.removeItem(KEY_STORAGE);
  } catch {
    /* ignore */
  }
}

function adminHeaders(key = getAdminKey()) {
  const headers = {};
  if (key) headers['X-Admin-Key'] = key;
  const initData = getTelegramInitData();
  if (initData) headers['X-Telegram-Init-Data'] = initData;
  return headers;
}

export function hasAdminCredentials() {
  return Boolean(getAdminKey() || getTelegramInitData());
}

export async function adminFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...adminHeaders(),
    ...(options.headers || {}),
  };

  const res = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (res.status === 403 || res.status === 503) {
    clearAdminKey();
    throw new Error('UNAUTHORIZED');
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

/** Check credentials: an explicit key, or (when key is omitted) the stored key / Telegram initData. */
export async function testAdminKey(key) {
  const headers = key === undefined ? adminHeaders() : adminHeaders(key.trim());
  const res = await fetch('/api/admin/dashboard', { headers });
  return res.ok;
}

export async function fetchAdminDashboard() {
  return adminFetch('/api/admin/dashboard');
}

export async function fetchAdminUsers({ limit = 50, offset = 0, search = '', status = '', category = '' } = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  params.set('offset', offset);
  if (search) params.set('search', search);
  if (status) params.set('status', status);
  if (category) params.set('category', category);
  return adminFetch(`/api/admin/users?${params.toString()}`);
}

export async function fetchAdminUserDetails(userId) {
  return adminFetch(`/api/admin/users/${userId}`);
}

export async function toggleAdminUserActive(userId) {
  return adminFetch(`/api/admin/users/${userId}/toggle-active`, { method: 'POST' });
}

export async function fetchAdminEvents({ limit = 100, offset = 0, eventType = '', userId = null } = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  params.set('offset', offset);
  if (eventType) params.set('event_type', eventType);
  if (userId) params.set('user_id', userId);
  return adminFetch(`/api/admin/events?${params.toString()}`);
}

export async function fetchAdminCards({ limit = 50, offset = 0, userId = null } = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  params.set('offset', offset);
  if (userId) params.set('user_id', userId);
  return adminFetch(`/api/admin/cards?${params.toString()}`);
}

export async function downloadUsersCsv() {
  const res = await fetch('/api/admin/export/users.csv', {
    headers: adminHeaders(),
  });
  if (!res.ok) throw new Error('Failed to download CSV');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `oqila_users_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadCardsCsv() {
  const res = await fetch('/api/admin/export/cards.csv', {
    headers: adminHeaders(),
  });
  if (!res.ok) throw new Error('Failed to download Cards CSV');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `oqila_cards_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

/**
 * Card photos are protected, and <img> cannot send the admin headers:
 * fetch the photo with them and return an object URL for the <img>.
 */
export async function fetchAdminPhotoUrl(cardId) {
  const res = await fetch(`/api/admin/cards/${cardId}/photo`, { headers: adminHeaders() });
  if (!res.ok) throw new Error(`Photo request failed: ${res.status}`);
  return URL.createObjectURL(await res.blob());
}
