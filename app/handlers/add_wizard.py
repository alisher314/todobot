from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from ..keyboards import (
    years_kb, months_kb, days_kb, hours_kb, minutes_kb,
    pre_reminder_kb, repeat_freq_kb, repeat_interval_kb, confirm_kb,
    categories_kb
)
from ..utils import now_local, to_iso, parse_local_dt, get_default_pre_offset
from ..db import db_conn
from ..config import TZ
from datetime import datetime

router = Router()

class AddTask(StatesGroup):
    waiting_title = State()
    picking_due = State()

def selection_preview(data: dict) -> str:
    y = data.get("year"); m = data.get("month"); d = data.get("day")
    h = data.get("hour"); mn = data.get("minute")
    pre = data.get("pre_offset")
    rf = data.get("rrule_freq"); ri = data.get("rrule_interval")
    cat = data.get("category")

    due_str = "без срока"
    if all(v is not None for v in (y,m,d,h,mn)):
        due_str = f"{y:04d}-{m:02d}-{d:02d} {h:02d}:{mn:02d}"

    rep_str = "нет"
    if rf and rf != "NONE":
        rep_str = f"FREQ={rf};INTERVAL={ri or 1}"

    pre_str = "Default" if pre is None else f"{pre} мин"
    cat_str = cat if cat else "нет"

    return (
        f"🧩 Выбор параметров\n"
        f"• Категория: {cat_str}\n"
        f"• Срок: {due_str}\n"
        f"• Пред-напоминание: {pre_str}\n"
        f"• Повтор: {rep_str}\n"
    )

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await state.set_state(AddTask.waiting_title)
    await message.answer("Шаг 1/5. Отправьте текст задачи:")

@router.message(AddTask.waiting_title)
async def st_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Текст пуст. Повторите:")
        return
    await state.update_data(
        title=title, category=None,
        year=None, month=None, day=None, hour=None, minute=None,
        pre_offset=None, rrule_freq=None, rrule_interval=None
    )
    txt = selection_preview(await state.get_data()) + "\nШаг 2/5. Выберите категорию:"
    await state.set_state(AddTask.picking_due)
    await message.answer(txt, reply_markup=categories_kb())

@router.callback_query(AddTask.picking_due, F.data.startswith("catpick:"))
async def cb_catpick(call: CallbackQuery, state: FSMContext):
    from ..utils import cat_by_slug
    slug = call.data.split(":")[1]
    cat = None if slug == "none" else cat_by_slug(slug)
    await state.update_data(category=cat)
    base_year = now_local().year
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 3/5. Выберите ГОД:")
    await call.message.edit_reply_markup(reply_markup=years_kb(base_year))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("y_nav:"))
async def cb_year_nav(call: CallbackQuery, state: FSMContext):
    base = int(call.data.split(":")[1])
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 3/5. Выберите ГОД:")
    await call.message.edit_reply_markup(reply_markup=years_kb(base))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("y:"))
async def cb_year(call: CallbackQuery, state: FSMContext):
    year = int(call.data.split(":")[1])
    await state.update_data(year=year, month=None, day=None, hour=None, minute=None)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите МЕСЯЦ:")
    await call.message.edit_reply_markup(reply_markup=months_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "back:year")
async def cb_back_year(call: CallbackQuery, state: FSMContext):
    base_year = now_local().year
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 3/5. Выберите ГОД:")
    await call.message.edit_reply_markup(reply_markup=years_kb(base_year))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("m:"))
async def cb_month(call: CallbackQuery, state: FSMContext):
    month = int(call.data.split(":")[1])
    data = await state.get_data()
    if not data.get("year"):
        await call.answer("Сначала выберите год", show_alert=True)
        return
    await state.update_data(month=month, day=None, hour=None, minute=None)
    y = data["year"]
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите ДЕНЬ:")
    await call.message.edit_reply_markup(reply_markup=days_kb(y, month))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "back:month")
