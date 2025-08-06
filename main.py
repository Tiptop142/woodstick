from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8265074513:AAECiHCO5pUSlzOs8KEZWYUU94h06ve25ic"

AUTHORIZED_USERS = [635809430]  # Твій ID

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Клавіатура меню "Майстерня"
menu_buttons = [
    KeyboardButton("🛠 Повідомити про поломку"),
    KeyboardButton("📊 Список активних поломок"),
    KeyboardButton("📈 Статистика за день"),
    KeyboardButton("❌ Вийти з меню"),
]
menu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(*menu_buttons)


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in AUTHORIZED_USERS:
        await message.answer("Ласкаво просимо до меню «Майстерня»", reply_markup=menu_keyboard)
    else:
        await message.answer("⛔️ У вас немає доступу до цього бота.")


@dp.message_handler()
async def menu_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in AUTHORIZED_USERS:
        await message.answer("⛔️ У вас немає доступу до цього бота.")
        return

    text = message.text

    if text == "🛠 Повідомити про поломку":
        await message.answer("Виберіть тип поломки (поки не реалізовано)")
    elif text == "📊 Список активних поломок":
        await message.answer("Список активних поломок (поки не реалізовано)")
    elif text == "📈 Статистика за день":
        await message.answer("Статистика за день (поки не реалізовано)")
    elif text == "❌ Вийти з меню":
        await message.answer("Вихід з меню. Щоб знову побачити меню, надішліть /start", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Будь ласка, оберіть пункт меню.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
