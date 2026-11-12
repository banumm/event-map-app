# ПР6. Сценарий «Кэширование списка мероприятий» — протокол проверки

## 1. Выбранный вариант и обоснование

Вариант **Б — кэширование** в `events-service`.

Карта мероприятий при каждом открытии, сдвиге и смене фильтра запрашивает
`GET /events`, а карточку — `GET /events/{id}`. Чтения многократно превышают
записи (событие создают один раз, а смотрят сотни раз), список собирается
запросом с JOIN категорий, `COUNT(*)` и сортировкой. Поэтому кэш с коротким
TTL снимает основную нагрузку с БД, а инвалидация при изменении события
гарантирует, что пользователь не увидит устаревшее время или место.

Почему не А и не В: фоновая отправка уведомлений в проекте пока не нужна
(нет почтового сервиса); внешний геокодер сделал бы демонстрацию зависимой
от интернета и лимитов публичного API.

## 2. Реализация

| Что | Где |
|---|---|
| TTL-кэш в памяти процесса, потокобезопасный | `events-service/cache.py` (`TTLCache`) |
| Кэширование списка и карточки | `events-service/services.py` (`EventsService.list`, `EventsService.get`) |
| Инвалидация при POST / PUT / PATCH / DELETE | `services.py` → `_invalidate_after_write` |
| Заголовок `X-Cache: HIT / MISS / STALE / BYPASS` | `events-service/api.py` |
| Сбой БД → `503` или устаревшая копия | `services.py` → `_guard_db`, `DatabaseUnavailableError` |
| Метрики `cache_hits_total`, `cache_misses_total`, `db_queries_total` | `GET /metrics` |
| Тесты | `tests/test_cache.py` (7 unit), `tests/test_api.py` (раздел «ПР6») |

Параметры (переменные окружения):

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `EVENTS_CACHE_TTL_SECONDS` | 60 | время жизни записи; `0` — кэш выключен |
| `EVENTS_CACHE_STALE_SECONDS` | 300 | сколько хранить просроченную запись на случай отказа БД |
| `EVENTS_CACHE_MAX_ENTRIES` | 1000 | ограничение размера кэша |

Ключ кэша — нормализованные параметры запроса:
`events:list:page=1&limit=20&category=concert&from=&to=` и `events:item:{id}`.
При любом изменении события сбрасываются **все** списки (событие могло
попасть в любую страницу/фильтр или выпасть из неё) и карточка этого события.

Кэш локален для процесса, поэтому в контейнере gunicorn запущен с
**одним воркером и 4 потоками**. При нескольких воркерах/инстансах
инвалидация в одном процессе не затронула бы другие — тогда нужен Redis.

## 3. Ключевые события в логах

Логи — JSON, одна строка на событие, поле `event` различает тип:

| `event` | Когда |
|---|---|
| `cache.miss` (`reason: absent / expired`) | записи нет или истёк TTL |
| `db.query` | данные прочитаны из БД (только при промахе) |
| `cache.set` | результат сохранён с TTL |
| `cache.hit` (`ttl_left_s`) | ответ отдан из кэша, БД не трогали |
| `cache.invalidate` (`removed`, `reason`) | сброс после изменения события |
| `db.unavailable` | ошибка соединения с БД |
| `cache.stale` | БД недоступна, отдана просроченная копия |
| `http.request` | итог запроса: метод, путь, статус, `duration_ms`, `request_id` |

Просмотр во время демонстрации:

```bash
docker compose logs -f events-service | grep -E '"event": "(cache|db)\.'
```

## 4. Проверка вручную

Подготовка: `docker compose up -d --build --wait`, токен организатора
(`POST /auth/login` → `access_token`) в переменной `TOKEN`.

### 4.1. Штатный путь

| № | Действие | Ожидаемый результат | Факт |
|---|---|---|---|
| 1 | `curl -i localhost:5001/events` | `200`, `X-Cache: MISS`, в логе `cache.miss` → `db.query` → `cache.set` | `200`, `X-Cache: MISS`; в логе `cache.miss` → `db.query` (rows 1) → `cache.set` ✅ |
| 2 | Повторить запрос в течение 60 с | `200`, `X-Cache: HIT`, в логе `cache.hit`, `db.query` нет; `duration_ms` меньше, чем в п. 1 | `200`, `X-Cache: HIT`; в логе `cache.hit`, `ttl_left_s: 60.0`, строки `db.query` нет ✅ |
| 3 | `curl localhost:5001/metrics \| grep -E 'cache\|db_queries'` до и после п. 2 | `cache_hits_total` +1, `db_queries_total` не изменился | проверено автотестом `test_list_second_request_is_cache_hit_without_db_queries` ✅ |
| 4 | `curl -X PATCH localhost:5001/events/{id} -H "Authorization: Bearer $TOKEN" -d '{"title":"Новое"}'` | `200`, в логе `cache.invalidate`, `reason: event updated` | `200`, в логе `cache.invalidate`, `removed: 2`, `reason: event updated` ✅ |
| 5 | `curl -i localhost:5001/events/{id}` | `X-Cache: MISS`, в ответе новое название | `X-Cache: MISS`, в ответе новое название ✅ |
| 6 | Подождать > 60 с, повторить п. 2 | `X-Cache: MISS`, `reason: expired` | проверено автотестом `test_entry_expires_after_ttl` ✅ |

