"""
Клиент events-service: проверка, что мероприятие существует, перед отметкой
участия (межсервисный вызов, описанный в архитектуре README).

- адрес задаётся EVENTS_SERVICE_URL (в docker compose — http://events-service:5001,
  по имени сервиса, а не localhost); если переменная пуста, проверка отключена
  (локальный запуск attendance-service без events-service, модульные тесты);
- у каждого вызова явный тайм-аут EVENTS_SERVICE_TIMEOUT_SECONDS;
- при сетевой ошибке или 5xx — ограниченное число повторов
  EVENTS_SERVICE_RETRIES с паузой; после исчерпания — EventsServiceUnavailable,
  который превращается в ответ 503, а не в зависание или падение;
- X-Request-ID пробрасывается, чтобы связать логи двух сервисов.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import g, has_request_context

logger = logging.getLogger("attendance-service.events-client")


class EventsServiceUnavailable(Exception):
    pass


def _settings():
    return {
        "url": os.environ.get("EVENTS_SERVICE_URL", "").rstrip("/"),
        "timeout": float(os.environ.get("EVENTS_SERVICE_TIMEOUT_SECONDS", "2")),
        "retries": int(os.environ.get("EVENTS_SERVICE_RETRIES", "2")),
        "backoff": float(os.environ.get("EVENTS_SERVICE_BACKOFF_SECONDS", "0.3")),
    }


def is_enabled():
    return bool(_settings()["url"])


def _request(url, timeout):
    headers = {"Accept": "application/json"}
    if has_request_context() and getattr(g, "request_id", None):
        headers["X-Request-ID"] = g.request_id
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL из конфигурации
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, None


def event_exists(event_id):
    """True/False — есть ли событие; EventsServiceUnavailable — если сервис не ответил."""
    cfg = _settings()
    url = f"{cfg['url']}/events/{urllib.parse.quote(str(event_id), safe='')}"
    attempts = cfg["retries"] + 1
    last_error = None
    for attempt in range(1, attempts + 1):
        started = time.perf_counter()
        try:
            status, _ = _request(url, cfg["timeout"])
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            status, last_error = None, str(getattr(exc, "reason", exc))
        duration_ms = round((time.perf_counter() - started) * 1000, 1)

        if status in (200, 404):
            logger.info("events-service call", extra={
                "event": "events_service.call", "event_id": event_id, "status": status,
                "attempt": attempt, "duration_ms": duration_ms,
            })
            return status == 200

        if status is not None:
            last_error = f"HTTP {status}"
        logger.warning("events-service call failed", extra={
            "event": "events_service.retry" if attempt < attempts else "events_service.failed",
            "event_id": event_id, "attempt": attempt, "max_attempts": attempts,
            "error": last_error, "duration_ms": duration_ms,
        })
        if status is not None and status < 500:
            break  # 4xx (кроме 404) не исправится повтором
        if attempt < attempts:
            time.sleep(cfg["backoff"] * attempt)

    raise EventsServiceUnavailable(last_error or "events-service unavailable")


def check_health():
    """Состояние зависимости для /health: (ok, ошибка). Без повторов, короткий тайм-аут."""
    cfg = _settings()
    if not cfg["url"]:
        return True, None
    try:
        status, _ = _request(f"{cfg['url']}/health", min(cfg["timeout"], 2.0))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return False, str(getattr(exc, "reason", exc))
    return status == 200, None if status == 200 else f"HTTP {status}"
