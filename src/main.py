import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import Dotenv
from payments import Invoice
from yoomoney import Client
from marzban import Marzban

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация конфигурации
config = Dotenv()

# Инициализация клиента YooMoney
client = Client(config.YOOMONEY_TOKEN)
invoice = Invoice(client=client, price=config.PRICE)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Подключение к базе данных SQLite
conn = sqlite3.connect('payments.db')
cursor = conn.cursor()

# Создание таблицы для хранения информации о платежах
cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    invoice_uuid TEXT,
                    amount REAL,
                    status TEXT,
                    vpn_link TEXT  -- Новый столбец для хранения ссылки
                )''')
conn.commit()

vpn = Marzban(config.MZB_URL, config.MZB_USERNAME, config.MZB_PASSWORD)


# Отправка сообщения с успешной ссылкой на VPN и удаление предыдущего сообщения
async def send_vpn_link(chat_id, message_id, username):
    link = vpn.update_user_subscription(username)
    await bot.send_message(chat_id, f"Ссылка на VPN:\n{link}")
    await bot.delete_message(chat_id, message_id)  # Удаляем сообщение о покупке


# Отправка информации о покупке
async def send_purchase_info(chat_id):
    cursor.execute("SELECT id, status, vpn_link FROM payments WHERE user_id = ?", (chat_id,))
    purchases = cursor.fetchall()

    if not purchases:
        await bot.send_message(chat_id, "У вас нет активных покупок.")
        return
    purchase_info = f"Ваша конфигурация:\n{max(purchases, key=lambda x: [x[1] == 'successful', x[0]])[2]}"

    await bot.send_message(chat_id, purchase_info)


# Greeting
@dp.message(Command("start"))
async def start(message: Message):
    my_purchase_button = InlineKeyboardButton(text="Моя покупка", callback_data="my_purchase")
    buy_button = InlineKeyboardButton(text="Купить", callback_data="buy:start")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[my_purchase_button], [buy_button]])

    await message.answer(
        f"Привет! Это бот {config.NAME}. Вы можете приобрести подписку на VPN.",
        reply_markup=keyboard
    )
    logger.info(f"User {message.chat.id} started the bot")


# Обработка кнопки "Моя покупка"
@dp.callback_query(lambda c: c.data == "my_purchase")
async def handle_my_purchase(callback_query: CallbackQuery):
    await send_purchase_info(callback_query.from_user.id)
    await callback_query.answer()  # Удаляем всплывающее уведомление


# Command to buy subscription
@dp.message(Command("buy"))
async def buy_vpn(message: Message):
    payment = invoice.create()

    # Получаем username пользователя с заменой @ на _
    username = message.chat.username
    if username:
        username = f"_{username}"
    else:
        username = str(message.chat.id)

    cursor.execute("INSERT INTO payments (user_id, invoice_uuid, amount, status) VALUES (?, ?, ?, ?)",
                   (message.chat.id, payment.invoice_uuid, config.PRICE, 'pending'))
    conn.commit()

    # Передаем username в callback_data вместе с invoice_uuid
    check_button = InlineKeyboardButton(text="Check", callback_data=f"check:{payment.invoice_uuid}:{username}")
    cancel_button = InlineKeyboardButton(text="Cancel", callback_data=f"cancel:{payment.invoice_uuid}:{username}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[check_button, cancel_button]])

    payment_message = await message.answer(
        f"Для оплаты перейдите по ссылке: {payment.url}\nПосле оплаты нажмите 'Check' для проверки статуса или 'Cancel' для отмены.",
        reply_markup=keyboard
    )
    logger.info(f"Payment created for user {username} with UUID {payment.invoice_uuid}")

    # Удаляем сообщение через 60 секунд, если не было успешной оплаты
    await asyncio.sleep(60)
    await bot.delete_message(message.chat.id, payment_message.message_id)


# Обработка всех callback_data
@dp.callback_query()
async def handle_callback(callback_query: CallbackQuery):
    try:
        data = callback_query.data

        # Если callback_data содержит только одно двоеточие, это buy или cancel, если два - check
        if data.startswith("buy:") or data.startswith("cancel:"):
            action, value = data.split(':', 1)
            username = callback_query.from_user.username
            if username:
                username = f"_{username}"
            else:
                username = str(callback_query.from_user.id)

            if action == "buy":
                await buy_vpn(callback_query.message)
            elif action == "cancel":
                await cancel_payment(callback_query.message, value)

        elif data.startswith("check:"):
            if data.count(":") != 2:
                await callback_query.answer("Неправильный формат данных. Попробуйте снова.")
                logger.warning(f"Invalid format data received: {data}")
                return

            action, invoice_uuid, username = data.split(':', 2)
            await check_payment(callback_query.message, invoice_uuid, username)

        else:
            await callback_query.answer("Неправильный формат данных. Попробуйте снова.")
            logger.warning(f"Invalid format data received: {data}")
    except Exception as e:
        logger.error(f"Exception in handle_callback: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте позже.")


async def check_payment(message: Message, invoice_uuid: str, username: str):
    try:
        if message.chat.id == int(config.ADMIN_ID):
            await message.answer("Оплата прошла успешно! (администратор)")
            logger.info(
                f"Admin {message.chat.id} checked payment with UUID {invoice_uuid} - automatically successful")
            payment_status = True
        else:
            cursor.execute(f'''SELECT * FROM payments WHERE user_id = "{message.chat.id}" AND status = "pending"''')
            payments = cursor.fetchall()

            if not payments:
                await message.answer("Платеж не найден. Попробуйте снова.")
                logger.warning(f"Payment with UUID {invoice_uuid} not found")
                return

            payment_status = False
            for payment in payments:
                if invoice.check(payment[2]):
                    payment_status = True
                    break

        if payment_status:
            # Получаем и сохраняем ссылку на VPN
            link = vpn.update_user_subscription(username)
            cursor.execute(f'''UPDATE payments SET status = 'successful', vpn_link = ? WHERE user_id = ?''',
                           (link, message.chat.id))
            conn.commit()

            await send_vpn_link(message.chat.id, message.message_id, username)
            logger.info(f"Payment with UUID {invoice_uuid} was successful for user {username}")
        else:
            await message.answer("Оплата еще не прошла или произошла ошибка. Попробуйте позже.")
            logger.info(f"Payment with UUID {invoice_uuid} not yet successful")
    except Exception as e:
        logger.error(f"Exception in check_payment: {str(e)}")
        await message.answer("Произошла ошибка при проверке оплаты. Попробуйте позже.")


# Отмена платежа
async def cancel_payment(message: Message, invoice_uuid: str):
    try:
        cursor.execute("DELETE FROM payments WHERE invoice_uuid = ?", (invoice_uuid,))
        conn.commit()

        await bot.delete_message(message.chat.id, message.message_id)  # Удаляем сообщение
        await start(message)
    except Exception as e:
        logger.error(f"Exception in cancel_payment: {str(e)}")
        await message.answer("Произошла ошибка при отмене платежа. Попробуйте позже.")


# Функция для запуска бота
async def main():
    await bot.set_my_commands([
        types.BotCommand(command="/start", description="Начать работу с ботом"),
        types.BotCommand(command="/buy", description="Купить подписку на VPN"),
        types.BotCommand(command="/check", description="Проверить статус оплаты")
    ])

    await dp.start_polling(bot)
    logger.info("Bot started")


# Запуск бота
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Exception in main: {str(e)}")
    finally:
        conn.close()
