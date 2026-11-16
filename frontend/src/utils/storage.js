/** localStorage that never throws: private windows, blocked site data and previews make it unavailable. */
export function readStorage(key, fallback = null) {
  try {
    const value = window.localStorage.getItem(key);
    return value === null ? fallback : value;
  } catch {
    return fallback;
  }
}

export function writeStorage(key, value) {
  try {
    if (value === null || value === undefined) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

export function readJson(key, fallback = null) {
  try {
    const raw = readStorage(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function clearStorage() {
  try {
    window.localStorage.clear();
  } catch { /* nothing to clear */ }
}
