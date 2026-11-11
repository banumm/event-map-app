import json
import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth import create_access_token, require_auth, require_role
from .errors import ApiError
from .ratelimit import rate_limit

User = get_user_model()
logger = logging.getLogger("users-service")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,150}$")
PUBLIC_ROLES = {User.ROLE_USER, User.ROLE_ORGANIZER}
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def _json_body(request):
    raw = request.body.decode("utf-8") if request.body else ""
    if not raw.strip():
        raise ApiError(400, "BadRequest", "Тело запроса пустое")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(
            400,
            "BadRequest",
            "Тело запроса не является корректным JSON",
            [{"field": None, "message": str(exc)}],
        ) from exc
    if not isinstance(data, dict):
        raise ApiError(
            400,
            "BadRequest",
            "Тело запроса должно быть JSON-объектом",
        )
    return data


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "created_at": user.date_joined.isoformat(),
    }


def _validate_registration(data):
    details = []

    username = data.get("username")
    if not isinstance(username, str) or not username.strip():
        details.append({"field": "username", "message": "логин обязателен"})
    elif not USERNAME_RE.match(username.strip()):
        details.append({
            "field": "username",
            "message": "логин: 3-150 символов, латиница, цифры, '_', '.', '-'",
        })

    email = data.get("email")
    if not isinstance(email, str) or not email.strip():
        details.append({"field": "email", "message": "email обязателен"})
    else:
        try:
            validate_email(email.strip())
        except DjangoValidationError:
            details.append({"field": "email", "message": "некорректный формат email"})

    password = data.get("password")
    if not isinstance(password, str) or not password:
        details.append({"field": "password", "message": "пароль обязателен"})
    elif len(password) < MIN_PASSWORD_LENGTH:
        details.append({
            "field": "password",
            "message": f"пароль должен содержать минимум {MIN_PASSWORD_LENGTH} символов",
        })
    elif len(password) > MAX_PASSWORD_LENGTH:
        details.append({
            "field": "password",
            "message": f"пароль не должен превышать {MAX_PASSWORD_LENGTH} символов",
        })

    role = data.get("role", User.ROLE_USER)
    if role not in PUBLIC_ROLES:
        details.append({
            "field": "role",
            "message": "допустимые роли при регистрации: " + ", ".join(sorted(PUBLIC_ROLES)),
        })

    return details, (username or "").strip(), (email or "").strip(), role


@require_http_methods(["GET"])
def health(request):
    """Процесс жив И база данных отвечает; иначе 503 (ПР7)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = {"status": "ok", "backend": connection.vendor}
        status_code = 200
    except Exception as exc:  # noqa: BLE001 — /health не должен падать
        database = {"status": "error", "error": str(exc).splitlines()[0][:200] if str(exc) else type(exc).__name__}
        status_code = 503
        logger.warning("health check failed", extra={"event": "health.fail", "dependency": "database"})
    return JsonResponse(
        {
            "status": "ok" if status_code == 200 else "unavailable",
            "service": "users-service",
            "checks": {"database": database},
        },
        status=status_code,
    )


@csrf_exempt
@require_http_methods(["POST"])
@rate_limit("register")
def register(request):
    """Регистрация пользователя. Пароль сразу сохраняется только в виде хэша."""
    data = _json_body(request)
    details, username, email, role = _validate_registration(data)
    if details:
        raise ApiError(400, "ValidationError", "Ошибка валидации", details)

    duplicates = []
    if User.objects.filter(username__iexact=username).exists():
        duplicates.append({"field": "username", "message": "логин уже занят"})
    if User.objects.filter(email__iexact=email).exists():
        duplicates.append({"field": "email", "message": "email уже зарегистрирован"})
    if duplicates:
        raise ApiError(
            409,
            "Conflict",
            "Пользователь с таким логином или email уже существует",
            duplicates,
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=data["password"],
                role=role,
            )
    except IntegrityError as exc:
        raise ApiError(
            409,
            "Conflict",
            "Пользователь с таким логином или email уже существует",
        ) from exc

    return JsonResponse(_user_payload(user), status=201)


@csrf_exempt
@require_http_methods(["POST"])
@rate_limit("login")
def login_view(request):
    """Проверяет логин/пароль (username или email) и выдаёт JWT."""
    data = _json_body(request)
    identifier = data.get("username") or data.get("email") or data.get("login")
    password = data.get("password")

    if not isinstance(identifier, str) or not identifier.strip() or not password:
        raise ApiError(
            400,
            "ValidationError",
            "Ошибка валидации",
            [{"field": "username", "message": "укажите username/email и password"}],
        )

    identifier = identifier.strip()
    user = User.objects.filter(
        Q(username__iexact=identifier) | Q(email__iexact=identifier)
    ).first()

    if user is None or not user.check_password(password) or not user.is_active:
        raise ApiError(
            401,
            "InvalidCredentials",
            "Неверный логин или пароль",
        )

    update_last_login(None, user)
    token = create_access_token(user)
    return JsonResponse({
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": settings.JWT_EXPIRES_MINUTES * 60,
        "user": _user_payload(user),
    })


@require_http_methods(["GET"])
@require_auth
def me(request):
    return JsonResponse(_user_payload(request.auth_user))


@require_http_methods(["GET"])
@require_auth
@require_role(User.ROLE_ADMIN)
def list_users(request):
    users = [_user_payload(user) for user in User.objects.all()]
    return JsonResponse({"items": users, "total": len(users)})


@require_http_methods(["GET"])
def get_user(request, user_id):
    """
    Внутренний эндпоинт для других сервисов: существование и роль пользователя.
    Наружу users-service не публикуется (см. архитектуру в README).
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as exc:
        raise ApiError(
            404,
            "NotFound",
            "Пользователь не найден",
            [{"field": "id", "message": f"пользователь {user_id} не найден"}],
        ) from exc
    return JsonResponse(_user_payload(user))
