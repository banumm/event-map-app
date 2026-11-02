"""
Единый формат ошибок events-service.

    {"error": {"code": "...", "message": "...", "details": [...]}}
"""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("events-service")

STATUS_META = {
    400: ("BadRequest", "Некорректный запрос"),
    401: ("Unauthorized", "Требуется аутентификация"),
    403: ("Forbidden", "Доступ запрещён"),
    404: ("NotFound", "Ресурс не найден"),
    405: ("MethodNotAllowed", "Метод не поддерживается"),
    409: ("Conflict", "Конфликт данных"),
    500: ("InternalServerError", "Внутренняя ошибка сервера"),
}


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []


def error_response(status, code=None, message=None, details=None, headers=None):
    default_code, default_message = STATUS_META.get(status, ("Error", "Ошибка"))
    response = jsonify({
        "error": {
            "code": code or default_code,
            "message": message or default_message,
            "details": details or [],
        }
    })
    response.status_code = status
    for name, value in (headers or {}).items():
        response.headers[name] = value
    return response


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return error_response(err.status, err.code, err.message, err.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        code, message = STATUS_META.get(
            err.code, ("Error", err.description or "Ошибка")
        )
        details = []
        if err.code == 404:
            message = "Ресурс не найден"
        elif err.code == 405:
            message = "Метод не поддерживается для этого ресурса"
        elif err.description:
            details = [{"field": None, "message": err.description}]
        return error_response(err.code, code, message, details)

    @app.errorhandler(Exception)
    def handle_internal_error(err):
        app.logger.exception("Необработанная ошибка events-service")
        return error_response(500)
