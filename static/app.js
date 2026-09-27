/* app.js — Oqila AI Client Logic
   Handles tab navigation, API calls, demo mode, calculator, legal guide, chat.
   Pure Vanilla JS — no build step required.
*/

// ============================================================
// STATE
// ============================================================
const state = {
  lang: 'ru',          // 'ru' | 'uz'
  activeTab: 'studio', // 'studio' | 'calc' | 'legal' | 'about'
  uploadedImage: null, // { dataUrl, file }
  cardResult: null,    // last generated card
  chatHistory: [],     // [{role, text}]
};

// ============================================================
// i18n STRINGS
// ============================================================
const i18n = {
  ru: {
    header: 'Oqila AI',
    subtitle: 'Карманный бизнес-ассистент',
    tab_studio: 'Студия',
    tab_calc: 'Финансы',
    tab_legal: 'Право',
    tab_about: 'О нас',
    upload_hint: 'Загрузите фото товара\n(нажмите или перетащите)',
    cost_price: 'Себестоимость (сум)',
    desired_price: 'Желаемая цена (сум)',
    note: 'Описание (необязательно)',
    demo_btn: '✨ Быстрое демо',
    gen_btn: '🚀 Сгенерировать упаковку (AI Launch)',
    copy_btn: '📋 Скопировать пост',
    copied: '✅ Скопировано!',
    share_btn: '✈️ В Telegram',
    share_toast: 'Отправка в Telegram...',
    generating: 'Генерирует AI...',
    sale_price: 'Цена продажи',
    cost_price_calc: 'Себестоимость',
    gross_profit: 'Валовая прибыль',
    margin: 'Маржинальность',
    tax: 'Налог',
    net_profit: 'Чистая прибыль',
    min_uzum: 'Мин. цена (Uzum)',
    min_direct: 'Мин. цена (прямая)',
    legal_title: 'Юридический гид',
    legal_subtitle: 'Легализуй бизнес за 10 минут',
    chat_placeholder: 'Задайте правовой вопрос...',
    send: 'Отправить',
    ai_thinking: '⏳ OqilaLegal думает...',
    about_mission: 'Наша миссия',
    about_tagline: 'Цифровые инструменты для женщин-предпринимательниц Узбекистана',
  },
  uz: {
    header: 'Oqila AI',
    subtitle: 'Qo\'l ostidagi biznes assistent',
    tab_studio: 'Studiya',
    tab_calc: 'Moliya',
    tab_legal: 'Huquq',
    tab_about: 'Biz haqimizda',
    upload_hint: 'Mahsulot rasmini yuklang\n(bosing yoki sudrab torting)',
    cost_price: 'Tannarx (so\'m)',
    desired_price: 'Maqsadli narx (so\'m)',
    note: 'Izoh (ixtiyoriy)',
    demo_btn: '✨ Tezkor demo',
    gen_btn: '🚀 Qadoqlashni yaratish (AI Launch)',
    copy_btn: '📋 Postni nusxalash',
    copied: '✅ Nusxalandi!',
    share_btn: '✈️ Telegram\'da ulashish',
    share_toast: 'Telegram\'ga yuborilmoqda...',
    generating: 'AI yaratmoqda...',
    sale_price: 'Sotish narxi',
    cost_price_calc: 'Tannarx',
    gross_profit: 'Yalpi foyda',
    margin: 'Marjinallik',
    tax: 'Soliq',
    net_profit: 'Sof foyda',
    min_uzum: 'Min. narx (Uzum)',
    min_direct: 'Min. narx (to\'g\'ridan)',
    legal_title: 'Huquqiy qo\'llanma',
    legal_subtitle: 'Biznesni 10 daqiqada rasmiylashtiring',
    chat_placeholder: 'Huquqiy savol bering...',
    send: 'Yuborish',
    ai_thinking: '⏳ OqilaLegal o\'ylamoqda...',
    about_mission: 'Bizning vazifamiz',
    about_tagline: 'O\'zbekiston ayol tadbirkorlari uchun raqamli vositalar',
  },
};

function t(key) {
  return (i18n[state.lang] || i18n.ru)[key] || key;
}

// ============================================================
// UTILITIES
// ============================================================
function formatNum(n) {
  if (n == null) return '—';
  return new Intl.NumberFormat('ru-RU').format(Math.round(n));
}

function showToast(msg, duration = 2200) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}

