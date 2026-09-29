"""
Слой маршрутов (API).

Только маршрутизация, разбор query-параметров и JSON-тела + статус-коды.
Все бизнес-правила и проверки — внутри EventsService.
"""

from flask import Blueprint, Flask, jsonify, request

from services import EventNotFoundError, EventsService, ValidationFailedError
from validation import json_body, parse_query_int

events_bp = Blueprint("events", __name__)

service = EventsService()


@events_bp.get("/events")
def list_events():
    result = service.list(
        page=parse_query_int("page", request.args.get("page")),
        limit=parse_query_int("limit", request.args.get("limit")),
        category=request.args.get("category"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
    )
    return jsonify(result), 200


@events_bp.post("/events")
def create_event():
    payload = json_body(request)
    event = service.create(payload)
    return jsonify(event), 201


@events_bp.get("/events/<event_id>")
def get_event(event_id):
    event = service.get(event_id)
    return jsonify(event), 200


@events_bp.put("/events/<event_id>")
def replace_event(event_id):
    payload = json_body(request)
    event = service.replace(event_id, payload)
    return jsonify(event), 200


@events_bp.patch("/events/<event_id>")
def patch_event(event_id):
    patch = json_body(request)
    event = service.patch(event_id, patch)
    return jsonify(event), 200


@events_bp.delete("/events/<event_id>")
def delete_event(event_id):
    service.delete(event_id)
    return "", 204

# ---- обработчики ошибок в едином формате ----


def register_error_handlers(app: Flask):
    @app.errorhandler(ValidationFailedError)
    def handle_validation(err):
        return jsonify({"error": "ValidationError", "details": err.details}), 400

    @app.errorhandler(EventNotFoundError)
    def handle_not_found(err):
        return jsonify({
            "error": "NotFound",
            "details": [{"field": "id", "message": f"событие {err.args[0]} не найдено"}],
        }), 404

    @app.errorhandler(400)
    def handle_bad_request(err):
        return jsonify({
            "error": "BadRequest",
            "details": [{"field": None, "message": err.description or "некорректный запрос"}],
        }), 400

    @app.errorhandler(405)
    def handle_method_not_allowed(err):
        return jsonify({
            "error": "MethodNotAllowed",
            "details": [{"field": None, "message": "метод не поддерживается для этого ресурса"}],
        }), 405

    @app.errorhandler(404)
    def handle_route_not_found(err):
        return jsonify({
            "error": "NotFound",
            "details": [{"field": None, "message": "ресурс не существует"}],
        }), 404

    @app.errorhandler(Exception)
    def handle_internal(err):
        app.logger.exception("unhandled error")
        return jsonify({"error": "InternalServerError", "details": []}), 500