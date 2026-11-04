"""
Ограничение частоты запросов для чувствительных эндпоинтов.

Реализовано скользящее окно в памяти процесса: для ключа (действие + IP)
хранится отметка времени каждого запроса. Если за окно набралось больше
`AUTH_RATE_LIMIT` запросов, возвращается 429 с заголовком Retry-After.

Ограничение in-memory и не разделяется между процессами/инстансами. Для
production нужен общий store (Redis) или ограничение на reverse proxy.
"""

import threading
import time
from collections import defaultdict, deque
from functools import wraps

from django.conf import settings

from .errors import error_response


class SlidingWindowLimiter:
    """Потокобезопасное скользящее окно."""

    def __init__(self, limit, window_seconds, clock=time.monotonic):
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._clock = clock
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key):
        """
        Регистрирует попытку.

        Возвращает (allowed, retry_after_seconds). allowed=False, если лимит
        исчерпан; retry_after — через сколько секунд окно освободится.
        """
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])) + 1)
                return False, retry_after

            events.append(now)
            return True, 0

    def reset(self):
        with self._lock:
            self._events.clear()


_limiter = None
_limiter_lock = threading.Lock()


def get_limiter():
    """Ленивая инициализация, чтобы тесты могли менять настройки."""
    global _limiter
    with _limiter_lock:
        if _limiter is None:
            _limiter = SlidingWindowLimiter(
                settings.AUTH_RATE_LIMIT,
                settings.AUTH_RATE_WINDOW_SECONDS,
            )
        return _limiter


def reset_limiter():
    """Сбрасывает счётчики (используется в тестах)."""
    global _limiter
    with _limiter_lock:
        _limiter = None


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(action):
    """Декоратор: не более AUTH_RATE_LIMIT запросов на action+IP за окно."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            limiter = get_limiter()
            key = f"{action}:{_client_ip(request)}"
            allowed, retry_after = limiter.hit(key)
            if not allowed:
                return error_response(
                    429,
                    "TooManyRequests",
                    "Слишком много запросов. Попробуйте позже.",
                    [{
                        "field": None,
                        "message": f"повторите запрос через {retry_after} с",
                    }],
                    headers={"Retry-After": str(retry_after)},
                )
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
