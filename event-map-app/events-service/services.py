"""
Слой бизнес-логики (services).

Содержит правила предметной области: фильтрацию, пагинацию, сборку события,
проверку существования. Не знает про HTTP — маршруты вызывают его через объект
EventsService.
"""

from datetime import datetime

from storage import InMemoryEventsStorage
from validation import validate_event, validate_query_params


class EventNotFoundError(Exception):
    pass


class ValidationFailedError(Exception):
    def __init__(self, details):
        super().__init__("validation failed")
        self.details = details


class EventsService:
    def __init__(self, storage=None):
        self.storage = storage or InMemoryEventsStorage()

    # ---- список с пагинацией и фильтрами ----
    def list(self, page, limit, category=None, date_from=None, date_to=None):
        details = validate_query_params(
            page=page,
            limit=limit,
            category=category,
            date_from=date_from,
            date_to=date_to,
        )
        if details:
            raise ValidationFailedError(details)

        page = int(page) if page is not None else 1
        limit = int(limit) if limit is not None else 20
        date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00")) if date_from else None
        date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00")) if date_to else None

        events = self.storage.all()

        if category is not None:
            events = [e for e in events if e["category"] == category]
        if date_from is not None:
            events = [e for e in events if _parse(e["starts_at"]) >= date_from]
        if date_to is not None:
            events = [e for e in events if _parse(e["starts_at"]) <= date_to]

        events.sort(key=lambda e: e["starts_at"])

        total = len(events)
        start = (page - 1) * limit
        items = events[start:start + limit]

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
        }

    # ---- получение одной записи ----
    def get(self, event_id):
        event = self.storage.get(event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        return event

    # ---- создание ----
    def create(self, payload):
        details = validate_event(payload)
        if details:
            raise ValidationFailedError(details)

        event_id = self.storage.next_id()
        event = {
            "id": event_id,
            "title": payload["title"].strip(),
            "description": payload["description"].strip(),
            "lat": float(payload["lat"]),
            "lng": float(payload["lng"]),
            "starts_at": payload["starts_at"],
            "category": payload["category"],
            "organizer_id": payload["organizer_id"].strip(),
            "created_at": self.storage.now_iso(),
            "updated_at": self.storage.now_iso(),
        }
        return self.storage.create(event)

    # ---- полное обновление (PUT) ----
    def replace(self, event_id, payload):
        existing = self.storage.get(event_id)
        if existing is None:
            raise EventNotFoundError(event_id)

        details = validate_event(payload)
        if details:
            raise ValidationFailedError(details)

        event = {
            **existing,
            "title": payload["title"].strip(),
            "description": payload["description"].strip(),
            "lat": float(payload["lat"]),
            "lng": float(payload["lng"]),
            "starts_at": payload["starts_at"],
            "category": payload["category"],
            "organizer_id": payload["organizer_id"].strip(),
            "updated_at": self.storage.now_iso(),
        }
        return self.storage.replace(event_id, event)

    # ---- частичное обновление (PATCH) ----
    def patch(self, event_id, patch):
        existing = self.storage.get(event_id)
        if existing is None:
            raise EventNotFoundError(event_id)

        details = validate_event(patch, partial=True)
        if details:
            raise ValidationFailedError(details)

        updated = dict(existing)
        for field, value in patch.items():
            if isinstance(value, str):
                value = value.strip()
            updated[field] = float(value) if field in ("lat", "lng") else value
        updated["updated_at"] = self.storage.now_iso()
        return self.storage.replace(event_id, updated)

    # ---- удаление ----
    def delete(self, event_id):
        if not self.storage.delete(event_id):
            raise EventNotFoundError(event_id)


def _parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))