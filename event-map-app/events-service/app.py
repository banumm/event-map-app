"""
Events Service — ПР3: реляционная база данных, миграции и слой доступа к данным.

Слои:
    api.py   → маршруты (HTTP, статус-коды)
    services.py  → бизнес-логика (валидация, пагинация, фильтры)
    repository/  → слой доступа к данным (DAO, по модулю на сущность)
    database.py  → движок/сессии, строка подключения из DATABASE_URL
    models.py    → ORM-модели (схема создаётся миграциями Alembic)

Миграции: alembic upgrade head   (см. alembic/versions/)
Контракт API: openapi.yaml
Схема БД: docs/db_schema.md, docs/er-diagram.svg
"""

import logging

from flask import Flask, jsonify

from api import events_bp, register_error_handlers
from database import connect_and_log
from services import seed_categories

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("events-service")


def create_app():
    app = Flask(__name__)
    app.register_blueprint(events_bp)

    # Явное подключение к БД при старте (требование ПР3)
    backend, url = connect_and_log()
    logger.info("Подключение к БД успешно: backend=%s url=%s", backend, url)
    logger.info("Категории подготовлены (сид)")
    seed_categories()

    @app.get("/")
    def root():
        return jsonify({
            "service": "events-service",
            "version": "3.0.0",
            "database": backend,
            "endpoints": [
                {"method": "GET", "path": "/"},
                {"method": "GET", "path": "/health"},
                {"method": "GET", "path": "/events"},
                {"method": "POST", "path": "/events"},
                {"method": "GET", "path": "/events/{id}"},
                {"method": "PUT", "path": "/events/{id}"},
                {"method": "PATCH", "path": "/events/{id}"},
                {"method": "DELETE", "path": "/events/{id}"},
            ],
        }), 200

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "events-service", "database": backend}), 200

    register_error_handlers(app)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)