async def cb_back_month(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите МЕСЯЦ:")
    await call.message.edit_reply_markup(reply_markup=months_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("d:"))
async def cb_day(call: CallbackQuery, state: FSMContext):
    day = int(call.data.split(":")[1])
    await state.update_data(day=day, hour=None, minute=None)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите ЧАС:")
    await call.message.edit_reply_markup(reply_markup=hours_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "back:day")
async def cb_back_day(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    y, m = data.get("year"), data.get("month")
    await call.message.edit_text(selection_preview(data) + "\nВыберите ДЕНЬ:")
    await call.message.edit_reply_markup(reply_markup=days_kb(y, m))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("h:"))
async def cb_hour(call: CallbackQuery, state: FSMContext):
    h = int(call.data.split(":")[1])
    await state.update_data(hour=h, minute=None)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите МИНУТЫ:")
    await call.message.edit_reply_markup(reply_markup=minutes_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "back:hour")
async def cb_back_hour(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите ЧАС:")
    await call.message.edit_reply_markup(reply_markup=hours_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("min:"))
async def cb_min(call: CallbackQuery, state: FSMContext):
    minute = int(call.data.split(":")[1])
    await state.update_data(minute=minute)
    default_pre = await get_default_pre_offset(call.from_user.id)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 4/5. Пред-напоминание:")
    await call.message.edit_reply_markup(reply_markup=pre_reminder_kb(default_pre))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "back:min")
async def cb_back_min(call: CallbackQuery, state: FSMContext):
    await state.update_data(minute=None)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите МИНУТЫ:")
    await call.message.edit_reply_markup(reply_markup=minutes_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("pre:"))
async def cb_pre(call: CallbackQuery, state: FSMContext):
    val = call.data.split(":")[1]
    pre = None if val == "def" else int(val)
    await state.update_data(pre_offset=pre)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 5/5. Повтор:")
    await call.message.edit_reply_markup(reply_markup=repeat_freq_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "back:pre")
async def cb_back_pre(call: CallbackQuery, state: FSMContext):
    default_pre = await get_default_pre_offset(call.from_user.id)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 4/5. Пред-напоминание:")
    await call.message.edit_reply_markup(reply_markup=pre_reminder_kb(default_pre))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("rep:"))
async def cb_rep_freq(call: CallbackQuery, state: FSMContext):
    freq = call.data.split(":")[1]
    if freq == "NONE":
        await state.update_data(rrule_freq=None, rrule_interval=None)
        await call.message.edit_text(selection_preview(await state.get_data()) + "\nПроверить и сохранить?")
        await call.message.edit_reply_markup(reply_markup=confirm_kb())
        await call.answer()
        return
    await state.update_data(rrule_freq=freq, rrule_interval=None)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nВыберите интервал (1–4):")
    await call.message.edit_reply_markup(reply_markup=repeat_interval_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "back:repfreq")
async def cb_back_repfreq(call: CallbackQuery, state: FSMContext):
    await state.update_data(rrule_interval=None)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 5/5. Повтор:")
    await call.message.edit_reply_markup(reply_markup=repeat_freq_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data.startswith("repint:"))
async def cb_rep_int(call: CallbackQuery, state: FSMContext):
    interval = int(call.data.split(":")[1])
    await state.update_data(rrule_interval=interval)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nПроверить и сохранить?")
    await call.message.edit_reply_markup(reply_markup=confirm_kb())
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "due_skip")
async def cb_due_skip(call: CallbackQuery, state: FSMContext):
    await state.update_data(year=None, month=None, day=None, hour=None, minute=None)
    default_pre = await get_default_pre_offset(call.from_user.id)
    await call.message.edit_text(selection_preview(await state.get_data()) + "\nШаг 4/5. Пред-напоминание:")
    await call.message.edit_reply_markup(reply_markup=pre_reminder_kb(default_pre))
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "save_task")
async def cb_save(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    title = data.get("title")
    y,m,d,h,mn = data.get("year"), data.get("month"), data.get("day"), data.get("hour"), data.get("minute")
    pre = data.get("pre_offset")
    rf, ri = data.get("rrule_freq"), data.get("rrule_interval")

    due_dt = None
    if all(v is not None for v in (y,m,d,h,mn)):
        due_dt = datetime(y, m, d, h, mn, tzinfo=TZ)

    rrule = None
    if rf and rf != "NONE":
        rrule = f"FREQ={rf};INTERVAL={ri or 1}"

    async with db_conn() as db:
        await db.execute(
            "INSERT INTO tasks (user_id, title, category, due_at, is_done, created_at, reminded_at, pre_offset_minutes, pre_reminded_at, rrule) "
            "VALUES (?, ?, ?, ?, 0, ?, NULL, ?, NULL, ?)",
            (
                call.from_user.id,
                title,
                data.get("category"),
                to_iso(due_dt),
                to_iso(now_local()),
                pre,
                rrule
            )
        )
        await db.commit()

    await state.clear()
    try:
        await call.message.edit_text("Задача добавлена ✅")
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        await call.message.answer("Задача добавлена ✅", reply_markup=None)
    await call.answer()

@router.callback_query(AddTask.picking_due, F.data == "cancel_task")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text("Отменено.")
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        await call.message.answer("Отменено.")
    await call.answer()
