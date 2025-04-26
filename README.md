# Telegram Shop Bot

Телеграм бот для управления магазином с функциями каталога товаров, бонусной программой и системой доставки.

## Функциональность

- 🛍 Каталог товаров с категориями
- 🎁 Бонусная программа (накопление и использование баллов)
- 📦 Система заказов и отслеживания
- 🚚 Различные способы доставки
- ❓ FAQ и информационные разделы
- 👤 Панель администратора

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/YOUR_USERNAME/telegram-shop-bot.git
cd telegram-shop-bot
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
pip install -r requirements.txt
```

3. Создайте файл .env и добавьте необходимые переменные окружения:
```
BOT_TOKEN=your_bot_token_here
```

4. Запустите бота:
```bash
python bot.py
```

## Зависимости

- python-telegram-bot
- python-dotenv

## Структура проекта

- `bot.py` - основной файл бота
- `orders.json` - база данных заказов
- `loyalty.json` - база данных бонусной программы
- `.env` - файл с переменными окружения
- `requirements.txt` - список зависимостей

## Лицензия

MIT 