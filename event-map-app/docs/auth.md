# ПР4. Аутентификация, авторизация, валидация и обработка ошибок

Документ описывает реализацию в репозитории `event-map-app`. Протокол ручной
проверки прав находится в [auth-check.md](auth-check.md).

## 1. Модель пользователя

Файл: `users-service/accounts/models.py`.
Миграция: `users-service/accounts/migrations/0001_initial.py`.

| Поле | Назначение | Ограничения |
|---|---|---|
| `id` | идентификатор | первичный ключ |
| `username` | логин | уникальный, 3–150 символов |
| `email` | email | уникальный, валидируется |
| `password` | хэш пароля | Argon2, пароль в открытом виде не хранится |
| `role` | роль | `user` / `organizer` / `admin`, по умолчанию `user` |
| `date_joined` | дата регистрации | заполняется Django автоматически |

Пароли хэшируются `Argon2PasswordHasher` (см. `PASSWORD_HASHERS` в
`users-service/config/settings.py`). Проверить можно так:

```bash
cd users-service
python manage.py shell -c "from accounts.models import User; u=User.objects.get(username='user1'); print(u.password[:20])"
# argon2$argon2id$v=19...
```

Администратор создаётся только доверенной командой, а не через публичную регистрацию:

```bash
python manage.py create_admin --username admin --email admin@example.com --password 'StrongPass123'
```

## 2. Регистрация

`POST /auth/register`

```json
{
  "username": "organizer1",
  "email": "organizer1@example.com",
  "password": "StrongPass123",
  "role": "organizer"
}
```

Проверки:
- `username`: 3–150 символов, латиница, цифры, `_`, `.`, `-`;
- `email`: корректный формат;
- `password`: длина 8–128 символов;
- `role`: при публичной регистрации разрешены только `user` и `organizer`;
- уникальность `username` и `email` (без учёта регистра);
- пароль сохраняется через `create_user`, то есть только как хэш.

Ответы:
- `201` — пользователь создан;
- `400 ValidationError` — ошибки полей;
- `409 Conflict` — дубликат логина/email.

## 3. Вход и JWT

`POST /auth/login` принимает `username` **или** `email` плюс `password`.

```json
{"username": "organizer1", "password": "StrongPass123"}
```

Успех `200`:

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {"id": 2, "username": "organizer1", "email": "organizer1@example.com", "role": "organizer", "created_at": "..."}
}
```

Неверный логин/пароль — `401 InvalidCredentials`.

JWT содержит `sub` (id пользователя), `username`, `email`, `role`, `iss`, `iat`,
`exp`, `jti`. Подпись HS256, секрет `JWT_SECRET`, issuer
`event-map-users-service`, срок жизни `JWT_EXPIRES_MINUTES` (по умолчанию 60).
Токен передаётся в заголовке:

```
Authorization: Bearer <access_token>
```

Проверить текущего пользователя: `GET /auth/me` (без токена — `401`).

### Почему JWT, а не серверная сессия

Users Service, Events Service и Attendance Service — отдельные процессы.
JWT позволяет events-service и attendance-service проверять пользователя локально,
не храня общую сессию и не делая синхронный запрос на каждый вызов. Django-сессии
используются только для встроенной админ-панели. Ограничение: токен нельзя отозвать
до истечения срока без дополнительного blacklist по `jti`.

## 4. Защита маршрутов

| Сервис | Защищённые маршруты | Механизм |
|---|---|---|
| users-service | `GET /auth/me`, `GET /users` | декоратор `require_auth`, затем `require_role` |
| events-service | `POST /events`, `PUT/PATCH/DELETE /events/{id}` | `auth.require_auth`, `auth.require_role` |
| attendance-service | `POST /attendance`, `GET /attendance/user/{id}` | `auth.require_auth` + проверка пользователя/роли |

Порядок проверок:
1. нет/испорчен/истёк токен → `401`;
2. токен валиден, но роль не подходит или запись чужая → `403`;
3. ресурс не найден → `404`;
4. данные не проходят валидацию → `400`;
5. непредвиденная ошибка → `500` без стектрейса.

`organizer_id` при создании события не берётся из тела запроса: для организатора
он всегда равен `sub` из JWT. `admin` может передать `organizer_id` явно.
Организатор может изменять и удалять только события со своим `organizer_id`.

## 5. Роли

| Действие | user | organizer | admin |
|---|---|---|---|
| Просмотр событий | да | да | да |
| Создание события | нет (403) | да | да |
| Изменение своего события | нет (403) | да | да |
| Изменение чужого события | нет (403) | нет (403) | да |
| Удаление своего события | нет (403) | да | да |
| Удаление чужого события | нет (403) | нет (403) | да |
| Отметка своего участия | да | да | да |
| Отметка участия за другого | нет (403) | нет (403) | да |
| Просмотр чужих отметок | нет (403) | нет (403) | да |
| `GET /users` | нет (403) | нет (403) | да |

## 6. Единый формат ошибок

Все сервисы возвращают ошибки в виде:

```json
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

`details` — всегда массив; для ошибок уровня запроса он может быть пустым.

| HTTP | `code` | Когда |
|---|---|---|
| 400 | `ValidationError` | поля не прошли проверку |
| 400 | `BadRequest` | пустое тело или некорректный JSON |
| 401 | `Unauthorized` | нет заголовка `Authorization: Bearer` |
| 401 | `InvalidToken` | неверная подпись/issuer или неизвестный пользователь |
| 401 | `TokenExpired` | истёк срок действия |
| 401 | `InvalidCredentials` | неверный логин/пароль |
| 403 | `Forbidden` | роли или владельца недостаточно |
| 404 | `NotFound` | ресурс/маршрут не найден |
| 405 | `MethodNotAllowed` | метод не поддерживается |
| 409 | `Conflict` | дубликат пользователя |
| 500 | `InternalServerError` | необработанная ошибка, тело без стектрейса |

Реализация:
- users-service: `accounts/errors.py` + `accounts/middleware.py`
  (`UnifiedErrorMiddleware`, `process_exception`, глобальные handler404/500);
- events-service и attendance-service: `errors.py` с `ApiError`,
  `register_error_handlers`, обработчиком `HTTPException` и `Exception`.

Необработанные исключения логируются на сервере, клиент получает только
`{"error": {"code": "InternalServerError", ...}}`.

## 7. Базовые меры защиты

- пароли только в виде Argon2-хэша;
- JWT подписан, проверяются подпись, `iss`, `exp`, наличие `sub`;
- роль берётся только из проверенного JWT, а не из тела запроса;
- `organizer_id` и `user_id` для обычного пользователя принудительно заменяются
  значением из токена;
- проверка владельца записи отдельно от проверки роли;
- срок жизни токена ограничен;
- `DEBUG` по умолчанию выключен (`DJANGO_DEBUG=0`, `FLASK_DEBUG=0`);
- секреты задаются через переменные окружения, в репозитории только dev-значения
  в `.env.example`;
- SQL-доступ идёт через ORM/параметризованные запросы SQLAlchemy.
