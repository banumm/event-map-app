"""
Репозиторий пользователей (DAO). Единственный модуль, знающий, как
пользователи хранятся в базе.
"""

import uuid

from models import User
from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    def __init__(self, session: Session):
        self._session = session

    def get(self, user_id: str) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

    def all(self) -> list[User]:
        return list(self._session.execute(select(User).order_by(User.name)).scalars())

    def create(self, name: str, email: str, role: str = "user") -> User:
        user = User(id=str(uuid.uuid4()), name=name, email=email, role=role)
        self._session.add(user)
        return user

    def remove(self, user_id: str) -> bool:
        user = self.get(user_id)
        if user is None:
            return False
        self._session.delete(user)
        return True