function setLoading(btnId, loading, label) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.dataset.origText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span> ${label || ''}`;
  } else {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.origText || label || '';
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

function markdownToHtml(text) {
  if (!text) return '';
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

// ============================================================
// TELEGRAM MINI APP INIT
// ============================================================
function initTelegram() {
  if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    // Apply Telegram theme colors
    if (tg.themeParams && tg.themeParams.bg_color) {
      document.documentElement.style.setProperty('--bg-main', tg.themeParams.bg_color);
    }
    console.log('✅ Telegram WebApp initialized. Version:', tg.version);
  } else {
    console.log('ℹ️ Running outside Telegram (browser mode).');
  }
}

// ============================================================
// LANGUAGE TOGGLE
// ============================================================
function setLang(lang) {
  state.lang = lang;
  document.querySelectorAll('.lang-toggle button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
  applyI18n();
  // Reload legal steps in new language
  if (state.activeTab === 'legal') loadLegalSteps();
}

function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      el.placeholder = t(key);
    } else {
      el.textContent = t(key);
    }
  });
}

// ============================================================
// TAB NAVIGATION
// ============================================================
function switchTab(tab) {
  state.activeTab = tab;

  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

  const pane = document.getElementById('tab-' + tab);
  if (pane) pane.classList.add('active');

  const navBtn = document.querySelector(`[data-tab="${tab}"]`);
  if (navBtn) navBtn.classList.add('active');

  // Lazy-load
  if (tab === 'legal' && !document.getElementById('legal-steps-container').dataset.loaded) {
    loadLegalSteps();
  }
  if (tab === 'about') {
    loadStats();
  }
}

// ============================================================
// TAB 1 — AI STUDIO
// ============================================================

// --- Upload zone ---
function initUploadZone() {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');

  zone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleImageFile(file);
  });

  // Drag and drop
  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) handleImageFile(file);
  });
}

function handleImageFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    state.uploadedImage = { dataUrl: e.target.result, file };
    renderUploadPreview(e.target.result, file.name);
  };
  reader.readAsDataURL(file);
}

function renderUploadPreview(dataUrl, name) {
  const zone = document.getElementById('upload-zone');
  zone.innerHTML = `
    <div class="relative w-full">
      <img src="${dataUrl}" alt="${name}" class="w-full object-cover rounded-xl" style="max-height:200px;object-fit:cover">
      <button onclick="clearImage()" class="absolute top-2 right-2 bg-white rounded-full p-1 shadow text-red-400 hover:text-red-600" style="font-size:1rem;line-height:1;border:none;cursor:pointer">✕</button>
    </div>
    <p class="text-xs text-center mt-1" style="color:var(--text-muted)">${name}</p>
  `;
}

function clearImage() {
  state.uploadedImage = null;
  const zone = document.getElementById('upload-zone');
  zone.innerHTML = `
    <div class="flex flex-col items-center gap-3 py-6">
      <span style="font-size:2.5rem">📸</span>
      <p class="text-sm font-medium" style="color:var(--text-muted);white-space:pre-line" data-i18n="upload_hint">${t('upload_hint')}</p>
    </div>
  `;
  document.getElementById('file-input').value = '';
}

// --- Demo button ---
async function runDemo() {
  setLoading('demo-btn', true, t('generating'));
  document.getElementById('result-section').style.display = 'none';

  try {
    const res = await fetch(`/api/demo-card?lang=${state.lang}`);
    const data = await res.json();
    state.cardResult = data;
    renderResultCard(data, null);
  } catch (err) {
    showToast('⚠️ Ошибка демо. Проверьте соединение.');
    console.error(err);
  } finally {
    setLoading('demo-btn', false, `${t('demo_btn')}`);
    document.getElementById('demo-btn').innerHTML = t('demo_btn');
  }
}

// --- Generate button ---
async function generateCard() {
  setLoading('gen-btn', true, t('generating'));
  document.getElementById('result-section').style.display = 'none';

  try {
    const formData = new FormData();
    formData.append('lang', state.lang);

    const costVal = document.getElementById('cost-price').value;
    const priceVal = document.getElementById('desired-price').value;
    const noteVal = document.getElementById('note').value;

    if (costVal) formData.append('cost_price', costVal);
    if (priceVal) formData.append('desired_price', priceVal);
    if (noteVal) formData.append('note', noteVal);
    if (state.uploadedImage) formData.append('image', state.uploadedImage.file);

    const res = await fetch('/api/generate-card', { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    state.cardResult = data;
    renderResultCard(data, state.uploadedImage ? state.uploadedImage.dataUrl : null);
  } catch (err) {
    showToast('⚠️ Ошибка генерации. Проверьте сервер.');
    console.error(err);
  } finally {
    setLoading('gen-btn', false);
    document.getElementById('gen-btn').innerHTML = t('gen_btn');
  }
}

function renderResultCard(data, imageDataUrl) {
  const section = document.getElementById('result-section');
  const hashtags = (data.hashtags || []).map(h => `<span class="hashtag-pill">${h}</span>`).join('');

  const imageHtml = imageDataUrl
    ? `<div class="product-frame mb-4">
         <img src="${imageDataUrl}" alt="product" class="w-full rounded-xl" style="max-height:220px;object-fit:cover">
       </div>`
    : `<div class="product-frame mb-4" style="background:linear-gradient(135deg,#d1fae5,#ede9fe);height:120px;display:flex;align-items:center;justify-content:center;border-radius:1rem">
         <span style="font-size:3rem">🌟</span>
       </div>`;

  section.innerHTML = `
    <div class="result-card p-4 mt-4">
      ${imageHtml}
      <h3 class="font-bold text-lg mb-2" style="color:var(--text-primary)">${escapeHtml(data.title || '')}</h3>
      <p class="text-sm mb-3" style="color:var(--text-primary);line-height:1.6;white-space:pre-line">${escapeHtml(data.description || '')}</p>
      <div class="flex items-center gap-2 mb-3 p-2 rounded-xl" style="background:var(--emerald-light)">
        <span class="text-lg">💰</span>
        <span class="font-bold" style="color:var(--emerald-dark)">${escapeHtml(data.price_tag || '')}</span>
      </div>
      <div class="mb-3">${hashtags}</div>
      <div class="p-3 rounded-xl mb-4" style="background:var(--lavender-light);border:1px solid var(--lavender)">
        <p class="text-xs font-bold mb-1" style="color:var(--lavender-dark)">💡 ${state.lang === 'uz' ? 'Savdo maslahati' : 'Совет по продажам'}</p>
        <p class="text-sm" style="color:var(--text-primary);white-space:pre-line">${escapeHtml(data.marketing_tip || '')}</p>
      </div>
      <div class="grid grid-cols-2 gap-2 mt-2">
        <button class="btn-copy w-full" id="copy-btn" onclick="copyPost()">
          ${t('copy_btn')}
        </button>
        <button class="btn-share w-full" id="share-btn" onclick="sharePost()">
          ${t('share_btn')}
        </button>
      </div>
    </div>
  `;

  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function buildPostText(data) {
  if (!data) return '';
  const hashtags = (data.hashtags || []).join(' ');
  return `${data.title}\n\n${data.description}\n\n${data.price_tag}\n\n${hashtags}`;
}

async function copyPost() {
  if (!state.cardResult) return;
  const text = buildPostText(state.cardResult);
  try {
    await navigator.clipboard.writeText(text);
    const btn = document.getElementById('copy-btn');
    if (btn) {
      btn.innerHTML = `✅ ${t('copied')}`;
      btn.classList.add('copied');
      setTimeout(() => {
        btn.innerHTML = `${t('copy_btn')}`;
        btn.classList.remove('copied');
      }, 2500);
    }
    showToast('✅ ' + t('copied'));
  } catch {
    showToast('⚠️ Clipboard unavailable');
  }
}

function sharePost() {
  if (!state.cardResult) return;
  const text = buildPostText(state.cardResult);
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent('https://t.me/oqila_ai_bot')}&text=${encodeURIComponent(text)}`;
  
  if (window.Telegram && window.Telegram.WebApp && typeof window.Telegram.WebApp.openTelegramLink === 'function') {
    window.Telegram.WebApp.openTelegramLink(shareUrl);
  } else {
    window.open(shareUrl, '_blank');
  }
  showToast(t('share_toast'));
}

