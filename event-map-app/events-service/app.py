"""
Events Service — REST API мероприятий (ПР2–ПР7).

Слои:
    api.py   → маршруты (HTTP, статус-коды)
    services.py  → бизнес-логика (валидация, пагинация, фильтры)
    repository/  → слой доступа к данным (DAO, по модулю на сущность)
    database.py  → движок/сессии, строка подключения из DATABASE_URL
    models.py    → ORM-модели (схема создаётся миграциями Alembic)

Кэш (ПР6): cache.py — TTL-кэш GET /events и GET /events/{id}
Наблюдаемость (ПР7): observability.py — JSON-логи, X-Request-ID, /metrics

Миграции: alembic upgrade head   (см. alembic/versions/)
Контракт API: openapi.yaml
Схема БД: docs/db_schema.md, docs/er-diagram.svg
"""

import logging
import os

from flask import Flask, jsonify

import observability
from api import events_bp
from cache import events_cache
from database import check_database, connect_and_log
from errors import register_error_handlers
from services import seed_categories

SERVICE_NAME = "events-service"
VERSION = "5.0.0"

observability.configure_logging(SERVICE_NAME, os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(SERVICE_NAME)


def create_app():
    app = Flask(__name__)
    observability.init_app(app, SERVICE_NAME)
    app.register_blueprint(events_bp)

    # Явное подключение к БД при старте (ПР3). Если база ещё недоступна,
    # процесс не падает: /health вернёт 503, а запросы — понятную ошибку.
    try:
        backend, url = connect_and_log()
        logger.info("database connected", extra={"event": "db.connected", "backend": backend, "url": url})
        seed_categories()
        logger.info("categories seeded", extra={"event": "db.seeded"})
    except Exception as exc:  # noqa: BLE001
        backend = "unknown"
        logger.error("database unavailable at startup",
                     extra={"event": "db.unavailable", "error": str(exc).splitlines()[0][:200]})

    @app.get("/")
    def root():
        return jsonify({
            "service": SERVICE_NAME,
            "version": VERSION,
            "database": backend,
            "cache": {"type": "in-memory TTL", "ttl_seconds": events_cache.ttl,
                      "stale_seconds": events_cache.stale},
            "auth": {
                "type": "JWT Bearer",
                "write_roles": ["organizer", "admin"],
                "note": "организатор меняет только свои события, admin — любые",
            },
            "endpoints": [
                {"method": "GET", "path": "/"},
                {"method": "GET", "path": "/health"},
                {"method": "GET", "path": "/metrics"},
                {"method": "GET", "path": "/events", "cached": True},
                {"method": "POST", "path": "/events", "auth": True},
                {"method": "GET", "path": "/events/{id}", "cached": True},
                {"method": "PUT", "path": "/events/{id}", "auth": True},
                {"method": "PATCH", "path": "/events/{id}", "auth": True},
                {"method": "DELETE", "path": "/events/{id}", "auth": True},
            ],
        }), 200

    @app.get("/health")
    def health():
        """Отражает реальное состояние: процесс жив И база данных отвечает (ПР7)."""
        db_ok, db_error = check_database()
        body = {
            "status": "ok" if db_ok else "unavailable",
            "service": SERVICE_NAME,
            "version": VERSION,
            "checks": {"database": {"status": "ok" if db_ok else "error"}},
        }
        if not db_ok:
            body["checks"]["database"]["error"] = db_error
            logger.warning("health check failed", extra={"event": "health.fail", "dependency": "database"})
        return jsonify(body), 200 if db_ok else 503

    register_error_handlers(app)
    return app


app = create_app()

if __name__ == "__main__":
    # Только для локальной разработки; в контейнере запускается gunicorn.
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5001")), debug=debug)
