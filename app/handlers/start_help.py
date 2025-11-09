from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import code

from ..keyboards import main_kb
from ..utils import get_default_pre_offset, set_default_pre_offset

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Бот-планировщик с инлайн-календарём, пред-напоминаниями, повторениями, категориями и утренней сводкой.\n\n"
        "Команды:\n"
        "• /add — добавить задачу (инлайн-мастер)\n"
        "• /list — список с фильтром по категориям\n"
        "• /done <id> — выполнить\n"
        "• /delete <id> — удалить\n"
        "• /repeat <id> <RRULE> — задать повтор\n"
        "• /settings — дефолт пред-напоминания\n"
        "• /help — помощь",
        reply_markup=main_kb()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "➕ /add — текст → категория → год → месяц → день → час → минуты (0/10/20/30/40/50) → пред-напоминание → повтор → сохранить.\n"
        "📋 /list — выберите категорию, затем получите карточки с быстрыми кнопками сроков.\n"
        "⏰ Напоминания приходят в срок; 🔔 пред-напоминания — за N минут.\n"
        "🗓 Сводка — ежедневно в 09:00 (Asia/Tashkent)."
    )

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    minutes = await get_default_pre_offset(message.from_user.id)
    cur = minutes if minutes is not None else "не задан"
    await message.answer(
        f"Текущий дефолт пред-напоминания: {cur}\n"
        "Установить: /setpre 0 | /setpre 10 | /setpre 30 | /setpre 60"
    )

@router.message(Command("setpre"))
async def cmd_setpre(message: Message):
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /setpre <минуты>")
        return
    minutes = int(parts[1])
    if not (0 <= minutes <= 1440):
        await message.answer("Минуты должны быть 0..1440")
        return
    await set_default_pre_offset(message.from_user.id, minutes)
    await message.answer(f"Дефолт пред-напоминания: {minutes} мин.")

# Текстовые кнопки главного меню
from .add_wizard import cmd_add  # переиспользуем
from .list_filter import cmd_list

@router.message(F.text == "➕ Добавить задачу")
async def kb_add(message: Message, state: FSMContext):
    await cmd_add(message, state)

@router.message(F.text == "📋 Список")
async def kb_list(message: Message):
    await cmd_list(message)

@router.message(F.text == "✅ Сделано")
async def kb_done_prompt(message: Message):
    await message.answer("Отправьте команду: " + code("/done <id>"))

@router.message(F.text == "🗑 Удалить")
async def kb_del_prompt(message: Message):
    await message.answer("Отправьте команду: " + code("/delete <id>"))

@router.message(F.text == "❓ Помощь")
async def kb_help(message: Message):
    await cmd_help(message)
