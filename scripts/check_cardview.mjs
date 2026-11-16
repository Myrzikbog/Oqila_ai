// Renders CardView on the server with a verification failure and a long title: catches runtime errors in the
// studio editor without a browser. Run from the repository root: node scripts/check_cardview.mjs
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const frontend = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'frontend');
const require = createRequire(path.join(frontend, 'package.json'));
const { build } = await import(pathToFileURL(require.resolve('vite')).href);
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

const out = await build({
  root: frontend, logLevel: 'silent', configFile: false,
  build: { write: false, ssr: true, lib: { entry: path.join(frontend, 'src/components/studio/CardView.jsx'), formats: ['cjs'] } },
  ssr: { noExternal: [] },
  esbuild: { jsx: 'automatic' },
});
const code = (Array.isArray(out) ? out[0] : out).output[0].code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', code)(mod, mod.exports, require);
const CardView = mod.exports.default || mod.exports;

const registry = { styles: [{
  id: 'promo_sale', kind: 'ai_text', ru: 'Скидка', uz: 'Chegirma', aspect: '1:1', aspects: ['3:4', '1:1', '4:5', '9:16'], max_blocks: 6,
  fields: { title: { count: 1, limit: 32 }, discount: { count: 1, limit: 6 }, price: { count: 1, limit: 24 }, old_price: { count: 1, limit: 24 }, deadline: { count: 1, limit: 28 } },
  limits: { title: 32, price: 24, old_price: 24, deadline: 28, bullet: 28, badge: 18, subtitle: 40, cta: 18, contact: 30, brand_name: 24, use: 14 },
}] };
const card = {
  id: 7, title: 't', photoshoot_style: 'promo_sale', aspect: '1:1', studio_photo_url: '/api/cards/7/photo?v=1', has_source: true, version: 1,
  copy: { title: 'Очень длинное название товара которое не влезает', price: '380 000 сум', old_price: '450 000 сум', lang: 'ru' },
  verification: { verified: false, problems: [{ expected: '380 000 сум', found: '308 000 сум' }], unexpected: [] },
};
const html = renderToStaticMarkup(React.createElement(CardView, { card, registry, lang: 'ru', onUpdate() {} }));
const must = ['aspect-square', 'На картинке ошибка в:', '«380 000 сум» — написано: «308 000 сум»', 'Исправить только надпись', 'Сократить текст', 'value="380000"', '/6'];
const missing = must.filter((m) => !html.includes(m));
if (missing.length) { console.error('FAIL, missing:', missing, '\n', html.slice(0, 1500)); process.exit(1); }
console.log('CardView: picture, problems, editor with limits and actions render');
