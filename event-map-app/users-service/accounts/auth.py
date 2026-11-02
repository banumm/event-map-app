"""JWT-аутентификация и проверка ролей для users-service."""

import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

from .errors import error_response


def create_access_token(user):
    """Выпускает подписанный JWT с сроком действия из настроек."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.pk),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRES_MINUTES),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token):
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        options={"require": ["exp", "sub", "iss"]},
    )


def _bearer_token(request):
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _unauthorized(code="Unauthorized", message="Требуется аутентификация"):
    return error_response(
        401,
        code,
        message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_auth(view):
    """Проверяет Bearer-токен и прикрепляет пользователя к request."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        token = _bearer_token(request)
        if token is None:
            return _unauthorized()

        try:
            claims = decode_token(token)
        except jwt.ExpiredSignatureError:
            return _unauthorized("TokenExpired", "Срок действия токена истёк")
        except jwt.InvalidTokenError:
            return _unauthorized("InvalidToken", "Токен недействителен")

        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=claims.get("sub"))
        except (user_model.DoesNotExist, ValueError, TypeError):
            return _unauthorized("InvalidToken", "Пользователь из токена не найден")

        if not user.is_active:
            return _unauthorized("InactiveUser", "Учётная запись отключена")

        request.auth_user = user
        request.auth_claims = claims
        return view(request, *args, **kwargs)

    return wrapper


def require_role(*roles):
    """Проверяет роль уже аутентифицированного пользователя (403 при нехватке прав)."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "auth_user", None)
            if user is None:
                return _unauthorized()
            if user.role not in roles:
                return error_response(
                    403,
                    "Forbidden",
                    "Недостаточно прав для выполнения операции",
                    [{
                        "field": "role",
                        "message": f"требуется одна из ролей: {', '.join(roles)}",
                    }],
                )
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
