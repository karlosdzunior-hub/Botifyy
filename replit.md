# Botify

Telegram-бот BotFactory — платформа для создания Telegram-ботов и Mini Apps через AI-диалог без знания кода.

## Run & Operate

- `cd bot && python main.py` — запустить Telegram-бота
- Workflow: `Botify Telegram Bot` — основной процесс бота

## Stack

- Python 3.11 + aiogram 3.x — Telegram bot framework
- Groq API (qwen-qwq-32b, llama-3.3-70b, gemma2-9b) — AI-диалог с ротацией моделей
- aiosqlite + SQLite — база данных
- Node.js / Express (api-server) — вспомогательный API

## Where things live

- `bot/main.py` — точка входа бота
- `bot/config.py` — конфигурация (модели, стоимость, тарифы)
- `bot/database.py` — все операции с БД (пользователи, боты, кредиты, диалоги)
- `bot/ai_client.py` — Groq AI клиент, системный промпт, парсинг резюме
- `bot/keyboards.py` — все клавиатуры и кнопки
- `bot/handlers/` — обработчики команд и callback'ов
- `botify.db` — SQLite база данных (создаётся автоматически)

## Architecture decisions

- FSM (MemoryStorage) для управления состоянием диалога создания бота
- Ротация AI-моделей при ошибках: qwen-qwq-32b → llama-3.3-70b → gemma2-9b
- История диалога хранится в БД (таблица dialogues), передаётся в контекст AI
- Кредиты списываются только после подтверждения резюме пользователем
- Рефералы через deep link: /start ref_{telegram_id}

## Product

- /start — приветствие + 150 кредитов новым пользователям
- 🤖 Создать бота — AI-диалог, сбор требований, резюме, списание кредитов
- 📱 Создать Mini App — аналогично для веб-приложений
- 📦 Мои боты — список созданных ботов с деталями
- 🖥️ Хостинг — тарифы Мини/Стандарт/Макс (399/890/1990 ₽/мес)
- 💳 Кредиты — баланс, история транзакций
- 👥 Рефералы — реферальная ссылка, статистика (+50 кредитов за реферала)
- ❓ Помощь — FAQ

## User preferences

- Язык: русский
- AI провайдер: Groq (qwen, llama, gemma)
- Secrets: TELEGRAM_BOT_TOKEN, GROK_API_KEY

## Gotchas

- DB_PATH должен быть абсолютным путём (/home/runner/workspace/botify.db)
- Groq API key хранится в секрете GROK_API_KEY
- После изменений в bot/ — перезапустить workflow "Botify Telegram Bot"
