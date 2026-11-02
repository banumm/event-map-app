from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Расширенная модель пользователя с ролью.

    role = "user"      — обычный пользователь: просмотр событий и отметка участия.
    role = "organizer" — может создавать и редактировать только свои мероприятия.
    role = "admin"     — полный доступ: управление всеми мероприятиями и пользователями.

    Пароль наследуется от AbstractUser и хранится только в виде хэша
    (Argon2, см. PASSWORD_HASHERS в config/settings.py). Дата регистрации —
    встроенное поле date_joined.
    """

    ROLE_USER = "user"
    ROLE_ORGANIZER = "organizer"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ORGANIZER, "Organizer"),
        (ROLE_ADMIN, "Admin"),
    ]

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} ({self.role})"
