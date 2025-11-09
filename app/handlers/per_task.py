from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from ..db import db_conn
from ..utils import parse_local_dt, to_iso, pretty_task
from ..models import next_occurrence, parse_rrule
from ..keyboards import inline_per_task_actions
from ..quick_due import make_due_today, make_due_tomorrow, make_due_this_week

router = Router()

# Быстрые сроки
@router.callback_query(F.data.startswith("qdue:"))
async def cb_quick_due(call: CallbackQuery):
    _, kind, sid = call.data.split(":")
    task_id = int(sid)

    if kind == "today":
        new_dt = make_due_today(); label = "сегодня"
    elif kind == "tom":
        new_dt = make_due_tomorrow(); label = "завтра"
    else:
        new_dt = make_due_this_week(); label = "на этой неделе"

    async with db_conn() as db:
        cur = await db.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, call.from_user.id))
        row = await cur.fetchone()
        if not row:
            await call.answer("Задача не найдена", show_alert=True)
            return

        await db.execute(
            "UPDATE tasks SET due_at=?, reminded_at=NULL, pre_reminded_at=NULL WHERE id=?",
            (to_iso(new_dt), task_id)
        )
        cur = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        updated = await cur.fetchone()
        await db.commit()

    try:
        await call.message.edit_text(pretty_task(updated))
        await call.message.edit_reply_markup(reply_markup=inline_per_task_actions(task_id))
    except Exception:
        pass
    await call.answer(f"Срок установлен {label} ({updated['due_at']})")

# Категории на карточке
from ..keyboards import categories_kb
from ..utils import cat_by_slug

@router.callback_query(F.data.startswith("catmenu:"))
async def cb_catmenu(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    async with db_conn() as db:
        cur = await db.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, call.from_user.id))
        row = await cur.fetchone()
        if not row:
            await call.answer("Задача не найдена", show_alert=True)
            return
    await call.message.edit_reply_markup(reply_markup=categories_kb(for_task_id=task_id))
    await call.answer("Выберите категорию")

@router.callback_query(F.data.startswith("catset:"))
async def cb_catset(call: CallbackQuery):
    _, sid, slug = call.data.split(":")
    task_id = int(sid)
    value = None if slug == "none" else cat_by_slug(slug)

    async with db_conn() as db:
        await db.execute("UPDATE tasks SET category=? WHERE id=? AND user_id=?", (value, task_id, call.from_user.id))
        cur = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        updated = await cur.fetchone()
        await db.commit()

    try:
        await call.message.edit_text(pretty_task(updated))
        await call.message.edit_reply_markup(reply_markup=inline_per_task_actions(task_id))
    except Exception:
        pass
    await call.answer("Категория обновлена")

# Done/Delete/Repeat + коллбэки
@router.message(Command("done"))
async def cmd_done_cmd(message: Message):
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /done <id>")
        return
    await handle_done(message.from_user.id, int(parts[1]), message)

@router.message(Command("delete"))
async def cmd_delete_cmd(message: Message):
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /delete <id>")
        return
    await handle_delete(message.from_user.id, int(parts[1]), message)

@router.message(Command("repeat"))
async def cmd_repeat(message: Message):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Использование: /repeat <id> <RRULE>, напр.: /repeat 12 FREQ=WEEKLY;INTERVAL=2")
        return
    task_id = int(parts[1])
    rrule = parts[2].upper().strip()
    if not parse_rrule(rrule):
        await message.answer("Некорректный RRULE. Допустимо: FREQ=DAILY|WEEKLY|MONTHLY и INTERVAL=n")
        return
    async with db_conn() as db:
        cur = await db.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, message.from_user.id))
        row = await cur.fetchone()
        if not row:
            await message.answer("Задача не найдена.")
            return
        await db.execute("UPDATE tasks SET rrule=? WHERE id=?", (rrule, task_id))
        await db.commit()
    await message.answer(f"Повторение для задачи #{task_id} установлено: {rrule}")

@router.callback_query(F.data.startswith("done:"))
async def cb_done(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    await handle_done(call.from_user.id, task_id, call.message, edit=True)
    await call.answer("Готово!")

@router.callback_query(F.data.startswith("del:"))
async def cb_del(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    await handle_delete(call.from_user.id, task_id, call.message, edit=True)
    await call.answer("Удалено")

async def handle_done(user_id: int, task_id: int, msg_obj, edit: bool = False):
    async with db_conn() as db:
        cur = await db.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
        row = await cur.fetchone()
        if not row:
            await msg_obj.answer("Задача не найдена.")
            return

        rrule = row["rrule"]
        due_at = parse_local_dt(row["due_at"]) if row["due_at"] else None

        if rrule and due_at:
            nxt = next_occurrence(due_at, rrule)
            if nxt is None:
                await db.execute("UPDATE tasks SET is_done=1 WHERE id=?", (task_id,))
            else:
                await db.execute(
                    "UPDATE tasks SET due_at=?, is_done=0, reminded_at=NULL, pre_reminded_at=NULL WHERE id=?",
                    (to_iso(nxt), task_id)
                )
        else:
            await db.execute("UPDATE tasks SET is_done=1 WHERE id=?", (task_id,))
        await db.commit()

    text = f"Задача #{task_id}: ✅ выполнено"
    if edit and msg_obj:
        try:
            await msg_obj.edit_text(text)
        except Exception:
            await msg_obj.answer(text)
    else:
        await msg_obj.answer(text)

async def handle_delete(user_id: int, task_id: int, msg_obj, edit: bool = False):
    async with db_conn() as db:
        await db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
        await db.commit()
    text = f"Задача #{task_id}: 🗑 удалена"
    if edit and msg_obj:
        try:
            await msg_obj.edit_text(text)
        except Exception:
            await msg_obj.answer(text)
    else:
        await msg_obj.answer(text)
