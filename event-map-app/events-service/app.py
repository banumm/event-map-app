"""
Events Service — ПР2: проектирование и реализация REST API.

Слои:
    api.py   → маршруты (HTTP, статус-коды)
    services.py  → бизнес-логика (фильтры, пагинация, правила)
    storage.py   → хранение (временное in-memory)

Контракт API: openapi.yaml
Описание сущности и операций: docs/api.md
Примеры запросов/ответов: docs/examples.http
"""

from flask import Flask, jsonify

from api import events_bp, register_error_handlers


def create_app():
    app = Flask(__name__)
    app.register_blueprint(events_bp)

    @app.get("/")
    def root():
        return jsonify({
            "service": "events-service",
            "version": "1.0.0",
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
        return jsonify({"status": "ok", "service": "events-service"}), 200

    register_error_handlers(app)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)