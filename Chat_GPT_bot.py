import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai
import time

# ВАШИ API-ключи
TELEGRAM_API_KEY = "telegram api key"
OPENAI_API_KEY = "openai api key"

# Настройка API OpenAI
openai.api_key = OPENAI_API_KEY

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\U0001F44B Привет! Я бот, подключенный к ChatGPT. Напишите мне что-нибудь!")

# Обработчик текстовых сообщений
async def chatgpt(update, context):
    user_message = update.message.text
    try:
        # Ограничение запросов
        time.sleep(20)  # Пауза 20 секунд перед запросом
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response['choices'][0]['message']['content']
        await update.message.reply_text(reply)
    except openai.error.RateLimitError:
        await update.message.reply_text("Превышен лимит запросов. Попробуйте позже.")

# Основная функция для запуска бота
def main():
    # Создание приложения Telegram
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))

    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chatgpt))

    # Запуск бота
    logger.info("Запуск бота...")
    application.run_polling()

if __name__ == "__main__":
    main()
