from typing import Optional
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from .config import CATEGORIES
from .utils import _days_in_month, cat_slug

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить задачу")],
            [KeyboardButton(text="📋 Список"), KeyboardButton(text="✅ Сделано")],
            [KeyboardButton(text="🗑 Удалить"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )

def years_kb(base_year: int) -> InlineKeyboardMarkup:
    y = base_year
    buttons = [[InlineKeyboardButton(text=str(y+i), callback_data=f"y:{y+i}") for i in range(0, 3)]]
    nav = [
        InlineKeyboardButton(text="⟵", callback_data=f"y_nav:{y-3}"),
        InlineKeyboardButton(text="Без срока", callback_data="due_skip"),
        InlineKeyboardButton(text="⟶", callback_data=f"y_nav:{y+3}")
    ]
    buttons.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def months_kb() -> InlineKeyboardMarkup:
    rows = []
    for r in range(0, 12, 3):
        rows.append([InlineKeyboardButton(text=str(m), callback_data=f"m:{m}") for m in range(1+r, 1+r+3)])
    rows.append([InlineKeyboardButton(text="◀ Год", callback_data="back:year")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def days_kb(year: int, month: int) -> InlineKeyboardMarkup:
    total = _days_in_month(year, month)
    buttons, row = [], []
    for d in range(1, total+1):
        row.append(InlineKeyboardButton(text=str(d), callback_data=f"d:{d}"))
        if len(row) == 7:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀ Месяц", callback_data="back:month")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def hours_kb() -> InlineKeyboardMarkup:
    buttons = []
    for r in range(0, 24, 6):
        buttons.append([InlineKeyboardButton(text=f"{h:02d}", callback_data=f"h:{h}") for h in range(r, r+6)])
    buttons.append([InlineKeyboardButton(text="◀ День", callback_data="back:day")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def minutes_kb() -> InlineKeyboardMarkup:
    opts = [0,10,20,30,40,50]
    rows = [
        [InlineKeyboardButton(text=f"{m:02d}", callback_data=f"min:{m}") for m in opts[:3]],
        [InlineKeyboardButton(text=f"{m:02d}", callback_data=f"min:{m}") for m in opts[3:]]
    ]
    rows.append([InlineKeyboardButton(text="◀ Час", callback_data="back:hour")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def pre_reminder_kb(default_minutes: Optional[int]) -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(text=f"Default ({default_minutes if default_minutes is not None else '—'})", callback_data="pre:def"),
        InlineKeyboardButton(text="0", callback_data="pre:0"),
        InlineKeyboardButton(text="10", callback_data="pre:10"),
    ]
    row2 = [
        InlineKeyboardButton(text="30", callback_data="pre:30"),
        InlineKeyboardButton(text="60", callback_data="pre:60"),
    ]
    back = [InlineKeyboardButton(text="◀ Минуты", callback_data="back:min")]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2, back])

def repeat_freq_kb() -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(text="Без повтора", callback_data="rep:NONE"),
        InlineKeyboardButton(text="DAILY", callback_data="rep:DAILY"),
        InlineKeyboardButton(text="WEEKLY", callback_data="rep:WEEKLY"),
        InlineKeyboardButton(text="MONTHLY", callback_data="rep:MONTHLY"),
    ]
    back = [InlineKeyboardButton(text="◀ Пред-напоминание", callback_data="back:pre")]
    return InlineKeyboardMarkup(inline_keyboard=[row1, back])

def repeat_interval_kb() -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton(text=str(i), callback_data=f"repint:{i}") for i in range(1,5)]
    back = [InlineKeyboardButton(text="◀ Частота", callback_data="back:repfreq")]
    return InlineKeyboardMarkup(inline_keyboard=[row, back])

def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💾 Сохранить", callback_data="save_task"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task"),
    ]])

def categories_kb(for_task_id: int | None = None) -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, c in enumerate(CATEGORIES, 1):
        data = f"catpick:{cat_slug(c)}" if for_task_id is None else f"catset:{for_task_id}:{cat_slug(c)}"
        row.append(InlineKeyboardButton(text=c, callback_data=data))
        if i % 3 == 0:
            rows.append(row); row = []
    if row:
        rows.append(row)
    if for_task_id is None:
        rows.append([InlineKeyboardButton(text="Без категории", callback_data="catpick:none")])
    else:
        rows.append([InlineKeyboardButton(text="Снять категорию", callback_data=f"catset:{for_task_id}:none")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def filter_kb() -> InlineKeyboardMarkup:
    head = [InlineKeyboardButton(text="Все", callback_data="qfilter:all")]
    cat_buttons = [InlineKeyboardButton(text=c, callback_data=f"qfilter:{cat_slug(c)}") for c in CATEGORIES]

    rows = [[*head]]
    for i in range(0, len(cat_buttons), 3):
        chunk = cat_buttons[i:i+3]
        if chunk:
            rows.append(chunk)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def inline_task_actions(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Сделано", callback_data=f"done:{task_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{task_id}")
    ]])

def inline_per_task_actions(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 На сегодня", callback_data=f"qdue:today:{task_id}"),
            InlineKeyboardButton(text="📆 На завтра", callback_data=f"qdue:tom:{task_id}"),
        ],
        [
            InlineKeyboardButton(text="🗓 На этой неделе", callback_data=f"qdue:week:{task_id}"),
            InlineKeyboardButton(text="🏷 Категория", callback_data=f"catmenu:{task_id}"),
        ],
        [
            InlineKeyboardButton(text="✅ Сделано", callback_data=f"done:{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{task_id}")
        ]
    ])