// ============================================================
// TAB 2 — CALCULATOR
// ============================================================
function initCalculator() {
  const saleInput = document.getElementById('calc-sale');
  const costInput = document.getElementById('calc-cost');
  [saleInput, costInput].forEach(el => el && el.addEventListener('input', runCalc));
}

async function runCalc() {
  const sale = parseFloat(document.getElementById('calc-sale').value) || 0;
  const cost = parseFloat(document.getElementById('calc-cost').value) || 0;

  if (sale <= 0 && cost <= 0) {
    document.getElementById('calc-results').style.display = 'none';
    return;
  }

  try {
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sale_price: sale, cost_price: cost, lang: state.lang }),
    });
    const d = await res.json();
    renderCalcResults(d);
  } catch {
    // Offline fallback — local calculation
    const gross = sale - cost;
    const margin = sale > 0 ? ((gross / sale) * 100).toFixed(1) : 0;
    renderCalcResults({
      sale_price: sale,
      gross_profit: gross,
      margin_pct: margin,
      self_employed_tax: 0,
      self_employed_net: gross,
      yatt_turnover_tax: Math.round(sale * 0.01),
      net_profit: gross,
      min_price_uzum: Math.round((cost + 5250) / 0.85),
      min_price_direct: cost + 15000,
      tip: state.lang === 'uz'
        ? "✅ <b>PQ-4742:</b> 100 mln so'mgacha 0% soliq. <b>SK 467-modda:</b> YaTT uchun 1% aylanma solig'i."
        : "✅ <b>ПП-4742:</b> До 100 млн сум налог 0%. <b>Ст. 467 НК РУз:</b> Для ЯТТ налог с оборота 1%.",
    });
  }
}

