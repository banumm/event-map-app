"""
Attendance Service

Зона ответственности: отметки "пойду / интересно", счётчик участников.
Владеет данными: связи user <-> event, статусы участия.

Изменение данных защищено JWT (users-service). Обычный пользователь может
отмечать только себя, администратор — любого пользователя.
"""

import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from auth import current_user, require_auth
from errors import ApiError, error_response, register_error_handlers
from validation import validate_attendance_payload

app = Flask(__name__)

attendance_db = {}


def _json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(
            400,
            "BadRequest",
            "Тело запроса должно быть JSON-объектом",
        )
    return data


@app.get("/")
def root():
    return jsonify({
        "service": "attendance-service",
        "version": "4.0.0",
        "auth": {
            "type": "JWT Bearer",
            "note": "пользователь отмечает только себя, admin — любого",
        },
        "endpoints": [
            {"method": "GET", "path": "/health"},
            {"method": "POST", "path": "/attendance", "auth": True},
            {"method": "GET", "path": "/attendance/event/{event_id}"},
            {"method": "GET", "path": "/attendance/user/{user_id}", "auth": True},
        ],
    }), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "attendance-service"}), 200


@app.post("/attendance")
@require_auth
def mark_attendance():
    """Отметить участие в мероприятии от имени текущего пользователя."""
    data = _json_body()
    actor = current_user()

    details = validate_attendance_payload(data)
    if details:
        raise ApiError(
            400,
            "ValidationError",
            "Ошибка валидации",
            details,
        )

    user_id = str(actor["sub"])
    requested_user_id = data.get("user_id")
    if requested_user_id is not None and str(requested_user_id) != user_id:
        if actor.get("role") != "admin":
            raise ApiError(
                403,
                "Forbidden",
                "Отмечать участие можно только от своего имени",
                [{"field": "user_id", "message": "недостаточно прав"}],
            )
        user_id = str(requested_user_id)

    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_id": data["event_id"],
        "status": data["status"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    attendance_db[record["id"]] = record
    return jsonify(record), 201


@app.get("/attendance/event/<event_id>")
def get_event_attendance(event_id):
    """Публичный список участников и счётчик по конкретному мероприятию."""
    records = [r for r in attendance_db.values() if r["event_id"] == event_id]
    going_count = len([r for r in records if r["status"] == "going"])
    interested_count = len([r for r in records if r["status"] == "interested"])
    return jsonify({
        "event_id": event_id,
        "going_count": going_count,
        "interested_count": interested_count,
        "records": records,
    }), 200


@app.get("/attendance/user/<user_id>")
@require_auth
def get_user_attendance(user_id):
    """Пользователь видит только свои отметки, admin — любые."""
    actor = current_user()
    if str(actor["sub"]) != str(user_id) and actor.get("role") != "admin":
        return error_response(
            403,
            "Forbidden",
            "Просматривать чужие отметки может только администратор",
            [{"field": "user_id", "message": "недостаточно прав"}],
        )
    records = [r for r in attendance_db.values() if r["user_id"] == str(user_id)]
    return jsonify(records), 200


register_error_handlers(app)


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    app.run(host="0.0.0.0", port=5002, debug=debug)
