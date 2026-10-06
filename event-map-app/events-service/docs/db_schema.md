# Схема базы данных — ПР3

База данных events-service: реляционная, по умолчанию **SQLite** (файл `events.db`),
подключаемая и к PostgreSQL — строка подключения задаётся через `DATABASE_URL`
(см. `.env.example`). Схема создаётся **только миграциями Alembic**,
а не вручную через SQL-консоль.

- Миграция `0001` — создание таблиц `categories` и `events`.
- Миграция `0002` — правка схемы: поле `categories.slug` + составной индекс.

ER-диаграмма: `er-diagram.svg`, `er-diagram.mmd` (Mermaid).

## Отношения

Связь **1:N**: одна категория (`categories`) →
много мероприятий (`events`). Внешний ключ с типом `RESTRICT` — нельзя удалить
категорию, пока есть мероприятия в ней.

## Таблица categories (справочник категорий)

| Поле       | Тип            | Ограничения                              |
|------------|----------------|------------------------------------------|
| id         | string (36)    | PRIMARY KEY, UUID                        |
| name       | string (50)    | NOT NULL, UNIQUE (uq_categories_name)    |
| slug       | string (50)    | UNIQUE (uq_categories_slug), добавлено миграцией 0002, backfill из name |
| created_at | datetime       | NOT NULL                                 |

## Таблица events (основная сущность)

| Поле          | Тип            | Ограничения                                        |
|---------------|----------------|----------------------------------------------------|
| id            | string (36)    | PRIMARY KEY, UUID                                  |
| title         | string (100)   | NOT NULL, CHECK 2..100 (ck_events_title_len)      |
| description   | string (2000)  | NOT NULL, CHECK <= 2000 (ck_events_description_len) |
| lat           | float          | NOT NULL, CHECK [-90; 90] (ck_events_lat_range)    |
| lng           | float          | NOT NULL, CHECK [-180; 180] (ck_events_lng_range)  |
| starts_at     | datetime       | NOT NULL                                           |
| category_id   | string (36)    | NOT NULL, FOREIGN KEY → categories.id, ON DELETE RESTRICT |
| organizer_id  | string (64)    | NOT NULL                                           |
| created_at    | datetime       | NOT NULL, default = now                            |
| updated_at    | datetime       | NOT NULL, обновляется при изменении записи         |

## Индексы и обоснование

| Индекс                          | Таблица     | Колонки                  | Зачем (частый запрос ПР2)              |
|---------------------------------|-------------|--------------------------|----------------------------------------|
| ix_events_category_id           | events      | category_id              | фильтр списка по категории             |
| ix_events_category_starts_at    | events      | (category_id, starts_at) | фильтр категория+даты и ORDER BY starts_at |

Составной индекс ведёт с `category_id`, поэтому покрывает главный сценарий:
`WHERE category_id = ? AND starts_at BETWEEN ? AND ? ORDER BY starts_at`.

## Транзакции

`database.db_session` — единица работы: commit при успехе, rollback при ошибке.
Демонстрация атомарности:
- `verify_tx.py` — (1) отдельный сценарий «категория + событие» в одной
  транзакции: при ошибке CHECK на событии откатывается и вставка категории;
  (2) пакетная вставка нескольких событий при сбое одной записи откатывается целиком.

## Как применить миграции

```bash
cd events-service
alembic upgrade head      # создать всю схему с нуля
alembic downgrade -1      # продемонстрировать откат последней миграции
alembic upgrade head      # вернуть схему обратно
```