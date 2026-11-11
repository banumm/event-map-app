"""
Кэш в памяти процесса с явным временем жизни записи (ПР6, вариант Б).

Что кэшируется: ответы GET /events (список с фильтрами и пагинацией) и
GET /events/{id}. Ключ строится из нормализованных параметров запроса.

Правила:
- запись живёт EVENTS_CACHE_TTL_SECONDS секунд (по умолчанию 60);
- при создании, изменении и удалении события сбрасываются все списки и
  карточка изменённого события (инвалидация);
- просроченная запись не отдаётся как свежая, но хранится ещё
  EVENTS_CACHE_STALE_SECONDS секунд: если база данных недоступна, сервис
  может вернуть её с пометкой X-Cache: STALE вместо ошибки 503.

Кэш локален для процесса, поэтому events-service запускается одним
gunicorn-воркером с потоками (см. Dockerfile): иначе инвалидация в одном
воркере не затронула бы кэш другого. Для нескольких инстансов нужен общий
кэш (Redis) — интерфейс TTLCache позволяет заменить реализацию.
"""

import logging
import os
import threading
import time

from observability import metrics

logger = logging.getLogger("events-service.cache")

HIT, MISS, STALE, BYPASS = "HIT", "MISS", "STALE", "BYPASS"


class TTLCache:
    def __init__(self, ttl_seconds, stale_seconds=0, max_entries=1000, clock=time.monotonic):
        self.ttl = float(ttl_seconds)
        self.stale = float(stale_seconds)
        self.max_entries = int(max_entries)
        self._clock = clock
        self._data = {}  # key -> (expires_at, value)
        self._lock = threading.Lock()

    @property
    def enabled(self):
        return self.ttl > 0

    def get(self, key):
        """Возвращает (статус, значение): HIT/значение или MISS/None."""
        if not self.enabled:
            return BYPASS, None
        now = self._clock()
        with self._lock:
            entry = self._data.get(key)
        if entry is not None and entry[0] > now:
            metrics.inc("cache_hits_total", help_text="Попадания в кэш")
            logger.info("cache hit", extra={"event": "cache.hit", "key": key,
                                            "ttl_left_s": round(entry[0] - now, 1)})
            return HIT, entry[1]
        metrics.inc("cache_misses_total", help_text="Промахи кэша")
        logger.info("cache miss", extra={"event": "cache.miss", "key": key,
                                         "reason": "expired" if entry else "absent"})
        return MISS, None

    def get_stale(self, key):
        """Просроченная, но ещё хранимая запись (для отдачи при сбое БД)."""
        if not self.enabled:
            return None
        now = self._clock()
        with self._lock:
            entry = self._data.get(key)
        if entry is not None and entry[0] + self.stale > now:
            return entry[1]
        return None

    def set(self, key, value):
        if not self.enabled:
            return
        now = self._clock()
        with self._lock:
            if len(self._data) >= self.max_entries:
                self._evict(now)
            self._data[key] = (now + self.ttl, value)
        logger.info("cache set", extra={"event": "cache.set", "key": key, "ttl_s": self.ttl})

    def invalidate(self, *keys, prefix=None, reason=""):
        with self._lock:
            targets = [k for k in self._data if prefix and k.startswith(prefix)]
            targets += [k for k in keys if k in self._data]
            for key in targets:
                self._data.pop(key, None)
        metrics.inc("cache_invalidations_total", len(targets), help_text="Сброшенные записи кэша")
        logger.info("cache invalidate", extra={
            "event": "cache.invalidate", "removed": len(targets),
            "prefix": prefix, "keys": list(keys), "reason": reason,
        })

    def clear(self):
        with self._lock:
            self._data.clear()

    def __len__(self):
        with self._lock:
            return len(self._data)

    def _evict(self, now):
        # Сначала удаляем записи, вышедшие и за окно stale; если мало — самые старые.
        dead = [k for k, (exp, _) in self._data.items() if exp + self.stale <= now]
        for key in dead:
            del self._data[key]
        if len(self._data) >= self.max_entries:
            oldest = sorted(self._data.items(), key=lambda item: item[1][0])
            for key, _ in oldest[: max(1, len(oldest) // 10)]:
                del self._data[key]


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


LIST_PREFIX = "events:list:"


def list_key(page, limit, category, date_from, date_to):
    return f"{LIST_PREFIX}page={page}&limit={limit}&category={category or ''}" \
           f"&from={date_from or ''}&to={date_to or ''}"


def event_key(event_id):
    return f"events:item:{event_id}"


events_cache = TTLCache(
    ttl_seconds=_env_float("EVENTS_CACHE_TTL_SECONDS", 60),
    stale_seconds=_env_float("EVENTS_CACHE_STALE_SECONDS", 300),
    max_entries=int(_env_float("EVENTS_CACHE_MAX_ENTRIES", 1000)),
)
