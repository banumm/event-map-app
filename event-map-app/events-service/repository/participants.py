"""Регистрации пользователей на мероприятия (связь N:M)."""

from models import EventParticipant
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class ParticipantRepository:
    def __init__(self, session: Session):
        self._session = session

    def get(self, event_id: str, user_id: str) -> EventParticipant | None:
        return self._session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.user_id == user_id,
            )
        ).scalar_one_or_none()

    def register(self, event_id: str, user_id: str, status: str = "registered") -> EventParticipant:
        participant = EventParticipant(
            event_id=event_id, user_id=user_id, status=status
        )
        self._session.add(participant)
        return participant

    def events_of_user(self, user_id: str) -> list[EventParticipant]:
        return list(
            self._session.execute(
                select(EventParticipant)
                .where(EventParticipant.user_id == user_id)
                .order_by(EventParticipant.registered_at.desc())
            ).scalars()
        )

    def count_for_event(self, event_id: str) -> int:
        return self._session.execute(
            select(func.count()).select_from(EventParticipant).where(
                EventParticipant.event_id == event_id
            )
        ).scalar_one()

    def counts_per_event(self) -> dict[str, int]:
        """Агрегат: {id события: число участников} для всех событий."""
        rows = self._session.execute(
            select(EventParticipant.event_id, func.count())
            .group_by(EventParticipant.event_id)
        ).all()
        return {event_id: count for event_id, count in rows}