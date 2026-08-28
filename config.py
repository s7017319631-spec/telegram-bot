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
# Раздельно для ru/kk — бот сам выберет нужный файл по языку пользователя.
# По умолчанию ищем файлы с суффиксами _ru.pdf / _kk.pdf и т.п. — если
# назвали файлы иначе, переопределите через переменные окружения на Render.
MINI_COURSE_FILE_PATH_RU = os.environ.get("MINI_COURSE_FILE_PATH_RU", "files/mini_course_materials_ru.pdf")
MINI_COURSE_FILE_PATH_KK = os.environ.get("MINI_COURSE_FILE_PATH_KK", "files/mini_course_materials_kk.pdf")

BUDGET_FREE_FILE_PATH_RU = os.environ.get("BUDGET_FREE_FILE_PATH_RU", "files/budget_free_ru.xlsx")
BUDGET_FREE_FILE_PATH_KK = os.environ.get("BUDGET_FREE_FILE_PATH_KK", "files/budget_free_kk.xlsx")

CONSULTING_FILE_PATH_RU = os.environ.get("CONSULTING_FILE_PATH_RU", "files/consulting_materials_ru.pdf")
CONSULTING_FILE_PATH_KK = os.environ.get("CONSULTING_FILE_PATH_KK", "files/consulting_materials_kk.pdf")
