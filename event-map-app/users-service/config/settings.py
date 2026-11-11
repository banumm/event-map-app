"""
Users Service — конфигурация Django.

Зона ответственности: регистрация, логин, профиль, роли (user / organizer / admin),
выдача JWT. Владеет данными: users, roles.

Пароли хранятся только в виде хэша Argon2 (PASSWORD_HASHERS).
JWT подписывается общим секретом JWT_SECRET: тот же секрет проверяют
events-service и attendance-service.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_bool(name, default="0"):
    return os.environ.get(name, default).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")

DEBUG = _env_bool("DJANGO_DEBUG", "0")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
]

MIDDLEWARE = [
    # Первым: видит итоговый статус ответа, в т.ч. сформированный обработчиком ошибок.
    "accounts.observability.ObservabilityMiddleware",
    "accounts.middleware.UnifiedErrorMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

def _database_from_url(url):
    """
    DATABASE_URL → настройки Django (ПР7). Поддерживаются:
        postgresql://user:password@host:5432/dbname
        sqlite:///absolute/path.db   (или пусто — локальный db.sqlite3)
    """
    if not url or url.startswith("sqlite"):
        path = url.split("sqlite:///", 1)[1] if url and "sqlite:///" in url else ""
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": path or BASE_DIR / "db.sqlite3"}
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise ValueError(f"Неподдерживаемая схема DATABASE_URL: {parsed.scheme}")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        # Явный тайм-аут: /health и запросы не зависают при остановленной БД.
        "OPTIONS": {"connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "3"))},
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


DATABASES = {"default": _database_from_url(os.environ.get("DATABASE_URL", ""))}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_USER_MODEL = "accounts.User"

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-jwt-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "event-map-users-service")
JWT_EXPIRES_MINUTES = int(os.environ.get("JWT_EXPIRES_MINUTES", "60"))

# Ограничение частоты запросов на /auth/login и /auth/register.
AUTH_RATE_LIMIT = int(os.environ.get("AUTH_RATE_LIMIT", "10"))
AUTH_RATE_WINDOW_SECONDS = int(os.environ.get("AUTH_RATE_WINDOW_SECONDS", "60"))

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Структурированные логи в stdout (ПР7): одна JSON-строка на событие.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "accounts.observability.JsonFormatter"}},
    "handlers": {"stdout": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["stdout"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {
        # access-лог пишет ObservabilityMiddleware; стандартный django.server/request
        # оставляем только для предупреждений и ошибок.
        "django.server": {"level": "WARNING"},
        "django.request": {"level": "ERROR"},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
