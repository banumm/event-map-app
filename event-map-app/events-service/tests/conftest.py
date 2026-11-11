"""Общие фикстуры тестов events-service.

Тесты используют отдельный SQLite-файл `test_events.db`, схема создаётся
миграциями Alembic. Перед каждым тестом таблицы events/event_participants
очищаются, поэтому тесты не зависят от порядка выполнения.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

DB_PATH = SERVICE_ROOT / "test_events.db"
for suffix in ("", "-journal", "-wal", "-shm"):
    candidate = Path(str(DB_PATH) + suffix)
    candidate.unlink(missing_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ISSUER"] = "event-map-users-service"
os.environ["EVENTS_CACHE_TTL_SECONDS"] = "60"
os.environ["EVENTS_CACHE_STALE_SECONDS"] = "300"

subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=SERVICE_ROOT,
    check=True,
    capture_output=True,
)

from sqlalchemy import delete  # noqa: E402

from app import app as flask_app  # noqa: E402
from cache import events_cache  # noqa: E402
from database import db_session  # noqa: E402
from models import Event, EventParticipant  # noqa: E402


@pytest.fixture(scope="session")
def app():
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_database():
    with db_session() as session:
        session.execute(delete(EventParticipant))
        session.execute(delete(Event))
    # Таблицы очищаются в обход сервиса — кэш тоже сбрасываем вручную.
    events_cache.clear()
    yield
