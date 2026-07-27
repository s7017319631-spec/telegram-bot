# storage.py — учёт пользователей и выдач документов в постоянной БД (Postgres)
# Render free не даёт постоянного диска, поэтому локальный SQLite/JSON
# теряются при каждом деплое/перезапуске. Внешний Postgres (например,
# бесплатный neon.tech) переживает рестарты и общий для всех воркеров.

import logging
from contextlib import contextmanager
import psycopg2
import psycopg2.extras
import config

logger = logging.getLogger(__name__)


@contextmanager
def get_conn():
    conn = psycopg2.connect(config.DATABASE_URL, sslmode="require")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Создаёт таблицы, если их ещё нет. Вызывается один раз при старте."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    full_name   TEXT,
                    username    TEXT,
                    phone       TEXT,
                    lang        TEXT,
                    first_seen  TIMESTAMPTZ DEFAULT now(),
                    last_action TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS deliveries (
                    id             SERIAL PRIMARY KEY,
                    telegram_id    BIGINT REFERENCES users(telegram_id),
                    document_type  TEXT,
                    sent_at        TIMESTAMPTZ DEFAULT now()
                );
            """)
    logger.info("✅ Таблицы БД проверены/созданы")


def upsert_user(telegram_id: int, full_name: str, username: str, phone: str = None, lang: str = None):
    """Создаёт пользователя или обновляет его данные при повторном визите."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (telegram_id, full_name, username, phone, lang)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    full_name   = EXCLUDED.full_name,
                    username    = EXCLUDED.username,
                    phone       = COALESCE(EXCLUDED.phone, users.phone),
                    lang        = COALESCE(EXCLUDED.lang, users.lang),
                    last_action = now();
            """, (telegram_id, full_name, username, phone, lang))


def log_delivery(telegram_id: int, document_type: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO deliveries (telegram_id, document_type)
                VALUES (%s, %s);
            """, (telegram_id, document_type))


def count_users() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            return cur.fetchone()[0]


def count_deliveries_by_type():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT document_type, COUNT(*) FROM deliveries GROUP BY document_type;")
            return cur.fetchall()


def recent_users(limit: int = 20):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT telegram_id, full_name, username, phone, first_seen
                FROM users
                ORDER BY first_seen DESC
                LIMIT %s;
            """, (limit,))
            return cur.fetchall()
