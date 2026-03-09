Python 3.13.12 (tags/v3.13.12:1cbe481, Feb  3 2026, 18:22:25) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ====== Настройки ======
TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = [123456789]  # Вставь сюда свой Telegram ID

# ====== Таблица пакетов ======
PACKAGES = {
    5000: 25000000,
    10000: 50000000,
    15000: 75000000,
    20000: 100000000,
    25000: 125000000,
    30000: 150000000,
    35000: 175000000,
    40000: 200000000,
    45000: 225000000,
    50000: 250000000,
    55000: 275000000,
    60000: 300000000,
    65000: 325000000,
    70000: 350000000,
    75000: 375000000,
    80000: 400000000,
    85000: 425000000,
    90000: 450000000,
    95000: 475000000,
    100000: 500000000
}

# ====== Инициализация базы ======
conn = sqlite3.connect("radmir_bot.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS cart(user_id INTEGER, package INTEGER, PRIMARY KEY(user_id, package))""")
cursor.execute("""CREATE TABLE IF NOT EXISTS orders(order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, total INTEGER, status TEXT, file_name TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS support_questions(question_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, question TEXT)""")
conn.commit()
conn.close()

# ====== Клавиатуры ======
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Обмен", callback_data="exchange")],
        [InlineKeyboardButton("Поддержка", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def package_keyboard():
    keyboard = []
    row = []
    for price in PACKAGES:
        row.append(InlineKeyboardButton(f"{price:,} ₽".replace(",", "."), callback_data=f"package_{price}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Перейти к оплате", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("Поддержка", callback_data="support")])
    return InlineKeyboardMarkup(keyboard)

# ====== Команды ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect("radmir_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)", (user.id, user.username))
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выберите действие:",
        reply_markup=main_menu_keyboard()
    )

# ====== Кнопки ======
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "exchange":
        await query.edit_message_text("Выберите пакет:", reply_markup=package_keyboard())

    elif query.data.startswith("package_"):
        price = int(query.data.split("_")[1])
        conn = sqlite3.connect("radmir_bot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO cart(user_id, package) VALUES(?,?)", (user_id, price))
        conn.commit()
        cursor.execute("SELECT SUM(package) FROM cart WHERE user_id=?", (user_id,))
        total = cursor.fetchone()[0] or 0
        conn.close()
        await query.edit_message_text(f"Пакет {price:,} ₽ добавлен в корзину.\nСумма в корзине: {total:,} ₽",
                                      reply_markup=package_keyboard())

    elif query.data == "checkout":
        conn = sqlite3.connect("radmir_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(package) FROM cart WHERE user_id=?", (user_id,))
        total = cursor.fetchone()[0]
        conn.close()
        if not total:
            await query.edit_message_text("Ваша корзина пуста!", reply_markup=package_keyboard())
            return
        await query.edit_message_text(
            f"Отлично! Сумма оплаты: {total:,} ₽\nСсылка: https://radmir.online/shop\n"
            "В поле никнейм пишите свой ник, сервер выбираете 21, сумму — из корзины.\n"
            "После оплаты пришлите чек (только файл).",
            reply_markup=main_menu_keyboard()
        )

    elif query.data == "support":
        await query.edit_message_text("Напишите свой вопрос. После отправки он попадёт в поддержку.")

# ====== Файлы (чеки) ======
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.document:
        file_name = update.message.document.file_name
        conn = sqlite3.connect("radmir_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(package) FROM cart WHERE user_id=?", (user_id,))
        total = cursor.fetchone()[0] or 0
        cursor.execute("INSERT INTO orders(user_id, total, status, file_name) VALUES(?,?,?,?)",
                       (user_id, total, "в очереди", file_name))
        cursor.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text("Отлично, ваш заказ поставлен в очередь. Ждите связи с вами.")
    else:
        await update.message.reply_text("Ошибка! Пришлите чек в виде файла.")

# ====== Сообщения (поддержка и админ) ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Админ: ответ на вопрос
    if user_id in ADMIN_IDS and text.startswith("/rep"):
        try:
            parts = text.split(" ", 2)
            qid = int(parts[1])
            answer = parts[2]
            conn = sqlite3.connect("radmir_bot.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM support_questions WHERE question_id=?", (qid,))
            row = cursor.fetchone()
            if row:
                uid = row[0]
                await context.bot.send_message(uid, f"Ответ поддержки: {answer}")
                cursor.execute("DELETE FROM support_questions WHERE question_id=?", (qid,))
                conn.commit()
            conn.close()
            await update.message.reply_text(f"Ответ отправлен на вопрос {qid}.")
        except:
            await update.message.reply_text("Ошибка формата /rep <номер> <ответ>")
        return

    # Админ: список вопросов
    elif user_id in ADMIN_IDS and text == "/reports":
        conn = sqlite3.connect("radmir_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT question_id, user_id, question FROM support_questions")
        rows = cursor.fetchall()
        msg = "\n".join([f"{r[0]} | {r[1]} | {r[2]}" for r in rows]) if rows else "Нет вопросов."
        conn.close()
        await update.message.reply_text(msg)
        return

    # Админ: список заказов
    elif user_id in ADMIN_IDS and text == "/orders":
        conn = sqlite3.connect("radmir_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, user_id, total, status FROM orders")
        rows = cursor.fetchall()
        msg = "\n".join([f"{r[0]} | {r[1]} | {r[2]:,} ₽ | {r[3]}" for r in rows]) if rows else "Нет заказов."
        conn.close()
        await update.message.reply_text(msg)
        return

    # Админ: просмотр заказа
    elif user_id in ADMIN_IDS and text.startswith("/order"):
...         try:
...             order_id = int(text.split(" ")[1])
...             conn = sqlite3.connect("radmir_bot.db")
...             cursor = conn.cursor()
...             cursor.execute("SELECT user_id, total, status FROM orders WHERE order_id=?", (order_id,))
...             row = cursor.fetchone()
...             conn.close()
...             if row:
...                 await update.message.reply_text(f"Здравствуйте! Жду вас в игре для выдачи виртов.\nЗаказ {order_id}: {row[1]:,} ₽ | {row[2]}")
...             else:
...                 await update.message.reply_text("Заказ не найден.")
...         except:
...             await update.message.reply_text("Ошибка в формате /order <номер>")
...         return
... 
...     # Обычные пользователи → поддержка
...     else:
...         conn = sqlite3.connect("radmir_bot.db")
...         cursor = conn.cursor()
...         cursor.execute("INSERT INTO support_questions(user_id, question) VALUES(?,?)", (user_id, text))
...         conn.commit()
...         conn.close()
...         await update.message.reply_text("Ваш вопрос передан в поддержку. Ждите ответа.")
... 
... # ====== Основная функция ======
... app = ApplicationBuilder().token(TOKEN).build()
... app.add_handler(CommandHandler("start", start))
... app.add_handler(CallbackQueryHandler(button))
... app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
... app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
... 
... print("Бот запущен!")
... app.run_polling()
SyntaxError: multiple statements found while compiling a single statement
