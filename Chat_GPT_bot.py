import logging
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI, APIError, RateLimitError, AuthenticationError

# ВАШИ API-ключи
TELEGRAM_API_KEY = "TELEGRAM_API_KEY"
OPENAI_API_KEY = "OPENAI_API_KEY"

# Настройка OpenAI клиента через прокси
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.proxyapi.ru/openai/v1"
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\U0001F44B Привет! Я бот, подключенный к ChatGPT через прокси. Напиши что-нибудь!")

# Обработчик текстовых сообщений
async def chatgpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    try:
        time.sleep(2)  # Пауза для ограничения частоты

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except RateLimitError:
        await update.message.reply_text("🚫 Превышен лимит запросов. Попробуйте позже.")
    except AuthenticationError:
        await update.message.reply_text("❌ Ошибка авторизации. Проверьте API-ключ.")
    except APIError as e:
        if "insufficient_quota" in str(e):
            await update.message.reply_text("❗ Недостаточно квоты в OpenAI. Пополните баланс.")
        else:
            await update.message.reply_text(f"⚠️ Произошла ошибка API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text("⚠️ Произошла непредвиденная ошибка. Попробуйте позже.")

# Основная функция запуска Telegram-бота
def main():
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chatgpt))

    logger.info("Бот запущен.")
    application.run_polling()

if __name__ == "__main__":
    main()
