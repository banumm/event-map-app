# Event Map App

[![CI](https://github.com/banumm/event-map-app/actions/workflows/ci.yml/badge.svg)](https://github.com/banumm/event-map-app/actions/workflows/ci.yml)

Приложение-карта локальных мероприятий: пользователи находят события рядом с собой
(концерты, лекции, выставки, встречи) на карте, фильтруют по дате и категории,
отмечают участие. Организаторы публикуют события и видят отклик аудитории.

Подробнее о бизнес-задаче и user stories — в [docs/requirements.md](docs/requirements.md).

## Архитектура

![Архитектурная схема](docs/architecture.svg)

Клиент публично обращается к **Events Service** и **Attendance Service**.
**Attendance Service** перед отметкой участия проверяет, что событие существует, через
`GET /events/{id}` в **Events Service** (тайм-аут, повторы, `503` при недоступности —
`attendance-service/events_client.py`).
**Users Service** выдаёт JWT; Events и Attendance проверяют подпись, срок действия
и роль локально общим секретом, не храня общую сессию. Сам Users Service
находится во внутренней зоне и наружу не публикуется (кроме API аутентификации).

## Сервисы

| Сервис | Ответственность | Владеет данными | Стек | Порт |
|---|---|---|---|---|
| **events-service** | CRUD мероприятий: название, описание, локация, дата/время, категория | events, categories | Flask | 5001 |
| **attendance-service** | Отметки "пойду / интересно", счётчики участников | attendance-записи (user↔event) | Flask | 5002 |
| **users-service** | Регистрация, логин, JWT, роли (user / organizer / admin), профиль | users, roles | Django | 8000 |

**Почему такой стек:**
- **Flask** для Events и Attendance — обоим сервисам нужен простой, лёгкий CRUD/REST без
  сложной админки; Flask даёт минимум лишнего кода.
- **Django** для Users — нужна полноценная система аутентификации, хеширование паролей,
  управление пользователями и готовая админ-панель (`django.contrib.auth`, `django.contrib.admin`).

## ПР4: аутентификация, авторизация, валидация и ошибки

- **Модель пользователя**: `users-service/accounts/models.py`, миграция
  `accounts/migrations/0001_initial.py`. Поля: `username`, `email` (уникальный),
  `password` (только хэш Argon2), `role`, `date_joined` (дата регистрации).
- **Регистрация**: `POST /auth/register` — валидация логина/email/пароля, проверка
  уникальности, хэширование Argon2. Дубликат возвращает `409 Conflict`.
- **Вход**: `POST /auth/login` — принимает `username` или `email`, при ошибке `401`,
  при успехе возвращает JWT (`access_token`).
- **Защита маршрутов**: JWT Bearer проверяется в events-service и attendance-service
  (`auth.py` каждого сервиса). Изменяющие запросы без валидного токена возвращают `401`.
- **Роли**:
  - `user` — просмотр событий, отметка только своего участия;
  - `organizer` — создание событий и изменение/удаление только своих событий;
  - `admin` — любые события, просмотр пользователей и чужих отметок.
  Аутентификация (`401`) и авторизация (`403`) реализованы отдельно.
- **Единый формат ошибок** для всех сервисов:
  ```json
  {"error": {"code": "Forbidden", "message": "Доступ запрещён", "details": []}}
  ```
  Глобальные обработчики не отдают стектрейсы и приводят к этому формату
  ответы 400/401/403/404/405/409/500.
- **Документация**: [docs/auth.md](docs/auth.md) — модель, JWT, роли, защита;
  [docs/auth-check.md](docs/auth-check.md) — протокол проверки трёх сценариев доступа.

### JWT или сессия

Выбран **JWT** (HS256, срок действия 60 минут, issuer `event-map-users-service`).
Причина: сервисы разделены, и events-service/attendance-service должны проверять
пользователя без обращения к сессионному хранилищу users-service. JWT подписывается
общим секретом `JWT_SECRET`; секрет и issuer задаются переменными окружения.
Django-сессии оставлены только для админ-панели. Ограничение JWT — отзыв токена до
истечения срока не поддерживается (в токене есть `jti`, при необходимости можно
добавить blacklist).

## ПР5: автоматизированные тесты и безопасность API

- **72 теста** на момент ПР5: 28 в users-service (Django `TestCase`/`SimpleTestCase`), 28 в
  events-service и 16 в attendance-service (pytest + Flask test client). В ПР6–ПР7
  добавлены тесты кэша, `/health`, `/metrics` и межсервисного вызова — см. «Тестирование».
- **Покрытие ≈85%** по трём сервисам: users-service — 88%, events-service — 82%,
  attendance-service — 93%. Отчёт и комментарий по слабым местам —
  [docs/testing.md](docs/testing.md).
- **Изоляция тестов**: отдельная тестовая БД Django, отдельный `test_events.db`
  с миграциями Alembic и очисткой таблиц, очистка in-memory attendance-хранилища.
- **Проверка безопасности**: чек-лист в [docs/testing.md](docs/testing.md#4-чек-лист-проверки-безопасности-api)
  — ORM вместо конкатенации SQL, отсутствие хэша пароля в ответах, корректные
  401/403, mass assignment, валидация, stack trace.
- **Найдено и исправлено**: на `/auth/login` и `/auth/register` не было
  ограничения частоты запросов. Добавлен in-memory rate limiter
  (`accounts/ratelimit.py`, 10 запросов за 60 секунд на IP, `429` + `Retry-After`).
  Дополнительно тесты выявили и закрыли дефект: после `PATCH`/`PUT` категория
  события возвращалась старая.
- Подробно: [docs/testing.md](docs/testing.md).

## ПР6: кэширование списка мероприятий

**Выбран вариант Б — кэширование.** Карта запрашивает `GET /events` при каждом открытии,
сдвиге и смене фильтра, а события меняются редко: чтений на порядки больше, чем записей.
Кэш с коротким TTL снимает с БД самый частый и самый дорогой запрос (JOIN категорий +
`COUNT` + сортировка), а сброс при изменении события не даёт показать устаревшие время
или место проведения.

- `events-service/cache.py` — потокобезопасный TTL-кэш в памяти процесса
  (`EVENTS_CACHE_TTL_SECONDS=60`). Кэшируются `GET /events` (ключ — параметры
  страницы и фильтров) и `GET /events/{id}`.
- Статус в заголовке ответа `X-Cache: MISS | HIT | STALE | BYPASS`; на `HIT` запросов к БД
  нет (метрика `db_queries_total` не растёт).
- **Инвалидация:** `POST`/`PUT`/`PATCH`/`DELETE` после commit сбрасывают все списки и
  карточку изменённого события.
- **Ошибочный путь:** при недоступной БД — `503 ServiceUnavailable` без падения и
  зависания (тайм-аут подключения 3 с); если в кэше есть просроченная копия
  (до `EVENTS_CACHE_STALE_SECONDS=300`), она отдаётся с `X-Cache: STALE`.
- **Логи:** `cache.hit`, `cache.miss`, `cache.set`, `cache.invalidate`, `db.query`,
  `db.unavailable`, `cache.stale`.
- Протокол проверки обоих путей и фрагмент логов — [docs/async-scenario.md](docs/async-scenario.md).

## ПР7: контейнеризация, развёртывание и наблюдаемость

- **Dockerfile** у каждого сервиса: `python:3.12-slim`, зависимости отдельным слоем,
  пользователь `app` (не root), запуск через **gunicorn**.
- **docker-compose.yml**: `db` (PostgreSQL 16, том `pgdata`) + три сервиса в сети
  `backend`, обращение по имени сервиса, healthcheck у каждого, `depends_on` по
  состоянию `healthy`.
- **Секреты** — только в `.env` (в `.gitignore`); шаблон [.env.example](.env.example).
  Без `.env` compose не стартует (`${VAR:?…}`).
- **Миграции при развёртывании** — `docker-entrypoint.sh`: `alembic upgrade head` /
  `manage.py migrate` до старта приложения.
- **/health** проверяет зависимости: БД (events, users), events-service (attendance);
  при сбое — `503` и описание в `checks`.
- **Наблюдаемость**: JSON-логи (время, уровень, сервис, `request_id`), заголовок
  `X-Request-ID` (пробрасывается между сервисами), `GET /metrics` в формате Prometheus
  (`http_requests_total`, `http_request_duration_seconds_sum`, `cache_*`, `db_queries_total`).
- **CI** — [.github/workflows/ci.yml](../.github/workflows/ci.yml): ruff → тесты +
  coverage → сборка образов → `docker compose up --wait` → `scripts/smoke_test.sh --db-down`.
- Протокол финальной проверки — [docs/deploy-check.md](docs/deploy-check.md).
- Отчёт последнего запуска CI (`docker compose ps`, вывод smoke-теста — 32 проверки,
  логи кэша) автоматически сохраняется в ветку
  [`ci-results`](https://github.com/banumm/event-map-app/tree/ci-results).

## СРС №1: презентация

- [СРС1_Фамилия_Имя_Группа.pptx](docs/srs1/СРС1_Фамилия_Имя_Группа.pptx) — 17 слайдов, 16:9.
- [СРС1_Фамилия_Имя_Группа.pdf](docs/srs1/СРС1_Фамилия_Имя_Группа.pdf) — PDF-версия.
- [docs/security.md](docs/security.md) — анализ угроз OWASP API Top 10 и меры защиты.
- [docs/srs1/build_presentation.py](docs/srs1/build_presentation.py) — генератор презентации и диаграмм.
- [docs/srs1/README.md](docs/srs1/README.md) — что заменить перед сдачей и как пересобрать.

Перед сдачей заменить `Фамилия Имя, группа ____` на реальные данные, вставить
ссылку на Kanban, ветку и SHA последнего коммита. Пересборка:

```bash
python docs/srs1/build_presentation.py
```

## Как запустить

### Вся система через Docker Compose (рекомендуется)

Требования: Docker 24+ с Compose v2; для `smoke_test.sh` — bash, curl, python3
(на Windows — Git Bash). Команды выполняются в папке проекта `event-map-app/`
внутри репозитория.

```bash
cp .env.example .env              # заполнить POSTGRES_USER/PASSWORD, JWT_SECRET, DJANGO_SECRET_KEY
docker compose up -d --build --wait
docker compose ps                 # все сервисы healthy
bash scripts/smoke_test.sh        # сквозная проверка (с --db-down — ещё и отказ БД)
```

| Сервис | URL |
|---|---|
| users-service | http://localhost:8000/health |
| events-service | http://localhost:5001/health, `/metrics` |
| attendance-service | http://localhost:5002/health |

Остановка: `docker compose down` (данные БД сохраняются в томе `pgdata`),
`docker compose down -v` — с удалением данных.

### Локально без Docker

Требования: Python 3.12.

Общий секрет JWT должен совпадать во всех сервисах (по умолчанию
`dev-jwt-secret-change-me`; для реального окружения задайте свой `JWT_SECRET`).

### Users Service (Django)
```bash
cd users-service
pip install -r requirements.txt
cp .env.example .env              # при необходимости
python manage.py migrate
python manage.py create_admin --username admin --email admin@example.com --password 'StrongPass123'
python manage.py runserver 0.0.0.0:8000
# http://localhost:8000/health
```

### Events Service (Flask)
```bash
cd events-service
pip install -r requirements.txt
cp .env.example .env              # DATABASE_URL и JWT_SECRET
alembic upgrade head
python app.py
# http://localhost:5001
```

Контракт API: `openapi.yaml`, описание — `docs/api.md`, примеры — `docs/examples.http`.
Проверки: `python verify.py` (CRUD + JWT + роли), `verify_schema.py`, `verify_persistence.py`,
`verify_tx.py`.

### Attendance Service (Flask)
```bash
cd attendance-service
pip install -r requirements.txt
cp .env.example .env              # JWT_SECRET должен совпадать
python app.py
# http://localhost:5002
python verify.py
```

## Основные эндпоинты

| Метод | Путь | Доступ |
|---|---|---|
| POST | `/auth/register` | публично |
| POST | `/auth/login` | публично |
| GET | `/auth/me` | любой валидный JWT |
| GET | `/users` | admin |
| GET | `/users/{id}` | внутренний (users-service) |
| GET | `/events`, `/events/{id}` | публично |
| POST / PUT / PATCH / DELETE | `/events`, `/events/{id}` | organizer/admin; чужие события — только admin |
| POST | `/attendance` | любой JWT; своё участие (admin — любое) |
| GET | `/attendance/event/{id}` | публично |
| GET | `/attendance/user/{id}` | сам пользователь или admin |
| GET | `/health` (все сервисы) | публично; `503`, если недоступна зависимость |
| GET | `/metrics` (все сервисы) | метрики Prometheus (во внутренней сети) |

## Тестирование

Установить тестовые зависимости и запустить все наборы с отчётом о покрытии:

```bash
python -m pip install -r requirements-dev.txt
python scripts/run_tests.py
```

Или по отдельности:

```bash
cd users-service
python manage.py test

cd events-service
python -m pytest -q

cd attendance-service
python -m pytest -q
```

Количество тестов (покрытие — замер ПР5, подробнее в [docs/testing.md](docs/testing.md);
актуальные цифры печатает `scripts/run_tests.py` и job `test` в CI):

| Сервис | Тестов (ПР5) | Тестов (ПР7) | Покрытие (ПР5) |
|---|---:|---:|---:|
| users-service | 28 | 31 | 88% |
| events-service | 28 | 49 | 82% |
| attendance-service | 16 | 24 | 93% |
| **Итого** | **72** | **104** | **≈85%** |

Тесты изолированы: Django создаёт отдельную тестовую БД и откатывает
транзакции; events-service использует `test_events.db`, миграции Alembic и
очистку таблиц перед каждым тестом; attendance-service очищает in-memory
хранилище. Рабочие данные не затрагиваются.

Чек-лист безопасности API и описание исправленной проблемы (rate limiting) —
в [docs/testing.md](docs/testing.md#4-чек-лист-проверки-безопасности-api).

## Структура репозитория

```
event-map-app/                ← корень репозитория
├── .github/workflows/ci.yml  ← ПР7: CI (lint → tests → docker → smoke)
└── event-map-app/            ← проект
├── README.md
├── docker-compose.yml       ← ПР7: db + 3 сервиса
├── .env.example             ← ПР7: переменные compose без значений
├── ruff.toml                ← конфигурация линтера
├── docker/postgres/         ← init-скрипт: БД на сервис
├── requirements-dev.txt     ← pytest + coverage
├── scripts/
│   ├── run_tests.py         ← все тесты + отчёт coverage
│   └── smoke_test.sh        ← ПР7: сквозная проверка в контейнерах
├── docs/
│   ├── requirements.md      ← user stories
│   ├── architecture.svg
│   ├── auth.md              ← ПР4: модель, JWT, роли, ошибки
│   ├── auth-check.md        ← ПР4: протокол проверки доступа
│   ├── testing.md           ← ПР5: тесты, покрытие, чек-лист безопасности
│   ├── async-scenario.md    ← ПР6: протокол проверки кэша
│   ├── deploy-check.md      ← ПР7: протокол проверки в контейнерах
│   ├── security.md          ← OWASP API Top 10
│   └── srs1/                ← СРС1: PPTX, PDF, диаграммы, генератор
├── events-service/
│   ├── Dockerfile, docker-entrypoint.sh  ← ПР7: образ + миграции на старте
│   ├── app.py               ← точка входа, /health с проверкой БД
│   ├── cache.py             ← ПР6: TTL-кэш
│   ├── observability.py     ← ПР7: JSON-логи, X-Request-ID, /metrics
│   ├── api.py               ← маршруты (защита JWT, X-Cache)
│   ├── auth.py              ← проверка JWT/ролей
│   ├── errors.py            ← единый формат ошибок
│   ├── services.py          ← бизнес-логика и проверка владельца
│   ├── validation.py        ← валидация входных данных
│   ├── models.py, database.py, repository/
│   ├── alembic/versions/    ← миграции
│   ├── openapi.yaml         ← контракт REST API
│   ├── tests/               ← pytest: unit + API
│   ├── verify.py            ← сквозной автотест CRUD + auth
│   └── docs/                ← api.md, examples.http, db_schema.md
├── attendance-service/
│   ├── Dockerfile
│   ├── app.py               ← защита JWT, /health с проверкой events-service
│   ├── events_client.py     ← вызов events-service: тайм-аут, повторы, 503
│   ├── observability.py
│   ├── auth.py, errors.py, validation.py
│   ├── tests/               ← pytest: unit + API
│   └── verify.py
└── users-service/
    ├── Dockerfile, docker-entrypoint.sh
    ├── manage.py
    ├── config/              ← settings (DATABASE_URL, LOGGING), urls
    ├── accounts/            ← модель User, JWT, views, errors, middleware
    │   ├── auth.py, ratelimit.py
    │   ├── observability.py ← ПР7: JSON-логи, X-Request-ID, /metrics
    │   ├── migrations/0001_initial.py
    │   ├── management/commands/create_admin.py
    │   ├── tests.py         ← API-тесты
    │   └── tests_unit.py    ← unit-тесты
    └── requirements.txt
```
