"""
Слой бизнес-логики (services).

Правила предметной области, валидация, сборка ответа. Данными управляет
слой доступа (repository/), сессиями — database.db_session. Маршруты
вызывают только методы EventsService.
"""

from database import db_session, from_iso, to_iso, utcnow
from models import Event
from repository.categories import CategoryRepository
from repository.events import EventRepository
from validation import validate_event, validate_query_params, CATEGORIES


class EventNotFoundError(Exception):
    pass


class ValidationFailedError(Exception):
    def __init__(self, details):
        super().__init__("validation failed")
        self.details = details


def _serialize(event):
    category_name = event.category.name if event.category else None
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "lat": event.lat,
        "lng": event.lng,
        "starts_at": to_iso(event.starts_at),
        "category": category_name,
        "organizer_id": event.organizer_id,
        "created_at": to_iso(event.created_at),
        "updated_at": to_iso(event.updated_at),
    }


class EventsService:
    # ---- список с пагинацией и фильтрами ----
    def list(self, page, limit, category=None, date_from=None, date_to=None):
        details = validate_query_params(
            page=page, limit=limit, category=category,
            date_from=date_from, date_to=date_to,
        )
        if details:
            raise ValidationFailedError(details)

        page = int(page) if page is not None else 1
        limit = int(limit) if limit is not None else 20
        start_dt = from_iso(date_from)
        end_dt = from_iso(date_to)

        with db_session() as session:
            events_repo = EventRepository(session)
            category_id = None
            if category is not None:
                cat = CategoryRepository(session).get_by_name(category)
                category_id = cat.id if cat else None

            query = events_repo.base_query(
                category_id=category_id, date_from=start_dt, date_to=end_dt,
            )
            total = events_repo.count(query)
            rows = events_repo.page(query, limit, (page - 1) * limit)
            items = [_serialize(e) for e in rows]

        return {"items": items, "total": total, "page": page, "limit": limit}

    # ---- получение одной записи ----
    def get(self, event_id):
        with db_session() as session:
            event = EventRepository(session).get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)
            return _serialize(event)

    # ---- создание ----
    def create(self, payload):
        details = validate_event(payload)
        if details:
            raise ValidationFailedError(details)

        with db_session() as session:
            category = CategoryRepository(session).get_or_create(payload["category"])
            event = Event(
                title=payload["title"].strip(),
                description=payload["description"].strip(),
                lat=float(payload["lat"]),
                lng=float(payload["lng"]),
                starts_at=from_iso(payload["starts_at"]),
                category_id=category.id,
                organizer_id=payload["organizer_id"].strip(),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            EventRepository(session).add(event)
            session.flush()
            return _serialize(event)

    # ---- полное обновление (PUT) ----
    def replace(self, event_id, payload):
        with db_session() as session:
            repo = EventRepository(session)
            event = repo.get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)

            details = validate_event(payload)
            if details:
                raise ValidationFailedError(details)

            category = CategoryRepository(session).get_or_create(payload["category"])
            event.title = payload["title"].strip()
            event.description = payload["description"].strip()
            event.lat = float(payload["lat"])
            event.lng = float(payload["lng"])
            event.starts_at = from_iso(payload["starts_at"])
            event.category_id = category.id
            event.organizer_id = payload["organizer_id"].strip()
            event.updated_at = utcnow()
            return _serialize(event)

    # ---- частичное обновление (PATCH) ----
    def patch(self, event_id, patch):
        with db_session() as session:
            repo = EventRepository(session)
            event = repo.get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)

            details = validate_event(patch, partial=True)
            if details:
                raise ValidationFailedError(details)

            for field, value in patch.items():
                if field == "category":
                    category = CategoryRepository(session).get_or_create(value)
                    event.category_id = category.id
                elif field in ("lat", "lng"):
                    setattr(event, field, float(value))
                elif field == "starts_at":
                    event.starts_at = from_iso(value)
                else:
                    setattr(event, field, value.strip() if isinstance(value, str) else value)
            event.updated_at = utcnow()
            return _serialize(event)

    # ---- удаление ----
    def delete(self, event_id):
        with db_session() as session:
            removed = EventRepository(session).remove(event_id)
            if not removed:
                raise EventNotFoundError(event_id)


def seed_categories():
    """Начальное наполнение справочника категорий (вызывается при старте)."""
    with db_session() as session:
        repo = CategoryRepository(session)
        for name in CATEGORIES:
            if repo.get_by_name(name) is None:
                repo.create(name)