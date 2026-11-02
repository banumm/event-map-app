# Анализ угроз API и меры защиты — СРС №1

Документ фиксирует угрозы по OWASP API Security Top 10 (2023), реализованные
меры и способ проверки. Используется в презентации СРС №1, слайд 14.

## Сводная таблица

| Угроза OWASP | Сценарий атаки | Реализованная мера | Как проверено | Остаточный риск |
|---|---|---|---|---|
| **API1: BOLA** — нарушение авторизации на уровне объекта | Организатор с валидным JWT изменяет или удаляет чужое мероприятие; пользователь читает чужую отметку attendance | В events-service `_authorize_event` сравнивает `organizer_id` события с `sub` из JWT; `admin` обходит проверку. В attendance-service пользователь видит только свои записи, чужой `user_id` возвращает `403`. | `events-service/verify.py`: DELETE чужого события → `403`, владельцем → `204`. `attendance-service/verify.py`: чужой пользователь → `403`. | Нет автоматического теста на все вложенные ресурсы; добавить при появлении новых сущностей. |
| **API2: Broken Authentication** — слабая аутентификация | Подбор пароля, подделка JWT, использование просроченного или чужого токена | Пароли хранятся только как Argon2-хеш; минимум 8 символов. JWT подписывается HS256 общим `JWT_SECRET`, проверяются подпись, `exp` и `iss`. Ошибки входа не раскрывают, существует ли пользователь. | `users-service/accounts/tests.py`: неверный пароль → `401`, невалидный токен → `401`. Ручной чек-лист: `docs/auth-check.md`. | Нет rate limiting и блокировки после серии неудачных попыток; нет отзыва токенов. Запланировано в PR6/PR7. |
| **API3: Broken Object Property Level Authorization** — массовое присвоение | Клиент передаёт `organizer_id`, `role` или `user_id`, чтобы действовать от имени другого пользователя | `organizer_id` и `user_id` берутся только из проверенного JWT, а не из тела запроса. Неизвестные поля отклоняются валидатором с `400`. Роль при регистрации ограничена `user`/`organizer`; `admin` создаётся только management-командой. | `events-service/verify.py`: попытка подменить `organizer_id` игнорируется; `users-service/accounts/tests.py`: регистрация с `role=admin` отклоняется. | Нет отдельной схемы whitelist для будущих PATCH-полей; добавлять явно при расширении API. |
| **API4: Unrestricted Resource Consumption** — исчерпание ресурсов | Запрос `limit=100000`, огромный JSON или массовая вставка событий | `limit` ограничен диапазоном `1..100`; `page >= 1`; длина `title` ≤ 100, `description` ≤ 2000; для `POST /events` проверяется обязательность полей. | `events-service/verify.py`: `limit=1000` → `400`. Валидация полей → `400` с `details`. | Нет rate limiting и ограничения размера тела на уровне reverse proxy. Запланировано в PR6/PR7. |
| **API5: Broken Function Level Authorization** — нарушение авторизации на уровне функций | Обычный пользователь вызывает админский `GET /users` или создаёт мероприятие | Декораторы `require_auth` и `require_role`; `GET /users` доступен только `admin`; `POST /events` — только `organizer`/`admin`; `DELETE /events/{id}` — владелец или `admin`. | `users-service/accounts/tests.py`: `GET /users` без токена → `401`, роль `user` → `403`, `admin` → `200`. `events-service/verify.py`: `user` → `403`. | Матрица ролей поддерживается вручную; при добавлении endpoint нужен чек-лист. |
| **API8: Security Misconfiguration** — небезопасная конфигурация | `DEBUG=True` в production, секреты в коде, stack trace в ответе | Секреты и параметры вынесены в `.env` (`JWT_SECRET`, `DJANGO_SECRET_KEY`, `DATABASE_URL`). `DEBUG` по умолчанию выключен. Все сервисы возвращают единый JSON-ответ без stack trace. | `.env.example` не содержит реальных секретов; проверка `500`-ответа в тестах middleware. | Нет отдельного production-профиля и HTTPS-терминации в docker-compose. |

## Единый формат ошибки

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Недостаточно прав для выполнения операции",
    "details": []
  }
}
```

Коды: `BadRequest`, `ValidationError`, `Unauthorized`, `Forbidden`, `NotFound`,
`Conflict`, `InvalidCredentials`, `InternalServerError`.

## Что проверить на защите

1. `DELETE /events/{id}` без токена → `401`, с токеном `user` → `403`,
   владельцем-организатором → `204`, `admin` → `204`.
2. `POST /events` с `organizer_id` другого пользователя → событие создаётся
   от имени владельца токена.
3. `GET /users` с ролью `user` → `403`, с ролью `admin` → `200`.
4. `GET /events?limit=1000` → `400 VALIDATION_ERROR`.
5. `POST /auth/login` с неверным паролем → `401` без раскрытия существования
   пользователя.

## План усиления до СРС №2

- Rate limiting на `/auth/login` и публичные `GET`.
- Refresh-токены или короткоживущие access-токены с ротацией.
- Ограничение размера тела запроса на уровне reverse proxy.
- Автоматическая синхронизация проекции `users` в events-service с users-service.
- Перенос attendance из памяти в БД с уникальным ограничением `(event_id, user_id)`.
