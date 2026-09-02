"""
Events Service
Зона ответственности: CRUD мероприятий (название, описание, координаты, дата/время, категория).
Владеет данными: events, categories, locations.
"""

from flask import Flask, jsonify, request
from datetime import datetime
import uuid

app = Flask(__name__)

# Временное in-memory хранилище (в реальном проекте — БД, например PostgreSQL + PostGIS для гео)
events_db = {}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "events-service"}), 200


@app.route("/events", methods=["GET"])
def list_events():
    """
    Список мероприятий с опциональными фильтрами по категории и дате.
    Query params: category, date_from, date_to, lat, lng, radius_km
    """
    category = request.args.get("category")
    result = list(events_db.values())
    if category:
        result = [e for e in result if e["category"] == category]
    return jsonify(result), 200


@app.route("/events/<event_id>", methods=["GET"])
def get_event(event_id):
    event = events_db.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event), 200


@app.route("/events", methods=["POST"])
def create_event():
    """
    Создание мероприятия. В реальной реализации здесь должен быть вызов
    Users Service, чтобы проверить, что создатель имеет роль "organizer".
    """
    data = request.get_json(force=True)

    required_fields = ["title", "description", "lat", "lng", "starts_at", "category", "organizer_id"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    event_id = str(uuid.uuid4())
    event = {
        "id": event_id,
        "title": data["title"],
        "description": data["description"],
        "lat": data["lat"],
        "lng": data["lng"],
        "starts_at": data["starts_at"],
        "category": data["category"],
        "organizer_id": data["organizer_id"],
        "created_at": datetime.utcnow().isoformat(),
    }
    events_db[event_id] = event
    return jsonify(event), 201


@app.route("/events/<event_id>", methods=["DELETE"])
def delete_event(event_id):
    if event_id not in events_db:
        return jsonify({"error": "Event not found"}), 404
    del events_db[event_id]
    return jsonify({"status": "deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
