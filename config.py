# config.py — все значения берутся из переменных окружения Render (Dashboard → Environment)
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ORGANIZER_CHAT_ID = os.environ.get("ORGANIZER_CHAT_ID", "")

WEBSITE_URL = os.environ.get("WEBSITE_URL", "")

# Прямой URL вебхука Render, например https://your-bot.onrender.com
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")

# Postgres для учёта пользователей (бесплатный, например neon.tech)
# Формат: postgresql://user:password@host/dbname?sslmode=require
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Telegram ID администраторов (через запятую), кому доступна команда /stats
ADMIN_IDS = {
    int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()
}

# Пути к файлам-материалам (лежат в репозитории бота, папка files/)
MINI_COURSE_FILE_PATH = os.environ.get("MINI_COURSE_FILE_PATH", "files/mini_course_materials.pdf")
BUDGET_FREE_FILE_PATH = os.environ.get("BUDGET_FREE_FILE_PATH", "files/budget_free.xlsx")
CONSULTING_FILE_PATH = os.environ.get("CONSULTING_FILE_PATH", "files/consulting_materials.pdf")
