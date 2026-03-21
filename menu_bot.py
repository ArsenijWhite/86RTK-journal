from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8514929224:AAEmcYywI2h6nwgrBbCIX26G8W1sgEf1fCM"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_app_url = "https://ваш-сайт.netlify.app/"  # Ссылка на мини-приложение
    
    keyboard = [[
        InlineKeyboardButton("🎵 Открыть плеер", web_app=WebAppInfo(url=web_app_url))
    ]]
    
    await update.message.reply_text(
        "🎧 Музыкальный плеер\nНажмите кнопку:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()