// Checks utils/telegram.js against a faked browser: downloadFile picks Telegram's downloader, the share sheet or a
// plain link; the back-button stack; native dialogs; closing confirmation. Run from the repository root.
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const frontend = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'frontend');
const require = createRequire(path.join(frontend, 'package.json'));
const { build } = await import(pathToFileURL(require.resolve('vite')).href);

const out = await build({
  root: frontend, logLevel: 'silent', configFile: false,
  build: { write: false, ssr: true, lib: { entry: path.join(frontend, 'src/utils/telegram.js'), formats: ['cjs'] } },
});
const code = (Array.isArray(out) ? out[0] : out).output[0].code;
const failures = [];
const check = (cond, msg) => { if (!cond) failures.push(msg); };

async function load(env) {
  const clicked = [];
  const doc = { createElement: () => ({ click() { clicked.push(this.href + '|' + this.download); }, remove() {} }), body: { appendChild() {} }, documentElement: { classList: { add() {}, remove() {} } } };
  globalThis.window = { location: { origin: 'https://oqila.example' }, Telegram: env.tg ? { WebApp: env.tg } : undefined, localStorage: { getItem: () => null }, matchMedia: () => ({ matches: false, addEventListener() {} }), alert: (m) => env.log?.push('alert:' + m), confirm: () => true };
  globalThis.document = doc;
  Object.defineProperty(globalThis, 'navigator', { value: env.navigator || {}, configurable: true });
  globalThis.fetch = env.fetch || (async () => ({ ok: true, blob: async () => new Blob(['x'], { type: 'image/jpeg' }) }));
  globalThis.File = class { constructor(parts, name, o) { this.name = name; this.type = o?.type; } };
  const mod = { exports: {} };
  new Function('module', 'exports', 'require', code)(mod, mod.exports, require);
  return { api: mod.exports, clicked };
}

// 1. Telegram 8.0+: its own downloader, with an absolute URL
let calls = [];
let { api } = await load({ tg: { isVersionAtLeast: (v) => v === '8.0', downloadFile: (o) => calls.push(o) } });
check(await api.downloadFile('/api/cards/5/photo?download=1&mt=abc', 'oqila-5.jpg') === 'telegram', 'telegram path');
check(calls[0]?.url === 'https://oqila.example/api/cards/5/photo?download=1&mt=abc' && calls[0]?.file_name === 'oqila-5.jpg', 'absolute url and file name');

// 2. older Telegram, a share sheet
const shared = [];
({ api } = await load({ tg: { isVersionAtLeast: () => false }, navigator: { canShare: () => true, share: async (d) => shared.push(d) } }));
check(await api.downloadFile('/x.jpg', 'x.jpg') === 'share' && shared.length === 1, 'share sheet path');

// 3. the person closes the share sheet
({ api } = await load({ navigator: { canShare: () => true, share: async () => { const e = new Error('closed'); e.name = 'AbortError'; throw e; } } }));
check(await api.downloadFile('/x.jpg', 'x.jpg') === 'cancelled', 'cancelled share');

// 4. nothing else: a plain link, never a data: URL
let clicked;
({ api, clicked } = await load({ navigator: {} }));
check(await api.downloadFile('/x.jpg', 'x.jpg') === 'link' && clicked[0] === 'https://oqila.example/x.jpg|x.jpg', 'link fallback');

// 5. back button: one handler stack, shown while there is one
const events = [];
const button = { show: () => events.push('show'), hide: () => events.push('hide'), onClick: (f) => { button.cb = f; events.push('on'); }, offClick: () => events.push('off') };
({ api } = await load({ tg: { BackButton: button } }));
const closed = [];
const off1 = api.pushBackHandler(() => closed.push('a'));
const off2 = api.pushBackHandler(() => closed.push('b'));
button.cb();
check(closed.join() === 'b', 'the top handler runs');
off2(); button.cb();
check(closed.join() === 'b,a', 'the next handler after the top is removed');
off1();
check(events.includes('hide') && events.at(-1) === 'off', 'the button hides when the last modal closes');

// 6. dialogs: native in Telegram, window.* in a browser
let answered = false;
({ api } = await load({ tg: { showConfirm: (m, cb) => cb(true), showAlert: (m, cb) => { answered = true; cb(); } } }));
check(await api.showConfirm('?') === true, 'tg confirm');
await api.showAlert('!'); check(answered, 'tg alert');
const log = [];
({ api } = await load({ log }));
check(await api.showConfirm('?') === true, 'browser confirm');
await api.showAlert('hi'); check(log.includes('alert:hi'), 'browser alert');

// 7. closing confirmation toggles
const states = [];
({ api } = await load({ tg: { enableClosingConfirmation: () => states.push('on'), disableClosingConfirmation: () => states.push('off') } }));
api.setClosingConfirmation(true); api.setClosingConfirmation(false);
check(states.join() === 'on,off', 'closing confirmation');

if (failures.length) { console.error('FAIL:', failures); process.exit(1); }
console.log('telegram utils: download paths, back-button stack, dialogs and closing confirmation behave');
