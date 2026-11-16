/**
 * api.js — one way to call the Oqila API and show what went wrong.
 * `apiFetch` adds a timeout, checks `res.ok` and turns the server's `detail` (a string, or the list a
 * 422 returns) into an Error with a readable message. Never "[object Object]".
 */
export function errorText(detail, fallback) {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    const msg = typeof first === 'string' ? first : first?.msg;
    if (typeof msg === 'string' && msg) return msg;
  }
  return fallback;
}

export async function apiFetch(url, { timeout = 60000, fallback = 'Request failed', ...init } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, { ...init, signal: init.signal || controller.signal });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const error = new Error(errorText(body.detail, fallback));
      error.status = res.status;
      throw error;
    }
    return res;
  } catch (err) {
    if (err.name === 'AbortError') {
      const error = new Error(fallback);
      error.timeout = true;
      throw error;
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
