"""
Attendance Service
Зона ответственности: отметки "пойду / интересно", счётчик участников, напоминания.
Владеет данными: связи user <-> event, статусы участия.
"""

from flask import Flask, jsonify, request
from datetime import datetime
import uuid

app = Flask(__name__)

# Временное in-memory хранилище (в реальном проекте — БД, например PostgreSQL)
attendance_db = {}

ALLOWED_STATUSES = {"going", "interested", "cancelled"}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "attendance-service"}), 200


@app.route("/attendance", methods=["POST"])
def mark_attendance():
    """
    Отметить участие в мероприятии.
    В реальной реализации здесь должен быть внутренний вызов к Events Service,
    чтобы убедиться, что событие существует и ещё не прошло.
    """
    data = request.get_json(force=True)

    required_fields = ["user_id", "event_id", "status"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    if data["status"] not in ALLOWED_STATUSES:
        return jsonify({"error": f"status must be one of {ALLOWED_STATUSES}"}), 400

    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "user_id": data["user_id"],
        "event_id": data["event_id"],
        "status": data["status"],
        "created_at": datetime.utcnow().isoformat(),
    }
    attendance_db[record_id] = record
    return jsonify(record), 201


@app.route("/attendance/event/<event_id>", methods=["GET"])
def get_event_attendance(event_id):
    """Список участников и счётчик по конкретному мероприятию."""
    records = [r for r in attendance_db.values() if r["event_id"] == event_id]
    going_count = len([r for r in records if r["status"] == "going"])
    interested_count = len([r for r in records if r["status"] == "interested"])
    return jsonify({
        "event_id": event_id,
        "going_count": going_count,
        "interested_count": interested_count,
        "records": records,
    }), 200


@app.route("/attendance/user/<user_id>", methods=["GET"])
def get_user_attendance(user_id):
    """Список мероприятий, на которые пользователь отметился."""
    records = [r for r in attendance_db.values() if r["user_id"] == user_id]
    return jsonify(records), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
