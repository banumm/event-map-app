# ПР5. Автоматизированные тесты и безопасность API

Документ описывает тестовый контур проекта Event Map App, отчёт о покрытии,
изоляцию тестовых данных и чек-лист проверки типовых уязвимостей API.
Команды запуска вынесены в [README](../README.md#тестирование).

Дата выполнения: 2026-11-04.

Готовая версия отчёта: [ПР5_Фамилия_Имя_Группа_документ.docx](pr5/ПР5_Фамилия_Имя_Группа_документ.docx)
и [PDF](pr5/ПР5_Фамилия_Имя_Группа_документ.pdf). Перед сдачей заменить
ФИО и группу, затем пересобрать: `python docs/pr5/build_pr5_document.py`.

## 1. Структура тестов

| Сервис | Файлы | Что проверяется | Тестов |
|---|---|---|---|
| users-service | `accounts/tests_unit.py` | валидация регистрации, разбор JSON, JWT, формат ответа пользователя, rate limiter | 14 |
| users-service | `accounts/tests.py` | API-сценарии регистрации, входа, `/auth/me`, `/users`, 401/403/409/429, единые ошибки | 14 |
| events-service | `tests/test_validation.py` | валидация события, координат, даты, категории, query-параметров | 12 |
| events-service | `tests/test_api.py` | CRUD, роли, владелец, JWT, 400/401/403/404, единые ошибки | 16 |
| attendance-service | `tests/test_validation.py` | валидация тела отметки участия | 6 |
| attendance-service | `tests/test_api.py` | отметка себя/другого, роли, чтение своих/чужих записей, 401/403/404 | 10 |
| **Итого** | | | **72** |

Модульные тесты не обращаются к сети и (кроме Django `SimpleTestCase`) к БД.
API-тесты используют штатные test client'ы Flask/Django и реальные маршруты.

## 2. Изоляция тестовых данных

| Сервис | Механизм | Гарантия |
|---|---|---|
| users-service | Django `TestCase` создаёт отдельную тестовую БД (SQLite in-memory) и откатывает транзакцию после каждого теста | рабочая `db.sqlite3` не затрагивается; тесты независимы |
| events-service | отдельный файл `test_events.db`, схема создаётся `alembic upgrade head`; autouse-фикстура очищает `events` и `event_participants` перед каждым тестом | тесты проходят в любом порядке и повторно |
| attendance-service | autouse-фикстура очищает in-memory `attendance_db` до и после каждого теста | нет зависимости от порядка выполнения |

Тестовые БД и файлы покрытия исключены из Git (`.gitignore`).

## 3. Отчёт о покрытии

Команда:

```bash
python scripts/run_tests.py
```

Скрипт запускает все три набора и печатает `coverage report -m` для каждого
сервиса. Данные сохраняются в `.coverage-data/`.

| Сервис | Покрытие | Покрыто/всего инструкций | Комментарий |
|---|---:|---:|---|
| users-service | **88%** | 280 / 320 | не покрыты ветки глобального middleware для `Http404`/`PermissionDenied`, management-команда `create_admin` и внутренний `GET /users/{id}` |
| events-service | **82%** | 498 / 605 | 0% у неиспользуемых в текущем API `storage.py`, `repository/participants.py`, `repository/users.py` (наследие ПР2–ПР3); остальное — ветки фильтров и ошибок |
| attendance-service | **93%** | 130 / 140 | не покрыты ветки `root`/`health` и часть обработчиков ошибок |
| **Итого** | **≈85%** | 908 / 1065 | с учётом трёх сервисов |

Покрытие считается по исходному коду без файлов тестов, миграций и
management-команд. Жёсткого порога нет: важнее, что покрыты все ключевые
пользовательские сценарии и негативные ветки.

## 4. Чек-лист проверки безопасности API

Проверялись пункты из задания ПР5 и OWASP API Security Top 10 (2023).
Подробный анализ угроз — в [security.md](security.md).

| № | Проверка | Статус | Что сделано / чем подтверждено |
|---|---|---|---|
| 1 | Параметризованные запросы вместо конкатенации строк (SQL-инъекции) | **выполнено** | events-service работает через SQLAlchemy ORM (`select`, `where`, bind-параметры), users-service — через Django ORM. Ручной SQL только `SELECT 1` в `database.connect_and_log()`. Конкатенации пользовательских значений в SQL нет. |
| 2 | API не возвращает лишние поля (хэш пароля, внутренние флаги) | **выполнено** | `_user_payload()` в users-service возвращает только `id`, `username`, `email`, `role`, `created_at`. Тесты `test_register_and_login_do_not_return_password_hash` и `test_payload_has_no_password_or_hash` проверяют отсутствие `password`/`argon2` в ответах. |
| 3 | Ограничение частоты запросов на чувствительных эндпоинтах | **исправлено** | До ПР5 лимита не было: `/auth/login` и `/auth/register` принимали неограниченное число попыток. Добавлен `accounts/ratelimit.py` (скользящее окно, `AUTH_RATE_LIMIT=10` за `AUTH_RATE_WINDOW_SECONDS=60` на IP). При превышении — `429 TooManyRequests` и заголовок `Retry-After`. Тесты: `test_register_rate_limit_returns_429`, `test_login_rate_limit_returns_429`, `SlidingWindowLimiter` unit-тесты. |
| 4 | Корректные `401`/`403` на всех защищённых маршрутах | **выполнено** | Без токена — `401 Unauthorized`; невалидный/просроченный токен — `401 InvalidToken`/`TokenExpired`; недостаточная роль или чужой объект — `403 Forbidden`. Покрыто в `events-service/tests/test_api.py`, `attendance-service/tests/test_api.py`, `users-service/accounts/tests.py`; матрица — в [auth.md](auth.md). |
| 5 | Mass assignment / подмена `organizer_id`, `user_id`, `role` | **выполнено** | Для организатора `organizer_id` принудительно берётся из `sub` JWT; `user_id` в attendance — из JWT; `role=admin` при регистрации отклоняется. Тесты: `test_create_organizer_ignores_foreign_organizer_id`, `test_user_cannot_mark_for_another`, `test_register_validates_email_password_and_role`. |
| 6 | Ограничение размера и валидация входных данных | **выполнено** | `limit` — 1..100, `page >= 1`; `title` 2..100, `description` ≤ 2000; координаты в допустимых диапазонах; тело обязано быть JSON-объектом. Негативные тесты возвращают `400 ValidationError` с `details`. |
| 7 | Отсутствие stack trace и секретов в ответах | **выполнено** | Глобальные обработчики возвращают единый JSON без текста исключения; тест `test_unhandled_exception_returns_unified_500` проверяет, что `boom` не попадает в тело. Секреты — только в `.env` (`.env.example` без реальных значений). |
| 8 | Безопасность JWT (подпись, срок, issuer) | **выполнено** | HS256, обязательные `exp`/`sub`/`iss`, проверка issuer; токен с другим секретом и просроченный токен отклоняются. Тесты `test_token_signed_with_other_secret_is_rejected`, `test_expired_token_returns_401` (events и attendance). |

## 5. Найденная и исправленная проблема

### 5.1. Отсутствие rate limiting на входе и регистрации

**До:** `/auth/login` и `/auth/register` можно было вызывать без ограничений.
Это позволяло перебирать пароли и создавать пользователей массово.

**После:** добавлен модуль `users-service/accounts/ratelimit.py`:

- скользящее окно в памяти процесса;
- ключ `действие + IP` (`X-Forwarded-For` учитывается, если задан прокси);
- лимит по умолчанию — 10 запросов за 60 секунд;
- настройки `AUTH_RATE_LIMIT` и `AUTH_RATE_WINDOW_SECONDS` в `config/settings.py`
  и `.env.example`;
- ответ при превышении:

```json
{
  "error": {
    "code": "TooManyRequests",
    "message": "Слишком много запросов. Попробуйте позже.",
    "details": [{"field": null, "message": "повторите запрос через 43 с"}]
  }
}
```

Заголовок `Retry-After` сообщает клиенту, когда можно повторить запрос.

**Ограничение решения:** счётчики хранятся в памяти процесса и не общие для
нескольких инстансов. Для production нужен Redis или лимит на reverse proxy.
Это зафиксировано в остаточных рисках.

### 5.2. Дополнительно найдено тестами: устаревшая категория после PATCH/PUT

При изменении категории события `services.py` присваивал только
`event.category_id`, а `_serialize()` читал уже загруженную связь `event.category`.
В ответе оставалась старая категория, хотя в БД сохранялась новая.
Исправлено присваиванием связи `event.category = category` в `replace()` и
`patch()`. Регрессия закрыта тестом `test_patch_valid_and_invalid`, который
проверяет не только статус, но и значение поля `category`.

## 6. Как воспроизвести

```bash
python -m pip install -r requirements-dev.txt
python scripts/run_tests.py
```

Или по отдельности:

```bash
cd users-service && python manage.py test
cd events-service && python -m pytest -q
cd attendance-service && python -m pytest -q
```

## 7. Выводы

- 72 теста покрывают валидацию, CRUD, регистрацию/вход, роли, владельца
  объекта и негативные сценарии 400/401/403/404/409/429.
- Тесты изолированы: отдельная тестовая БД у Django, отдельный файл и очистка
  таблиц у events-service, очистка in-memory хранилища у attendance-service.
- Покрытие ≈85% по трём сервисам; слабые места перечислены и осознанно
  оставлены (неиспользуемые модули, ветки инфраструктурных обработчиков).
- Найдена и устранена реальная проблема — отсутствие rate limiting на
  аутентификации; дополнительно исправлен дефект сериализации категории.
