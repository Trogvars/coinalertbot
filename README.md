# 🤖 Crypto Alert Bot

Профессиональный бот для мониторинга Open Interest и обнаружения ликвидаций.

## 🚀 Возможности

- 📊 Мониторинг Open Interest на Binance Futures
- ⚡ Обнаружение вероятных ликвидаций через анализ OI
- 🎯 Множественные таймфреймы (15 мин, 30 мин, 1 час)
- 🔄 WebSocket для real-time мониторинга
- ⚙️ Гибкие пользовательские настройки

## 📦 Установка

\`\`\`bash
git clone https://github.com/Trogvars/coinalertbot.git
cd coinalertbot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

## ⚙️ Настройка

Создайте `.env`:
\`\`\`
BOT_TOKEN=your_telegram_bot_token
COINMARKETCAP_API_KEY=your_cmc_api_key
UPDATE_INTERVAL=60
\`\`\`

## 🚀 Запуск

\`\`\`bash
./start_bot.sh
# или
python main.py
\`\`\`

## 📖 Команды

- `/start` - Запуск бота
- `/start_monitoring` - Включить мониторинг
- `/settings` - Настройки
- `/status` - Статус системы