function renderCalcResults(d) {
  const container = document.getElementById('calc-results');
  const profitColor = d.gross_profit >= 0 ? 'var(--emerald-dark)' : '#ef4444';
  const curr = state.lang === 'uz' ? "so'm" : "сум";

  container.innerHTML = `
    <div class="glass-card p-4 mt-4">
      <div class="calc-row">
        <span class="calc-label font-bold">${t('gross_profit')}</span>
        <span class="calc-value font-bold" style="color:${profitColor}">${formatNum(d.gross_profit)} ${curr}</span>
      </div>
      <div class="calc-row">
        <span class="calc-label">${t('margin')}</span>
        <span class="calc-value margin">${d.margin_pct}%</span>
      </div>
      
      <div class="my-2 border-t" style="border-color:var(--border)"></div>

      <!-- Self-employed mode (PP-4742) -->
      <div class="calc-row">
        <span class="calc-label font-medium">🌿 ${state.lang === 'uz' ? "O'z-o'zini band qilish (PQ-4742)" : "Самозанятый (ПП-4742, <100 млн)"}</span>
        <span class="calc-value tax">0 ${curr} (0%) ✅</span>
      </div>
      <div class="calc-row">
        <span class="calc-label text-xs" style="color:var(--text-muted)">↳ ${state.lang === 'uz' ? "Sof foyda" : "Чистая прибыль"}</span>
        <span class="calc-value profit">${formatNum(d.self_employed_net ?? d.net_profit)} ${curr}</span>
      </div>

      <!-- YaTT mode (Tax Code Art 467) -->
      <div class="calc-row mt-2">
        <span class="calc-label font-medium">🏢 ${state.lang === 'uz' ? "YaTT aylanma solig'i (SK 467-modda, 1%)" : "Налог с оборота ЯТТ (ст. 467 НК, 1%)"}</span>
        <span class="calc-value" style="color:#d97706">${formatNum(d.yatt_turnover_tax || (d.sale_price * 0.01))} ${curr}</span>
      </div>
      <div class="calc-row">
        <span class="calc-label text-xs" style="color:var(--text-muted)">↳ ${state.lang === 'uz' ? "Majburiy ijtimoiy soliq (SK 408)" : "Обязательный соцналог (ст. 408)"}</span>
        <span class="calc-value text-xs" style="color:var(--text-muted)">1 БРВ (${formatNum(d.yatt_social_tax_monthly || 440000)} ${curr})/мес</span>
      </div>

      <div class="my-2 border-t" style="border-color:var(--border)"></div>

      <!-- Marketplace & Delivery -->
      <div class="calc-row">
        <span class="calc-label">🛍️ ${t('min_uzum')} (${state.lang === 'uz' ? "15% + 5 250 so'm" : "15% + 5 250 сум"})</span>
        <span class="calc-value" style="color:var(--gold)">${formatNum(d.min_price_uzum)} ${curr}</span>
      </div>
      <div class="calc-row">
        <span class="calc-label">💬 ${t('min_direct')} (+доставка)</span>
        <span class="calc-value" style="color:var(--text-muted)">${formatNum(d.min_price_direct)} ${curr}</span>
      </div>
    </div>
    <div class="glass-card p-4 mt-3" style="border-color:var(--emerald-light)">
      <div class="text-sm" style="line-height:1.6;color:var(--text-primary)">${d.tip || ''}</div>
    </div>
  `;
  container.style.display = 'block';
}

