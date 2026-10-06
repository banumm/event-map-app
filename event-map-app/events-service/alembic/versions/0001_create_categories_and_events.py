"""create categories and events tables

Revision ID: 0001
Revises:
Create Date: 2026-09-29

Схема ПР3:
- categories: справочник категорий (name UNIQUE). Связь 1:N с events.
- events: основная сущность; category_id — внешний ключ на categories.id;
  CHECK-ограничения на длину title/description и диапазоны lat/lng.
- Индекс на category_id — частое фильтрование списка по категории (ПР2).
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", name="uq_categories_name"),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("organizer_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "length(title) >= 2 AND length(title) <= 100",
            name="ck_events_title_len",
        ),
        sa.CheckConstraint("length(description) <= 2000", name="ck_events_description_len"),
        sa.CheckConstraint("lat >= -90 AND lat <= 90", name="ck_events_lat_range"),
        sa.CheckConstraint("lng >= -180 AND lng <= 180", name="ck_events_lng_range"),
    )
    op.create_index("ix_events_category_id", "events", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_events_category_id", table_name="events")
    op.drop_table("events")
    op.drop_table("categories")