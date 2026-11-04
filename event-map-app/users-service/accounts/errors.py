"""
Единый формат ошибок users-service.

Любой ответ об ошибке имеет вид:
    {"error": {"code": "...", "message": "...", "details": [...]}}
"""

import logging

from django.http import JsonResponse

logger = logging.getLogger("users-service")


STATUS_META = {
    400: ("BadRequest", "Некорректный запрос"),
    401: ("Unauthorized", "Требуется аутентификация"),
    403: ("Forbidden", "Доступ запрещён"),
    404: ("NotFound", "Ресурс не найден"),
    405: ("MethodNotAllowed", "Метод не поддерживается"),
    409: ("Conflict", "Конфликт данных"),
    429: ("TooManyRequests", "Слишком много запросов"),
    500: ("InternalServerError", "Внутренняя ошибка сервера"),
}


class ApiError(Exception):
    """Исключение с явным HTTP-статусом и машинным кодом ошибки."""

    def __init__(self, status, code, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []
        self.headers = headers or {}


def error_payload(code, message, details=None):
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }


def error_response(status, code=None, message=None, details=None, headers=None):
    default_code, default_message = STATUS_META.get(
        status, ("Error", "Ошибка")
    )
    response = JsonResponse(
        error_payload(
            code or default_code,
            message or default_message,
            details,
        ),
        status=status,
    )
    for name, value in (headers or {}).items():
        response[name] = value
    return response


def handler400(request, exception=None):
    return error_response(400)


def handler403(request, exception=None):
    return error_response(403)


def handler404(request, exception=None):
    return error_response(404)


def handler500(request):
    return error_response(500)
