from aiogram import Bot
from .db import db_conn
from .utils import now_local, to_iso, parse_local_dt, pretty_task
from .models import next_occurrence
from .keyboards import inline_task_actions
from .config import TZ
from datetime import datetime, timedelta

async def check_pre_and_due(bot: Bot):
    now = now_local().replace(second=0, microsecond=0)
    now_iso = to_iso(now)

    async with db_conn() as db:
        # Пред-напоминания
        cur = await db.execute(
            "SELECT t.*, "
            "(CASE WHEN t.pre_offset_minutes IS NOT NULL THEN t.pre_offset_minutes "
            " ELSE us.default_pre_offset_minutes END) AS eff_pre "
            "FROM tasks t LEFT JOIN user_settings us ON us.user_id=t.user_id "
            "WHERE t.is_done=0 AND t.due_at IS NOT NULL AND t.pre_reminded_at IS NULL"
        )
        rows = await cur.fetchall()
        for r in rows:
            due = parse_local_dt(r["due_at"])
            if not due:
                continue
            eff_pre = r["eff_pre"]
            if eff_pre is None or eff_pre <= 0:
                continue
            pre_time = due - timedelta(minutes=int(eff_pre))
            if now >= pre_time:
                try:
                    await bot.send_message(
                        r["user_id"],
                        f"🔔 Пред-напоминание: задача #{r['id']} — «{r['title']}»\n"
                        f"Срок: {r['due_at']} (за {int(eff_pre)} мин)",
                        reply_markup=inline_task_actions(r["id"])
                    )
                except Exception:
                    pass
                await db.execute("UPDATE tasks SET pre_reminded_at=? WHERE id=?", (now_iso, r["id"]))
        await db.commit()

        # Основные напоминания
        cur = await db.execute(
            "SELECT * FROM tasks WHERE is_done=0 AND due_at IS NOT NULL AND reminded_at IS NULL AND due_at <= ?",
            (now_iso,)
        )
        rows = await cur.fetchall()
        for r in rows:
            try:
                await bot.send_message(
                    r["user_id"],
                    f"⏰ Напоминание: срок задачи #{r['id']} — «{r['title']}» наступил.\nСрок: {r['due_at']}",
                    reply_markup=inline_task_actions(r["id"])
                )
            except Exception:
                pass

            if r["rrule"] and r["due_at"]:
                due = parse_local_dt(r["due_at"])
                nxt = due
                safety = 0
                while nxt is not None and nxt <= now and safety < 1000:
                    nxt = next_occurrence(nxt, r["rrule"])
                    safety += 1
                if nxt and nxt > now:
                    await db.execute(
                        "UPDATE tasks SET due_at=?, reminded_at=NULL, pre_reminded_at=NULL WHERE id=?",
                        (to_iso(nxt), r["id"])
                    )
                else:
                    await db.execute("UPDATE tasks SET reminded_at=? WHERE id=?", (now_iso, r["id"]))
            else:
                await db.execute("UPDATE tasks SET reminded_at=? WHERE id=?", (now_iso, r["id"]))
        await db.commit()

async def send_morning_digest(bot: Bot):
    from .config import TZ
    today = now_local().date()
    start = datetime(today.year, today.month, today.day, 0, 0, tzinfo=TZ)
    end = start + timedelta(days=1)

    async with db_conn() as db:
        cur = await db.execute("SELECT DISTINCT user_id FROM tasks WHERE is_done=0")
        users = [r["user_id"] for r in await cur.fetchall()]
        for uid in users:
            cur1 = await db.execute(
                "SELECT * FROM tasks WHERE user_id=? AND is_done=0 AND due_at IS NOT NULL AND due_at < ? "
                "ORDER BY due_at ASC",
                (uid, to_iso(start))
            )
            overdue = await cur1.fetchall()
            cur2 = await db.execute(
                "SELECT * FROM tasks WHERE user_id=? AND is_done=0 AND due_at IS NOT NULL AND due_at >= ? AND due_at < ? "
                "ORDER BY due_at ASC",
                (uid, to_iso(start), to_iso(end))
            )
            today_rows = await cur2.fetchall()

            if not overdue and not today_rows:
                continue

            lines = []
            if overdue:
                lines.append("❗ Просроченные:")
                lines += [f"— {pretty_task(r)}" for r in overdue]
            if today_rows:
                if lines:
                    lines.append("")
                lines.append("📅 Сегодня:")
                lines += [f"— {pretty_task(r)}" for r in today_rows]

            try:
                await bot.send_message(uid, "Утренняя сводка задач:\n" + "\n".join(lines))
            except Exception:
                pass
