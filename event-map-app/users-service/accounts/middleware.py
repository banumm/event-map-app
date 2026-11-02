"""
Глобальный обработчик ошибок Django.

Перехватывает необработанные исключения, Http404, PermissionDenied и
превращает любые не-JSON ответы со статусом >= 400 в единый формат:
    {"error": {"code": ..., "message": ..., "details": [...]}}
Стектрейсы никогда не попадают в тело ответа.
"""

import json
import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404

from .errors import ApiError, error_response

logger = logging.getLogger("users-service")


class UnifiedErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_exception(self, request, exception):
        """Вызывается Django до превращения исключения в debug-страницу."""
        if isinstance(exception, ApiError):
            return error_response(
                exception.status,
                exception.code,
                exception.message,
                exception.details,
            )
        if isinstance(exception, Http404):
            return error_response(404)
        if isinstance(exception, PermissionDenied):
            return error_response(403)
        if isinstance(exception, ValidationError):
            return error_response(
                400,
                "ValidationError",
                "Ошибка валидации",
                [{"field": None, "message": "; ".join(exception.messages)}],
            )
        if isinstance(exception, json.JSONDecodeError):
            return error_response(
                400,
                "BadRequest",
                "Тело запроса не является корректным JSON",
            )
        logger.exception("Необработанная ошибка users-service")
        return error_response(500)

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except ApiError as exc:
            return error_response(
                exc.status, exc.code, exc.message, exc.details
            )
        except Http404:
            return error_response(404)
        except PermissionDenied:
            return error_response(403)
        except ValidationError as exc:
            return error_response(
                400,
                "ValidationError",
                "Ошибка валидации",
                [{"field": None, "message": "; ".join(exc.messages)}],
            )
        except json.JSONDecodeError:
            return error_response(
                400,
                "BadRequest",
                "Тело запроса не является корректным JSON",
            )
        except Exception:
            logger.exception("Необработанная ошибка users-service")
            return error_response(500)

        if response.status_code >= 400 and not self._is_json(response):
            return error_response(response.status_code)

        return response

    @staticmethod
    def _is_json(response):
        content_type = response.get("Content-Type", "")
        return content_type.startswith("application/json")
