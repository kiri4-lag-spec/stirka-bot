import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.environ.get('BOT_TOKEN', "8257155005:AAHfpnulJs_caIfE4zGZtxPvcJKZdXqM0-E")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ Команда /start получена!")
    await update.message.reply_text("🔄 Бот работает! Это тестовая версия.")

def main():
    print("🚀 Запуск тестового бота...")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        print("✅ Тестовый бот запущен!")
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        # Принудительно держим процесс активным для логирования
        import time
        while True:
            print(f"🕒 Процесс жив... {time.ctime()}")
            time.sleep(10)

if __name__ == "__main__":
    main()