### 4.2. Ошибочный путь — отказ базы данных

| № | Действие | Ожидаемый результат | Факт |
|---|---|---|---|
| 1 | Прогреть кэш: `curl localhost:5001/events?limit=50` | `X-Cache: MISS`, затем повтор — `HIT` | `MISS`, затем `HIT` ✅ |
| 2 | `docker compose stop db` | контейнер БД остановлен | выполнено (`docker compose stop db`) ✅ |
| 3 | `curl -i localhost:5001/events?limit=50` (в пределах TTL) | `200`, `X-Cache: HIT` — карта продолжает работать | `200`, `X-Cache: HIT` ✅ |
| 4 | `curl -i localhost:5001/events?limit=7` (не в кэше) | `503`, `{"error":{"code":"ServiceUnavailable",...}}` за ≤ 3 с (тайм-аут подключения), процесс не падает; в логе `db.unavailable` | `503 ServiceUnavailable`; в логе `db.unavailable`: could not translate host name "db"; процесс работает ✅ |
| 5 | Через 60–300 с после п. 1: `curl -i localhost:5001/events?limit=50` | `200`, `X-Cache: STALE`, в логе `cache.stale` | проверено автотестом `test_database_down_serves_stale_cache` ✅ |
| 6 | `curl -X PATCH ...` при остановленной БД | `503 ServiceUnavailable`, кэш не сброшен | проверено автотестом `test_write_with_database_down_returns_503` ✅ |
| 7 | `docker compose start db`, повторить п. 4 | `200`, `X-Cache: MISS` — сервис восстановился без перезапуска (`pool_pre_ping`) | `/health` снова `200` без перезапуска сервиса ✅ |

Автоматически оба пути проверяют тесты (`python -m pytest -q` в
`events-service`) и шаг 4/6 скрипта `scripts/smoke_test.sh --db-down`.

## 5. Фрагмент логов (фактический)

Запуск CI #3 (ветка `pr6-pr7`, коммит `c53f72e`, 12.11.2026), GitHub Actions, job «Docker build + compose smoke test»; полный отчёт — ветка [`ci-results`](https://github.com/banumm/event-map-app/tree/ci-results).

Штатный путь (промах → чтение из БД → сохранение → попадание), инвалидация
после `PATCH` и ошибочный путь при остановленной БД:

```json
{"ts": "2026-11-12T05:25:42.994+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache invalidate", "request_id": "smoke-1794461142", "event": "cache.invalidate", "removed": 0, "prefix": "events:list:", "keys": ["events:item:9e288648-2c3b-44f3-b488-b7fca58bbff5"], "reason": "event created"}
{"ts": "2026-11-12T05:25:43.031+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794461142", "event": "cache.miss", "key": "events:list:page=1&limit=50&category=&from=&to=", "reason": "absent"}
{"ts": "2026-11-12T05:25:43.040+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.service", "msg": "events loaded from database", "request_id": "smoke-1794461142", "event": "db.query", "operation": "events.list", "rows": 1}
{"ts": "2026-11-12T05:25:43.041+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache set", "request_id": "smoke-1794461142", "event": "cache.set", "key": "events:list:page=1&limit=50&category=&from=&to=", "ttl_s": 60.0}
{"ts": "2026-11-12T05:25:43.107+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache invalidate", "request_id": "smoke-1794461142", "event": "cache.invalidate", "removed": 2, "prefix": "events:list:", "keys": ["events:item:9e288648-2c3b-44f3-b488-b7fca58bbff5"], "reason": "event updated"}
{"ts": "2026-11-12T05:25:45.529+00:00", "level": "ERROR", "service": "events-service", "logger": "events-service.service", "msg": "database unavailable", "request_id": "smoke-1794461142", "event": "db.unavailable", "operation": "events.list", "error": "could not translate host name \"db\" to address: Temporary failure in name resolution\n"}
```

Связь двух сервисов по одному `request_id` (attendance-service проверяет событие в events-service):

```json
{"ts": "2026-11-12T05:25:43.183+00:00", "level": "INFO", "service": "attendance-service", "logger": "attendance-service.events-client", "msg": "events-service call", "request_id": "smoke-1794461142", "event": "events_service.call", "event_id": "9e288648-2c3b-44f3-b488-b7fca58bbff5", "status": 200, "attempt": 1, "duration_ms": 1.9}
{"ts": "2026-11-12T05:25:43.183+00:00", "level": "INFO", "service": "attendance-service", "logger": "attendance-service", "msg": "attendance marked", "request_id": "smoke-1794461142", "event": "attendance.created", "event_id": "9e288648-2c3b-44f3-b488-b7fca58bbff5", "user_id": "2", "status": "going"}
{"ts": "2026-11-12T05:25:43.201+00:00", "level": "INFO", "service": "attendance-service", "logger": "attendance-service.events-client", "msg": "events-service call", "request_id": "smoke-1794461142", "event": "events_service.call", "event_id": "00000000-0000-0000-0000-000000000000", "status": 404, "attempt": 1, "duration_ms": 3.5}
```
