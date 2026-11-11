"""Общие фикстуры тестов attendance-service."""

import os
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ISSUER", "event-map-users-service")
# Интеграция с events-service в тестах по умолчанию выключена;
# отдельные тесты включают её через monkeypatch.
os.environ.pop("EVENTS_SERVICE_URL", None)

from app import app as flask_app, attendance_db  # noqa: E402


@pytest.fixture(scope="session")
def app():
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_storage():
    attendance_db.clear()
    yield
    attendance_db.clear()
