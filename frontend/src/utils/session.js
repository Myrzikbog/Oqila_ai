/**
 * session.js — signed session token handling for the Oqila API.
 *
 * After /api/auth/login the server returns a session token. Every same-origin `/api/` request
 * (except the admin API, which uses its own key) gets `Authorization: Bearer <token>`.
 * URLs loaded by <img>/<a>/window.open cannot send headers: they get a short-lived media token via withToken().
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
  setMediaToken(null, 0); // belongs to the previous session
  if (token) refreshMediaToken();
}

// ---------------------------------------------------------------------------
// Media token: URLs loaded by <img>, <a> or window.open cannot send headers. They carry a 10-minute
// media token (`?mt=`) from POST /api/media-token. The 30-day session token never goes into a URL:
// URLs end up in server logs, browser history and Referer headers.
// ---------------------------------------------------------------------------
let mediaToken = null;
let mediaExpiresAt = 0;
let mediaPending = null;
let mediaTimer = null;
const mediaListeners = new Set();

function setMediaToken(token, ttlSeconds) {
  mediaToken = token || null;
  mediaExpiresAt = token ? Date.now() + ttlSeconds * 1000 : 0;
  if (mediaTimer) clearTimeout(mediaTimer);
  // renew a minute before it expires, so pictures on screen keep loading
  if (token) mediaTimer = setTimeout(() => { refreshMediaToken(); }, Math.max(15, ttlSeconds - 60) * 1000);
  mediaListeners.forEach((fn) => fn());
}

/** Fetch a new media token (one request at a time). Resolves to the token or null. */
export function refreshMediaToken() {
  if (!getSessionToken()) return Promise.resolve(null);
  if (!mediaPending) {
    mediaPending = fetch('/api/media-token', { method: 'POST' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.media_token) setMediaToken(data.media_token, data.expires_in || 600);
        return mediaToken;
      })
      .catch(() => null)
      .finally(() => { mediaPending = null; });
  }
  return mediaPending;
}

/** A media token that is valid for at least another 30 seconds. */
export async function ensureMediaToken() {
  if (mediaToken && mediaExpiresAt - Date.now() > 30000) return mediaToken;
  return refreshMediaToken();
}

export function getMediaToken() {
  return mediaToken && mediaExpiresAt > Date.now() ? mediaToken : null;
}

export function subscribeMediaToken(fn) {
  mediaListeners.add(fn);
  return () => mediaListeners.delete(fn);
}

function appendMediaToken(url, token) {
  if (!url || !token || typeof url !== 'string' || !url.startsWith('/api/')) return url;
  return `${url}${url.includes('?') ? '&' : '?'}mt=${encodeURIComponent(token)}`;
}

/**
 * Add the cached media token to an API URL used by <img src>. Components that call it should also call
 * useMediaToken() (utils/useMediaToken.js), so they render again when the token arrives or is renewed.
 */
export function withToken(url) {
  const token = getMediaToken();
  if (!token && getSessionToken()) refreshMediaToken();
  return appendMediaToken(url, token);
}

/** For click handlers (download, window.open): waits for a fresh token first. */
export async function mediaUrl(url) {
  return appendMediaToken(url, await ensureMediaToken());
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
