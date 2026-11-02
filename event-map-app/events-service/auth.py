"""Проверка JWT и ролей в events-service."""

import os
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import g, request

from errors import error_response

load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-jwt-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "event-map-users-service")


def _auth_error(code, message):
    return error_response(
        401,
        code,
        message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer_token():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _bearer_token()
        if token is None:
            return _auth_error("Unauthorized", "Требуется аутентификация")

        try:
            claims = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                options={"require": ["exp", "sub", "iss"]},
            )
        except jwt.ExpiredSignatureError:
            return _auth_error("TokenExpired", "Срок действия токена истёк")
        except jwt.InvalidTokenError:
            return _auth_error("InvalidToken", "Токен недействителен")

        if not claims.get("role"):
            return _auth_error("InvalidToken", "В токене отсутствует роль")

        g.current_user = claims
        return view(*args, **kwargs)

    return wrapper


def require_role(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if user is None:
                return _auth_error("Unauthorized", "Требуется аутентификация")
            if user.get("role") not in roles:
                return error_response(
                    403,
                    "Forbidden",
                    "Недостаточно прав для выполнения операции",
                    [{
                        "field": "role",
                        "message": f"требуется одна из ролей: {', '.join(roles)}",
                    }],
                )
            return view(*args, **kwargs)

        return wrapper

    return decorator


def current_user():
    return g.current_user
