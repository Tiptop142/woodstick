import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ContentType
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart

API_TOKEN = '8265074513:AAECiHCO5pUSlzOs8KEZWYUU94h06ve25ic'
GROUP_ID = -1002726032172
ALLOWED_USERS = [635809430]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class ReportState(StatesGroup):
    choosing_mech_option = State()
    type = State()
    machine = State()
    equipment = State()
    description = State()
    photo = State()

active_reports = {}  # {message_id: {...}}

last_menu_message_id = None  # Зберігаємо ID останнього повідомлення з меню

async def delete_old_messages(state: FSMContext, chat_id: int):
    data = await state.get_data()
    msg_ids = data.get("message_ids", [])
    for msg_id in msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as ex:
            logger.warning(f"Не вдалося видалити проміжне повідомлення {msg_id}: {ex}")
    await state.update_data(message_ids=[])

async def save_message_id(state: FSMContext, message: Message):
    data = await state.get_data()
    msg_ids = data.get("message_ids", [])
    msg_ids.append(message.message_id)
    await state.update_data(message_ids=msg_ids)

async def send_menu_button():
    global last_menu_message_id

    # Видаляємо попереднє меню з кнопкою, якщо є
    if last_menu_message_id is not None:
        try:
            await bot.delete_message(chat_id=GROUP_ID, message_id=last_menu_message_id)
        except Exception as ex:
            logger.warning(f"Не вдалося видалити старе меню: {ex}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Меню", callback_data="show_menu")]
    ])
    sent_msg = await bot.send_message(chat_id=GROUP_ID, text="Натисніть кнопку, щоб відкрити меню:", reply_markup=kb)
    last_menu_message_id = sent_msg.message_id

@dp.callback_query(F.data == "show_menu")
async def show_menu_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ALLOWED_USERS:
        await callback.answer("⛔ У вас немає доступу до цієї функції.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Механічна служба", callback_data="open_mech")],
        [InlineKeyboardButton(text="📊 Звіти", callback_data="open_reports")]
    ])
    # Відповідаємо у групі (редагуємо повідомлення кнопки або надсилаємо нове)
    try:
        # Редагуємо кнопки в тому ж повідомленні, щоб показати меню
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Вітаю! Оберіть опцію:",
            reply_markup=kb
        )
    except Exception as e:
        logger.warning(f"Не вдалося показати меню: {e}")
        # Якщо не вийшло редагувати, просто надсилаємо нове повідомлення
        await callback.message.answer("Вітаю! Оберіть опцію:", reply_markup=kb)

    await callback.answer()

@dp.callback_query(F.data == "open_mech")
async def mech_menu(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Додати несправність", callback_data="mech_add_issue")],
        [InlineKeyboardButton(text="2. Зауваження по роботі", callback_data="mech_feedback")]
    ])
    sent_msg = await callback.message.answer("Меню Механічного цеху:", reply_markup=kb)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.choosing_mech_option)
    await callback.answer()

@dp.callback_query(ReportState.choosing_mech_option, F.data == "mech_add_issue")
async def mech_add_issue(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Критична", callback_data="type_critical"),
            InlineKeyboardButton(text="Не критична", callback_data="type_noncritical"),
        ]
    ])
    sent_msg = await callback.message.answer("Оберіть тип поломки:", reply_markup=builder)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.type)
    await callback.answer()

@dp.callback_query(ReportState.choosing_mech_option, F.data == "mech_feedback")
async def mech_feedback(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    sent_msg = await callback.message.answer("Розділ 'Зауваження по роботі' поки що не реалізований.")
    await save_message_id(state, sent_msg)
    await callback.answer()

@dp.callback_query(ReportState.type, F.data.startswith("type_"))
async def type_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    issue_type = callback.data.split("_")[1]
    await state.update_data(type=issue_type)
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Станок 1", callback_data="machine_1"),
            InlineKeyboardButton(text="Станок 2", callback_data="machine_2"),
            InlineKeyboardButton(text="Станок 3", callback_data="machine_3"),
        ]
    ])
    sent_msg = await callback.message.answer("Оберіть станок:", reply_markup=builder)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.machine)
    await callback.answer()

