# Event Map App

Приложение-карта локальных мероприятий: пользователи находят события рядом с собой
(концерты, лекции, выставки, встречи) на карте, фильтруют по дате и категории,
отмечают участие. Организаторы публикуют события и видят отклик аудитории.

Подробнее о бизнес-задаче и user stories — в [docs/requirements.md](docs/requirements.md).

## Архитектура

![Архитектурная схема](docs/architecture.svg)

Клиент публично обращается к **Events Service** и **Attendance Service**.
**Attendance Service** внутренне проверяет актуальность события в **Events Service**.
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

- **72 теста**: 28 в users-service (Django `TestCase`/`SimpleTestCase`), 28 в
  events-service и 16 в attendance-service (pytest + Flask test client).
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

Покрытие по сервисам (подробнее — [docs/testing.md](docs/testing.md)):

| Сервис | Тестов | Покрытие |
|---|---:|---:|
| users-service | 28 | 88% |
| events-service | 28 | 82% |
| attendance-service | 16 | 93% |
| **Итого** | **72** | **≈85%** |

Тесты изолированы: Django создаёт отдельную тестовую БД и откатывает
транзакции; events-service использует `test_events.db`, миграции Alembic и
очистку таблиц перед каждым тестом; attendance-service очищает in-memory
хранилище. Рабочие данные не затрагиваются.

Чек-лист безопасности API и описание исправленной проблемы (rate limiting) —
в [docs/testing.md](docs/testing.md#4-чек-лист-проверки-безопасности-api).

## Структура репозитория

```
event-map-app/
├── README.md
├── requirements-dev.txt     ← pytest + coverage
├── scripts/
│   └── run_tests.py         ← все тесты + отчёт coverage
├── docs/
│   ├── requirements.md      ← user stories
│   ├── architecture.svg
│   ├── auth.md              ← ПР4: модель, JWT, роли, ошибки
│   ├── auth-check.md        ← ПР4: протокол проверки доступа
│   ├── testing.md           ← ПР5: тесты, покрытие, чек-лист безопасности
│   ├── security.md          ← OWASP API Top 10
│   └── srs1/                ← СРС1: PPTX, PDF, диаграммы, генератор
├── events-service/
│   ├── app.py               ← точка входа
│   ├── api.py               ← маршруты (защита JWT)
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
│   ├── app.py               ← защита JWT
│   ├── auth.py, errors.py, validation.py
│   ├── tests/               ← pytest: unit + API
│   └── verify.py
└── users-service/
    ├── manage.py
    ├── config/              ← settings, urls
    ├── accounts/            ← модель User, JWT, views, errors, middleware
    │   ├── auth.py, ratelimit.py
    │   ├── migrations/0001_initial.py
    │   ├── management/commands/create_admin.py
    │   ├── tests.py         ← API-тесты
    │   └── tests_unit.py    ← unit-тесты
    └── requirements.txt
```
