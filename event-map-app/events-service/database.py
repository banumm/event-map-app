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
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DEFAULT_DATABASE_URL = "sqlite:///./events.db"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

if engine.url.get_backend_name() == "sqlite":
    from sqlalchemy import event

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