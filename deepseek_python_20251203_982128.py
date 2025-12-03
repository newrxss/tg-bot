import telebot
import sqlite3
import threading
import time
from datetime import datetime
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

TOKEN = '8535821276:AAG7U9dk1YyEFY7kEyhyIOI31i7kokvXsvo'
CHANNEL_LINK = 'https://t.me/+KepHOdtzVuo0NTM8'
CREATOR_USERNAME = '@Xaklu'
ADMIN_IDS = [123456789]  # ID создателя

bot = telebot.TeleBot(TOKEN)

# База данных
conn = sqlite3.connect('show.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS orders
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER, username TEXT, animal_type TEXT,
                 details TEXT, price INTEGER, status TEXT DEFAULT 'pending',
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                (user_id INTEGER PRIMARY KEY, username TEXT,
                 join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 warning_count INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS content
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 file_id TEXT, caption TEXT, content_type TEXT,
                 posted_by INTEGER, likes INTEGER DEFAULT 0,
                 posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

# ========== КРАСИВЫЙ ИНТЕРФЕЙС ==========
def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎬 Вход в Шоу", url=CHANNEL_LINK),
        InlineKeyboardButton("🔪 Заказать Услугу", callback_data='order_service'),
        InlineKeyboardButton("💰 Мой Баланс", callback_data='my_balance'),
        InlineKeyboardButton("📊 Топ Заказов", callback_data='top_orders'),
        InlineKeyboardButton("🎲 Случайный Контент", callback_data='random_content'),
        InlineKeyboardButton("📢 Правила", callback_data='rules'),
        InlineKeyboardButton("👑 Админ-Панель", callback_data='admin_panel'),
        InlineKeyboardButton("💬 Поддержка", url=f"tg://resolve?domain={CREATOR_USERNAME[1:]}")
    )
    return markup

def admin_panel():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Статистика", callback_data='admin_stats'),
        InlineKeyboardButton("📋 Список Заказов", callback_data='admin_orders'),
        InlineKeyboardButton("⚠ Выдать Предупреждение", callback_data='admin_warn'),
        InlineKeyboardButton("🚫 Заблокировать", callback_data='admin_ban'),
        InlineKeyboardButton("📤 Рассылка", callback_data='admin_broadcast'),
        InlineKeyboardButton("➕ Добавить Контент", callback_data='admin_add_content'),
        InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')
    )
    return markup

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    
    welcome_text = f"""
<b>🔥 ДОБРО ПОЖАЛОВАТЬ В ЭКСКЛЮЗИВНЫЙ КЛУБ {username or 'Гость'}!</b>

<code>┏━━━━━━━━━━━━━━━━━━┓
┃   ПРИВАТНЫЙ БОТ   ┃
┃    ДЛЯ ШОУ        ┃
┗━━━━━━━━━━━━━━━━━━┛</code>

🎬 <b>Основной канал:</b> {CHANNEL_LINK}
👑 <b>Создатель:</b> {CREATOR_USERNAME}

Используйте меню ниже для навигации.
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=main_menu())

# ========== CALLBACK ОБРАБОТЧИКИ ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'order_service':
        start_order(call.message)
    elif call.data == 'my_balance':
        show_balance(call)
    elif call.data == 'top_orders':
        show_top_orders(call)
    elif call.data == 'random_content':
        send_random_content(call)
    elif call.data == 'rules':
        show_rules(call)
    elif call.data == 'admin_panel':
        if call.from_user.id in ADMIN_IDS:
            bot.edit_message_text("👑 <b>Админ-Панель</b>", call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=admin_panel())
    elif call.data == 'admin_stats':
        admin_stats(call)
    elif call.data == 'admin_orders':
        admin_show_orders(call)
    elif call.data == 'back_to_main':
        bot.edit_message_text("Главное меню", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

# ========== ФУНКЦИЯ ЗАКАЗА ==========
def start_order(message):
    msg = bot.send_message(message.chat.id, """
<b>🔪 ФОРМА ЗАКАЗА</b>

Шаг 1/3: <b>Укажите тип животного</b>
Пример: <i>Собака, порода, возраст</i>
""", parse_mode='HTML', reply_markup=types.ForceReply())
    bot.register_next_step_handler(msg, process_order_step1)

def process_order_step1(message):
    user_data = {'animal': message.text, 'user_id': message.from_user.id}
    msg = bot.send_message(message.chat.id, """
Шаг 2/3: <b>Детализация заказа</b>
Пример: <i>Метод, качество видео, особые пожелания</i>
""", parse_mode='HTML', reply_markup=types.ForceReply())
    bot.register_next_step_handler(msg, process_order_step2, user_data)

def process_order_step2(message, user_data):
    user_data['details'] = message.text
    msg = bot.send_message(message.chat.id, """
