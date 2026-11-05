/**
 * session.js — signed session token handling for the Oqila API.
 *
 * After /api/auth/login the server returns a session token. Every same-origin `/api/` request
 * (except the admin API, which uses its own key) gets `Authorization: Bearer <token>`.
 * URLs loaded by <img>/<a>/window.open cannot send headers, so they get `?token=` via withToken().
 */

const TOKEN_KEY = 'oqila_session_token';
let memoryToken = null;

export function getSessionToken() {
  if (memoryToken) return memoryToken;
  try {
    memoryToken = localStorage.getItem(TOKEN_KEY);
  } catch {
    memoryToken = null;
  }
  return memoryToken;
}

export function setSessionToken(token) {
  memoryToken = token || null;
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode): keep the in-memory token */
  }
}

/** Append the session token to an API URL used by <img src>, <a href> or window.open. */
export function withToken(url) {
  const token = getSessionToken();
  if (!url || !token || typeof url !== 'string' || !url.startsWith('/api/')) return url;
  return `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
}

function isUserApiRequest(input) {
  let url = typeof input === 'string' ? input : input?.url;
  if (!url) return false;
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.origin !== window.location.origin) return false;
    url = parsed.pathname;
  } catch {
    return false;
  }
  return url.startsWith('/api/') && !url.startsWith('/api/admin/') && url !== '/api/auth/login';
}

let reloginHandler = null;
let pendingLogin = null;

/** Register how to obtain a fresh token when the server answers 401 (e.g. after a restart). */
export function setReloginHandler(fn) {
  reloginHandler = fn;
}

/**
 * Run a login at most once at a time: concurrent callers share the same promise,
 * so parallel 401 responses never create several guest accounts.
 */
export function runLoginOnce(loginFn) {
  if (!pendingLogin) {
    pendingLogin = Promise.resolve()
      .then(loginFn)
      .finally(() => {
        pendingLogin = null;
      });
  }
  return pendingLogin;
}

/** Install a fetch wrapper that attaches the session token to the user API. */
export function installAuthFetch() {
  if (typeof window === 'undefined' || window.__oqilaAuthFetch) return;
  const nativeFetch = window.fetch.bind(window);
  window.__oqilaAuthFetch = true;
  window.__oqilaNativeFetch = nativeFetch;

  const withAuth = (init = {}) => {
    const token = getSessionToken();
    if (!token) return init;
    const headers = new Headers(init.headers || {});
    if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
    return { ...init, headers };
  };

  window.fetch = async (input, init) => {
    if (!isUserApiRequest(input)) return nativeFetch(input, init);
    if (!getSessionToken() && pendingLogin) {
      try {
        await pendingLogin;
      } catch {
        /* fall through: the request will get 401 */
      }
    }
    const res = await nativeFetch(input, withAuth(init));
    if (res.status === 401 && reloginHandler) {
      const ok = await runLoginOnce(reloginHandler);
      if (ok) return nativeFetch(input, withAuth(init));
    }
    return res;
  };
}
