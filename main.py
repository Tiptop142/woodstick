
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

TOKEN = "8265074513:AAECiHCO5pUSlzOs8KEZWYUU94h06ve25ic"

AUTHORIZED_USERS = [635809430]  # Твій ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клавіатура меню "Майстерня"
menu_buttons = [
    KeyboardButton(text="🛠 Повідомити про поломку"),
    KeyboardButton(text="📊 Список активних поломок"),
    KeyboardButton(text="📈 Статистика за день"),
    KeyboardButton(text="❌ Вийти з меню"),
]
menu_keyboard = ReplyKeyboardMarkup(keyboard=[[menu_buttons[0], menu_buttons[1]], [menu_buttons[2], menu_buttons[3]]], resize_keyboard=True)


@dp.message(Command('start'))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in AUTHORIZED_USERS:
        await message.answer("Ласкаво просимо до меню «Майстерня»", reply_markup=menu_keyboard)
    else:
        await message.answer("⛔️ У вас немає доступу до цього бота.")


@dp.message()
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


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
