import os
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get('BOT_TOKEN', "8257155005:AAHfpnulJs_caIfE4zGZtxPvcJKZdXqM0-E")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'laundry.db')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def init_db():
    try:
        print("🔄 Инициализация базы данных...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                machine_type TEXT NOT NULL,
                date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(machine_type, date, time_slot)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        raise

def get_db_connection():
    return sqlite3.connect(DB_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
        (user.id, user.username, user.first_name, user.last_name)
    )
    conn.commit()
    conn.close()
    
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n"
        "Я бот для записи на стирку.\n\n"
        "Доступные машины:\n"
        "🧼 Новая 1\n" 
        "🧼 Новая 2\n"
        "🧼 Старая\n\n"
        "Выберите команду:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📅 Расписание", callback_data='view_schedule')],
        [InlineKeyboardButton("➕ Записаться", callback_data='choose_machine')],
        [InlineKeyboardButton("👀 Мои записи", callback_data='my_bookings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT machine_type, time_slot, u.first_name 
        FROM bookings b 
        LEFT JOIN users u ON b.user_id = u.user_id 
        WHERE date = ?
        ORDER BY machine_type, time_slot
    ''', (today,))
    
    bookings = cursor.fetchall()
    conn.close()
    
    schedule_text = f"📅 Расписание на сегодня ({today}):\n\n"
    machines = {"Новая 1": [], "Новая 2": [], "Старая": []}
    
    for machine, time_slot, user_name in bookings:
        machines[machine].append(f"{time_slot} - {user_name or 'Аноним'}")
    
    for machine in ["Новая 1", "Новая 2", "Старая"]:
        schedule_text += f"🧼 {machine} машина:\n"
        if machines[machine]:
            for booking in machines[machine]:
                schedule_text += f"  ⏰ {booking}\n"
        else:
            schedule_text += "  ✅ Свободно\n"
        schedule_text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Записаться", callback_data='choose_machine')],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(schedule_text, reply_markup=reply_markup)

async def choose_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🧼 Новая 1", callback_data="book_new1")],
        [InlineKeyboardButton("🧼 Новая 2", callback_data="book_new2")],
        [InlineKeyboardButton("🧼 Старая", callback_data="book_old")],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите стиральную машину:", reply_markup=reply_markup)

async def handle_booking_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    if choice == "book_new1":
        await show_time_slots(query, "Новая 1")
    elif choice == "book_new2":
        await show_time_slots(query, "Новая 2")
    elif choice == "book_old":
        await show_time_slots(query, "Старая")

async def show_time_slots(query, machine_type):
    today = datetime.now()
    time_slots = []
    
    for day in range(3):
        current_date = today + timedelta(days=day)
        date_str = current_date.strftime("%Y-%m-%d")
        for hour in range(8, 22):
            time_slot = f"{hour:02d}:00"
            time_slots.append((date_str, time_slot))
    
    keyboard = []
    for i, (date, time_slot) in enumerate(time_slots):
        date_display = "Сегодня" if date == today.strftime("%Y-%m-%d") else \
                      "Завтра" if date == (today + timedelta(days=1)).strftime("%Y-%m-%d") else \
                      "Послезавтра"
        
        callback_data = f"confirm_{machine_type}_{date}_{time_slot}"
        button_text = f"{date_display} {time_slot}"
        
        if i % 2 == 0:
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        else:
            keyboard[-1].append(InlineKeyboardButton(button_text, callback_data=callback_data))
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='choose_machine')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    machine_text = {
        "Новая 1": "Новой 1 машины",
        "Новая 2": "Новой 2 машины", 
        "Старая": "Старой машины"
    }[machine_type]
    
    await query.edit_message_text(f"Выберите время для {machine_text}:", reply_markup=reply_markup)

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    machine_type = parts[1]
    date = parts[2]
    time_slot = parts[3]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO bookings (user_id, machine_type, date, time_slot) VALUES (?, ?, ?, ?)',
            (query.from_user.id, machine_type, date, time_slot)
        )
        conn.commit()
        
        date_display = "Сегодня" if date == datetime.now().strftime("%Y-%m-%d") else \
                      "Завтра" if date == (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d") else \
                      "Послезавтра"
        
        success_text = f"✅ Вы успешно забронировали {machine_type.lower()} машину на {date_display} в {time_slot}"
        
        keyboard = [
            [InlineKeyboardButton("📅 Расписание", callback_data='view_schedule')],
            [InlineKeyboardButton("👀 Мои записи", callback_data='my_bookings')],
            [InlineKeyboardButton("🔙 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(success_text, reply_markup=reply_markup)
        
    except sqlite3.IntegrityError:
        await query.edit_message_text("❌ Это время уже занято. Пожалуйста, выберите другое время.")
    finally:
        conn.close()

async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, machine_type, date, time_slot 
        FROM bookings 
        WHERE user_id = ? AND date >= date('now')
        ORDER BY date, time_slot
    ''', (user_id,))
    
    bookings = cursor.fetchall()
    conn.close()
    
    if not bookings:
        message = "📋 Ваши бронирования:\n\nУ вас пока нет активных бронирований."
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]]
    else:
        message = "📋 Ваши бронирования:\n\n"
        keyboard = []
        
        for booking_id, machine, date, time_slot in bookings:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            today = datetime.now().date()
            
            if date_obj.date() == today:
                date_display = "Сегодня"
            elif date_obj.date() == today + timedelta(days=1):
                date_display = "Завтра"
            else:
                date_display = date_obj.strftime("%d.%m")
            
            message += f"🧼 {machine} машина\n"
            message += f"📅 {date_display} в {time_slot}\n"
            message += "─" * 20 + "\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"❌ Отменить {machine} {date_display} {time_slot}", 
                callback_data=f'cancel_booking_{booking_id}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    booking_id = query.data.replace('cancel_booking_', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT machine_type, date, time_slot FROM bookings WHERE id = ? AND user_id = ?', (booking_id, query.from_user.id))
    booking = cursor.fetchone()
    
    if booking:
        machine, date, time_slot = booking
        cursor.execute('DELETE FROM bookings WHERE id = ? AND user_id = ?', (booking_id, query.from_user.id))
        conn.commit()
        
        date_display = "Сегодня" if date == datetime.now().strftime("%Y-%m-%d") else \
                      "Завтра" if date == (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d") else \
                      "Послезавтра"
        
        keyboard = [
            [InlineKeyboardButton("👀 Мои записи", callback_data='my_bookings')],
            [InlineKeyboardButton("🔙 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Бронирование отменено!\n\n"
            f"🧼 Машина: {machine}\n"
            f"📅 Дата: {date_display}\n"
            f"🕐 Время: {time_slot}",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "❌ Бронирование не найдено.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='my_bookings')]])
        )
    
    conn.close()

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'main_menu':
        await start(update, context)
    elif data == 'view_schedule':
        await show_schedule(update, context)
    elif data == 'choose_machine':
        await choose_machine(update, context)
    elif data in ['book_new1', 'book_new2', 'book_old']:
        await handle_booking_choice(update, context)
    elif data == 'my_bookings':
        await my_bookings(update, context)
    elif data.startswith('confirm_'):
        await confirm_booking(update, context)
    elif data.startswith('cancel_booking_'):
        await cancel_booking(update, context)

def main():
    print("🚀 Запуск бота для записи на стирку...")
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    print("✅ Бот запущен и готов к работе!")
    application.run_polling()

if __name__ == "__main__":
    main()
