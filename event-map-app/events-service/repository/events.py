"""
Репозиторий событий (DAO). Отвечает только за create/read/update/delete
и поиск по фильтрам. Никаких правил валидации и HTTP — это зона services/api.
"""

from datetime import datetime

from models import Event
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload


class EventRepository:
    def __init__(self, session: Session):
        self._session = session

    def base_query(self, category_id=None, date_from=None, date_to=None):
        query = select(Event).options(joinedload(Event.category))
        if category_id is not None:
            query = query.where(Event.category_id == category_id)
        if date_from is not None:
            query = query.where(Event.starts_at >= date_from)
        if date_to is not None:
            query = query.where(Event.starts_at <= date_to)
        return query

    def count(self, query) -> int:
        count_query = select(func.count()).select_from(query.subquery())
        return self._session.execute(count_query).scalar_one()

    def page(self, query, limit, offset) -> list[Event]:
        rows = self._session.execute(
            query.order_by(Event.starts_at).limit(limit).offset(offset)
        ).unique().scalars().all()
        return list(rows)

    def get(self, event_id) -> Event | None:
        return self._session.execute(
            select(Event)
            .options(joinedload(Event.category))
            .where(Event.id == event_id)
        ).unique().scalar_one_or_none()

    def add(self, event: Event) -> Event:
        self._session.add(event)
        return event

    def remove(self, event_id) -> bool:
        event = self.get(event_id)
        if event is None:
            return False
        self._session.delete(event)
        return True