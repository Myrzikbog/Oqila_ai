// Renders LegalAnswerCard on the server with every kind of notice and section; markup in the answer must stay text.
// Run from the repository root: node scripts/check_legal_card.mjs
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
  build: { write: false, ssr: true, lib: { entry: path.join(frontend, 'src/components/legal/LegalAnswerCard.jsx'), formats: ['cjs'] } },
  esbuild: { jsx: 'automatic' },
});
const code = (Array.isArray(out) ? out[0] : out).output[0].code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', code)(mod, mod.exports, require);
const Card = mod.exports.default || mod.exports;

const t = new Proxy({}, { get: (_, k) => `[${String(k)}]` });
const message = {
  id: 5, rating: 1, fallback: true, conflict: true, calc_warning: true, sources: [{ title: 'Закон', url: 'https://lex.uz/x', official: true, verified_at: '2026-11-05' }],
  answer: {
    short_answer: '**1%** <img src=x onerror=alert(1)>', steps: ['Шаг <script>x</script>'], documents: ['ЭЦП'], where_to_go: [{ name: 'soliq.uz', url: 'https://soliq.uz' }],
    deadlines: [{ what: 'налог', when: 'до 15' }], costs: [{ item: 'Соцналог', amount_uzs: 440000, fact_id: 'brv' }], risks: ['риск'],
    follow_up_questions: ['Когда платить?'], confidence: 'low', escalate: true, escalate_reason: 'суд',
  },
};
const html = renderToStaticMarkup(React.createElement(Card, { message, lang: 'ru', t, isLast: true, onFollowUp() {}, onRate() {} }));
const must = ['[legal_mock_notice]', '[legal_escalate]: суд', '[legal_check_calc]', '[legal_conflict]', '<b>1%</b>', '&lt;img src=x onerror=alert(1)&gt;', 'href="https://soliq.uz"', '[legal_costs]', '[legal_sources]', '[legal_deadlines]', 'Когда платить?'];
const rated = renderToStaticMarkup(React.createElement(Card, { message: { ...message, fallback: false }, lang: 'ru', t, isLast: false, onFollowUp() {}, onRate() {} }));
if (!rated.includes('aria-pressed="true"') || rated.includes('Когда платить?')) { console.error('FAIL rating buttons or follow-ups', rated.slice(0, 400)); process.exit(1); }
const missing = must.filter((m) => !html.includes(m));
if (missing.length || html.includes('<img') || html.includes('<script')) { console.error('FAIL', missing, '\n', html.slice(0, 1200)); process.exit(1); }
console.log('LegalAnswerCard: notices, sections, sources and follow-ups render; markup stays text');
