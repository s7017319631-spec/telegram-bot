# app.py — точка входа для Render (gunicorn app:app)
import asyncio
import logging
import threading
import requests
from flask import Flask, request

import config
import bot_handlers
import storage
from telegram import Update

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

_telegram_app = None
_telegram_loop = None
_telegram_lock = threading.Lock()


def _ensure_webhook():
    """Автоматически сообщает Telegram актуальный адрес вебхука.
    На Render free нет Shell, поэтому делаем это сами при каждом холодном
    старте — не нужно вручную запускать set_webhook.py."""
    if not config.WEBHOOK_BASE_URL:
        logger.warning("WEBHOOK_BASE_URL не задан — пропускаю автонастройку вебхука")
        return
    webhook_url = f"{config.WEBHOOK_BASE_URL}/telegram-webhook/{config.BOT_TOKEN}"
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/setWebhook",
            params={"url": webhook_url},
            timeout=10,
        )
        logger.info(f"🔗 Webhook автонастроен: {resp.json()}")
    except Exception as e:
        logger.error(f"❌ Не удалось автоматически установить webhook: {e}", exc_info=True)


def _get_telegram_app():
    global _telegram_app, _telegram_loop
    if _telegram_app is None:
        _telegram_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_telegram_loop)

        try:
            storage.init_db()
        except Exception as e:
            logger.error(f"❌ Не удалось инициализировать БД: {e}", exc_info=True)

        _telegram_app = bot_handlers.build_application()
        _telegram_loop.run_until_complete(_telegram_app.initialize())
        logger.info("✅ Telegram Application инициализирован")

        _ensure_webhook()
    return _telegram_app, _telegram_loop


@app.route(f"/telegram-webhook/{config.BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    application, loop = _get_telegram_app()
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        with _telegram_lock:
            loop.run_until_complete(application.process_update(update))
    except Exception as e:
        logger.error(f"Ошибка обработки апдейта: {e}", exc_info=True)
    return "OK"


@app.route("/")
def health():
    # Render дергает "/" при проверках здоровья — держим лёгкий ответ без обращения к БД
    return {"status": "ok"}


# Инициализируем бота (и регистрируем webhook) СРАЗУ при старте процесса,
# а не при первом входящем запросе — иначе получается замкнутый круг:
# пока webhook не зарегистрирован, Telegram не шлёт POST на /telegram-webhook,
# а значит _get_telegram_app() (и вызов setWebhook внутри неё) никогда не запустится.
try:
    _get_telegram_app()
except Exception as e:
    # Не роняем весь процесс, если Telegram/БД временно недоступны при старте —
    # Flask всё равно поднимется и ответит на "/", а _get_telegram_app()
    # повторится лениво при первом реальном запросе на вебхук.
    logger.error(f"❌ Не удалось инициализировать бота при старте: {e}", exc_info=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
