import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Добавьте BOT_TOKEN в .env")

TZ = ZoneInfo("Asia/Tashkent")
DB_PATH = "tasks.db"

# Время ежедневной сводки
MORNING_DIGEST_HOUR = 9  # 09:00 Asia/Tashkent

# Пресеты быстрых сроков
DEFAULT_DUE_HOUR = 18
DEFAULT_DUE_MINUTE = 0

# Категории по умолчанию
CATEGORIES = ["Работа", "Личное", "Учёба", "Здоровье", "Семья", "Проект"]
