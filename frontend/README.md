# Oqila AI: frontend

React 19 + Vite + Tailwind CSS 3. The Telegram Mini App, the admin panel (`/admin`) and the presentation screen
(`/stage`) are built from this folder; the FastAPI server in the repository root serves the result from `dist/`.

```bash
npm ci               # exact dependencies from package-lock.json (Node 20.19+ or 22.12+)
npm run dev          # Vite dev server (proxy the API to the backend on :8000 if you need it)
npm run build        # production build into dist/ (not stored in git; deploy.sh builds it)
npx oxlint src       # lint: no warnings are left, keep it that way
```

Smoke checks that need no browser (run from the repository root; CI runs them all):

```bash
node scripts/check_i18n.mjs          # RU and UZ have the same keys, no inline "uz ? ... : ..." strings, no dead keys
node scripts/check_render.mjs        # the main screens render on the server with a stubbed browser
node scripts/check_cardview.mjs      # the picture editor; check_legal_card.mjs: the legal answer card
node scripts/check_richtext.mjs      # markup in an answer is shown as text, never as HTML
node scripts/check_telegram_utils.mjs # downloads, back button, dialogs, closing confirmation
```

Layout: `src/App.jsx` is the shell (tabs and modals are loaded on first use), `src/components/` the screens,
`src/components/studio/` the picture editor and brand settings, `src/components/legal/` the legal answer card,
`src/utils/` shared helpers (`api.js` for requests with timeouts and readable errors, `telegram.js` for the Mini App
SDK, `session.js` for tokens, `i18n.js` for every text in Russian and Uzbek).

Rules that keep the app consistent: all user-visible text goes into `src/utils/i18n.js` (both languages); a request
goes through `apiFetch`; a modal uses `useTelegramBackButton` and `useDialog`; text from the server or the AI is rendered
through `RichText` (never as HTML); a file is saved through `downloadServerFile`.
