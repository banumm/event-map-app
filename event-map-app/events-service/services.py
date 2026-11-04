"""
Слой бизнес-логики (services).

Правила предметной области, валидация, сборка ответа. Данными управляет
слой доступа (repository/), сессиями — database.db_session. Маршруты
вызывают только методы EventsService.
"""

from database import db_session, from_iso, to_iso, utcnow
from errors import ApiError
from models import Event
from repository.categories import CategoryRepository
from repository.events import EventRepository
from validation import validate_event, validate_query_params, CATEGORIES


class EventNotFoundError(ApiError):
    def __init__(self, event_id):
        super().__init__(
            404,
            "NotFound",
            "Мероприятие не найдено",
            [{"field": "id", "message": f"событие {event_id} не найдено"}],
        )


class ValidationFailedError(ApiError):
    def __init__(self, details):
        super().__init__(400, "ValidationError", "Ошибка валидации", details)


class ForbiddenError(ApiError):
    def __init__(self, message="Недостаточно прав для выполнения операции"):
        super().__init__(
            403,
            "Forbidden",
            message,
            [{"field": "organizer_id", "message": message}],
        )


def _is_admin(actor):
    return actor.get("role") == "admin"


def _authorize_event(event, actor):
    if _is_admin(actor):
        return
    if event.organizer_id != str(actor.get("sub")):
        raise ForbiddenError("Изменять мероприятие может только владелец или администратор")


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
    def create(self, payload, actor):
        details = validate_event(payload)
        if details:
            raise ValidationFailedError(details)

        if _is_admin(actor):
            organizer_id = (payload.get("organizer_id") or "").strip() or str(actor["sub"])
        else:
            organizer_id = str(actor["sub"])

        with db_session() as session:
            category = CategoryRepository(session).get_or_create(payload["category"])
            event = Event(
                title=payload["title"].strip(),
                description=payload["description"].strip(),
                lat=float(payload["lat"]),
                lng=float(payload["lng"]),
                starts_at=from_iso(payload["starts_at"]),
                category_id=category.id,
                organizer_id=organizer_id,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            EventRepository(session).add(event)
            session.flush()
            return _serialize(event)

    # ---- полное обновление (PUT) ----
    def replace(self, event_id, payload, actor):
        with db_session() as session:
            repo = EventRepository(session)
            event = repo.get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)
            _authorize_event(event, actor)

            details = validate_event(payload)
            if details:
                raise ValidationFailedError(details)

            if _is_admin(actor):
                organizer_id = (
                    (payload.get("organizer_id") or "").strip()
                    or event.organizer_id
                )
            else:
                organizer_id = str(actor["sub"])

            category = CategoryRepository(session).get_or_create(payload["category"])
            event.title = payload["title"].strip()
            event.description = payload["description"].strip()
            event.lat = float(payload["lat"])
            event.lng = float(payload["lng"])
            event.starts_at = from_iso(payload["starts_at"])
            event.category = category
            event.organizer_id = organizer_id
            event.updated_at = utcnow()
            return _serialize(event)

    # ---- частичное обновление (PATCH) ----
    def patch(self, event_id, patch, actor):
        with db_session() as session:
            repo = EventRepository(session)
            event = repo.get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)
            _authorize_event(event, actor)

            details = validate_event(patch, partial=True)
            if details:
                raise ValidationFailedError(details)

            for field, value in patch.items():
                if field == "category":
                    category = CategoryRepository(session).get_or_create(value)
                    event.category = category
                elif field == "organizer_id":
                    if _is_admin(actor):
                        event.organizer_id = value.strip()
                elif field in ("lat", "lng"):
                    setattr(event, field, float(value))
                elif field == "starts_at":
                    event.starts_at = from_iso(value)
                else:
                    setattr(event, field, value.strip() if isinstance(value, str) else value)
            event.updated_at = utcnow()
            return _serialize(event)

    # ---- удаление ----
    def delete(self, event_id, actor):
        with db_session() as session:
            repo = EventRepository(session)
            event = repo.get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)
            _authorize_event(event, actor)
            repo.remove(event_id)


def seed_categories():
    """Начальное наполнение справочника категорий (вызывается при старте)."""
    with db_session() as session:
        repo = CategoryRepository(session)
        for name in CATEGORIES:
            if repo.get_by_name(name) is None:
                repo.create(name)