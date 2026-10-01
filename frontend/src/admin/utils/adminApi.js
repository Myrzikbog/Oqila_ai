/**
 * adminApi.js — Administrative API client with session key handling
 */

export function getAdminKey() {
  if (typeof window === 'undefined') return '';
  // 1. Check URL parameters (?admin_key=... or ?key=...)
  try {
    const params = new URLSearchParams(window.location.search);
    const paramKey = params.get('admin_key') || params.get('key');
    if (paramKey && paramKey.trim()) {
      const clean = paramKey.trim();
      sessionStorage.setItem('oqila_admin_key', clean);
      localStorage.setItem('oqila_admin_key', clean);
      return clean;
    }
  } catch {}

  // 2. Check session or local storage
  return (
    sessionStorage.getItem('oqila_admin_key') ||
    localStorage.getItem('oqila_admin_key') ||
    ''
  );
}

export function setAdminKey(key) {
  if (typeof window === 'undefined') return;
  const clean = (key || '').trim();
  sessionStorage.setItem('oqila_admin_key', clean);
  localStorage.setItem('oqila_admin_key', clean);
}

export function clearAdminKey() {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem('oqila_admin_key');
  localStorage.removeItem('oqila_admin_key');
}

export async function adminFetch(endpoint, options = {}) {
  const key = getAdminKey();
  const headers = {
    'Content-Type': 'application/json',
    'X-Admin-Key': key,
    ...(options.headers || {}),
  };

  const res = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (res.status === 403) {
    clearAdminKey();
    throw new Error('UNAUTHORIZED');
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

export async function testAdminKey(key) {
  const res = await fetch('/api/admin/dashboard', {
    headers: { 'X-Admin-Key': key.trim() },
  });
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
  const key = getAdminKey();
  const res = await fetch('/api/admin/export/users.csv', {
    headers: { 'X-Admin-Key': key },
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
  const key = getAdminKey();
  const res = await fetch('/api/admin/export/cards.csv', {
    headers: { 'X-Admin-Key': key },
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
