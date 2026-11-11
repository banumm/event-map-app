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
| 1 | Health (ПР1, ПР7) | `GET /health` трёх сервисов | `200`, `checks.database.status = ok` | |
| 2 | Метрики (ПР7) | `GET :5001/metrics` | `200`, `http_requests_total{…}` | |
| 3 | Регистрация (ПР4) | `POST :8000/auth/register` организатора и пользователя | `201`; повтор — `409` | |
| 4 | Вход (ПР4) | `POST :8000/auth/login` | `200`, `access_token`; неверный пароль — `401` | |
| 5 | Роли (ПР4) | `POST :5001/events` без токена / user / organizer | `401` / `403` / `201` | |
| 6 | Валидация (ПР2) | `POST :5001/events` с `{"title":"x"}` | `400 ValidationError` | |
| 7 | Кэш (ПР6) | дважды `GET :5001/events` | `X-Cache: MISS`, затем `HIT` | |
| 8 | Инвалидация (ПР6) | `PATCH` события, затем `GET` | `X-Cache: MISS`, новое название | |
| 9 | Межсервисный вызов | `POST :5002/attendance` на существующее / несуществующее событие | `201` / `404` | |
| 10 | Отказ БД (ПР7) | `docker compose stop db`, `GET /health` | `503`, `checks.database.status = error` | |
| 11 | Отказ БД (ПР6) | закэшированный / новый `GET /events` | `200 HIT` / `503 ServiceUnavailable` | |
| 12 | Восстановление | `docker compose start db`, `GET /health` | снова `200` без перезапуска сервисов | |
| 13 | CRUD (ПР2) | `DELETE` события, затем `GET` | `204`, затем `404` | |
| 14 | Сохранность данных (ПР3) | `docker compose restart`, `GET /events` | созданные ранее события на месте | |

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
   `scripts/smoke_test.sh --db-down`, вывод логов, `docker compose down -v`.

Статус последнего запуска — бейдж в README и вкладка Actions репозитория.

## 6. Результат

> Заполнить после запуска: дата, ветка и SHA коммита, вывод
> `docker compose ps` и итоговая строка `scripts/smoke_test.sh`,
> ссылка на зелёный запуск CI.
