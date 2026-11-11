"""
Слой доступа к базе данных (соединение и сессии).

Строка подключения задаётся ТОЛЬКО через переменную окружения DATABASE_URL
(см. .env.example). По умолчанию — SQLite-файл events.db в каталоге сервиса;
тот же код работает с PostgreSQL: DATABASE_URL=postgresql+psycopg2://...
"""

import os
from contextlib import contextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from observability import metrics

load_dotenv()

DEFAULT_DATABASE_URL = "sqlite:///./events.db"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "3"))


def _connect_args(url):
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if url.startswith("postgresql"):
        # Явный тайм-аут: при остановленной БД запрос и /health не зависают.
        return {"connect_timeout": DB_CONNECT_TIMEOUT}
    return {}


engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args(DATABASE_URL),
    # Проверка соединения перед выдачей из пула: после перезапуска БД
    # «мёртвые» соединения отбрасываются, а не приводят к ошибке запроса.
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

@event.listens_for(engine, "before_cursor_execute")
def _count_queries(conn, cursor, statement, parameters, context, executemany):
    # Метрика db_queries_total доказывает, что попадание в кэш не идёт в БД.
    metrics.inc("db_queries_total", help_text="SQL-запросы к базе данных")


if engine.url.get_backend_name() == "sqlite":

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        # SQLite по умолчанию не проверяет внешние ключи — включаем принудительно.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def utcnow():
    """Наивное UTC-время (хранение без timezone для простоты в SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_iso(dt):
    """Сериализация datetime в ISO 8601 с суффиксом Z (формат API из ПР2)."""
    return dt.replace(tzinfo=timezone.utc).isoformat(timespec="seconds") if dt else None


def from_iso(value):
    """Парсинг ISO 8601 (с Z/+00:00) в наивное UTC-время БД."""
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@contextmanager
def db_session(commit=True):
    """
    Единица работы (Unit of Work): сессия-транзакция.

    Все обращения к БД выполняются внутри этого контекста. При успехе —
    commit, при любой ошибке — rollback, затем сессия закрывается.
    Nested-сценарии управляют транзакцией явно (verify_tx.py).
    """
    session = SessionLocal()
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def connect_and_log():
    """Проверяет соединение и явно логирует результат (требование ПР3)."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    backend = engine.url.get_backend_name()
    url = engine.url.render_as_string(hide_password=True)
    return backend, url


def check_database():
    """Проверка доступности БД для /health: (ok, текст ошибки или None)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001 — /health не должен падать
        return False, str(getattr(exc, "orig", None) or exc).splitlines()[0][:200]