Шаг 3/3: <b>Предполагаемый бюджет (в рублях)</b>
Пример: <i>5000</i>
""", parse_mode='HTML', reply_markup=types.ForceReply())
    bot.register_next_step_handler(msg, process_order_final, user_data)

def process_order_final(message, user_data):
    try:
        price = int(message.text)
        user_id = user_data['user_id']
        username = message.from_user.username
        
        cursor.execute("""
            INSERT INTO orders (user_id, username, animal_type, details, price, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (user_id, username, user_data['animal'], user_data['details'], price))
        order_id = cursor.lastrowid
        conn.commit()
        
        # Уведомление админу
        admin_msg = f"""
🚨 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>
👤 Пользователь: @{username or 'NO_USERNAME'} (ID: {user_id})
🐕 Животное: {user_data['animal']}
📋 Детали: {user_data['details']}
💰 Бюджет: {price} RUB
"""
        for admin in ADMIN_IDS:
            try:
                bot.send_message(admin, admin_msg, parse_mode='HTML')
            except:
                pass
        
        # Подтверждение пользователю
        confirm_text = f"""
✅ <b>Заказ #{order_id} принят!</b>

С вами свяжется {CREATOR_USERNAME} для уточнения деталей и подтверждения цены.
Статус заказа можно отслеживать через /myorders
"""
        bot.send_message(message.chat.id, confirm_text, parse_mode='HTML', reply_markup=main_menu())
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверная сумма. Заказ отменен.", reply_markup=main_menu())

# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========
def show_balance(call):
    cursor.execute("SELECT SUM(price) FROM orders WHERE user_id=? AND status='completed'", (call.from_user.id,))
    total = cursor.fetchone()[0] or 0
    bot.answer_callback_query(call.id, f"💰 Ваш общий оборот: {total} RUB", show_alert=True)

def show_top_orders(call):
    cursor.execute("""
        SELECT username, animal_type, price FROM orders
        WHERE status='completed' ORDER BY price DESC LIMIT 5
    """)
    orders = cursor.fetchall()
    
    text = "🏆 <b>ТОП-5 ЗАКАЗОВ</b>\n\n"
    for idx, (username, animal, price) in enumerate(orders, 1):
        text += f"{idx}. @{username or 'Аноним'} - {animal[:20]}... - {price} RUB\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')

def send_random_content(call):
    cursor.execute("SELECT file_id, caption FROM content ORDER BY RANDOM() LIMIT 1")
    content = cursor.fetchone()
    if content:
        file_id, caption = content
        bot.send_video(call.message.chat.id, file_id, caption=f"🎲 Случайный контент:\n{caption}")
    else:
        bot.answer_callback_query(call.id, "Контент пока отсутствует")

def show_rules(call):
    rules = """
📢 <b>ПРАВИЛА КЛУБА</b>

1. Анонимность гарантируется
2. Оплата только в RUB
3. Все обсуждения через @Xaklu
4. Контент не распространять
5. Нарушители блокируются
"""
    bot.edit_message_text(rules, call.message.chat.id, call.message.message_id, parse_mode='HTML')

# ========== АДМИН ФУНКЦИИ ==========
def admin_stats(call):
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(price) FROM orders WHERE status='completed'")
    revenue = cursor.fetchone()[0] or 0
    
    stats = f"""
📊 <b>СТАТИСТИКА</b>

👥 Пользователей: {users}
🔪 Заказов: {orders}
💰 Оборот: {revenue} RUB
"""
    bot.edit_message_text(stats, call.message.chat.id, call.message.message_id, parse_mode='HTML')

def admin_show_orders(call):
    cursor.execute("SELECT id, username, animal_type, price, status FROM orders ORDER BY id DESC LIMIT 10")
    orders = cursor.fetchall()
    
    text = "📋 <b>ПОСЛЕДНИЕ 10 ЗАКАЗОВ</b>\n\n"
    for order in orders:
        text += f"#{order[0]} @{order[1] or 'Аноним'}\n{order[2][:15]}... - {order[3]}RUB [{order[4]}]\n\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')

# ========== ЗАПУСК БОТА ==========
def schedule_checker():
    while True:
        time.sleep(60)
        # Фоновая проверка новых заказов для админов
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
        pending = cursor.fetchone()[0]
        if pending > 0:
            for admin in ADMIN_IDS:
                try:
                    bot.send_message(admin, f"📥 Ожидают обработки: {pending} заказов")
                except:
                    pass

if __name__ == '__main__':
    print("Бот запущен с расширенным функционалом...")
    threading.Thread(target=schedule_checker, daemon=True).start()
    bot.infinity_polling()