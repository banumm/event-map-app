# ПР7. Протокол финальной проверки в контейнерах

Цель: убедиться, что система, поднятая **только** командой `docker compose up`
из чистого клона, полностью работоспособна.

## 1. Состав системы

| Сервис compose | Образ | Порт | Зависит от | Healthcheck |
|---|---|---|---|---|
| `db` | `postgres:16-alpine` | — (только внутренняя сеть) | — | `pg_isready` |
| `users-service` | `./users-service/Dockerfile` | 8000 | `db` (healthy) | `GET /health` (БД) |
| `events-service` | `./events-service/Dockerfile` | 5001 | `db` (healthy) | `GET /health` (БД) |
| `attendance-service` | `./attendance-service/Dockerfile` | 5002 | `events-service` (healthy) | `GET /health` (events-service) |

- Одна сеть `backend`; сервисы обращаются друг к другу по имени
  (`db:5432`, `http://events-service:5001`), не по `localhost`.
- Именованный том `pgdata` — данные PostgreSQL переживают `docker compose down` / `up`.
- База на сервис: `events_db` (Alembic) и `users_db` (Django), создаются
  `docker/postgres/init-databases.sh` при первой инициализации тома.
- Миграции применяются в entrypoint каждого контейнера
  (`alembic upgrade head`, `manage.py migrate`) до запуска gunicorn; при
  неготовой БД — до 10 попыток.
- Образы: `python:3.12-slim`, зависимости отдельным слоем, пользователь `app`
  (не root), запуск через gunicorn.
- Секреты только в `.env` (в `.gitignore`); `docker-compose.yml` содержит
  ссылки `${VAR:?…}` — без `.env` compose откажется стартовать.

## 2. Запуск с нуля

```bash
git clone https://github.com/banumm/event-map-app.git
cd event-map-app/event-map-app
cp .env.example .env          # заполнить POSTGRES_*, JWT_SECRET, DJANGO_SECRET_KEY
docker compose down -v        # чистый том БД (для проверки «с нуля»)
docker compose up -d --build --wait
docker compose ps             # все сервисы: running (healthy)
```

## 3. Проверка сценариев

Автоматически — скриптом (тот же скрипт выполняется в CI, job `docker`):

```bash
bash scripts/smoke_test.sh --db-down
```

| № | Сценарий (ПР) | Проверка | Ожидается | Факт |
|---|---|---|---|---|
| 1 | Health (ПР1, ПР7) | `GET /health` трёх сервисов | `200`, `checks.database.status = ok` | `200` ×3 ✅ |
| 2 | Метрики (ПР7) | `GET :5001/metrics` | `200`, `http_requests_total{…}` | `200` ✅ |
| 3 | Регистрация (ПР4) | `POST :8000/auth/register` организатора и пользователя | `201`; повтор — `409` | `201`, повтор `409` ✅ |
| 4 | Вход (ПР4) | `POST :8000/auth/login` | `200`, `access_token`; неверный пароль — `401` | `200` + токен, `401` ✅ |
| 5 | Роли (ПР4) | `POST :5001/events` без токена / user / organizer | `401` / `403` / `201` | `401` / `403` / `201` ✅ |
| 6 | Валидация (ПР2) | `POST :5001/events` с `{"title":"x"}` | `400 ValidationError` | `400` ✅ |
| 7 | Кэш (ПР6) | дважды `GET :5001/events` | `X-Cache: MISS`, затем `HIT` | `MISS` → `HIT` ✅ |
| 8 | Инвалидация (ПР6) | `PATCH` события, затем `GET` | `X-Cache: MISS`, новое название | `MISS`, новое название ✅ |
| 9 | Межсервисный вызов | `POST :5002/attendance` на существующее / несуществующее событие | `201` / `404` | `201` / `404` ✅ |
| 10 | Отказ БД (ПР7) | `docker compose stop db`, `GET /health` | `503`, `checks.database.status = error` | events `503`, users `503` ✅ |
| 11 | Отказ БД (ПР6) | закэшированный / новый `GET /events` | `200 HIT` / `503 ServiceUnavailable` | `200 HIT` / `503` ✅ |
| 12 | Восстановление | `docker compose start db`, `GET /health` | снова `200` без перезапуска сервисов | `200` ✅ |
| 13 | CRUD (ПР2) | `DELETE` события, затем `GET` | `204`, затем `404` | `204` → `404` ✅ |
| 14 | Сохранность данных (ПР3) | `docker compose restart`, `GET /events` | созданные ранее события на месте | не входит в smoke-тест — проверить вручную |

Итог скрипта: `Итог: пройдено N, ошибок 0`.

## 4. Наблюдаемость

```bash
docker compose logs -f events-service attendance-service   # JSON-логи
curl -s localhost:5001/metrics                              # метрики events-service
curl -s localhost:8000/metrics                              # метрики users-service
```

Каждый ответ содержит `X-Request-ID`; attendance-service передаёт его в
events-service, поэтому один запрос пользователя находится в логах обоих
сервисов по одному `request_id`.

## 5. CI

`.github/workflows/ci.yml` (в корне репозитория), запуск на каждый push и PR:

1. `lint` — `ruff check .`;
2. `test` — установка зависимостей, `python scripts/run_tests.py` (тесты
   трёх сервисов + coverage). Падение любого теста → ненулевой код выхода →
   job красный, следующие шаги не выполняются;
3. `docker` — `docker compose build`, `docker compose up --wait`,
   `scripts/smoke_test.sh --db-down`, вывод логов, `docker compose down -v`;
4. отчёт (статус контейнеров, вывод smoke-теста, логи кэша) публикуется в
   Summary запуска и в ветку `ci-results`.

Статус последнего запуска — бейдж в README и вкладка Actions репозитория.

## 6. Результат (фактический)

Запуск CI #3 (ветка `pr6-pr7`, коммит `c53f72e`, 12.11.2026), GitHub Actions, job «Docker build + compose smoke test»; полный отчёт — ветка [`ci-results`](https://github.com/banumm/event-map-app/tree/ci-results).

Запуск с нуля (чистый раннер, пустой том БД): образы собраны, миграции
применены в entrypoint, все сервисы `healthy`:

```
NAME                             IMAGE                          COMMAND                  SERVICE              CREATED          STATUS                           PORTS
event-map-attendance-service-1   event-map-attendance-service   "sh -c 'exec gunicor…"   attendance-service   22 seconds ago   Up 10 seconds (healthy)          0.0.0.0:5002->5002/tcp, [::]:5002->5002/tcp
event-map-db-1                   postgres:16-alpine             "docker-entrypoint.s…"   db                   23 seconds ago   Up 1 second (health: starting)   5432/tcp
event-map-events-service-1       event-map-events-service       "./docker-entrypoint…"   events-service       22 seconds ago   Up 16 seconds (healthy)          0.0.0.0:5001->5001/tcp, [::]:5001->5001/tcp
event-map-users-service-1        event-map-users-service        "./docker-entrypoint…"   users-service        22 seconds ago   Up 16 seconds (healthy)          0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
```

(`db` в момент снимка — `health: starting`: его только что перезапустил
сценарий отказа БД.)

Вывод `scripts/smoke_test.sh --db-down`:

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

Итог: **32 проверки, 0 ошибок**; CI зелёный на всех этапах (lint → tests → docker).
