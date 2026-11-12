// Renders RichText on the server and checks that markup in a message stays text (master plan 1.7).
// Run from the repository root: node scripts/check_richtext.mjs
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
  build: { write: false, ssr: true, lib: { entry: path.join(frontend, 'src/components/RichText.jsx'), formats: ['cjs'] },
           rollupOptions: { external: ['react', 'react/jsx-runtime'] } },
});
const code = (Array.isArray(out) ? out[0] : out).output[0].code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', code)(mod, mod.exports, require);
const RichText = mod.exports.default || mod.exports;

const html = renderToStaticMarkup(React.createElement(RichText, { text: '<img src=x onerror=alert(1)> **жирный** <b>ok</b> <script>x</script>' }));
const fail = (msg) => { console.error('FAIL:', msg, '\n', html); process.exit(1); };
if (html.includes('<img') || html.includes('<script')) fail('markup was rendered as HTML');
if (!html.includes('&lt;img src=x onerror=alert(1)&gt;')) fail('the tag is not shown as text');
if (!html.includes('<b>жирный</b>') || !html.includes('<b>ok</b>')) fail('bold spans are missing');
console.log('RichText: markup is rendered as text, bold works');
