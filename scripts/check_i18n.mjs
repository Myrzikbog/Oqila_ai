// i18n consistency (master plan 4.5). Run from the repository root: node scripts/check_i18n.mjs [--list-unused]
//  1. RU and UZ have exactly the same keys
//  2. no component picks between two string literals with `lang === 'uz' ? '...' : '...'` (texts belong in i18n.js)
//  3. every key is used somewhere (a dead key is a translation nobody maintains)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'frontend', 'src');
const { translations } = await import(pathToFileURL(path.join(root, 'utils', 'i18n.js')).href);

const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]));
const files = walk(root).filter((f) => /\.(jsx?|mjs)$/.test(f));
const problems = [];

const ru = Object.keys(translations.ru), uz = Object.keys(translations.uz);
for (const k of ru.filter((k) => !uz.includes(k))) problems.push(`key only in RU: ${k}`);
for (const k of uz.filter((k) => !ru.includes(k))) problems.push(`key only in UZ: ${k}`);

const STR = String.raw`(?:'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*")`;
const inline = new RegExp(String.raw`(?:lang\s*===\s*'uz'|isUz)\s*\?\s*${STR}\s*:\s*${STR}`);
for (const f of files.filter((f) => f.includes(`${path.sep}components${path.sep}`))) {
  fs.readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
    if (inline.test(line)) problems.push(`${path.relative(root, f)}:${i + 1}: inline RU/UZ strings: ${line.trim().slice(0, 90)}`);
  });
}

const sources = files.filter((f) => !f.endsWith(`${path.sep}i18n.js`)).map((f) => fs.readFileSync(f, 'utf8')).join('\n');
const dynamic = /\bt\[\s*[`'"]?\$?\{?/.test(sources) ? [...sources.matchAll(/\bt\[\s*`([^`$]*)\$\{/g)].map((m) => m[1]) : [];
const unused = ru.filter((k) => !new RegExp(`\\b${k}\\b`).test(sources) && !dynamic.some((p) => k.startsWith(p)));
if (process.argv.includes('--list-unused')) console.log(unused.join('\n'));
for (const k of unused) problems.push(`unused key: ${k}`);

if (problems.length) {
  console.error(problems.join('\n'));
  console.error(`\n${problems.length} problem(s)`);
  process.exit(1);
}
console.log(`i18n: ${ru.length} keys in RU and UZ, no inline string pairs, no unused keys`);
