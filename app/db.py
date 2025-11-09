import sqlite3
import aiosqlite
from contextlib import asynccontextmanager
from .config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT,
            due_at TEXT,                 -- ISO 8601 в локальном TZ
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            reminded_at TEXT,            -- признак отправленного основного напоминания
            pre_offset_minutes INTEGER,  -- индивидуальный пред-офсет (NULL => дефолт юзера)
            pre_reminded_at TEXT,        -- отправлено пред-напоминание
            rrule TEXT                   -- FREQ=DAILY|WEEKLY|MONTHLY;INTERVAL=n
        );
        """)
        # Миграции на случай старых БД: оборачиваем в try
        for alter in [
            "ALTER TABLE tasks ADD COLUMN reminded_at TEXT;",
            "ALTER TABLE tasks ADD COLUMN pre_offset_minutes INTEGER;",
            "ALTER TABLE tasks ADD COLUMN pre_reminded_at TEXT;",
            "ALTER TABLE tasks ADD COLUMN rrule TEXT;",
            "ALTER TABLE tasks ADD COLUMN category TEXT;"
        ]:
            try:
                await db.execute(alter)
            except Exception:
                pass

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            default_pre_offset_minutes INTEGER
        );
        """)
        await db.commit()

@asynccontextmanager
async def db_conn():
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        await conn.close()
