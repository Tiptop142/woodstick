import logging
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ContentType
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '8265074513:AAECiHCO5pUSlzOs8KEZWYUU94h06ve25ic'
GROUP_ID = -1002726032172
ALLOWED_USERS = [635809430]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_PATH = "malfunctions.db"

class ReportState(StatesGroup):
    choosing_mech_option = State()
    work_area = State()
    type = State()
    machine = State()
    equipment = State()
    malfunction_type = State()
    description = State()
    photo = State()
    adding_comment = State()

last_menu_message_id = None

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            message_id INTEGER PRIMARY KEY,
            work_area TEXT,
            malfunction_type TEXT,
            machine TEXT,
            equipment TEXT,
            description TEXT,
            critical INTEGER,
            status TEXT DEFAULT 'Активна'
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            comment TEXT,
            FOREIGN KEY(message_id) REFERENCES reports(message_id)
        )
        """)
        await db.commit()

async def save_report(message_id, data):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO reports
            (message_id, work_area, malfunction_type, machine, equipment, description, critical, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            data.get('work_area', ''),
            data.get('malfunction_type', ''),
            data.get('machine', ''),
            data.get('equipment', ''),
            data.get('description', ''),
            int(data.get('critical', False)),
            'Активна'
        ))
        await db.commit()

async def get_report_by_message_id(message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT work_area, malfunction_type, machine, equipment, description, critical, status FROM reports WHERE message_id = ?", (message_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        work_area, malfunction_type, machine, equipment, description, critical, status = row
        cursor = await db.execute("SELECT comment FROM comments WHERE message_id = ?", (message_id,))
        comments_rows = await cursor.fetchall()
        comments = [c[0] for c in comments_rows]
        return {
            "work_area": work_area,
            "malfunction_type": malfunction_type,
            "machine": machine,
            "equipment": equipment,
            "description": description,
            "critical": bool(critical),
            "status": status,
            "comments": comments
        }

async def update_report_status(message_id, new_status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE reports SET status = ? WHERE message_id = ?", (new_status, message_id))
        await db.commit()

async def add_comment_to_report(message_id, comment_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO comments (message_id, comment) VALUES (?, ?)", (message_id, comment_text))
        await db.commit()

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
    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Вітаю! Оберіть опцію:",
            reply_markup=kb
        )
    except Exception as e:
        logger.warning(f"Не вдалося показати меню: {e}")
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ділянка 4.8", callback_data="workarea_4_8")],
        [InlineKeyboardButton(text="Ділянка 5.10", callback_data="workarea_5_10")],
        [InlineKeyboardButton(text="Цех ремонту шпону", callback_data="workarea_spone")],
        [InlineKeyboardButton(text="Меблевий цех", callback_data="workarea_mebel")],
        [InlineKeyboardButton(text="Палички", callback_data="workarea_palichky")],
        [InlineKeyboardButton(text="Цех виготовлення паличок", callback_data="workarea_palichky_making")],
        [InlineKeyboardButton(text="Масляна котельня", callback_data="workarea_boiler")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_mech_menu")],
    ])
    sent_msg = await callback.message.answer("Оберіть робочу ділянку:", reply_markup=kb)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.work_area)
    await callback.answer()

@dp.callback_query(ReportState.work_area, F.data.startswith("workarea_"))
async def work_area_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    work_area = callback.data.split("_", 1)[1]
    await state.update_data(work_area=work_area)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Станок 1", callback_data="machine_1")],
        [InlineKeyboardButton(text="Станок 2", callback_data="machine_2")],
        [InlineKeyboardButton(text="Станок 3", callback_data="machine_3")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_work_area")],
    ])
    sent_msg = await callback.message.answer("Оберіть станок:", reply_markup=kb)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.machine)
    await callback.answer()

@dp.callback_query(ReportState.machine, F.data.startswith("machine_"))
async def machine_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    machine = callback.data.split("_")[1]
    await state.update_data(machine=machine)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обладнання A", callback_data="equip_A")],
        [InlineKeyboardButton(text="Обладнання B", callback_data="equip_B")],
        [InlineKeyboardButton(text="Обладнання C", callback_data="equip_C")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_machine")],
    ])
    sent_msg = await callback.message.answer("Оберіть обладнання:", reply_markup=kb)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.equipment)
    await callback.answer()

@dp.callback_query(ReportState.equipment, F.data.startswith("equip_"))
async def equipment_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    equipment = callback.data.split("_")[1]
    await state.update_data(equipment=equipment)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Механічна", callback_data="malfunc_mechanical")],
        [InlineKeyboardButton(text="Електрична", callback_data="malfunc_electric")],
        [InlineKeyboardButton(text="Невідома", callback_data="malfunc_unknown")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_equipment")],
    ])
    sent_msg = await callback.message.answer("Оберіть тип несправності:", reply_markup=kb)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.malfunction_type)
    await callback.answer()

@dp.callback_query(ReportState.malfunction_type, F.data.startswith("malfunc_"))
async def malfunction_type_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    malfunction_type = callback.data.split("_")[1]
    await state.update_data(malfunction_type=malfunction_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Критична", callback_data="type_critical")],
        [InlineKeyboardButton(text="Не критична", callback_data="type_noncritical")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_malfunction_type")],
    ])
    sent_msg = await callback.message.answer("Оберіть критичність поломки:", reply_markup=kb)
    await save_message_id(state, sent_msg)
    await state.set_state(ReportState.type)
    await callback.answer()

@dp.callback_query(ReportState.type, F.data.startswith("type_"))
async def type_selected(callback: CallbackQuery, state: FSMContext):
    await delete_old_messages(state, callback.message.chat.id)
    issue_type = callback.data.split("_")[1]
    await state.update_data(type=issue_type)
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

from aiogram.enums import ContentType  # У тебе він вже імпортований, просто для ясності

@dp.message(ReportState.photo, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT, ContentType.VIDEO}))
async def media_received(message: Message, state: FSMContext):
    data = await state.get_data()
    malfunction_type_dict = {
        "mechanical": "Механічна",
        "electric": "Електрична",
        "unknown": "Невідома"
    }
    malfunction_type_text = malfunction_type_dict.get(data.get('malfunction_type', ''), 'Невідома')

    critical_flag = (data.get('type') == 'critical')

    caption_base = (
        f"<b>🚨 Поломка</b>\n"
        f"<b>Робоча ділянка:</b> {data.get('work_area', '')}\n"
        f"<b>Тип поломки:</b> {malfunction_type_text}\n"
        f"<b>Станок:</b> {data.get('machine', '')}\n"
        f"<b>Обладнання:</b> {data.get('equipment', '')}\n"
        f"<b>Опис:</b> {data.get('description', '')}\n"
    )

    if critical_flag:
        caption_base += "\n‼️ <b>УВАГА!!! Критична несправність верстата</b> ‼️"

    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            sent = await bot.send_photo(
                chat_id=GROUP_ID,
                photo=file_id,
                caption=caption_base,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        elif message.document:
            file_id = message.document.file_id
            sent = await bot.send_document(
                chat_id=GROUP_ID,
                document=file_id,
                caption=caption_base,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        elif message.video:
            file_id = message.video.file_id
            sent = await bot.send_video(
                chat_id=GROUP_ID,
                video=file_id,
                caption=caption_base,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        else:
            await message.answer("❗ Будь ласка, надішліть фото, відео або документ.")
            return

        # Зберігаємо у базу
        db_data = {
            "work_area": data.get('work_area', ''),
            "malfunction_type": malfunction_type_text,
            "machine": data.get('machine', ''),
            "equipment": data.get('equipment', ''),
            "description": data.get('description', ''),
            "critical": critical_flag
        }
        await save_report(sent.message_id, db_data)

        # Кнопки "Відремонтовано" та "Коментар"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Відремонтовано", callback_data=f"mark_done:{sent.message_id}"),
                InlineKeyboardButton(text="Коментар", callback_data=f"add_comment:{sent.message_id}")
            ]
        ])
        await bot.edit_message_reply_markup(
            chat_id=GROUP_ID,
            message_id=sent.message_id,
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Помилка надсилання в групу: {e}")
        await message.answer("❌ Сталася помилка при надсиланні повідомлення в групу.")
        return

    await delete_old_messages(state, message.chat.id)
    try:
        await message.delete()
    except Exception:
        pass

    await state.clear()
    await send_menu_button()


@dp.message(ReportState.photo)
async def invalid_input(message: Message):
    await message.answer("Будь ласка, надішліть фото або документ з поломкою.")

def build_caption(report, show_buttons=True):
    caption = (
        f"<b>🚨 Поломка</b>\n"
        f"<b>Робоча ділянка:</b> {report.get('work_area','')}\n"
        f"<b>Тип поломки:</b> {report.get('malfunction_type','')}\n"
        f"<b>Станок:</b> {report.get('machine','')}\n"
        f"<b>Обладнання:</b> {report.get('equipment','')}\n"
        f"<b>Опис:</b> {report.get('description','')}\n"
    )
    if report.get('critical'):
        caption += "\n‼️ <b>УВАГА!!! Критична несправність верстата</b> ‼️"

    if report.get('status') == "Відремонтовано":
        caption += f"\n\n<b>🟩 Статус: <b><i>ВІДРЕМОНТОВАНО</i></b></b>"
    else:
        caption += f"\n\n<b>Статус:</b> {report.get('status','')}"

    if report.get("comments"):
        caption += "\n<b>Коментарі:</b>\n"
        for c in report["comments"]:
            caption += f"💬 {c}\n"

    return caption.strip()

@dp.callback_query(F.data.startswith("mark_done:"))
async def mark_done_handler(callback: CallbackQuery):
    message_id_str = callback.data.split(":")[1]
    try:
        message_id = int(message_id_str)
    except ValueError:
        await callback.answer("Невірні дані.")
        return
    report = await get_report_by_message_id(message_id)
    if not report:
        await callback.answer("Цей звіт вже відмічений або не існує.")
        return
    if report["status"] == "Відремонтовано":
        await callback.answer("Цей звіт уже відмічений як відремонтований.")
        return
    await update_report_status(message_id, "Відремонтовано")
    report = await get_report_by_message_id(message_id)  # оновлюємо
    try:
        await bot.edit_message_caption(
            chat_id=GROUP_ID,
            message_id=message_id,
            caption=build_caption(report, show_buttons=False),
            parse_mode=ParseMode.HTML,
            reply_markup=None
        )
        await callback.answer("Статус успішно оновлено.")
    except Exception as e:
        logger.error(f"Помилка оновлення повідомлення: {e}")
        await callback.answer("Не вдалося оновити статус повідомлення.")

@dp.callback_query(F.data.startswith("add_comment:"))
async def add_comment_handler(callback: CallbackQuery, state: FSMContext):
    message_id_str = callback.data.split(":")[1]
    try:
        message_id = int(message_id_str)
    except ValueError:
        await callback.answer("Невірні дані.")
        return
    report = await get_report_by_message_id(message_id)
    if not report:
        await callback.answer("Звіт не знайдено.")
        return
    await state.update_data(comment_message_id=message_id)
    await state.set_state(ReportState.adding_comment)
    await callback.answer("Напишіть свій коментар у повідомленні.")

@dp.message(ReportState.adding_comment)
async def add_comment_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    message_id = data.get("comment_message_id")

    if not message_id:
        await message.answer("Не вдалося знайти поломку для додавання коментаря.")
        await state.clear()
        return

    comment_text = message.text.strip()
    if not comment_text:
        await message.answer("Коментар не може бути порожнім. Напишіть, будь ласка, текст коментаря.")
        return

    await add_comment_to_report(message_id, comment_text)
    report = await get_report_by_message_id(message_id)

    show_buttons = (report.get('status') != "Відремонтовано")

    markup = None
    if show_buttons:
        markup = InlineKeyboardMarkup(inline_keyboard=[[  
            InlineKeyboardButton(text="Відремонтовано", callback_data=f"mark_done:{message_id}"),
            InlineKeyboardButton(text="Коментар", callback_data=f"add_comment:{message_id}")
        ]])

    try:
        await bot.edit_message_caption(
            chat_id=GROUP_ID,
            message_id=message_id,
            caption=build_caption(report, show_buttons),
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Помилка оновлення повідомлення з коментарем: {e}")
        await message.answer("Сталася помилка при додаванні коментаря.")

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення користувача з коментарем: {e}")

    await state.clear()

# --- Обробники кнопок Назад (працюють у будь-якому стані) ---

@dp.callback_query(F.data == "back_to_mech_menu")
async def back_to_mech_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await mech_menu(callback, state)
    await callback.answer()

@dp.callback_query(F.data == "back_to_work_area")
async def back_to_work_area(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReportState.choosing_mech_option)
    await mech_add_issue(callback, state)
    await callback.answer()

@dp.callback_query(F.data == "back_to_machine")
async def back_to_machine(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReportState.work_area)
    await work_area_selected(callback, state)
    await callback.answer()

@dp.callback_query(F.data == "back_to_equipment")
async def back_to_equipment(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReportState.machine)
    await machine_selected(callback, state)
    await callback.answer()

@dp.callback_query(F.data == "back_to_malfunction_type")
async def back_to_malfunction_type(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReportState.equipment)
    await equipment_selected(callback, state)
    await callback.answer()

async def main():
    logger.info("Ініціалізація бази даних...")
    await init_db()
    logger.info("Бот запускається...")
    await send_menu_button()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
