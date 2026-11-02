# Протокол проверки сценариев доступа (ПР4)

Проверка выполнялась вручную через HTTP на локально запущенных сервисах
(users-service :8000, events-service :5001, attendance-service :5002).
Дата проверки: 2026-10-23.

Проверяется одна и та же операция — **удаление мероприятия** `DELETE /events/{id}` —
от имени трёх субъектов:

1. без токена;
2. с токеном роли `user`;
3. с токеном роли `admin`.

Дополнительно проверены владелец-организатор и чужой организатор, регистрация,
вход, валидация и единый формат ошибок.

## Подготовка

```bash
cd users-service
python manage.py migrate
python manage.py create_admin --username admin --email admin@example.com --password 'StrongPass123'
python manage.py runserver 127.0.0.1:8000

cd events-service
alembic upgrade head
python app.py                       # :5001

cd attendance-service
python app.py                       # :5002
```

Создание пользователей и получение токенов:

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"organizer1","email":"organizer1@example.com","password":"StrongPass123","role":"organizer"}'

curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"user1","email":"user1@example.com","password":"StrongPass123","role":"user"}'

curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"organizer1","password":"StrongPass123"}'

curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"user1","password":"StrongPass123"}'

curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"StrongPass123"}'
```

Токены сохраняются в переменные `ORG_TOKEN`, `USER_TOKEN`, `ADMIN_TOKEN`.
Мероприятие создаёт организатор:

```bash
curl -s -X POST http://127.0.0.1:5001/events \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Concert in park","description":"Live music","lat":55.7558,"lng":37.6176,"starts_at":"2026-10-01T19:00:00Z","category":"concert"}'
```

Из ответа берётся `id` созданного события (`EVENT_ID`).

## Сценарии для `DELETE /events/{EVENT_ID}`

| № | Субъект | Заголовок | Фактический код | Вывод |
|---|---------|-----------|-----------------|-------|
| 1 | без токена | отсутствует | **401** | не аутентифицирован |
| 2 | `user1` (роль `user`) | `Bearer USER_TOKEN` | **403** | аутентифицирован, но роль не позволяет |
| 3 | `admin` (роль `admin`) | `Bearer ADMIN_TOKEN` | **204** | операция выполнена |

Дополнительно:

| Субъект | Операция | Код |
|---|---|---|
| `organizer1` (владелец) | `DELETE /events/{EVENT_ID}` | **204** |
| `organizer2` (чужой организатор) | `PUT /events/{EVENT_ID}` | **403** |
| `organizer2` (чужой организатор) | `DELETE /events/{EVENT_ID}` | **403** |

Сценарий 1:

```bash
curl -i -X DELETE http://127.0.0.1:5001/events/$EVENT_ID
```

```http
HTTP/1.1 401 UNAUTHORIZED
WWW-Authenticate: Bearer

{
  "error": {
    "code": "Unauthorized",
    "message": "Требуется аутентификация",
    "details": []
  }
}
```

Сценарий 2:

```bash
curl -i -X DELETE http://127.0.0.1:5001/events/$EVENT_ID \
  -H "Authorization: Bearer $USER_TOKEN"
```

```http
HTTP/1.1 403 FORBIDDEN

{
  "error": {
    "code": "Forbidden",
    "message": "Недостаточно прав для выполнения операции",
    "details": [
      {"field": "role", "message": "требуется одна из ролей: organizer, admin"}
    ]
  }
}
```

Сценарий 3:

```bash
curl -i -X DELETE http://127.0.0.1:5001/events/$EVENT_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

```http
HTTP/1.1 204 NO CONTENT
```

## Проверка регистрации и входа

| Запрос | Фактический код |
|---|---|
| `POST /auth/register` (organizer1, user1, organizer2) | **201** |
| `POST /auth/register` повторно с тем же username | **409** |
| `POST /auth/register` с `username="x"`, `email="bad"`, `password="123"`, `role="admin"` | **400** |
| `POST /auth/login` с верным паролем (username или email) | **200** |
| `POST /auth/login` с неверным паролем | **401** |
| `GET /auth/me` без токена | **401** |
| `GET /auth/me` с токеном | **200** |
| `GET /users` с токеном `user1` | **403** |
| `GET /users` с токеном `admin` | **200** |

Пример ответа на дубликат:

```json
{
  "error": {
    "code": "Conflict",
    "message": "Пользователь с таким логином или email уже существует",
    "details": [{"field": "username", "message": "логин уже занят"}]
  }
}
```

Пример ответа на неверный пароль:

```json
{
  "error": {
    "code": "InvalidCredentials",
    "message": "Неверный логин или пароль",
    "details": []
  }
}
```

## Проверка events-service

| Запрос | Фактический код |
|---|---|
| `POST /events` без токена | **401** |
| `POST /events` с токеном `user` | **403** |
| `POST /events` с токеном `organizer` | **201** |
| `GET /events/{id}` публично | **200** |
| `PUT /events/{id}` чужим организатором | **403** |
| `DELETE /events/{id}` владельцем | **204** |
| `DELETE /events/{id}` администратором | **204** |
| `GET /events/{несуществующий id}` | **404** |
| `POST /events` с неверными типами/полями | **400** |
| `GET /no-such-route` | **404** |

Пример ошибки валидации:

```json
{
  "error": {
    "code": "ValidationError",
    "message": "Ошибка валидации",
    "details": [
      {"field": "title", "message": "обязательное поле отсутствует"},
      {"field": "lat", "message": "должно быть числом"},
      {"field": "category", "message": "допустимые значения: ..."}
    ]
  }
}
```

Пример 404 без сырого HTML/стектрейса:

```json
{
  "error": {
    "code": "NotFound",
    "message": "Мероприятие не найдено",
    "details": [{"field": "id", "message": "событие ... не найдено"}]
  }
}
```

## Проверка attendance-service

| Запрос | Фактический код |
|---|---|
| `POST /attendance` без токена | **401** |
| `POST /attendance` с токеном `user` (своё участие) | **201** |
| `POST /attendance` с `user_id` другого пользователя (роль `user`) | **403** |
| `GET /attendance/user/{чужой id}` (роль `user`) | **403** |
| `GET /attendance/user/{чужой id}` (роль `admin`) | **200** |
| `GET /attendance/event/{id}` публично | **200** |

Пример 403 для отметки за другого:

```json
{
  "error": {
    "code": "Forbidden",
    "message": "Отмечать участие можно только от своего имени",
    "details": [{"field": "user_id", "message": "недостаточно прав"}]
  }
}
```

## Вывод

Права различаются не только названием роли:

- без токена protected-маршруты возвращают `401`;
- роль `user` получает `403` на изменение событий и на действия за других;
- `organizer` может менять только свои события (`403` на чужие);
- `admin` проходит проверку роли и владельца и получает `204`/`200`.
- все перечисленные ошибки возвращаются в едином формате
  `{"error": {"code": ..., "message": ..., "details": [...]}}`.

Автоматизированные проверки: `users-service/accounts/tests.py`
(`python manage.py test`), `events-service/verify.py`,
`attendance-service/verify.py`.
