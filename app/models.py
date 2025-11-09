from datetime import datetime, timedelta
from typing import Optional

def parse_rrule(text: str) -> Optional[tuple[str, int]]:
    if not text:
        return None
    parts = {}
    for piece in text.split(";"):
        if "=" in piece:
            k, v = piece.split("=", 1)
            parts[k.strip().upper()] = v.strip().upper()
    freq = parts.get("FREQ")
    if freq not in {"DAILY", "WEEKLY", "MONTHLY"}:
        return None
    interval = int(parts.get("INTERVAL", "1"))
    return (freq, max(1, interval))

def next_occurrence(due: datetime, rrule: str) -> Optional[datetime]:
    parsed = parse_rrule(rrule)
    if not parsed:
        return None
    freq, interval = parsed
    if freq == "DAILY":
        return due + timedelta(days=interval)
    if freq == "WEEKLY":
        return due + timedelta(weeks=interval)
    if freq == "MONTHLY":
        # упрощённый месяц = 30 дней
        return due + timedelta(days=30 * interval)
    return None
