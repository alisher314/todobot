# app/utils.py
import sqlite3
from datetime import datetime
from typing import Optional

from .config import TZ, CATEGORIES
from .db import db_conn
from .models import parse_rrule  # ок: utils -> models (без циклов)


# ---------- время и парсинг ----------

def now_local() -> datetime:
    return datetime.now(TZ)


def to_iso(dt: datetime | None) -> Optional[str]:
    return dt.replace(second=0, microsecond=0).isoformat() if dt else None


def parse_local_dt(text: str) -> Optional[datetime]:
    """
    Поддерживаем:
    - 'YYYY-MM-DD'
    - 'YYYY-MM-DD HH:MM'
    - 'YYYY-MM-DD HH:MM:SS'
    - 'YYYY-MM-DDTHH:MM%z'           (ISO без секунд, с таймзоной)
    - 'YYYY-MM-DDTHH:MM:SS%z'        (ISO с секундами, с таймзоной)
    Возвращаем aware-datetime в Asia/Tashkent.
    """
    if not text:
        return None
    s = text.strip()
    formats = (
        "%Y-%m-%dT%H:%M:%S%z",  # ISO c секундами и TZ (например: 2025-11-11T09:50:00+05:00)
        "%Y-%m-%dT%H:%M%z",     # ISO без секунд и с TZ
        "%Y-%m-%d %H:%M:%S",    # локальное без TZ, с секундами
        "%Y-%m-%d %H:%M",       # локальное без TZ
        "%Y-%m-%d",             # только дата
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            return dt.astimezone(TZ)
        except ValueError:
            continue
    return None


# ---------- календарная математика ----------

def _days_in_month(year: int, month: int) -> int:
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    leap = (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0)
    return 29 if leap else 28


# ---------- категории ----------

def cat_slug(name: str) -> str:
    return name.strip().lower()


def cat_by_slug(slug: str) -> str | None:
    for c in CATEGORIES:
        if cat_slug(c) == slug:
            return c
    return None


# ---------- дефолтный пред-офсет пользователя ----------

async def get_default_pre_offset(user_id: int) -> Optional[int]:
    async with db_conn() as db:
        cur = await db.execute(
            "SELECT default_pre_offset_minutes FROM user_settings WHERE user_id=?",
            (user_id,)
        )
        r = await cur.fetchone()
        return r["default_pre_offset_minutes"] if r and r["default_pre_offset_minutes"] is not None else None


async def set_default_pre_offset(user_id: int, minutes: Optional[int]):
    async with db_conn() as db:
        await db.execute(
            "INSERT INTO user_settings (user_id, default_pre_offset_minutes) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET default_pre_offset_minutes=excluded.default_pre_offset_minutes",
            (user_id, minutes)
        )
        await db.commit()


# ---------- humanize ----------

def _ru_plural(n: int, forms: tuple[str, str, str]) -> str:
    n = abs(n) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return forms[2]
    if 2 <= n1 <= 4:
        return forms[1]
    if n1 == 1:
        return forms[0]
    return forms[2]


def human_rrule(rrule: str | None) -> str:
    if not rrule:
        return "—"
    parsed = parse_rrule(rrule)
    if not parsed:
        return "—"
    freq, interval = parsed
    n = interval
    if freq == "DAILY":
        if n == 1: return "каждый день"
        if n == 2: return "через день"
        return f"каждые {n} {_ru_plural(n, ('день', 'дня', 'дней'))}"
    if freq == "WEEKLY":
        if n == 1: return "каждую неделю"
        return f"каждые {n} {_ru_plural(n, ('неделю', 'недели', 'недель'))}"
    if freq == "MONTHLY":
        if n == 1: return "каждый месяц"
        return f"каждые {n} {_ru_plural(n, ('месяц', 'месяца', 'месяцев'))}"
    return "—"


def human_time_diff_ru(due_dt: datetime, now_dt: datetime) -> str:
    """
    'Осталось до завершения: 7 дней, 5 часов'
    или 'Просрочено на: 1 день, 3 часа'
    Если разница < 1 часа — 'менее часа'.
    """
    delta = due_dt - now_dt
    sign_future = delta.total_seconds() >= 0
    total = abs(int(delta.total_seconds()))
    days = total // 86400
    hours = (total % 86400) // 3600

    if days == 0 and hours == 0:
        return ("Осталось до завершения: менее часа" if sign_future
                else "Просрочено на: менее часа")

    d_part = f"{days} {_ru_plural(days, ('день', 'дня', 'дней'))}" if days else None
    h_part = f"{hours} {_ru_plural(hours, ('час', 'часа', 'часов'))}" if hours else None
    parts = [p for p in (d_part, h_part) if p]

    return (f"Осталось до завершения: {', '.join(parts)}"
            if sign_future else
            f"Просрочено на: {', '.join(parts)}")


# ---------- форматирование карточки задачи ----------

def pretty_task(row: sqlite3.Row) -> str:
    """
    #7 🟡 Тренировка |

    срок: 2025-11-11T09:50:00+05:00 |

    предупредить за: 60 мин |

    повтор: через день |

    🏷 Личное

    Осталось до завершения: 7 дней, 5 часов
    """
    r = dict(row)

    # Заголовок
    mark = "✅" if r.get("is_done") else "🟡"
    title = r.get("title", "")
    header = f"#{r.get('id')} {mark} {title} |"

    # Срок и «сколько осталось»
    due_line = "срок: — |"
    remain_line = None
    if r.get("due_at"):
        dt = parse_local_dt(r["due_at"])
        if dt:
            due_str = dt.isoformat(timespec="seconds")  # ISO с таймзоной
            due_line = f"срок: {due_str} |"
            remain_line = human_time_diff_ru(dt, now_local())
        else:
            due_line = f"срок: {r['due_at']} |"

    # Пред-напоминание
    pre = r.get("pre_offset_minutes")
    pre_line = f"предупредить за: {pre} мин |" if pre is not None else "предупредить за: — |"

    # Повтор (человечно)
    rep_line = f"повтор: {human_rrule(r.get('rrule'))} |"

    # Категория
    cat_line = f"🏷 {r['category']}" if r.get("category") else ""

    blocks = [header, due_line, pre_line, rep_line]
    if cat_line:
        blocks.append(cat_line)
    if remain_line:
        blocks.append(remain_line)

    return "\n\n".join(blocks)
