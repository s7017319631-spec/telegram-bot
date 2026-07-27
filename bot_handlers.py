# bot_handlers.py
import logging
import time
import asyncio
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import config
import storage

logger = logging.getLogger(__name__)

user_language = {}

# Какие документы отдаём за какое действие. Список — можно прикреплять
# сколько угодно файлов на категорию, все уйдут пользователю один за другим.
DOCS = {
    "mini_course": {
        "files": [
            {
                "path": config.MINI_COURSE_FILE_PATH,
                "caption_ru": "🎯 Материалы мини-курса «Как вести личный и семейный бюджет»",
                "caption_kk": "🎯 «Жеке және отбасылық бюджет» мини-курсының материалдары",
            },
            {
                "path": config.BUDGET_FREE_FILE_PATH,
                "caption_ru": "📊 Бесплатный шаблон личного бюджета (Excel)",
                "caption_kk": "📊 Жеке бюджеттің тегін үлгісі (Excel)",
            },
        ],
    },
    "consulting": {
        "files": [
            {
                "path": config.CONSULTING_FILE_PATH,
                "caption_ru": "💼 Материалы по консультационным услугам",
                "caption_kk": "💼 Консультациялық қызметтер бойынша материалдар",
            },
        ],
    },
}

# Подписи действий для уведомления организатору и /stats
ACTION_LABELS = {
    "mini_course": "Мини-курс (бесплатно)",
    "consulting": "Консультация",
    "paid_course": "Основной курс (платный, интерес)",
}

# Кэш file_id — чтобы не заливать один и тот же файл в Telegram повторно.
# Живёт, пока жив процесс; после холодного старта Render просто зальётся 1 раз заново.
_file_id_cache = {}


def get_text(key: str, lang: str = "kk") -> str:
    texts = {
        "start_ru": "Здравствуйте! 👋\nЯ — помощник по финансовой грамотности.\n\nЧем могу помочь?",
        "start_kk": "Сәлеметсіз бе! 👋\nМен — қаржылық сауаттылық бойынша көмекшімін.\n\nНе істеуге көмектесе аламын?",
        "choose_lang": "Тілді таңдаңыз/Выберите язык:",
        "course_btn_ru": "1️⃣ Хочу изучить курс",
        "course_btn_kk": "1️⃣ Курсты үйренгім келеді",
        "consulting_btn_ru": "2️⃣ Нужна консультация/услуга",
        "consulting_btn_kk": "2️⃣ Консультация/қызмет қажет",
        "site_btn_ru": "3️⃣ Сайт",
        "site_btn_kk": "3️⃣ Сайт",
        "paid_course_btn_ru": "4️⃣ Хочу основной курс (платный)",
        "paid_course_btn_kk": "4️⃣ Негізгі курсты қалаймын (ақылы)",
        "ask_phone_ru": "Чтобы отправить материалы, поделитесь, пожалуйста, номером телефона:",
        "ask_phone_kk": "Материалдарды жіберу үшін телефон нөміріңізбен бөлісіңізші:",
        "share_contact_ru": "📱 Отправить номер телефона",
        "share_contact_kk": "📱 Телефон нөмірін жіберу",
        "thanks_ru": "Спасибо! Отправляю материалы 👇",
        "thanks_kk": "Рақмет! Материалдарды жіберемін 👇",
        "paid_course_thanks_ru": (
            "Спасибо за интерес к основному курсу! 🎓\n"
            "Наш менеджер свяжется с вами по этому номеру, чтобы рассказать про формат и стоимость.\n\n"
            "А пока — небольшой бесплатный материал в подарок 👇"
        ),
        "paid_course_thanks_kk": (
            "Негізгі курсқа қызығушылық танытқаныңызға рақмет! 🎓\n"
            "Менеджеріміз осы нөмір бойынша хабарласып, форматы мен құны туралы айтады.\n\n"
            "Ал әзірге — сыйлыққа шағын тегін материал 👇"
        ),
        "need_contact_first_ru": "Сначала нажмите одну из кнопок меню, затем поделитесь номером.",
        "need_contact_first_kk": "Алдымен мәзір батырмаларының бірін басыңыз, содан кейін нөмірмен бөлісіңіз.",
    }
    return texts.get(f"{key}_{lang}", texts.get(f"{key}_kk", key))


async def safe_call(coro_func, *args, retries: int = 3, delay: float = 2.0, **kwargs):
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except (NetworkError, TimedOut) as e:
            last_exc = e
            logger.warning(f"Telegram API: попытка {attempt}/{retries} не удалась: {e}")
            if attempt < retries:
                await asyncio.sleep(delay)
    logger.error(f"Telegram API: все {retries} попытки исчерпаны: {last_exc}")
    return None


# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_language[user_id] = "kk"

    keyboard = [
        [InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kk")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
    ]
    await safe_call(
        update.message.reply_text,
        get_text("choose_lang"), reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_main_menu(query, lang: str):
    keyboard = [
        [InlineKeyboardButton(get_text("course_btn", lang), callback_data="request_mini_course")],
        [InlineKeyboardButton(get_text("consulting_btn", lang), callback_data="request_consulting")],
        [InlineKeyboardButton(get_text("paid_course_btn", lang), callback_data="request_paid_course")],
        [InlineKeyboardButton(get_text("site_btn", lang), url=config.WEBSITE_URL)],
    ]
    await safe_call(
        query.edit_message_text,
        get_text("start", lang), reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- Кнопки главного меню ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await safe_call(query.answer)
    user_id = query.from_user.id
    data = query.data

    try:
        if data.startswith("lang_"):
            lang = data.split("_")[1]
            user_language[user_id] = lang
            await show_main_menu(query, lang)
            return

        lang = user_language.get(user_id, "kk")

        if data == "menu":
            await show_main_menu(query, lang)

        elif data in ("request_mini_course", "request_consulting", "request_paid_course"):
            doc_key = {
                "request_mini_course": "mini_course",
                "request_consulting": "consulting",
                "request_paid_course": "paid_course",
            }[data]
            # запоминаем, какое действие обрабатывать после получения контакта
            context.user_data["pending_doc"] = doc_key

            contact_keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton(get_text("share_contact", lang), request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            await safe_call(
                context.bot.send_message,
                chat_id=query.message.chat_id,
                text=get_text("ask_phone", lang),
                reply_markup=contact_keyboard,
            )

    except Exception as e:
        logger.error(f"Ошибка в button: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id, text="⚠️ Ошибка. Попробуйте /start"
            )
        except Exception:
            pass


# --- Получение контакта → выдача документа ---
async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = user_language.get(user.id, "kk")
    contact = update.message.contact
    doc_key = context.user_data.get("pending_doc")

    if not doc_key:
        await safe_call(
            update.message.reply_text,
            get_text("need_contact_first", lang),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "—"
    phone = contact.phone_number

    # 1) сохраняем пользователя в БД (переживает рестарты Render)
    try:
        storage.upsert_user(
            telegram_id=user.id,
            full_name=full_name,
            username=user.username or "",
            phone=phone,
            lang=lang,
        )
        storage.log_delivery(user.id, doc_key)
    except Exception as e:
        logger.error(f"Ошибка записи в БД: {e}", exc_info=True)

    # 2) убираем клавиатуру, благодарим (для платного курса — отдельный текст)
    thanks_key = "paid_course_thanks" if doc_key == "paid_course" else "thanks"
    await safe_call(
        update.message.reply_text,
        get_text(thanks_key, lang),
        reply_markup=ReplyKeyboardRemove(),
    )

    # 3) отправляем документ:
    #    - для мини-курса/консультации — соответствующий файл
    #    - для платного курса своего файла нет — дарим бесплатный мини-курс материал как бонус
    send_key = "mini_course" if doc_key == "paid_course" else doc_key
    await send_document_cached(context, update.message.chat_id, send_key, lang)

    # 4) уведомляем организатора
    await notify_organizer(context, user, phone, doc_key)

    context.user_data.pop("pending_doc", None)


async def send_document_cached(context: ContextTypes.DEFAULT_TYPE, chat_id: int, doc_key: str, lang: str):
    """Отправляет ВСЕ файлы категории, используя кэш file_id на каждый
    (эффективно — без повторной загрузки на Render при повторных заявках)."""
    doc_info = DOCS[doc_key]

    for file_info in doc_info["files"]:
        path = file_info["path"]
        caption = file_info.get(f"caption_{lang}", file_info.get("caption_ru"))

        cached_file_id = _file_id_cache.get(path)
        if cached_file_id:
            msg = await safe_call(
                context.bot.send_document,
                chat_id=chat_id, document=cached_file_id, caption=caption,
            )
            if msg:
                continue

        # первая отправка (или кэш пуст после рестарта) — грузим файл с диска один раз
        if not os.path.exists(path):
            logger.error(f"Файл не найден: {path}")
            await safe_call(context.bot.send_message, chat_id=chat_id, text="⚠️ Один из файлов временно недоступен, мы уже разбираемся.")
            continue

        with open(path, "rb") as f:
            msg = await safe_call(
                context.bot.send_document,
                chat_id=chat_id, document=f, caption=caption,
            )
        if msg and msg.document:
            _file_id_cache[path] = msg.document.file_id
            logger.info(f"📎 file_id для {path} закэширован")


async def notify_organizer(context: ContextTypes.DEFAULT_TYPE, user, phone: str, doc_key: str):
    try:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "—"
        username = user.username or "—"
        action = ACTION_LABELS.get(doc_key, doc_key)

        text = (
            "✅ <b>Новая заявка!</b>\n\n"
            f"👤 {full_name}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"🔗 @{username}\n"
            f"📞 {phone}\n"
            f"📝 Действие: {action}\n"
            f"⏰ {time.strftime('%d %b %Y, %H:%M')}"
        )
        await safe_call(
            context.bot.send_message,
            chat_id=config.ORGANIZER_CHAT_ID, text=text, parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления: {e}", exc_info=True)


# --- Админ-команда: количество и список пользователей ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in config.ADMIN_IDS:
        return  # молча игнорируем не-админов

    try:
        total = storage.count_users()
        by_doc = storage.count_deliveries_by_type()
        recent = storage.recent_users(limit=10)

        lines = [f"👥 Всего пользователей: <b>{total}</b>", ""]
        if by_doc:
            lines.append("📎 Заявки по категориям:")
            for doc_type, cnt in by_doc:
                label = ACTION_LABELS.get(doc_type, doc_type)
                lines.append(f"  • {label}: {cnt}")
            lines.append("")

        lines.append("🕐 Последние 10:")
        for u in recent:
            name = u["full_name"] or "—"
            uname = f"@{u['username']}" if u["username"] else "—"
            phone = u["phone"] or "—"
            lines.append(f"  • {name} ({uname}), {phone} — {u['first_seen']:%d.%m.%Y %H:%M}")

        await safe_call(update.message.reply_text, "\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка /stats: {e}", exc_info=True)
        await safe_call(update.message.reply_text, f"⚠️ Ошибка: {e}")


def build_application() -> Application:
    if not config.BOT_TOKEN.strip():
        raise ValueError("BOT_TOKEN не задан (переменные окружения Render)!")

    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .connect_timeout(20)
        .read_timeout(20)
        .write_timeout(20)
        .pool_timeout(10)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.CONTACT, contact_received))
    return application
