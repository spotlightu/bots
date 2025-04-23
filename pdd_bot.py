import logging
import pyodbc  # Для работы с MS Access
import time  # Для ограничения запросов
import numpy as np
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

nlp = spacy.load("ru_core_news_sm")

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути и настройки
DB_PATH = r"C:/Users/danil/Desktop/bot.accdb"
TOKEN = "6871710717:AAFtb5nZlm0h3PtbUIRUnqvRpvZxp3yymJw"

# Ограничение на запросы
user_request_times = {}
REQUEST_LIMIT = 5  # Ограничение: 1 запрос в 5 секунд

async def send_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        # Отправка изображения пользователю
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo="")
        await update.message.reply_text("ЛОВИ АПТЕЧКУ!!!")  # Ответное сообщение
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")  # Обработка ошибок

def lemmatize_text(text):
    """
    Лемматизирует входной текст с использованием spaCy.
    Возвращает строку из лемматизированных слов.
    """
    doc = nlp(text)  # Обработка текста через модель spaCy
    lemmatized_words = [token.lemma_ for token in doc if not token.is_punct and not token.is_space]
    return " ".join(lemmatized_words)

# Подключение к базе данных Access
def connect_db():
    conn = pyodbc.connect(
        r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={DB_PATH};"
    )
    return conn

# Загрузка FAQ из базы данных
def load_faq():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM questions")
    faq = cursor.fetchall()
    conn.close()
    return faq


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот для ответов на часто задаваемые вопросы по ПДД. Напишите вопрос или используйте /opros для обратной связи.",
        reply_markup=ForceReply(selective=True),
    )


# Ограничение на частоту запросов
def is_request_allowed(user_id):
    current_time = time.time()
    if user_id in user_request_times:
        last_request_time = user_request_times[user_id]
        if current_time - last_request_time < REQUEST_LIMIT:
            return False
    user_request_times[user_id] = current_time
    return True


# Обработка сообщений с вопросами
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Проверка на лимит запросов
    if not is_request_allowed(user_id):
        await update.message.reply_text("Пожалуйста, подождите 5 секунд перед следующим запросом.")
        return

    user_message = lemmatize_text(update.message.text)
    faq = load_faq()

    if len(user_message.split()) < 3:  # Разбиваем текст по пробелам и считаем количество слов
        await update.message.reply_text("Пожалуйста, введите минимум 3 слова для обработки запроса.")
        return

    if not faq:
        await update.message.reply_text("Извините, база данных вопросов пуста.")
        return

        # Создание векторизатора и лемматизация вопросов
    questions = [lemmatize_text(q[0]) for q in faq]  # Лемматизация вопросов из базы данных

    # Векторизация пользовательского сообщения
    vectorizer = CountVectorizer().fit(questions)
    user_vector = vectorizer.transform([user_message]).toarray()
    faq_vectors = vectorizer.transform(questions).toarray()

    # Нахождение самого подходящего вопроса
    similarities = np.dot(faq_vectors, user_vector.T)

    # Проверка на совпадения
    if np.all(similarities == 0):
        await update.message.reply_text("Извините, я не нашёл подходящего ответа.")
        return

    best_match_index = np.argmax(similarities)
    await update.message.reply_text(faq[best_match_index][1])


# Команда /survey
async def survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Пожалуйста, оставьте свою обратную связь о работе бота:")
    return 1


# Сохранение обратной связи
async def save_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    feedback = update.message.text
    username = update.message.from_user.username or "Не указано"

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO feedback (username, feedback) VALUES (?, ?)", (username, feedback))
        conn.commit()
        await update.message.reply_text("Спасибо за обратную связь!")
    except Exception as e:
        logger.error(f"Ошибка при сохранении обратной связи: {e}")
        await update.message.reply_text("Произошла ошибка при сохранении обратной связи.")
    finally:
        conn.close()

    return ConversationHandler.END


# Главная функция
def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("survey", send_image))

    # Обработчики
    app.add_handler(CommandHandler("start", start))

    # ConversationHandler для обратной связи
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("opros", survey)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_feedback)]},
        fallbacks=[],
    )
    app.add_handler(conv_handler)

    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
