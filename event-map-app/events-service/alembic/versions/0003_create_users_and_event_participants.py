"""create users and event_participants tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-07

Расширение схемы для защиты:
- users: пользователи платформы (организаторы и посетители).
- event_participants: связующая таблица N:M «пользователь <-> мероприятие»
  (регистрации посетителей). Составной первичный ключ (event_id, user_id),
  внешние ключи с ON DELETE CASCADE — при удалении пользователя/мероприятия
  регистрации удаляются автоматически.
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "role IN ('admin', 'organizer', 'user')", name="ck_users_role"
        ),
    )
    op.create_table(
        "event_participants",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("registered_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "user_id", name="pk_event_participants"),
        sa.CheckConstraint(
            "status IN ('registered', 'attended', 'cancelled')",
            name="ck_participant_status",
        ),
    )
    # Индекс для обратной выборки: «на какие мероприятия записан пользователь».
    op.create_index("ix_event_participants_user_id", "event_participants", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_event_participants_user_id", table_name="event_participants")
    op.drop_table("event_participants")
    op.drop_table("users")