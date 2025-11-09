import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from ..db import db_conn
from ..keyboards import filter_kb, inline_per_task_actions
from ..utils import pretty_task, cat_by_slug

router = Router()

@router.message(Command("list"))
async def cmd_list(message: Message):
    await message.answer("Выберите категорию:", reply_markup=filter_kb())

@router.callback_query(F.data.startswith("qfilter:"))
async def cb_qfilter(call: CallbackQuery):
    slug = call.data.split(":")[1]
    where = "user_id=? AND is_done=0"
    params = [call.from_user.id]

    if slug != "all":
        name = cat_by_slug(slug)
        if name is None:
            await call.answer("Неизвестная категория", show_alert=True)
            return
        where += " AND category=?"
        params.append(name)

    query = f"SELECT * FROM tasks WHERE {where} ORDER BY due_at IS NULL, due_at ASC, id DESC"
    async with db_conn() as db:
        cur = await db.execute(query, params)
        rows = await cur.fetchall()

    if not rows:
        await call.message.edit_text("Задач нет для выбранного фильтра.")
        await call.message.edit_reply_markup(reply_markup=filter_kb())
        await call.answer()
        return

    title = "Все категории" if slug == "all" else f"Категория: {cat_by_slug(slug)}"
    try:
        await call.message.edit_text(f"{title}. Открытых задач: {len(rows)}")
        await call.message.edit_reply_markup(reply_markup=filter_kb())
    except Exception:
        pass

    for r in rows:
        await call.message.answer(pretty_task(r), reply_markup=inline_per_task_actions(r["id"]))
        await asyncio.sleep(0.05)  # мягкий троттлинг

    await call.answer()