@dp.callback_query(ReportState.machine, F.data.startswith("machine_"))
async def machine_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    machine = callback.data.split("_")[1]
    await state.update_data(machine=machine)
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Обладнання A", callback_data="equip_A"),
            InlineKeyboardButton(text="Обладнання B", callback_data="equip_B"),
            InlineKeyboardButton(text="Обладнання C", callback_data="equip_C"),
        ]
    ])
    sent_msg = await callback.message.answer("Оберіть обладнання:", reply_markup=builder)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.equipment)
    await callback.answer()

@dp.callback_query(ReportState.equipment, F.data.startswith("equip_"))
async def equipment_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    equipment = callback.data.split("_")[1]
    await state.update_data(equipment=equipment)
    sent_msg = await callback.message.answer("Опишіть поломку текстом:")
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.description)
    await callback.answer()

@dp.message(ReportState.description)
async def description_entered(message: Message, state: FSMContext):
    await delete_old_messages(state, message.chat.id)
    await state.update_data(description=message.text)
    try:
        await message.delete()
    except Exception:
        pass
    sent_msg = await message.answer("Тепер надішліть фото або документ з поломкою.")
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.photo)

@dp.message(ReportState.photo, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def photo_or_doc_received(message: Message, state: FSMContext):
    data = await state.get_data()
    caption = (
        f"<b>🚨 Поломка</b>\n"
        f"<b>Тип:</b> {'Критична' if data['type'] == 'critical' else 'Не критична'}\n"
        f"<b>Станок:</b> {data['machine']}\n"
        f"<b>Обладнання:</b> {data['equipment']}\n"
        f"<b>Опис:</b> {data['description']}"
    )

    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            sent = await bot.send_photo(
                chat_id=GROUP_ID,
                photo=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        elif message.document:
            file_id = message.document.file_id
            sent = await bot.send_document(
                chat_id=GROUP_ID,
                document=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        else:
            await message.answer("❗ Будь ласка, надішліть фото або документ.")
            return

        markup = InlineKeyboardMarkup(inline_keyboard=[[  
            InlineKeyboardButton(text="Відремонтовано", callback_data=f"mark_done:{sent.message_id}")
        ]])
        await bot.edit_message_reply_markup(
            chat_id=GROUP_ID,
            message_id=sent.message_id,
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Помилка надсилання в групу: {e}")
        await message.answer("❌ Сталася помилка при надсиланні повідомлення в групу.")
        return

    active_reports[sent.message_id] = {
        "user_id": message.from_user.id,
        "description": data['description'],
        "status": "Активна"
    }

    # Видалення проміжкових повідомлень
    await delete_old_messages(state, message.chat.id)
    try:
        await message.delete()
    except Exception:
        pass

    await state.clear()

    # Після відправки поломки оновлюємо кнопку меню в кінці групи
    await send_menu_button()

@dp.message(ReportState.photo)
async def invalid_input(message: Message):
    await message.answer("Будь ласка, надішліть фото або документ з поломкою.")

@dp.callback_query(F.data.startswith("mark_done:"))
async def mark_done_handler(callback: CallbackQuery, state: FSMContext):
    message_id_str = callback.data.split(":")[1]
    try:
        message_id = int(message_id_str)
    except ValueError:
        await callback.answer("Невірні дані.")
        return

    report = active_reports.get(message_id)
    if not report:
        await callback.answer("Цей звіт вже відмічений або не існує.")
        return

    if report["status"] == "Відремонтовано":
        await callback.answer("Цей звіт уже відмічений як відремонтований.")
        return

    report["status"] = "Відремонтовано"
    active_reports[message_id] = report

    try:
        await bot.edit_message_caption(
            chat_id=GROUP_ID,
            message_id=message_id,
            caption=(
                f"<b>🚨 Поломка</b>\n"
                f"<b>Опис:</b> {report['description']}\n\n"
                f"<b>✅ Статус: Відремонтовано</b>"
            ),
            parse_mode=ParseMode.HTML
        )
        await callback.answer("Статус успішно оновлено.")
    except Exception as e:
        logger.error(f"Помилка оновлення повідомлення: {e}")
        await callback.answer("Не вдалося оновити статус повідомлення.")

async def main():
    logger.info("Бот запускається...")
    await send_menu_button()  # Відправляємо кнопку меню при старті бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
