// Server-renders the main screens with a stubbed browser to catch runtime errors (undefined names, bad props)
// that lint and build cannot see. Run from the repository root: node scripts/check_render.mjs
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const frontend = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'frontend');
const require = createRequire(path.join(frontend, 'package.json'));
const { build } = await import(pathToFileURL(require.resolve('vite')).href);
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

globalThis.window = { location: { origin: 'https://x.example', search: '', pathname: '/' }, localStorage: { getItem: () => null, setItem() {} }, matchMedia: () => ({ matches: false, addEventListener() {} }), scrollTo() {}, addEventListener() {} };
globalThis.document = { documentElement: { classList: { add() {}, remove() {} } }, addEventListener() {}, removeEventListener() {}, activeElement: null };
Object.defineProperty(globalThis, 'navigator', { value: {}, configurable: true });
globalThis.fetch = async () => ({ ok: false, json: async () => ({}) });

const screens = [
  ['TabStudio', { lang: 'ru' }], ['TabStudio', { lang: 'uz' }], ['TabLegal', { lang: 'ru', profile: { name: 'Мадина', status: 'yatt' } }],
  ['TabLegal', { lang: 'uz' }], ['TabFinance', { lang: 'ru' }], ['TabUzum', { lang: 'uz' }], ['TabAbout', { lang: 'ru' }],
  ['HistoryModal', { lang: 'ru', isOpen: true }], ['ProfileModal', { lang: 'uz', isOpen: true, isOnboarding: true }], ['OnboardingModal', { lang: 'ru', isOpen: true }],
  ['Header', { lang: 'ru', theme: 'dark' }], ['BottomNav', { activeTab: 'legal' }],
];
const { translations } = await import(pathToFileURL(path.join(frontend, 'src/utils/i18n.js')).href);
const failures = [];
for (const [name, props] of screens) {
  try {
    const out = await build({
      root: frontend, logLevel: 'silent', configFile: false, esbuild: { jsx: 'automatic' },
      build: { write: false, ssr: true, lib: { entry: path.join(frontend, 'src/components', `${name}.jsx`), formats: ['cjs'] } },
    });
    const mod = { exports: {} };
    new Function('module', 'exports', 'require', (Array.isArray(out) ? out[0] : out).output[0].code)(mod, mod.exports, require);
    const Comp = mod.exports.default || mod.exports;
    const t = translations[props.lang || 'ru'];
    const html = renderToStaticMarkup(React.createElement(Comp, { t, onClose() {}, onSave() {}, onOpenHistory() {}, onOpenProfile() {}, setActiveTab() {}, setLang() {}, toggleTheme() {}, ...props }));
    if (html.length < 100) failures.push(`${name}: renders almost nothing`);
    if (/undefined|\[object Object\]/.test(html.replace(/<svg[\s\S]*?<\/svg>/g, ''))) failures.push(`${name}: "undefined" or "[object Object]" in the markup`);
  } catch (err) {
    failures.push(`${name}(${props.lang}): ${err.message}`);
  }
}
if (failures.length) { console.error(failures.join('\n')); process.exit(1); }
console.log(`render: ${screens.length} screens render without errors`);
