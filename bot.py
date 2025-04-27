import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler, CallbackQueryHandler
from dotenv import load_dotenv
from datetime import datetime, time, timedelta
import telegram
import pandas as pd
import io

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Conversation states
MAIN_MENU, CATALOG, LOYALTY, TRACKING, FAQ, DELIVERY, SELECTING_QUANTITY, USE_POINTS, DELIVERY_METHOD, ENTER_USER_DATA, CONFIRM_ORDER, WAITING_TRACKING, ORDER_COMMENT = range(13)

# Add new state for admin input
ADMIN_TRACKING_INPUT = 999  # New state for admin tracking code input

# Path to orders file
ORDERS_FILE = 'orders.json'
LOYALTY_FILE = 'loyalty.json'

# Admin settings
ADMIN_ID = "7100115774"  # Admin ID
ADMIN_CHAT_ID = "-1002673493739"  # Admin group ID as string

# Add global variables
PROMO_CODES = {
    'SUMMER': {'discount': 5, 'type': 'percent', 'min_order': 0, 'uses_left': float('inf')}
}

# Add delivery methods
DELIVERY_METHODS = {
    'shuttle': {
        'name': '🚐 Маршруткой',
        'description': 'Отправка в день заказа',
        'details': '• Отправка в день заказа\n• Быстрая доставка\n• Удобное время получения\n• Оплата при получении\n• Проверка товара на месте'
    },
    'euro_post': {
        'name': '📮 Европочтой',
        'description': 'Доставка 1-3 дня',
        'details': '• Доставка по всей РБ\n• Оплата при получении\n• Срок доставки 1-3 дня\n• Требуемые данные:\n  - ФИО получателя\n  - Номер телефона\n  - Полный адрес с индексом\n  - Номер отделения Европочты'
    },
    'bel_post': {
        'name': '📫 Белпочтой',
        'description': 'Доставка 2-5 дней',
        'details': '• Доставка по всей РБ\n• Оплата при получении\n• Срок доставки 2-5 дней\n• Требуемые данные:\n  - ФИО получателя\n  - Номер телефона\n  - Полный адрес с индексом\n  - Номер отделения Белпочты'
    },
    'pickup': {
        'name': '🏃 Самовывоз',
        'description': 'Бесплатно, в Гродно',
        'details': '• Без дополнительной платы\n• В любое удобное время\n• Проверка товара на месте\n• Адрес: г. Гродно\n• Требуется номер телефона и желаемое время'
    }
}

# Load orders
def load_orders():
    """Load orders from file"""
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading orders: {e}")
        return {}

# Save orders
def save_orders():
    """Save orders to file"""
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ORDERS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving orders: {e}")

