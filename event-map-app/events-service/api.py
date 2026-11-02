"""
Слой маршрутов (API).

Только маршрутизация, разбор query-параметров и JSON-тела + статус-коды.
Все бизнес-правила и проверки — внутри EventsService.

Изменение данных защищено JWT: требуется роль organizer или admin;
организатор может менять только свои мероприятия, admin — любые.
"""

from flask import Blueprint, jsonify, request

from auth import current_user, require_auth, require_role
from services import EventsService
from validation import json_body, parse_query_int

events_bp = Blueprint("events", __name__)

service = EventsService()

WRITE_ROLES = ("organizer", "admin")


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
@require_auth
@require_role(*WRITE_ROLES)
def create_event():
    payload = json_body(request)
    event = service.create(payload, current_user())
    return jsonify(event), 201


@events_bp.get("/events/<event_id>")
def get_event(event_id):
    event = service.get(event_id)
    return jsonify(event), 200


@events_bp.put("/events/<event_id>")
@require_auth
@require_role(*WRITE_ROLES)
def replace_event(event_id):
    payload = json_body(request)
    event = service.replace(event_id, payload, current_user())
    return jsonify(event), 200


@events_bp.patch("/events/<event_id>")
@require_auth
@require_role(*WRITE_ROLES)
def patch_event(event_id):
    patch = json_body(request)
    event = service.patch(event_id, patch, current_user())
    return jsonify(event), 200


@events_bp.delete("/events/<event_id>")
@require_auth
@require_role(*WRITE_ROLES)
def delete_event(event_id):
    service.delete(event_id, current_user())
    return "", 204
