"""
Репозиторий категорий (DAO). Единственный модуль, знающий, как
категории хранятся в базе. Маршруты/business-логика не используют
SQL/ORM-вызовы напрямую.
"""

import uuid

from models import Category
from sqlalchemy import select
from sqlalchemy.orm import Session


class CategoryRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_name(self, name: str) -> Category | None:
        return self._session.execute(
            select(Category).where(Category.name == name)
        ).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Category | None:
        return self._session.execute(
            select(Category).where(Category.slug == slug)
        ).scalar_one_or_none()

    def all(self) -> list[Category]:
        return list(self._session.execute(select(Category).order_by(Category.name)).scalars())

    def counts(self) -> dict[str, int]:
        counts = {}
        for cat in self.all():
            counts[cat.name] = len(cat.events)
        return counts

    def create(self, name: str, slug: str | None = None) -> Category:
        category = Category(
            id=str(uuid.uuid4()),
            name=name,
            slug=slug or name.lower(),
        )
        self._session.add(category)
        return category

    def get_or_create(self, name: str) -> Category:
        """Возвращает существующую категорию или создаёт новую."""
        category = self.get_by_name(name)
        if category is None:
            category = self.create(name)
            self._session.flush()
        return category