from datetime import datetime, timedelta
from .config import TZ, DEFAULT_DUE_HOUR, DEFAULT_DUE_MINUTE
from .utils import now_local

def make_due_today() -> datetime:
    now = now_local()
    return datetime(now.year, now.month, now.day, DEFAULT_DUE_HOUR, DEFAULT_DUE_MINUTE, tzinfo=TZ)

def make_due_tomorrow() -> datetime:
    return make_due_today() + timedelta(days=1)

def make_due_this_week() -> datetime:
    # Пн(0)..Вс(6) → ставим на воскресенье 18:00 текущей недели
    today = now_local().date()
    weekday = today.weekday()
    days_to_sun = 6 - weekday
    target = today + timedelta(days=days_to_sun)
    return datetime(target.year, target.month, target.day, DEFAULT_DUE_HOUR, DEFAULT_DUE_MINUTE, tzinfo=TZ)
