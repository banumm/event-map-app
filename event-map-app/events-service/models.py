"""
ORM-модели (схема БД).

Таблицы и ограничения создаются ТОЛЬКО системой миграций Alembic
(см. alembic/versions/). Здесь модели описаны для отображения в ORM.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database import utcnow


class Base(DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


class Category(Base):
    """Категория мероприятия. Связь 1:N с events (одна категория — много событий)."""

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    slug: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    events: Mapped[list["Event"]] = relationship(back_populates="category")


class Event(Base):
    """Мероприятие. Основная сущность проекта (из ПР2)."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organizer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    category: Mapped["Category"] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint("length(title) >= 2 AND length(title) <= 100",
                        name="ck_events_title_len"),
        CheckConstraint("length(description) <= 2000",
                        name="ck_events_description_len"),
        CheckConstraint("lat >= -90 AND lat <= 90", name="ck_events_lat_range"),
        CheckConstraint("lng >= -180 AND lng <= 180", name="ck_events_lng_range"),
    )