// ============================================================
// TAB 3 — LEGAL
// ============================================================
async function loadLegalSteps() {
  const container = document.getElementById('legal-steps-container');
  container.dataset.loaded = '1';

  try {
    const res = await fetch(`/api/legal-steps?lang=${state.lang}`);
    const data = await res.json();
    renderLegalSteps(data.steps || []);
  } catch {
    container.innerHTML = '<p class="text-sm text-center" style="color:var(--text-muted)">⚠️ Не удалось загрузить шаги. Проверьте сервер.</p>';
  }
}

function renderLegalSteps(steps) {
  const container = document.getElementById('legal-steps-container');
  container.innerHTML = steps.map(step => `
    <div class="legal-step">
      <div class="step-number">${step.step}</div>
      <div class="flex-1">
        <p class="font-bold text-sm mb-1">${escapeHtml(step.title)}</p>
        <p class="text-xs mb-2" style="color:var(--text-muted);line-height:1.5">${escapeHtml(step.description)}</p>
        <div class="flex items-center gap-2">
          <span class="step-badge">${escapeHtml(step.badge)}</span>
          <a href="${step.link}" target="_blank" class="text-xs font-medium" style="color:var(--lavender-dark)">${step.link}</a>
        </div>
      </div>
    </div>
  `).join('');
}

// --- Legal Chat ---
async function sendLegalQuestion() {
  const input = document.getElementById('legal-input');
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  appendChatBubble('user', question);
  appendChatBubble('ai', t('ai_thinking'), 'thinking-bubble');

  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  try {
    const res = await fetch('/api/legal-qa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, lang: state.lang }),
    });
    const data = await res.json();

    // Remove thinking bubble
    const thinking = document.getElementById('thinking-bubble');
    if (thinking) thinking.remove();

    appendChatBubble('ai', data.answer || '');
  } catch (err) {
    const thinking = document.getElementById('thinking-bubble');
    if (thinking) thinking.remove();
    appendChatBubble('ai', '⚠️ Ошибка соединения. Попробуйте позже.');
  } finally {
    sendBtn.disabled = false;
  }
}

function appendChatBubble(role, text, id) {
  const chat = document.getElementById('chat-messages');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  if (id) bubble.id = id;
  bubble.innerHTML = markdownToHtml(text);
  chat.appendChild(bubble);
  chat.scrollTop = chat.scrollHeight;
}

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();
    const types = data.events_by_type || {};
    const aiCount = (types['generate_card'] || 0) + (types['demo_card'] || 0);
    const calcCount = types['calculate'] || 0;
    const legalCount = types['legal_qa'] || 0;

    const elAi = document.getElementById('stat-ai-count');
    const elCalc = document.getElementById('stat-calc-count');
    const elLegal = document.getElementById('stat-legal-count');

    if (elAi) elAi.textContent = aiCount;
    if (elCalc) elCalc.textContent = calcCount;
    if (elLegal) elLegal.textContent = legalCount;
  } catch (err) {
    console.log('Stats fetch error:', err);
  }
}

// Legal input — send on Enter (Shift+Enter for newline)
function initLegalChat() {
  const input = document.getElementById('legal-input');
  if (!input) return;
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendLegalQuestion();
    }
  });
}

// ============================================================
// BOOTSTRAP
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  initTelegram();
  initUploadZone();
  initCalculator();
  initLegalChat();
  applyI18n();
  switchTab('studio');

  // Add greeting bubble in chat
  setTimeout(() => {
    appendChatBubble('ai',
      state.lang === 'uz'
        ? '👋 Salom! Men OqilaLegal — O\'zbekiston qonunchiligi bo\'yicha sizning AI yordamchingizman. Savolingizni yozing!'
        : '👋 Привет! Я OqilaLegal — ваш AI-помощник по законодательству Узбекистана. Задайте любой вопрос о регистрации, налогах или онлайн-торговле!'
    );
  }, 300);
});
