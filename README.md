# 🌿 Oqila AI — Tadbirkor Ayollar
> **Oqila AI Platform** · Экосистема цифровизации женского предпринимательства в Узбекистане

Карманный AI бизнес-ассистент для женщин-предпринимательниц, ремесленниц и микробизнеса. Автоматизирует упаковку товаров, копирайтинг, финансовые расчёты и базовый юридический комплаенс.

---

## 🚀 1. Локальный запуск (для тестирования)

```bash
# 1. Перейти в папку проекта
cd oqila-ai

# 2. Установить зависимости Python
pip install -r requirements.txt

# 3. (Опционально) Пересобрать React-фронтенд (dist уже собран):
# cd frontend && npm install && npm run build && cd ..

# 4. Запустить сервер
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Откройте в браузере: **http://localhost:8000** (откроется современный React SPA интерфейс)

---

## ☁️ 2. Развёртывание на VDS (Ubuntu / Debian)

Мы подготовили автоматический скрипт развёртывания `deploy.sh`:

```bash
# На вашем сервере VDS:
git clone <ваш_репозиторий>
cd oqila-ai

# Сделать скрипт исполняемым и запустить
chmod +x deploy.sh
./deploy.sh
```

### Что делает `deploy.sh`:
1. Устанавливает `python3`, `venv`, `nginx`, `git`, `curl`.
2. Создаёт виртуальное окружение и ставит зависимости из `requirements.txt`.
3. Создаёт и запускает фоновый сервис **systemd** (`oqila-ai.service`), который автоматически перезапускается при падении и при перезагрузке сервера.
4. Проверяет health check.

### Настройка HTTPS для Telegram Mini App (Nginx + Let's Encrypt):
Telegram требует HTTPS для Web App URL. Настройте Nginx за 2 минуты:

```bash
# 1. Скопировать конфиг Nginx
sudo cp nginx.conf /etc/nginx/sites-available/oqila-ai

# 2. Укажите ваш домен внутри файла:
sudo nano /etc/nginx/sites-available/oqila-ai

# 3. Активировать сайт и перезагрузить Nginx
sudo ln -s /etc/nginx/sites-available/oqila-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 4. Выпустить бесплатный SSL-сертификат:
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Привязка Telegram Webhook:
Если в `.env` задан `WEBAPP_URL`, вебхук регистрируется автоматически при старте сервера.
Вручную (только для администратора, ключ из `ADMIN_SECRET_KEY`):
```bash
curl -X POST "https://your-domain.com/api/set-webhook" -H "Content-Type: application/json" -H "X-Admin-Key: $ADMIN_SECRET_KEY" -d '{"url":"https://your-domain.com"}'
```
Каждое обновление от Telegram проверяется по секрету `X-Telegram-Bot-Api-Secret-Token`.

---

## 🤖 3. Telegram Bot & Mini App

- Бот: `@oqila_ai_bot` (токен задан в `.env`).
- Команда `/start` приветствует пользователя и выводит интерактивную кнопку с запуском **Telegram Mini App**.
- Внутри Mini App есть кнопка **«✈️ В Telegram»** для мгновенной отправки готового поста в чаты, каналы или истории.

---

## 📊 4. SQLite Метрики & Логирование

Все действия на платформе логируются в локальную базу данных `oqila_ai.db`:
- Кол-во генераций упаковки (AI и Mock)
- Кол-во финансово-налоговых расчётов
- Кол-во юридических консультаций
- Статистика по языкам (O'zbek / Русский)

Эндпоинт для жюри: `GET /api/stats`  
Вкладка **«О нас»** в Mini App отображает живые метрики в реальном времени!

---

## 🔑 Переменные окружения (.env)

```env
GEMINI_API_KEY=your_gemini_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
AI_MODE=gemini
WEBAPP_URL=https://your-domain.com   # (укажите при деплое на VDS)
ADMIN_SECRET_KEY=...                 # ключ админ-панели, минимум 16 символов
SESSION_SECRET=...                   # подпись сессий пользователей
TELEGRAM_WEBHOOK_SECRET=...          # секрет вебхука Telegram
ADMIN_TELEGRAM_IDS=123456789         # Telegram id администраторов (вход в /admin без ключа)
ALLOW_GUEST_LOGIN=1                  # 0 — пускать только из Telegram
HOST=0.0.0.0
PORT=8000
```
`deploy.sh` сам генерирует `ADMIN_SECRET_KEY`, `SESSION_SECRET` и `TELEGRAM_WEBHOOK_SECRET`, если они пустые.
Полный список — в `.env.example`.

---

## 🔒 Безопасность

- **Вход.** В Telegram пользователь определяется только по подписанному `initData` (проверка HMAC и срока давности).
  В обычном браузере сервер создаёт гостевой аккаунт. После входа выдаётся подписанный токен сессии,
  и все пользовательские API берут `user_id` из него, а не из запроса.
- **Изоляция данных.** История карточек, фото, профиль и все данные Uzum (ключ API, магазины, заказы,
  остатки, уведомления) хранятся отдельно для каждого пользователя.
- **Админ-панель** (`/admin`): заголовок `X-Admin-Key` с `ADMIN_SECRET_KEY` или Telegram-аккаунт
  администратора (`ADMIN_TELEGRAM_IDS` или `/admin <ключ>` в боте). Ключ никогда не передаётся в URL.
  Без `ADMIN_SECRET_KEY` вход по ключу отключён.
- Uvicorn слушает только `127.0.0.1`, наружу сервис открыт через nginx с HTTPS.

## 🧪 Тесты

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

---

## 🛡️ Безотказность для живого демо

Если API-ключ не задан или интернет нестабилен:
- Включается **железный Mock-fallback**: возвращает реалистичный красивый JSON с описанием узбекского национального изделия на узбекском и русском языках.
- Кнопка **«✨ Быстрое демо»** позволяет мгновенно показать работу жюри без фотографирования на камеру.
