"""add slug to categories and composite index for frequent filter

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29

Что делает (правка схемы после создания):
1. Поле slug у categories (уникальный URL-аналог имени, backfill из name).
2. Составной индекс (category_id, starts_at) для events.

Обоснование индекса: самый частый запрос ПР2 — список с фильтром по
категории и/или диапазону дат, отсортированный по starts_at:
    WHERE category_id = ? AND starts_at BETWEEN ? AND ? ORDER BY starts_at
Составной индекс категория-первая покрывает и фильтр, и сортировку.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("slug", sa.String(length=50), nullable=True))
    op.execute("UPDATE categories SET slug = name WHERE slug IS NULL")
    op.create_index("uq_categories_slug", "categories", ["slug"], unique=True)
    op.create_index("ix_events_category_starts_at", "events", ["category_id", "starts_at"])


def downgrade() -> None:
    op.drop_index("ix_events_category_starts_at", table_name="events")
    op.drop_index("uq_categories_slug", table_name="categories")
    op.drop_column("categories", "slug")