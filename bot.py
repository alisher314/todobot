import asyncio
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import BOT_TOKEN, TZ, MORNING_DIGEST_HOUR
from app.db import init_db
from app.router import build_router
from app.scheduler import check_pre_and_due, send_morning_digest

async def main():
    await init_db()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(build_router())

    scheduler = AsyncIOScheduler(timezone=str(TZ))
    scheduler.add_job(check_pre_and_due, "interval", minutes=1, args=[bot], id="reminders", coalesce=True, max_instances=1)
    scheduler.add_job(send_morning_digest, "cron", hour=MORNING_DIGEST_HOUR, minute=0, args=[bot], id="morning_digest", coalesce=True)
    scheduler.start()

    print("Bot is up.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
