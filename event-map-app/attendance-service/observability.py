"""
Наблюдаемость Flask-сервиса (ПР7): структурированные логи, request id, метрики.

- Логи пишутся в stdout одной JSON-строкой на событие: время, уровень,
  сервис, логгер, сообщение, request_id и дополнительные поля из extra=.
- Каждый запрос получает идентификатор: берётся из заголовка X-Request-ID
  (если пришёл от вызывающего сервиса) или генерируется; возвращается
  клиенту в том же заголовке.
- Метрики в памяти процесса отдаются на GET /metrics в текстовом формате
  Prometheus: количество запросов, суммарное время ответа, произвольные
  счётчики сервиса (например, попадания/промахи кэша).

Файл одинаковый в events-service и attendance-service: сервисы собираются
в отдельные образы и не имеют общего пакета.
"""

import json
import logging
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

from flask import Response, g, has_request_context, request

# Поля стандартного LogRecord — не переносим их в JSON как «extra».
_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if has_request_context():
            entry["request_id"] = getattr(g, "request_id", None)
        for key, value in vars(record).items():
            if key not in _RESERVED and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(service, level="INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Стандартный access-лог werkzeug дублирует наш — оставляем только ошибки.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


class Metrics:
    """Простейший потокобезопасный реестр счётчиков в формате Prometheus."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {}  # (name, labels_tuple) -> value
        self._help = {}

    def inc(self, name, value=1.0, help_text="", **labels):
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value
            if help_text:
                self._help.setdefault(name, help_text)

    def value(self, name, **labels):
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            return self._counters.get(key, 0.0)

    def reset(self):
        with self._lock:
            self._counters.clear()

    def render(self):
        with self._lock:
            items = sorted(self._counters.items())
            helps = dict(self._help)
        lines, seen = [], set()
        for (name, labels), value in items:
            if name not in seen:
                seen.add(name)
                if name in helps:
                    lines.append(f"# HELP {name} {helps[name]}")
                lines.append(f"# TYPE {name} counter")
            label_str = ",".join(f'{k}="{v}"' for k, v in labels)
            suffix = "{" + label_str + "}" if label_str else ""
            lines.append(f"{name}{suffix} {value:g}")
        return "\n".join(lines) + "\n"


metrics = Metrics()


def init_app(app, service):
    """Подключает request id, access-лог и /metrics к Flask-приложению."""
    access_log = logging.getLogger(f"{service}.access")

    @app.before_request
    def _start_request():
        incoming = request.headers.get("X-Request-ID", "")
        g.request_id = incoming[:64] if incoming else uuid.uuid4().hex
        g.request_started = time.perf_counter()

    @app.after_request
    def _finish_request(response):
        started = getattr(g, "request_started", None)
        duration = time.perf_counter() - started if started else 0.0
        path = request.url_rule.rule if request.url_rule else "unmatched"
        labels = {"method": request.method, "path": path, "status": str(response.status_code)}
        metrics.inc("http_requests_total", help_text="Количество HTTP-запросов", **labels)
        metrics.inc(
            "http_request_duration_seconds_sum",
            duration,
            help_text="Суммарное время обработки запросов, с",
            method=request.method,
            path=path,
        )
        response.headers["X-Request-ID"] = g.get("request_id", "")
        if path != "/metrics":
            access_log.info(
                "request",
                extra={
                    "event": "http.request",
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
        return response

    @app.get("/metrics")
    def _metrics():
        return Response(metrics.render(), mimetype="text/plain; version=0.0.4")
