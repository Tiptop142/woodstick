
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8265074513:AAECiHCO5pUSlzOs8KEZWYUU94h06ve25ic"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class ReportStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_comment = State()

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    print(f"/start від користувача {message.from_user.id}")
    await message.answer("Надішліть фото несправності:")
    await state.set_state(ReportStates.waiting_for_photo)

@dp.message(F.photo & F.state(ReportStates.waiting_for_photo))
async def photo_handler(message: types.Message, state: FSMContext):
    print(f"Отримано фото від {message.from_user.id}")
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await message.answer("Фото отримано! Тепер надішліть коментар.")
    await state.set_state(ReportStates.waiting_for_comment)

@dp.message(F.state(ReportStates.waiting_for_comment))
async def comment_handler(message: types.Message, state: FSMContext):
    print(f"Отримано коментар від {message.from_user.id}: {message.text}")
    data = await state.get_data()
    photo_id = data.get("photo")
    comment = message.text
    await message.answer(f"Отримано коментар: {comment}\nФото file_id: {photo_id}")
    await state.clear()

async def main():
    print("Бот запускається...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