async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's orders"""
    user_id = str(update.effective_user.id)
    orders = load_orders()
    
    user_orders = []
    for order_id, order in orders.items():
        if order.get('user_id') == user_id:
            user_orders.append((order_id, order))
    
    if not user_orders:
        await update.message.reply_text(
            "У вас пока нет заказов.\n"
            "Напишите менеджеру для оформления заказа: @pmaaaaaaaaaa",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    orders_text = "📦 Ваши заказы:\n\n"
    
    for order_id, order in sorted(user_orders, key=lambda x: x[1]['timestamp'], reverse=True):
        status = "✅ Доставлен" if order.get('delivered') else "🚚 В пути"
        orders_text += (
            f"🆔 Заказ: {order_id}\n"
            f"📅 Дата: {order['timestamp']}\n"
            f"💰 Сумма: {order.get('final_sum', 0)} р.\n"
            f"📦 Статус: {status}\n"
        )
        if order.get('tracking_code'):
            orders_text += f"📤 Трек-код: {order['tracking_code']}\n"
        orders_text += "\n"
    
    keyboard = [[KeyboardButton("◀️ В главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(orders_text, reply_markup=reply_markup)
    return MAIN_MENU

# Product catalog
PRODUCTS = {
    'airpods_pro_2': {
        'name': 'AirPods Pro 2',
        'price': 65,
        'old_price': 105,
        'category': 'Наушники',
        'bonus': '🎁 Фирменный чехол в подарок',
        'description': '✨ Премиум копия\n• Активное шумоподавление\n• Поддержка iOS и Android\n• До 6 часов работы\n• Прозрачный режим'
    },
    'airpods_4': {
        'name': 'AirPods 4',
        'price': 135,
        'category': 'Наушники',
        'description': '✨ Премиум качество\n• Улучшенный звук\n• Автоподключение\n• До 5 часов работы\n• Сенсорное управление'
    },
    'airpods_2': {
        'name': 'AirPods 2',
        'price': 35,
        'category': 'Наушники',
        'description': '✨ Отличное качество\n• Чистый звук\n• Быстрое подключение\n• До 4 часов работы'
    },
    'airpods_3': {
        'name': 'AirPods 3',
        'price': 50,
        'category': 'Наушники',
        'description': '✨ Премиум качество\n• Объемный звук\n• Автоподключение\n• До 5 часов работы\n• Влагозащита'
    },
    'watch_8_ultra': {
        'name': 'Apple Watch 8 Ultra',
        'price': 65,
        'old_price': 75,
        'category': 'Часы',
        'description': '✨ Премиум копия\n• Титановый корпус\n• Спортивный дизайн\n• Пульсометр\n• До 36 часов работы'
    },
    'watch_9': {
        'name': 'Apple Watch 9',
        'price': 100,
        'category': 'Часы',
        'description': '✨ Премиум качество\n• Алюминиевый корпус\n• Контроль здоровья\n• До 18 часов работы\n• Always-On Display'
    },
    'watch_ultra_2': {
        'name': 'Apple Watch Ultra 2',
        'price': 120,
        'category': 'Часы',
        'description': '✨ Максимальная комплектация\n• Титановый корпус\n• Расширенные датчики\n• До 36 часов работы\n• Сверхяркий экран'
    },
    'dyson_fan': {
        'name': 'Фен Dyson(full)',
        'price': 185,
        'old_price': 220,
        'category': 'Другое',
        'bonus': '🎁 AirPods 2 в подарок',
        'description': '✨ Премиум копия\n• Мощный поток воздуха\n• Контроль температуры\n• Защита от перегрева\n• Полная комплектация'
    },
    'block_20w': {
        'name': 'Блок 20w (AAA+)',
        'price': 20,
        'category': 'Аксессуары',
        'description': '✨ Высшее качество AAA+\n• Быстрая зарядка 20W\n• Для iPhone/iPad\n• Защита от перегрева'
    },
    'cable_lightning': {
        'name': 'Кабель lightning',
        'price': 10,
        'category': 'Аксессуары',
        'description': '✨ Премиум качество\n• Быстрая зарядка\n• Усиленная оплетка\n• Длина 1 метр'
    },
    'cable_magsafe': {
        'name': 'Кабель Magsafe',
        'price': 20,
        'category': 'Аксессуары',
        'description': '✨ Оригинальное качество\n• Магнитное крепление\n• Быстрая зарядка 15W\n• Для iPhone 12+'
    },
    'dualsock_4': {
        'name': 'DualShock 4 v2',
        'price': 50,
        'category': 'Другое',
        'description': '✨ Премиум копия\n• Беспроводной геймпад\n• До 8 часов работы\n• Тачпад\n• Поддержка PC/PS4'
    },
    'casio_vintage': {
        'name': 'Casio Vintage square',
        'price': 35,
        'category': 'Часы',
        'description': '✨ Премиум качество\n• Стальной корпус\n• Календарь\n• Подсветка\n• Влагозащита'
    }
}

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Return main menu keyboard"""
    keyboard = [
        ["🛍 Каталог"],
        ["🎁 Бонусная программа", "📦 Мои заказы"],
        ["❓ FAQ", "🚚 Доставка"],
        ["🔄 Перезапустить бота"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_catalog_keyboard():
    """Get catalog keyboard"""
    categories = sorted(set(product['category'] for product in PRODUCTS.values()))
    keyboard = []
    for category in categories:
        keyboard.append([KeyboardButton(f"📁 {category}")])
    keyboard.append([KeyboardButton("◀️ В главное меню")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def format_product(product):
    """Format product information"""
    text = f"📱 {product['name']}\n💰 Цена: {product['price']} р."
    
    if 'old_price' in product:
        text += f" (было {product['old_price']} р.)"
    
    if 'description' in product:
        text += f"\n\n{product['description']}"
    if 'bonus' in product:
        text += f"\n{product['bonus']}"
    
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_message = (
        "Привет👋\n\n"
        "🌐Мы являемся розничным магазином ‼️\n\n"
        "✅Всегда в сети 24/7\n\n"
        "•  Наши преимущества на рынке:\n"
        "•  Отличное качество\n"
        "•  Самая дешёвые цены в РБ\n"
        "•  Отправка по всей РБ и СНГ\n"
        "•  Отправка в день заказа\n\n"
        "✏️По всем технически вопросам:\n"
        "❕ @pmaaaaaaaaaa\n\n"
        "[✅Отзывы](https://t.me/+Iss7Cv_-kboxYzdi)\n\n"
        "✅Личная встреча Гродно\n"
        "✅Отправка почтой!\n\n"
        "Наши каналы:\n"
        "🛍 Розница: @GlovHandy\n"
        "📦 Опт: @GlovHandyOPT\n\n"
        "Все представленные товары являются репликами Premium+ качества📄"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu handler"""
    text = update.message.text

    if text == "🛍 Каталог":
        await update.message.reply_text(
            "Выберите категорию товаров:",
            reply_markup=get_catalog_keyboard()
        )
        return CATALOG
    elif text == "🎁 Бонусная программа":
        return await show_loyalty(update, context)
    elif text == "📦 Мои заказы":
        return await show_my_orders(update, context)
    elif text == "❓ FAQ":
        return await show_faq(update, context)
    elif text == "🚚 Доставка":
        return await show_delivery(update, context)
    elif text == "🔄 Перезапустить бота":
        return await restart_bot(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки меню",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU

async def handle_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catalog handler"""
    text = update.message.text
    
    if text == "◀️ В главное меню":
        await update.message.reply_text(
            "Вы вернулись в главное меню",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    if text == "◀️ Назад":
        await update.message.reply_text(
            "Выберите категорию товаров:",
            reply_markup=get_catalog_keyboard()
        )
        return CATALOG
    
    # If category selected
    if text.startswith("📁 "):
        category = text[2:].strip()
        products_in_category = []
        keyboard = []
        products_text = []
        
        # Collect products info and create buttons
        for product_id, product in PRODUCTS.items():
            if product['category'] == category:
                products_text.append(format_product(product))
                button_text = f"{product['name']}"  # Removed phone emoji
                keyboard.append([KeyboardButton(button_text)])
                products_in_category.append(product_id)
        
        keyboard.extend([
            [KeyboardButton("◀️ Назад")],
            [KeyboardButton("◀️ В главное меню")]
        ])
        
        if products_in_category:
            context.user_data['current_category'] = category
            context.user_data['category_products'] = {
                f"{PRODUCTS[pid]['name']}": pid  # Removed phone emoji
                for pid in products_in_category
            }
            
            message = f"📁 Категория: {category}\n\n"
            message += "\n\n".join(products_text)
            
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                "В этой категории пока нет товаров",
                reply_markup=get_catalog_keyboard()
            )
        return CATALOG
    
    # If product selected
    if 'category_products' in context.user_data and text in context.user_data['category_products']:
        product_id = context.user_data['category_products'][text]
        product = PRODUCTS[product_id]
        
        # Save selected product
        context.user_data['selected_product'] = product_id
        
        # Show quantity selection keyboard
        keyboard = []
        # Create rows of 3 numbers each
        for i in range(1, 10, 3):
            row = [str(i), str(i+1), str(i+2)]
            keyboard.append([KeyboardButton(num) for num in row])
        keyboard.append([KeyboardButton("◀️ Назад")])
        
        await update.message.reply_text(
            f"Выберите количество для {product['name']}:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return SELECTING_QUANTITY
    
    await update.message.reply_text(
        "Выберите категорию из меню",
        reply_markup=get_catalog_keyboard()
    )
    return CATALOG

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity selection"""
    text = update.message.text
    
    if text == "◀️ Назад":
        # Go back to category view
        category = context.user_data.get('current_category')
        if category:
            products_in_category = []
            keyboard = []
            products_text = []
            
            for product_id, product in PRODUCTS.items():
                if product['category'] == category:
                    products_text.append(format_product(product))
                    button_text = f"{product['name']}"  # Removed phone emoji
                    keyboard.append([KeyboardButton(button_text)])
                    products_in_category.append(product_id)
            
            keyboard.extend([
                [KeyboardButton("◀️ Назад")],
                [KeyboardButton("◀️ В главное меню")]
            ])
            
            message = f"📁 Категория: {category}\n\n"
            message += "\n\n".join(products_text)
            
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return CATALOG
    
    try:
        quantity = int(text)
        if quantity <= 0 or quantity > 9:
            raise ValueError
        
        product_id = context.user_data.get('selected_product')
        if not product_id:
            await update.message.reply_text(
                "❌ Произошла ошибка. Пожалуйста, начните выбор товара заново.",
                reply_markup=get_catalog_keyboard()
            )
            return CATALOG
        
        product = PRODUCTS[product_id]
        total_price = product['price'] * quantity
        
        # Save order details in context
        context.user_data['order'] = {
            'product_id': product_id,
            'product_name': product['name'],
            'quantity': quantity,
            'total_price': total_price
        }
        
        # Check loyalty points
        user_id = str(update.effective_user.id)
        loyalty_data = load_loyalty_data()
        user_data = loyalty_data.get(user_id, {"points": 0, "total_spent": 0, "orders": 0})
        available_points = user_data.get("points", 0)
        
        message = (
            "🛍️ Ваш заказ:\n"
            "━━━━━━━━━━━━━━━\n"
            f"📱 Товар: {product['name']}\n"
            f"📦 Количество: {quantity}\n"
            f"💰 Сумма: {total_price} р.\n"
            "━━━━━━━━━━━━━━━\n\n"
        )
        
        if available_points > 0:
            points_value = available_points * 0.1  # 1 балл = 0.1 руб
            message += f"🎁 У вас есть {available_points} бонусных баллов!\n"
            message += f"💫 Можно оплатить до {points_value:.1f} р.\n"
            message += "Хотите использовать баллы для оплаты?"
            
            keyboard = [
                [KeyboardButton("✅ Использовать баллы"), KeyboardButton("❌ Без баллов")],
                [KeyboardButton("◀️ Назад")]
            ]
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return USE_POINTS
        else:
            message += "ℹ️ У вас пока нет бонусных баллов.\n"
            message += "✨ Выберите способ доставки:"
            keyboard = [[KeyboardButton(method['name'])] for method in DELIVERY_METHODS.values()]
            keyboard.append([KeyboardButton("◀️ Назад")])
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return DELIVERY_METHOD
            
    except ValueError:
        keyboard = [
            [KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3")],
            [KeyboardButton("4"), KeyboardButton("5"), KeyboardButton("6")],
            [KeyboardButton("7"), KeyboardButton("8"), KeyboardButton("9")],
            [KeyboardButton("◀️ Назад")]
        ]
        await update.message.reply_text(
            "🔢 Пожалуйста, выберите количество от 1 до 9:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return SELECTING_QUANTITY

async def handle_points_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle loyalty points usage decision"""
    text = update.message.text
    order = context.user_data.get('order', {})
    
    if text == "◀️ Назад":
        return await handle_quantity(update, context)
    
    if text == "✅ Использовать баллы":
        user_id = str(update.effective_user.id)
        loyalty_data = load_loyalty_data()
        user_data = loyalty_data.get(user_id, {"points": 0, "total_spent": 0, "orders": 0})
        available_points = user_data["points"]
        points_value = available_points * 0.1  # 1 балл = 0.1 руб
        
        # Рассчитываем максимально возможную скидку
        max_discount = min(points_value, order['total_price'])
        final_price = order['total_price'] - max_discount
        points_used = int(max_discount * 10)  # Конвертируем обратно в баллы
        
        # Сохраняем данные заказа
        context.user_data['order'].update({
            'points_used': points_used,
            'points_value': max_discount,
            'final_price': final_price
        })
        
        # Обновляем баллы пользователя
        user_data["points"] -= points_used
        loyalty_data[user_id] = user_data
        save_loyalty_data(loyalty_data)
        
        message = (
            "💫 Баллы будут использованы!\n\n"
            f"Начальная сумма: {order['total_price']} р.\n"
            f"Скидка баллами: {max_discount} р.\n"
            f"Использовано баллов: {points_used}\n"
            f"Итоговая сумма: {final_price} р.\n\n"
            "✨ Выберите способ доставки:"
        )
    else:  # "❌ Без баллов"
        context.user_data['order'].update({
            'points_used': 0,
            'points_value': 0,
            'final_price': order['total_price']
        })
        message = "✨ Выберите способ доставки:"
    
    keyboard = [[KeyboardButton(method['name'])] for method in DELIVERY_METHODS.values()]
    keyboard.append([KeyboardButton("◀️ Назад")])
    
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return DELIVERY_METHOD

async def handle_delivery_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delivery method selection"""
    text = update.message.text
    
    if text == "◀️ Назад":
        return await handle_quantity(update, context)
    
    selected_method = None
    for method_id, method in DELIVERY_METHODS.items():
        if method['name'] == text:
            selected_method = method
            context.user_data['order']['delivery_method'] = method_id
            break
    
    if not selected_method:
        keyboard = [[KeyboardButton(method['name'])] for method in DELIVERY_METHODS.values()]
        keyboard.append([KeyboardButton("◀️ Назад")])
        await update.message.reply_text(
            "❌ Пожалуйста, выберите способ доставки из предложенных вариантов:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return DELIVERY_METHOD
    
    # Ask for order comment
    await update.message.reply_text(
        "💬 Хотите добавить комментарий к заказу? (например, пожелания по доставке или особые требования)\n"
        "Если комментарий не нужен, отправьте 'Нет'",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Нет")], [KeyboardButton("◀️ Назад")]], resize_keyboard=True)
    )
    return ORDER_COMMENT

async def handle_order_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order comment input"""
    text = update.message.text
    
    if text == "◀️ Назад":
        keyboard = [[KeyboardButton(method['name'])] for method in DELIVERY_METHODS.values()]
        keyboard.append([KeyboardButton("◀️ Назад")])
        await update.message.reply_text(
            "✨ Выберите способ доставки:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return DELIVERY_METHOD
    
    # Save comment or None if user doesn't want to add one
    context.user_data['order']['comment'] = None if text.lower() == 'нет' else text
    
    # After selecting delivery method, ask for user data
    example_format = (
        "📝 Пример заполнения:\n"
        "━━━━━━━━━━━━━━━\n"
    )
    
    delivery_method = DELIVERY_METHODS[context.user_data['order']['delivery_method']]
    
    if delivery_method['name'] == '📮 Европочтой':
        example_format += (
            "ФИО: Иванов Иван Иванович\n"
            "Телефон: +375291234567\n"
            "Адрес: г. Минск, ул. Пушкина, д. 5, кв. 10\n"
            "Индекс: 220000\n"
            "Отделение: Европочта №15 (ул. Ленина 23)"
        )
    elif delivery_method['name'] == '📫 Белпочтой':
        example_format += (
            "ФИО: Иванов Иван Иванович\n"
            "Телефон: +375291234567\n"
            "Адрес: г. Минск, ул. Пушкина, д. 5, кв. 10\n"
            "Индекс: 220000\n"
            "Отделение: Белпочта №12 (ул. Советская 15)"
        )
    elif delivery_method['name'] == '🚐 Маршруткой':
        example_format += (
            "Имя: Иван\n"
            "Телефон: +375291234567\n"
            "Город: Минск\n"
            "Желаемое время: 14:00"
        )
    else:  # Самовывоз
        example_format += (
            "Имя: Иван\n"
            "Телефон: +375291234567\n"
            "Желаемое время: 16:30"
        )
    
    example_format += "\n━━━━━━━━━━━━━━━"
    
    message = (
        "📋 Пожалуйста, укажите ваши данные в следующем формате:\n\n"
    )
    
    if delivery_method['name'] == '📮 Европочтой':
        message += (
            "ФИО: \n"
            "Телефон: \n"
            "Адрес: \n"
            "Индекс: \n"
            "Отделение: \n"
        )
    elif delivery_method['name'] == '📫 Белпочтой':
        message += (
            "ФИО: \n"
            "Телефон: \n"
            "Адрес: \n"
            "Индекс: \n"
            "Отделение: \n"
        )
    elif delivery_method['name'] == '🚐 Маршруткой':
        message += (
            "Имя: \n"
            "Телефон: \n"
            "Город: \n"
            "Желаемое время: \n"
        )
    else:  # Самовывоз
        message += (
            "Имя: \n"
            "Телефон: \n"
            "Желаемое время: \n"
        )
    
    message += f"\n{example_format}\n\n✨ Скопируйте формат выше и заполните своими данными"
    
    keyboard = [[KeyboardButton("◀️ Назад")]]
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ENTER_USER_DATA

async def handle_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user data input"""
    text = update.message.text
    
    if text == "◀️ Назад":
        keyboard = [[KeyboardButton(method['name'])] for method in DELIVERY_METHODS.values()]
        keyboard.append([KeyboardButton("◀️ Назад")])
        await update.message.reply_text(
            "✨ Выберите способ доставки:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return DELIVERY_METHOD
    
    # Validate user data format
    lines = text.strip().split('\n')
    delivery_method = DELIVERY_METHODS[context.user_data['order']['delivery_method']]
    
    # Define required fields based on delivery method
    required_fields = []
    if delivery_method['name'] in ['📮 Европочтой', '📫 Белпочтой']:
        required_fields = ['ФИО:', 'Телефон:', 'Адрес:', 'Индекс:', 'Отделение:']
    elif delivery_method['name'] == '🚐 Маршруткой':
        required_fields = ['Имя:', 'Телефон:', 'Город:', 'Желаемое время:']
    else:  # Самовывоз
        required_fields = ['Имя:', 'Телефон:', 'Желаемое время:']
    
    # Check if all required fields are present and not empty
    missing_fields = []
    for field in required_fields:
        field_found = False
        for line in lines:
            if line.strip().startswith(field):
                # Check if the field has a value after the colon
                if len(line.split(':')) < 2 or not line.split(':', 1)[1].strip():
                    missing_fields.append(field)
                field_found = True
                break
        if not field_found:
            missing_fields.append(field)
    
    if missing_fields:
        error_message = "❌ Пожалуйста, укажите все необходимые данные. Не заполнены поля:\n\n"
        for field in missing_fields:
            error_message += f"{field} ...\n"
        error_message += "\n✨ Скопируйте формат выше и заполните своими данными полностью."
        await update.message.reply_text(
            error_message,
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("◀️ Назад")]], resize_keyboard=True)
        )
        return ENTER_USER_DATA
    
    # Save user data
    context.user_data['order']['user_data'] = text
    
    # Show order confirmation
    order = context.user_data.get('order', {})
    final_price = order.get('final_price', order.get('total_price', 0))
    
    message = (
        "📋 Подтверждение заказа:\n"
        "━━━━━━━━━━━━━━━\n"
        f"📱 Товар: {order['product_name']}\n"
        f"📦 Количество: {order['quantity']}\n"
        f"🚚 Доставка: {delivery_method['name']}\n"
        f"💰 Итоговая сумма: {final_price} р.\n\n"
        "👤 Данные получателя:\n"
        f"{text}\n"
        "━━━━━━━━━━━━━━━\n\n"
        "✅ Подтвердите заказ"
    )
    
    keyboard = [
        [KeyboardButton("✅ Оформить заказ")],
        [KeyboardButton("❌ Отменить"), KeyboardButton("◀️ Назад")]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CONFIRM_ORDER

async def handle_order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle final order confirmation"""
    text = update.message.text.strip()
    print(f"Received button press: '{text}'")
    
    if text == "◀️ Назад":
        return await handle_user_data(update, context)
        
    if text == "❌ Отменить":
        await update.message.reply_text(
            "❌ Заказ отменен. Возвращаемся в главное меню.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
        
    if text in ["✅ Оформить заказ", "Оформить заказ"]:
        try:
            # Get order details
            order = context.user_data.get('order', {})
            print(f"Order data from context: {order}")
            
            if not order:
                print("No order data found in context")
                await update.message.reply_text(
                    "❌ Ошибка: данные заказа не найдены. Пожалуйста, начните заказ заново.",
                    reply_markup=get_main_keyboard()
                )
                return MAIN_MENU

            user = update.effective_user
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate final price if not set
            if 'final_price' not in order:
                product = PRODUCTS[order['product_id']]
                order['final_price'] = product['price'] * order['quantity']
                context.user_data['order'] = order
            
            print(f"Preparing to send order to admin group {ADMIN_CHAT_ID}")
            print(f"User info: {user.first_name} (ID: {user.id})")
            
            # Format admin message
            admin_message = (
                "🆕 НОВЫЙ ЗАКАЗ!\n\n"
                f"📅 Дата: {current_time}\n"
                f"👤 Покупатель: {user.first_name}\n"
                f"🆔 ID: {user.id}\n"
            )
            
            if user.username:
                admin_message += f"📱 Username: @{user.username}\n"
            
            admin_message += (
                "\n📦 Заказанные товары:\n"
                f"• {order.get('product_name', 'Неизвестный товар')} x{order.get('quantity', 1)} - {order.get('final_price', 0)} р.\n\n"
                f"💰 Сумма заказа: {order.get('final_price', 0)} р.\n"
                f"💵 Итого к оплате: {order.get('final_price', 0)} р.\n\n"
                f"🚚 Способ доставки: {DELIVERY_METHODS[order['delivery_method']]['name']}\n\n"
            )
            
            # Add comment if exists
            if order.get('comment'):
                admin_message += f"💬 Комментарий к заказу:\n{order['comment']}\n\n"
            
            admin_message += "📝 Данные для доставки:\n"
            
            # Add delivery data in a clean format
            delivery_data = order['user_data'].split('\n')
            for line in delivery_data:
                if line.strip():  # Only add non-empty lines
                    admin_message += f"{line}\n"

            print("Attempting to send message to admin group...")
            
            # Create inline keyboard for tracking code
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Отправить трек-код", callback_data=f"track|{user.id}")]
            ])
            
            # Send message to admin group
            sent_message = await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_message,
                parse_mode=None,
                reply_markup=keyboard
            )
            print(f"Message successfully sent to admin group: {sent_message.message_id}")
            
            # Send confirmation to user with improved formatting
            success_message = (
                "✅ Заказ успешно оформлен!\n"
                "━━━━━━━━━━━━━━━\n\n"
                "📋 Информация о заказе:\n"
                f"• Товар: {order.get('product_name')}\n"
                f"• Количество: {order.get('quantity')}\n"
                f"• Сумма: {order.get('final_price')} р.\n"
            )
            
            if order.get('comment'):
                success_message += f"• Комментарий: {order['comment']}\n"
            
            success_message += (
                "\n🚚 Статус:\n"
                "• Заказ принят в обработку\n"
                "• Ожидает подтверждения\n\n"
                "👤 Что дальше:\n"
                "• Наш менеджер проверит заказ\n"
                "• Свяжется с вами для подтверждения\n"
                "• Отправит информацию об оплате\n\n"
                "💫 Спасибо за покупку!\n"
                "━━━━━━━━━━━━━━━"
            )
            
            await update.message.reply_text(
                success_message,
                reply_markup=get_main_keyboard()
            )
            
            # Clear the order data from context
            if 'order' in context.user_data:
                del context.user_data['order']
                print("Order data cleared from context")
            
            # Начисляем баллы за заказ
            user_id = str(update.effective_user.id)
            loyalty_data = load_loyalty_data()
            user_data = loyalty_data.get(user_id, {"points": 0, "total_spent": 0, "orders": 0})
            
            # Рассчитываем и начисляем новые баллы
            order_total = order.get('final_price', 0)
            new_points = calculate_points(order_total)
            
            # Обновляем данные пользователя
            user_data["points"] += new_points
            user_data["total_spent"] += order_total
            user_data["orders"] += 1
            
            loyalty_data[user_id] = user_data
            save_loyalty_data(loyalty_data)
            
            # Отправляем сообщение о начислении баллов
            points_message = (
                "🎁 Начислены бонусные баллы!\n"
                "━━━━━━━━━━━━━━━\n\n"
                f"✨ За этот заказ: +{new_points} баллов\n"
                f"💎 Всего баллов: {user_data['points']}\n"
                f"💵 Сумма в рублях: {user_data['points'] * 0.1:.1f} р.\n\n"
                "💫 Используйте баллы в следующих заказах!\n"
                "━━━━━━━━━━━━━━━"
            )
            
            await update.message.reply_text(points_message)
            
            return MAIN_MENU
                
        except Exception as e:
            print(f"Error processing order: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Full error details: {e.__dict__}")
            # Send error message to user only if no success message was sent
            if 'success_message' not in locals():
                await update.message.reply_text(
                    "❌ Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте еще раз или свяжитесь с администратором.",
                    reply_markup=get_main_keyboard()
                )
            return MAIN_MENU
    
    # If none of the above conditions met
    await update.message.reply_text(
        "❌ Пожалуйста, подтвердите или отмените заказ",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("✅ Оформить заказ")],
            [KeyboardButton("❌ Отменить"), KeyboardButton("◀️ Назад")]
        ], resize_keyboard=True)
    )
    return CONFIRM_ORDER

def load_loyalty_data():
    """Load loyalty data from file"""
    try:
        if os.path.exists(LOYALTY_FILE):
            with open(LOYALTY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"Error loading loyalty data: {e}")
        return {}

def save_loyalty_data(data):
    """Save loyalty data to file"""
    try:
        with open(LOYALTY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, ensure_ascii=False, indent=2, fp=f)
    except Exception as e:
        logging.error(f"Error saving loyalty data: {e}")

def calculate_points(amount):
    """Calculate bonus points from purchase amount"""
    return int(amount * 0.05)  # 5% от суммы заказа в баллах

async def show_loyalty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show loyalty program information"""
    user_id = str(update.effective_user.id)
    loyalty_data = load_loyalty_data()
    user_data = loyalty_data.get(user_id, {"points": 0, "total_spent": 0, "orders": 0})
    
    # Форматируем числа для красивого отображения
    points = user_data.get("points", 0)
    total_spent = user_data.get("total_spent", 0)
    orders = user_data.get("orders", 0)
    points_value = points * 0.1  # 1 балл = 0.1 руб
    
    loyalty_text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"💎 Ваши бонусные баллы: {points}\n"
        f"💵 Сумма в рублях: {points_value:.1f} р.\n"
        f"💰 Общая сумма покупок: {total_spent} р.\n"
        f"📦 Количество заказов: {orders}\n\n"
        "📋 Правила программы:\n"
        "• За каждую покупку 5% возвращается баллами\n"
        "• 1 бонусный балл = 0.1 руб. скидки\n"
        "• Баллы можно использовать при любом заказе\n"
        "• Можно оплатить баллами до 100% стоимости\n\n"
        "🎯 Как накопить больше:\n"
        "• Совершайте покупки регулярно\n"
        "• Приглашайте друзей\n"
        "• Участвуйте в акциях\n\n"
        "💫 Специальные предложения:\n"
        "• Удвоенные баллы в день рождения\n"
        "• Дополнительные баллы за отзывы\n"
        "• Бонусы за покупки друзей\n"
        "━━━━━━━━━━━━━━━"
    )
    
    keyboard = [[KeyboardButton("◀️ В главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(loyalty_text, reply_markup=reply_markup)
    return MAIN_MENU

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show FAQ"""
    faq_text = (
        "❓ Часто задаваемые вопросы\n\n"
        "1️⃣ Как связаться с менеджером?\n"
        "• Напишите @pmaaaaaaaaaa\n\n"
        "2️⃣ Какие способы доставки доступны?\n"
        "• Европочта\n"
        "• Белпочта\n"
        "• Маршрутка\n"
        "• Самовывоз в Гродно\n\n"
        "3️⃣ Как работает бонусная программа?\n"
        "• За каждую покупку начисляются баллы\n"
        "• 1 балл = 10 копеек скидки\n"
        "• Баллы можно использовать при оформлении заказа\n\n"
        "4️⃣ Есть ли гарантия на товар?\n"
        "• Да, на все товары действует гарантия\n"
        "• При обнаружении брака - замена\n"
        "• Проверка товара при получении\n\n"
        "5️⃣ Какие способы оплаты?\n"
        "• Наложенный платёж\n"
        "• Перевод на карту\n"
        "• Наличными при получении"
    )
    
    keyboard = [[KeyboardButton("◀️ В главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(faq_text, reply_markup=reply_markup)
    return MAIN_MENU

async def show_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show delivery information"""
    delivery_text = (
        "🚚 Способы доставки\n\n"
        "📮 Европочта\n"
        f"{DELIVERY_METHODS['euro_post']['details']}\n\n"
        "📫 Белпочта\n"
        f"{DELIVERY_METHODS['bel_post']['details']}\n\n"
        "🚐 Маршрутка\n"
        f"{DELIVERY_METHODS['shuttle']['details']}\n\n"
        "🏃‍♂️ Самовывоз в Гродно\n"
        f"{DELIVERY_METHODS['pickup']['details']}\n\n"
        "ℹ️ Важная информация:\n"
        "• Все посылки отправляются с наложенным платежом\n"
        "• Оплата производится при получении\n"
        "• Проверка товара обязательна при получении\n"
        "• При обнаружении брака - замена товара\n"
        "• Страховка посылки включена в стоимость\n"
        "• Отслеживание посылки через трек-номер\n"
        "• Поддержка 24/7 по всем вопросам"
    )
    
    keyboard = [[KeyboardButton("◀️ В главное меню")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(delivery_text, reply_markup=reply_markup)
    return MAIN_MENU

async def send_tracking_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the tracking code button press"""
    query = update.callback_query
    await query.answer()  # Answer the callback query to remove loading state
    
    try:
        # Parse user ID from callback data
        _, user_id = query.data.split('|')
        user_id = int(user_id)
        
        # Save target user ID in context
        context.user_data['target_user_id'] = user_id
        
        # Remove inline keyboard
        await query.message.edit_reply_markup(None)
        
        # Ask admin for tracking code
        await update.effective_message.reply_text(
            f"📝 Введите трек-код для отправки пользователю (ID: {user_id}):"
        )
        
        # Set state for admin input
        return ADMIN_TRACKING_INPUT
        
    except Exception as e:
        logging.error(f"Error in send_tracking_code: {e}")
        await query.message.reply_text("❌ Ошибка при обработке запроса.")
        return ConversationHandler.END

async def handle_admin_tracking_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the tracking code input from admin"""
    try:
        # Get target user ID from context
        user_id = context.user_data.get('target_user_id')
        if not user_id:
            await update.message.reply_text("❌ Ошибка: не найден ID пользователя.")
            return ConversationHandler.END
        
        # Get tracking code from admin's message
        tracking_code = update.message.text.strip()
        
        try:
            # Send tracking code to user with improved formatting
            tracking_message = (
                "📦 Информация о доставке\n"
                "━━━━━━━━━━━━━━━\n\n"
                "✨ Статус: Заказ отправлен\n\n"
                "📤 Трек-код для отслеживания:\n"
                f"• {tracking_code}\n\n"
                "📍 Как отследить:\n"
                "• Перейдите на сайт почтовой службы\n"
                "• Введите трек-код в поле отслеживания\n"
                "• Проверяйте статус регулярно\n\n"
                "❗️ Важно:\n"
                "• Доставка занимает 1-3 дня\n"
                "• Проверьте товар при получении\n"
                "• По вопросам пишите менеджеру\n"
                "━━━━━━━━━━━━━━━"
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=tracking_message
            )
            
            # Confirm to admin
            await update.message.reply_text(
                f"✅ Трек-код успешно отправлен пользователю (ID: {user_id})"
            )
            
            # Clear context data
            if 'target_user_id' in context.user_data:
                del context.user_data['target_user_id']
            
            return MAIN_MENU
            
        except telegram.error.Forbidden:
            await update.message.reply_text(
                "❌ Ошибка: Бот заблокирован пользователем."
            )
            return MAIN_MENU
            
        except Exception as e:
            logging.error(f"Error sending tracking code: {e}")
            await update.message.reply_text(
                "❌ Ошибка при отправке трек-кода. Пожалуйста, попробуйте еще раз."
            )
            return MAIN_MENU
            
    except Exception as e:
        logging.error(f"Error in handle_admin_tracking_input: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз."
        )
        return MAIN_MENU

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot restart"""
    welcome_message = (
        "🔄 Бот перезапущен!\n\n"
        "🌐Мы являемся розничным магазином ‼️\n\n"
        "✅Всегда в сети 24/7\n\n"
        "•  Наши преимущества на рынке:\n"
        "•  Отличное качество\n"
        "•  Самая дешёвые цены в РБ\n"
        "•  Отправка по всей РБ и СНГ\n"
        "•  Отправка в день заказа\n\n"
        "✏️По всем технически вопросам:\n"
        "❕ @pmaaaaaaaaaa\n\n"
        "[✅Отзывы](https://t.me/+Iss7Cv_-kboxYzdi)\n\n"
        "✅Личная встреча Гродно\n"
        "✅Отправка почтой!\n\n"
        "Наши каналы:\n"
        "🛍 Розница: @GlovHandy\n"
        "📦 Опт: @GlovHandyOPT\n\n"
        "Все представленные товары являются репликами Premium+ качества📄"
    )
    
    # Clear user data
    context.user_data.clear()
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    return MAIN_MENU

def get_stats_for_last_7_days():
    """Get statistics for the last 7 days"""
    orders = load_orders()
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    # Filter orders for last 7 days
    recent_orders = {
        order_id: order for order_id, order in orders.items()
        if datetime.strptime(order.get('timestamp', ''), "%Y-%m-%d %H:%M:%S") > week_ago
    }
    
    # Calculate statistics
    total_orders = len(recent_orders)
    total_sum = sum(order.get('final_price', 0) for order in recent_orders.values())
    completed = sum(1 for order in recent_orders.values() if order.get('delivered'))
    in_progress = total_orders - completed
    
    # Get unique users
    unique_users = len(set(order.get('user_id') for order in recent_orders.values()))
    
    # Get top 3 clients
    user_totals = {}
    for order in recent_orders.values():
        user_id = order.get('user_id')
        if user_id:
            user_totals[user_id] = user_totals.get(user_id, 0) + order.get('final_price', 0)
    
    top_clients = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    
    return {
        'total_orders': total_orders,
        'total_sum': total_sum,
        'completed': completed,
        'in_progress': in_progress,
        'new_users': unique_users,
        'top_clients': top_clients
    }

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None):
    """Show admin panel with statistics"""
    # Get statistics for last 7 days
    stats = get_stats_for_last_7_days()
    
    # Format admin panel message
    admin_message = (
        "🛠 Админ-панель\n"
        "━━━━━━━━━━━━━━━\n\n"
        "За 7 дней:\n"
        f"Всего заказов: {stats['total_orders']}\n"
        f"На сумму: {stats['total_sum']} р.\n"
        f"Выполнено: {stats['completed']}\n"
        f"В обработке: {stats['in_progress']}\n"
        f"Новых пользователей: {stats['new_users']}\n\n"
        "Топ-3 клиента:\n"
    )
    
    # Add top clients
    for i, (user_id, total) in enumerate(stats['top_clients'], 1):
        admin_message += f"{i}. {user_id} — {total} р.\n"
    
    # Create inline keyboard with admin actions
    keyboard = [
        [
            InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton("📥 Экспорт в Excel", callback_data="admin_export")
        ],
        [
            InlineKeyboardButton("📋 Заказы за 7 дней", callback_data="admin_recent_orders"),
            InlineKeyboardButton("👥 Новые пользователи", callback_data="admin_new_users")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=admin_message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(admin_message, reply_markup=reply_markup)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin command - show admin panel"""
    # Check if the command is from admin group
    if str(update.effective_chat.id) != ADMIN_CHAT_ID:
        return
    
    await show_admin_panel(update, context)
    return MAIN_MENU

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_back":
        # Return to main admin panel
        await show_admin_panel(update, context, query.message.message_id)
        return MAIN_MENU
    
    elif query.data == "admin_broadcast":
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        await query.message.edit_text(
            "📢 Введите текст для рассылки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_BROADCAST
        
    elif query.data == "admin_add_product":
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        await query.message.edit_text(
            "➕ Для добавления товара отправьте данные в формате:\n"
            "Название\n"
            "Цена\n"
            "Категория\n"
            "Описание",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_ADD_PRODUCT
        
    elif query.data == "admin_stats":
        stats = get_stats_for_last_7_days()
        stats_message = (
            "📊 Подробная статистика\n"
            "━━━━━━━━━━━━━━━\n\n"
            f"Заказов за неделю: {stats['total_orders']}\n"
            f"Общая сумма: {stats['total_sum']} р.\n"
            f"Средний чек: {stats['total_sum']/stats['total_orders'] if stats['total_orders'] else 0:.2f} р.\n"
            f"Конверсия: {(stats['completed']/stats['total_orders']*100) if stats['total_orders'] else 0:.1f}%"
        )
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        await query.message.edit_text(
            stats_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif query.data == "admin_export":
        try:
            # Show processing message
            processing_message = await query.message.edit_text(
                "📊 Подготовка файла...",
                reply_markup=None
            )
            
            # Generate Excel file
            excel_buffer = await export_to_excel(context)
            
            # Get current date for filename
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Send Excel file
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=excel_buffer,
                filename=f'orders_{current_date}.xlsx',
                caption="📊 Отчет по заказам"
            )
            
            # Return to admin panel
            await show_admin_panel(update, context, processing_message.message_id)
            
        except Exception as e:
            logging.error(f"Error exporting to Excel: {e}")
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
            await query.message.edit_text(
                "❌ Произошла ошибка при создании отчета",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return MAIN_MENU
        
    elif query.data == "admin_recent_orders":
        orders = load_orders()
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        recent_orders = {
            order_id: order for order_id, order in orders.items()
            if datetime.strptime(order.get('timestamp', ''), "%Y-%m-%d %H:%M:%S") > week_ago
        }
        
        if not recent_orders:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
            await query.message.edit_text(
                "📋 Нет заказов за последние 7 дней",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        orders_message = "📋 Заказы за 7 дней:\n\n"
        for order_id, order in recent_orders.items():
            status = "✅" if order.get('delivered') else "🕒"
            orders_message += (
                f"{status} Заказ {order_id}\n"
                f"👤 Пользователь: {order.get('user_id')}\n"
                f"💰 Сумма: {order.get('final_price')} р.\n"
                f"📅 Дата: {order.get('timestamp')}\n\n"
            )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        await query.message.edit_text(
            orders_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif query.data == "admin_new_users":
        orders = load_orders()
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        new_users = set()
        
        for order in orders.values():
            if datetime.strptime(order.get('timestamp', ''), "%Y-%m-%d %H:%M:%S") > week_ago:
                new_users.add(order.get('user_id'))
        
        users_message = f"👥 Новые пользователи за 7 дней: {len(new_users)}\n\n"
        for user_id in new_users:
            users_message += f"• ID: {user_id}\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        await query.message.edit_text(
            users_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return MAIN_MENU

async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message from admin"""
    if str(update.effective_chat.id) != ADMIN_CHAT_ID:
        return MAIN_MENU
    
    if update.message.text == "◀️ Назад":
        await show_admin_panel(update, context)
        return MAIN_MENU
        
    broadcast_text = update.message.text
    
    # Load orders to get unique users
    orders = load_orders()
    all_users = set(order.get('user_id') for order in orders.values() if order.get('user_id'))
    
    success_count = 0
    fail_count = 0
    
    # Send message to all users
    for user_id in all_users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=broadcast_text
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to send broadcast to {user_id}: {e}")
            fail_count += 1
    
    # Send summary to admin
    summary = (
        "📢 Результаты рассылки:\n"
        f"✅ Успешно отправлено: {success_count}\n"
        f"❌ Ошибок отправки: {fail_count}\n"
        f"👥 Всего пользователей: {len(all_users)}"
    )
    
    await update.message.reply_text(summary)
    await show_admin_panel(update, context)
    return MAIN_MENU

async def handle_admin_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding new product from admin"""
    if str(update.effective_chat.id) != ADMIN_CHAT_ID:
        return MAIN_MENU
    
    if update.message.text == "◀️ Назад":
        await show_admin_panel(update, context)
        return MAIN_MENU
        
    try:
        # Parse product data
        lines = update.message.text.strip().split('\n')
        if len(lines) < 4:
            raise ValueError("Недостаточно данных")
            
        name = lines[0].strip()
        price = float(lines[1].strip())
        category = lines[2].strip()
        description = '\n'.join(lines[3:]).strip()
        
        # Generate product ID
        product_id = name.lower().replace(' ', '_')
        
        # Add to PRODUCTS dictionary
        PRODUCTS[product_id] = {
            'name': name,
            'price': price,
            'category': category,
            'description': description
        }
        
        # Confirm to admin
        confirmation = (
            "✅ Товар добавлен:\n\n"
            f"📱 {name}\n"
            f"💰 {price} р.\n"
            f"📁 {category}\n"
            f"📝 {description}"
        )
        
        await update.message.reply_text(confirmation)
        await show_admin_panel(update, context)
        
    except ValueError as e:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        await update.message.reply_text(
            "❌ Ошибка в формате данных!\n\n"
            "Используйте формат:\n"
            "Название\n"
            "Цена\n"
            "Категория\n"
            "Описание",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error adding product: {e}")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        await update.message.reply_text(
            "❌ Произошла ошибка при добавлении товара",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return MAIN_MENU

async def export_to_excel(context: ContextTypes.DEFAULT_TYPE):
    """Export orders data to Excel file"""
    orders = load_orders()
    
    # Prepare data for Excel
    excel_data = []
    for order_id, order in orders.items():
        # Convert timestamp string to datetime
        try:
            order_date = datetime.strptime(order.get('timestamp', ''), "%Y-%m-%d %H:%M:%S")
        except:
            order_date = None
            
        excel_data.append({
            'ID заказа': order_id,
            'Дата': order_date,
            'Покупатель ID': order.get('user_id'),
            'Товар': order.get('product_name'),
            'Количество': order.get('quantity'),
            'Сумма': order.get('final_price'),
            'Способ доставки': DELIVERY_METHODS[order.get('delivery_method', '')]['name'] if order.get('delivery_method') else '',
            'Статус': 'Доставлен' if order.get('delivered') else 'В обработке',
            'Трек-код': order.get('tracking_code', ''),
            'Использовано баллов': order.get('points_used', 0),
            'Комментарий': order.get('comment', '')
        })
    
    # Create DataFrame
    df = pd.DataFrame(excel_data)
    
    # Sort by date
    if not df.empty and df['Дата'].notna().any():
        df = df.sort_values('Дата', ascending=False)
    
    # Create Excel file in memory
    excel_buffer = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # Write orders sheet
        df.to_excel(writer, sheet_name='Заказы', index=False)
        
        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Заказы']
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        # Apply formats
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Auto-adjust columns width
        for i, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            ) + 2
            worksheet.set_column(i, i, max_length)
            
        # Add totals
        total_row = len(df) + 2
        worksheet.write(total_row, 0, 'ИТОГО:', header_format)
        worksheet.write(total_row, 5, f'=SUM(F2:F{len(df)+1})', header_format)
    
    # Get the value of the buffer
    excel_buffer.seek(0)
    return excel_buffer

def main():
    """Start the bot"""
    token = os.getenv('BOT_TOKEN')
    if not token:
        raise ValueError("Bot token not found. Create .env file and add BOT_TOKEN")

    # Create and configure application
    application = Application.builder().token(token).build()
    
    # Add new states for admin functions
    global ADMIN_BROADCAST, ADMIN_ADD_PRODUCT
    ADMIN_BROADCAST = 1000
    ADMIN_ADD_PRODUCT = 1001
    
    # Main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_command),
            CallbackQueryHandler(send_tracking_code, pattern="^track")
        ],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Regex("^🛍 Каталог$"), handle_catalog),
                MessageHandler(filters.Regex("^🎁 Бонусная программа$"), show_loyalty),
                MessageHandler(filters.Regex("^📦 Мои заказы$"), show_my_orders),
                MessageHandler(filters.Regex("^❓ FAQ$"), show_faq),
                MessageHandler(filters.Regex("^🚚 Доставка$"), show_delivery),
                MessageHandler(filters.Regex("^🔄 Перезапустить бота$"), restart_bot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu),
                CallbackQueryHandler(send_tracking_code, pattern="^track"),
                CallbackQueryHandler(handle_admin_callback, pattern="^admin_"),
                CommandHandler("admin", admin_command)
            ],
            ADMIN_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_broadcast)
            ],
            ADMIN_ADD_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_add_product)
            ],
            CATALOG: [
                MessageHandler(filters.Regex("^◀️ В главное меню$"), start),
                MessageHandler(filters.Regex("^◀️ Назад$"), handle_catalog),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_catalog)
            ],
            SELECTING_QUANTITY: [
                MessageHandler(filters.Regex("^◀️ Назад$"), handle_catalog),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)
            ],
            USE_POINTS: [
                MessageHandler(filters.Regex("^◀️ Назад$"), handle_quantity),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_points_usage)
            ],
            DELIVERY_METHOD: [
                MessageHandler(filters.Regex("^◀️ Назад$"), handle_quantity),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delivery_method)
            ],
            ORDER_COMMENT: [
                MessageHandler(filters.Regex("^◀️ Назад$"), handle_delivery_method),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_comment)
            ],
            ENTER_USER_DATA: [
                MessageHandler(filters.Regex("^◀️ Назад$"), handle_delivery_method),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_data)
            ],
            CONFIRM_ORDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_confirmation)
            ],
            ADMIN_TRACKING_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_tracking_input)
            ]
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^◀️ В главное меню$"), start)
        ],
        name="main_conversation"
    )

    # Add handlers
    application.add_handler(conv_handler)

    print("Bot is running!")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 