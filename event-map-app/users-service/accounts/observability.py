"""
Наблюдаемость users-service (ПР7): JSON-логи, X-Request-ID, метрики.

- JsonFormatter подключается в settings.LOGGING: одна JSON-строка на событие
  с уровнем, временем, сервисом и request_id;
- ObservabilityMiddleware присваивает запросу идентификатор (или берёт его
  из заголовка X-Request-ID), пишет access-лог и считает метрики;
- metrics_view отдаёт счётчики в текстовом формате Prometheus на GET /metrics.
"""

import contextvars
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone

from django.http import HttpResponse

SERVICE_NAME = "users-service"

_request_id = contextvars.ContextVar("request_id", default=None)
_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = _request_id.get()
        if request_id:
            entry["request_id"] = request_id
        for key, value in vars(record).items():
            # request — объект Django, который логгеры django.* кладут в extra.
            if key not in _RESERVED and not key.startswith("_") and key != "request":
                entry[key] = value
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {}

    def inc(self, name, value=1.0, **labels):
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def render(self):
        with self._lock:
            items = sorted(self._counters.items())
        lines, seen = [], set()
        for (name, labels), value in items:
            if name not in seen:
                seen.add(name)
                lines.append(f"# TYPE {name} counter")
            label_str = ",".join(f'{k}="{v}"' for k, v in labels)
            lines.append(f"{name}{{{label_str}}} {value:g}" if label_str else f"{name} {value:g}")
        return "\n".join(lines) + "\n"


metrics = Metrics()
access_log = logging.getLogger("users-service.access")


class ObservabilityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming[:64] if incoming else uuid.uuid4().hex
        token = _request_id.set(request_id)
        request.request_id = request_id
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        finally:
            duration = time.perf_counter() - started
        try:
            match = getattr(request, "resolver_match", None)
            path = "/" + match.route if match and match.route else "unmatched"
            metrics.inc("http_requests_total", method=request.method, path=path,
                        status=str(response.status_code))
            metrics.inc("http_request_duration_seconds_sum", duration,
                        method=request.method, path=path)
            response["X-Request-ID"] = request_id
            if path != "/metrics":
                access_log.info("request", extra={
                    "event": "http.request", "method": request.method, "path": request.path,
                    "status": response.status_code, "duration_ms": round(duration * 1000, 2),
                })
        finally:
            _request_id.reset(token)
        return response


def metrics_view(request):
    return HttpResponse(metrics.render(), content_type="text/plain; version=0.0.4")
