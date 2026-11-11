"""
Слой бизнес-логики (services).

Правила предметной области, валидация, сборка ответа. Данными управляет
слой доступа (repository/), сессиями — database.db_session. Маршруты
вызывают только методы EventsService.
"""

import logging
from functools import wraps

from sqlalchemy.exc import InterfaceError, OperationalError

from cache import HIT, STALE, event_key, events_cache, list_key, LIST_PREFIX
from database import db_session, from_iso, to_iso, utcnow
from errors import ApiError
from models import Event
from repository.categories import CategoryRepository
from repository.events import EventRepository
from validation import CATEGORIES, validate_event, validate_query_params

logger = logging.getLogger("events-service.service")

# Ошибки уровня соединения с БД (база остановлена, сеть, тайм-аут).
DB_UNAVAILABLE_ERRORS = (OperationalError, InterfaceError)


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


class DatabaseUnavailableError(ApiError):
    def __init__(self):
        super().__init__(
            503,
            "ServiceUnavailable",
            "База данных временно недоступна, повторите запрос позже",
            [{"field": None, "message": "database unavailable"}],
        )


def _guard_db(operation):
    """Переводит сбой соединения с БД в контролируемый ответ 503 и пишет лог."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DB_UNAVAILABLE_ERRORS as exc:
                logger.error(
                    "database unavailable",
                    extra={"event": "db.unavailable", "operation": operation,
                           "error": str(exc.orig if getattr(exc, "orig", None) else exc)[:300]},
                )
                raise DatabaseUnavailableError() from exc
        return wrapper
    return decorator


def _invalidate_after_write(event_id, reason):
    """Инвалидация кэша после успешного commit: все списки + карточка события."""
    events_cache.invalidate(event_key(event_id), prefix=LIST_PREFIX, reason=reason)


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
    # ---- список с пагинацией и фильтрами (кэшируется, ПР6) ----
    def list(self, page, limit, category=None, date_from=None, date_to=None):
        """Возвращает (результат, статус кэша: HIT / MISS / STALE / BYPASS)."""
        details = validate_query_params(
            page=page, limit=limit, category=category,
            date_from=date_from, date_to=date_to,
        )
        if details:
            raise ValidationFailedError(details)

        page = int(page) if page is not None else 1
        limit = int(limit) if limit is not None else 20

        key = list_key(page, limit, category, date_from, date_to)
        status, cached = events_cache.get(key)
        if status == HIT:
            return cached, status

        try:
            result = self._list_from_db(page, limit, category, date_from, date_to)
        except DatabaseUnavailableError:
            stale = events_cache.get_stale(key)
            if stale is not None:
                logger.warning("serving stale cache", extra={"event": "cache.stale", "key": key})
                return stale, STALE
            raise
        events_cache.set(key, result)
        return result, status

    @_guard_db("events.list")
    def _list_from_db(self, page, limit, category, date_from, date_to):
        start_dt = from_iso(date_from)
        end_dt = from_iso(date_to)
        with db_session() as session:
            events_repo = EventRepository(session)
            category_id = None
            if category is not None:
                cat = CategoryRepository(session).get_by_name(category)
                if cat is None:
                    # Раньше category_id=None отключал фильтр и возвращались ВСЕ
                    # события; если категории нет в справочнике — список пуст.
                    return {"items": [], "total": 0, "page": page, "limit": limit}
                category_id = cat.id

            query = events_repo.base_query(
                category_id=category_id, date_from=start_dt, date_to=end_dt,
            )
            total = events_repo.count(query)
            rows = events_repo.page(query, limit, (page - 1) * limit)
            items = [_serialize(e) for e in rows]
        logger.info("events loaded from database",
                    extra={"event": "db.query", "operation": "events.list", "rows": len(items)})
        return {"items": items, "total": total, "page": page, "limit": limit}

    # ---- получение одной записи (кэшируется, ПР6) ----
    def get(self, event_id):
        """Возвращает (событие, статус кэша)."""
        key = event_key(event_id)
        status, cached = events_cache.get(key)
        if status == HIT:
            return cached, status
        try:
            result = self._get_from_db(event_id)
        except DatabaseUnavailableError:
            stale = events_cache.get_stale(key)
            if stale is not None:
                logger.warning("serving stale cache", extra={"event": "cache.stale", "key": key})
                return stale, STALE
            raise
        events_cache.set(key, result)
        return result, status

    @_guard_db("events.get")
    def _get_from_db(self, event_id):
        with db_session() as session:
            event = EventRepository(session).get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)
            return _serialize(event)

    # ---- создание ----
    @_guard_db("events.create")
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
            result = _serialize(event)
        _invalidate_after_write(result["id"], "event created")
        return result

    # ---- полное обновление (PUT) ----
    @_guard_db("events.replace")
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
            result = _serialize(event)
        _invalidate_after_write(event_id, "event replaced")
        return result

    # ---- частичное обновление (PATCH) ----
    @_guard_db("events.patch")
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
            result = _serialize(event)
        _invalidate_after_write(event_id, "event updated")
        return result

    # ---- удаление ----
    @_guard_db("events.delete")
    def delete(self, event_id, actor):
        with db_session() as session:
            repo = EventRepository(session)
            event = repo.get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)
            _authorize_event(event, actor)
            repo.remove(event_id)
        _invalidate_after_write(event_id, "event deleted")


def seed_categories():
    """Начальное наполнение справочника категорий (вызывается при старте)."""
    with db_session() as session:
        repo = CategoryRepository(session)
        for name in CATEGORIES:
            if repo.get_by_name(name) is None:
                repo.create(name)
