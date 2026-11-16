## docker compose ps
```
NAME                             IMAGE                          COMMAND                  SERVICE              CREATED          STATUS                           PORTS
event-map-attendance-service-1   event-map-attendance-service   "sh -c 'exec gunicor…"   attendance-service   23 seconds ago   Up 10 seconds (healthy)          0.0.0.0:5002->5002/tcp, [::]:5002->5002/tcp
event-map-db-1                   postgres:16-alpine             "docker-entrypoint.s…"   db                   26 seconds ago   Up 1 second (health: starting)   5432/tcp
event-map-events-service-1       event-map-events-service       "./docker-entrypoint…"   events-service       23 seconds ago   Up 16 seconds (healthy)          0.0.0.0:5001->5001/tcp, [::]:5001->5001/tcp
event-map-users-service-1        event-map-users-service        "./docker-entrypoint…"   users-service        23 seconds ago   Up 16 seconds (healthy)          0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
```
## scripts/smoke_test.sh --db-down
```
== 1. Health и метрики
  [OK]   users-service /health                                   200 
  [OK]   events-service /health (БД доступна)          200 
  [OK]   attendance-service /health (events доступен)    200 
  [OK]   events-service /metrics                                 200 
== 2. Аутентификация (ПР4)
  [OK]   регистрация организатора         201 
  [OK]   повторная регистрация → 409       409 
  [OK]   регистрация пользователя         201 
  [OK]   вход организатора (JWT)                 200 
  [OK]   вход пользователя (JWT)                 200 
  [OK]   неверный пароль → 401                   401 
== 3. CRUD событий и роли (ПР2, ПР4)
  [OK]   создание без токена → 401            401 
  [OK]   создание ролью user → 403                403 
  [OK]   невалидные данные → 400               400 
  [OK]   создание организатором → 201     201 
== 4. Кэш (ПР6)
  [OK]   GET /events — первый запрос               200 MISS
  [OK]   GET /events — повтор в пределах TTL    200 HIT
  [OK]   GET /events/{id} — первый запрос          200 MISS
  [OK]   GET /events/{id} — повтор                       200 HIT
  [OK]   PATCH события → 200                            200 
  [OK]   после PATCH кэш сброшен                  200 MISS
  [OK]   в ответе новое название
  [OK]   список после PATCH                           200 MISS
== 5. Attendance → events-service
  [OK]   отметка на существующее событие → 201 201 
  [OK]   отметка на несуществующее событие → 404 404 
  [OK]   счётчик участников                     200 
== 6. Отказ базы данных
  [OK]   events-service /health при остановленной БД → 503 503 
  [OK]   users-service /health при остановленной БД → 503 503 
  [OK]   закэшированный список отдаётся без БД 200 HIT
  [OK]   незакэшированный запрос → 503, без падения 503 
  [OK]   events-service /health после запуска БД → 200 200 
== 7. Удаление
  [OK]   DELETE → 204                                          204 
  [OK]   после удаления → 404                     404 

Итог: пройдено 32, ошибок 0
```
## events-service: события кэша и БД (ПР6)
```
{"ts": "2026-11-16T15:47:26.220+00:00", "level": "INFO", "service": "events-service", "logger": "events-service", "msg": "database connected", "event": "db.connected", "backend": "postgresql", "url": "postgresql+psycopg2://eventmap:***@db:5432/events_db"}
{"ts": "2026-11-16T15:47:26.233+00:00", "level": "INFO", "service": "events-service", "logger": "events-service", "msg": "categories seeded", "event": "db.seeded"}
{"ts": "2026-11-16T15:47:36.799+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache invalidate", "request_id": "smoke-1794844055", "event": "cache.invalidate", "removed": 0, "prefix": "events:list:", "keys": ["events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929"], "reason": "event created"}
{"ts": "2026-11-16T15:47:36.815+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794844055", "event": "cache.miss", "key": "events:list:page=1&limit=50&category=&from=&to=", "reason": "absent"}
{"ts": "2026-11-16T15:47:36.822+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.service", "msg": "events loaded from database", "request_id": "smoke-1794844055", "event": "db.query", "operation": "events.list", "rows": 1}
{"ts": "2026-11-16T15:47:36.822+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache set", "request_id": "smoke-1794844055", "event": "cache.set", "key": "events:list:page=1&limit=50&category=&from=&to=", "ttl_s": 60.0}
{"ts": "2026-11-16T15:47:36.834+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache hit", "request_id": "smoke-1794844055", "event": "cache.hit", "key": "events:list:page=1&limit=50&category=&from=&to=", "ttl_left_s": 60.0}
{"ts": "2026-11-16T15:47:36.847+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794844055", "event": "cache.miss", "key": "events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929", "reason": "absent"}
{"ts": "2026-11-16T15:47:36.850+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache set", "request_id": "smoke-1794844055", "event": "cache.set", "key": "events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929", "ttl_s": 60.0}
{"ts": "2026-11-16T15:47:36.862+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache hit", "request_id": "smoke-1794844055", "event": "cache.hit", "key": "events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929", "ttl_left_s": 60.0}
{"ts": "2026-11-16T15:47:36.877+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache invalidate", "request_id": "smoke-1794844055", "event": "cache.invalidate", "removed": 2, "prefix": "events:list:", "keys": ["events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929"], "reason": "event updated"}
{"ts": "2026-11-16T15:47:36.890+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794844055", "event": "cache.miss", "key": "events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929", "reason": "absent"}
{"ts": "2026-11-16T15:47:36.891+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache set", "request_id": "smoke-1794844055", "event": "cache.set", "key": "events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929", "ttl_s": 60.0}
{"ts": "2026-11-16T15:47:36.906+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794844055", "event": "cache.miss", "key": "events:list:page=1&limit=50&category=&from=&to=", "reason": "absent"}
{"ts": "2026-11-16T15:47:36.911+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.service", "msg": "events loaded from database", "request_id": "smoke-1794844055", "event": "db.query", "operation": "events.list", "rows": 1}
{"ts": "2026-11-16T15:47:36.911+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache set", "request_id": "smoke-1794844055", "event": "cache.set", "key": "events:list:page=1&limit=50&category=&from=&to=", "ttl_s": 60.0}
{"ts": "2026-11-16T15:47:36.931+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache hit", "request_id": "smoke-1794844055", "event": "cache.hit", "key": "events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929", "ttl_left_s": 60.0}
{"ts": "2026-11-16T15:47:36.945+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794844055", "event": "cache.miss", "key": "events:item:00000000-0000-0000-0000-000000000000", "reason": "absent"}
{"ts": "2026-11-16T15:47:36.974+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache hit", "request_id": "smoke-1794844055", "event": "cache.hit", "key": "events:list:page=1&limit=50&category=&from=&to=", "ttl_left_s": 59.9}
{"ts": "2026-11-16T15:47:39.426+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache hit", "request_id": "smoke-1794844055", "event": "cache.hit", "key": "events:list:page=1&limit=50&category=&from=&to=", "ttl_left_s": 57.5}
{"ts": "2026-11-16T15:47:39.439+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794844055", "event": "cache.miss", "key": "events:list:page=1&limit=7&category=&from=&to=", "reason": "absent"}
{"ts": "2026-11-16T15:47:39.484+00:00", "level": "ERROR", "service": "events-service", "logger": "events-service.service", "msg": "database unavailable", "request_id": "smoke-1794844055", "event": "db.unavailable", "operation": "events.list", "error": "could not translate host name \"db\" to address: Name or service not known\n"}
{"ts": "2026-11-16T15:47:40.819+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache invalidate", "request_id": "smoke-1794844055", "event": "cache.invalidate", "removed": 2, "prefix": "events:list:", "keys": ["events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929"], "reason": "event deleted"}
{"ts": "2026-11-16T15:47:40.832+00:00", "level": "INFO", "service": "events-service", "logger": "events-service.cache", "msg": "cache miss", "request_id": "smoke-1794844055", "event": "cache.miss", "key": "events:item:cbd60be6-a525-43fb-89d3-68cdcdc88929", "reason": "absent"}
```
## attendance-service → events-service
```
{"ts": "2026-11-16T15:47:36.931+00:00", "level": "INFO", "service": "attendance-service", "logger": "attendance-service.events-client", "msg": "events-service call", "request_id": "smoke-1794844055", "event": "events_service.call", "event_id": "cbd60be6-a525-43fb-89d3-68cdcdc88929", "status": 200, "attempt": 1, "duration_ms": 1.5}
{"ts": "2026-11-16T15:47:36.931+00:00", "level": "INFO", "service": "attendance-service", "logger": "attendance-service", "msg": "attendance marked", "request_id": "smoke-1794844055", "event": "attendance.created", "event_id": "cbd60be6-a525-43fb-89d3-68cdcdc88929", "user_id": "2", "status": "going"}
{"ts": "2026-11-16T15:47:36.947+00:00", "level": "INFO", "service": "attendance-service", "logger": "attendance-service.events-client", "msg": "events-service call", "request_id": "smoke-1794844055", "event": "events_service.call", "event_id": "00000000-0000-0000-0000-000000000000", "status": 404, "attempt": 1, "duration_ms": 3.0}
```
