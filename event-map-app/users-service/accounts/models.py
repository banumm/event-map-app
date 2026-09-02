from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Расширенная модель пользователя с ролью.
    role = "user" — обычный пользователь, может отмечать участие в мероприятиях.
    role = "organizer" — может создавать и редактировать мероприятия в Events Service.
    """
    ROLE_CHOICES = [
        ("user", "User"),
        ("organizer", "Organizer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")

    def __str__(self):
        return f"{self.username} ({self.role})"
