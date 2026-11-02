"""Создание администратора (роль admin) из командной строки.

Пример:
    python manage.py create_admin --username admin --email admin@example.com \
        --password 'StrongPass123'
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт пользователя с ролью admin"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        username = options["username"].strip()
        email = options["email"].strip()
        password = options["password"]

        try:
            validate_email(email)
        except DjangoValidationError as exc:
            raise CommandError("Некорректный email") from exc

        if len(password) < 8:
            raise CommandError("Пароль должен содержать минимум 8 символов")

        if User.objects.filter(username__iexact=username).exists():
            raise CommandError("Логин уже занят")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("Email уже зарегистрирован")

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=User.ROLE_ADMIN,
                    is_staff=True,
                    is_superuser=True,
                )
        except IntegrityError as exc:
            raise CommandError("Пользователь уже существует") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Создан администратор {user.username} (id={user.id})"
            )
        )
