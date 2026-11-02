#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the SRS1 PPTX/PDF deck and its diagram/screenshot assets."""

from __future__ import annotations

import math
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
SHOTS = ASSETS / "screenshots"
for folder in (ASSETS, SHOTS):
    folder.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("C:/Windows/Fonts")
NAVY = "#152238"
TEAL = "#1F8A70"
ORANGE = "#E76F51"
LIGHT = "#F4F7FA"
WHITE = "#FFFFFF"
DARK = "#17212B"
GRAY = "#5B6770"
MUTED = "#D9E2E8"
RED = "#C0392B"
GREEN = "#2E7D32"

FONT = "Arial"
MONO = "Consolas"


def rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def pil_font(size: int, bold: bool = False, mono: bool = False):
    if mono:
        name = "consolab.ttf" if bold else "consola.ttf"
    else:
        name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def draw_wrapped(draw, text, x, y, max_width, font, fill, line_gap=6, align="left"):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    line_height = (font.size if hasattr(font, "size") else 24) + line_gap
    for line in lines:
        width = draw.textlength(line, font=font)
        tx = x
        if align == "center":
            tx = x + (max_width - width) / 2
        draw.text((tx, y), line, font=font, fill=fill)
        y += line_height
    return y


def draw_box(draw, box, title, lines, accent=TEAL, fill=WHITE, title_size=30, line_size=24):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=rgb(fill), outline=rgb(accent), width=3)
    draw.rectangle((x1, y1 + 12, x1 + 10, y2 - 12), fill=rgb(accent))
    draw.text((x1 + 26, y1 + 16), title, font=pil_font(title_size, True), fill=rgb(NAVY))
    y = y1 + 16 + title_size + 18
    for line in lines:
        y = draw_wrapped(
            draw,
            line,
            x1 + 26,
            y,
            x2 - x1 - 48,
            pil_font(line_size),
            rgb("#2F3B47"),
            line_gap=4,
        )
        y += 4
    return box


def draw_arrow(draw, points, color="#5B6770", width=4, dashed=False):
    for a, b in zip(points, points[1:]):
        if dashed:
            length = math.dist(a, b)
            if length == 0:
                continue
            steps = int(length // 16)
            for i in range(steps):
                t0 = i / max(steps, 1)
                t1 = min((i + 0.55) / max(steps, 1), 1)
                p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
                p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
                draw.line([p0, p1], fill=rgb(color), width=width)
        else:
            draw.line([a, b], fill=rgb(color), width=width)
    a, b = points[-2], points[-1]
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    size = 17
    left = (b[0] - size * math.cos(angle) + size * 0.55 * math.sin(angle),
            b[1] - size * math.sin(angle) - size * 0.55 * math.cos(angle))
    right = (b[0] - size * math.cos(angle) - size * 0.55 * math.sin(angle),
             b[1] - size * math.sin(angle) + size * 0.55 * math.cos(angle))
    draw.polygon([b, left, right], fill=rgb(color))


def build_architecture():
    img = Image.new("RGB", (1920, 1080), rgb(LIGHT))
    d = ImageDraw.Draw(img)
    d.text((60, 30), "Архитектура Event Map App", font=pil_font(50, True), fill=rgb(NAVY))
    d.rounded_rectangle((520, 38, 1740, 92), radius=14, fill=rgb("#E8F4F0"), outline=rgb(TEAL), width=2)
    d.text(
        (540, 51),
        "JWT HS256 · общий секрет · issuer = event-map-users-service",
        font=pil_font(25, True),
        fill=rgb(TEAL),
    )

    draw_box(d, (50, 300, 400, 780), "Клиент", ["Web / Mobile", "REST + JSON", "JWT Bearer", "Карта и фильтры"], accent=ORANGE, line_size=25)
    draw_box(d, (520, 130, 1080, 330), "users-service · Django :8000", ["Регистрация / вход / me", "Argon2 + выдача JWT", "GET /users — только admin"])
    draw_box(d, (1220, 130, 1740, 330), "users.sqlite3", ["users · роли", "учётные записи", "источник истины auth"])
    draw_box(d, (520, 390, 1080, 590), "attendance-service · Flask :5002", ["POST /attendance", "GET /attendance/event/{id}", "GET /attendance/user/{id}"])
    draw_box(d, (1220, 390, 1740, 590), "in-memory dict", ["attendance_db", "MVP без persistence", "статусы going / interested"])
    draw_box(d, (520, 650, 1080, 850), "events-service · Flask :5001", ["CRUD /events + фильтры", "JWT middleware, RBAC + owner", "валидация и единые ошибки"])
    draw_box(d, (1220, 650, 1740, 850), "events.db", ["categories · events", "users (проекция)", "event_participants"])

    draw_arrow(d, [(400, 380), (520, 230)], color=ORANGE)
    draw_arrow(d, [(400, 520), (520, 490)], color=ORANGE)
    draw_arrow(d, [(400, 700), (520, 750)], color=ORANGE)
    draw_arrow(d, [(1080, 230), (1220, 230)], color=TEAL)
    draw_arrow(d, [(1080, 490), (1220, 490)], color=TEAL)
    draw_arrow(d, [(1080, 750), (1220, 750)], color=TEAL)

    d.text((430, 270), "HTTP", font=pil_font(21, True), fill=rgb(ORANGE))
    d.text((430, 470), "HTTP", font=pil_font(21, True), fill=rgb(ORANGE))
    d.text((430, 735), "HTTP", font=pil_font(21, True), fill=rgb(ORANGE))
    d.text((1120, 200), "SQL", font=pil_font(21, True), fill=rgb(TEAL))
    d.text((1120, 460), "RAM", font=pil_font(21, True), fill=rgb(TEAL))
    d.text((1120, 720), "SQL", font=pil_font(21, True), fill=rgb(TEAL))

    d.rounded_rectangle((60, 900, 1860, 1000), radius=14, fill=rgb(WHITE), outline=rgb(MUTED), width=2)
    d.text(
        (84, 921),
        "users-service — единственный источник JWT; events и attendance только проверяют подпись, exp и iss.",
        font=pil_font(26),
        fill=rgb(GRAY),
    )
    img.save(ASSETS / "architecture.png")


def draw_entity(d, box, name, fields, accent):
    x1, y1, x2, y2 = box
    d.rounded_rectangle(box, radius=16, fill=rgb(WHITE), outline=rgb(accent), width=3)
    d.rectangle((x1 + 1, y1 + 1, x2 - 1, y1 + 54), fill=rgb(accent))
    d.text((x1 + 22, y1 + 12), name, font=pil_font(29, True), fill=rgb(WHITE))
    y = y1 + 72
    for field in fields:
        d.text((x1 + 24, y), field, font=pil_font(23), fill=rgb("#2F3B47"))
        y += 34


def build_er():
    img = Image.new("RGB", (1920, 1080), rgb(LIGHT))
    d = ImageDraw.Draw(img)
    d.text((60, 30), "ER-модель events-service", font=pil_font(50, True), fill=rgb(NAVY))
    d.text((60, 92), "Категории, мероприятия, пользователи и регистрации", font=pil_font(26), fill=rgb(GRAY))

    draw_entity(d, (70, 180, 500, 500), "CATEGORIES", ["id · UUID · PK", "name · UNIQUE", "slug · UNIQUE", "created_at"], TEAL)
    draw_entity(d, (650, 120, 1250, 600), "EVENTS", ["id · UUID · PK", "title · CHECK 2..100", "description · ≤ 2000", "lat · CHECK -90..90", "lng · CHECK -180..180", "starts_at · NOT NULL", "category_id · FK", "organizer_id · NOT NULL", "created_at / updated_at"], ORANGE)
    draw_entity(d, (1400, 180, 1830, 500), "USERS", ["id · UUID · PK", "name · NOT NULL", "email · UNIQUE", "role · CHECK", "created_at"], TEAL)
    draw_entity(d, (650, 700, 1250, 930), "EVENT_PARTICIPANTS", ["event_id · PK / FK", "user_id · PK / FK", "registered_at", "status · CHECK"], NAVY)

    draw_arrow(d, [(500, 340), (650, 340)], color=TEAL)
    draw_arrow(d, [(950, 600), (950, 700)], color=ORANGE)
    draw_arrow(d, [(1615, 500), (1615, 815), (1250, 815)], color=TEAL)

    d.text((535, 300), "1 : N", font=pil_font(22, True), fill=rgb(TEAL))
    d.text((965, 635), "1 : N", font=pil_font(22, True), fill=rgb(ORANGE))
    d.text((1470, 750), "N : M", font=pil_font(22, True), fill=rgb(TEAL))

    d.rounded_rectangle((70, 965, 1830, 1035), radius=14, fill=rgb(WHITE), outline=rgb(MUTED), width=2)
    d.text(
        (92, 982),
        "Составной PK (event_id, user_id) исключает дубли · CASCADE при удалении · RESTRICT для категории",
        font=pil_font(24),
        fill=rgb(GRAY),
    )
    img.save(ASSETS / "er.png")


def wrap_terminal(line: str, width: int = 70):
    if len(line) <= width:
        return [line]
    indent = len(line) - len(line.lstrip())
    return textwrap.wrap(
        line,
        width=width,
        subsequent_indent=" " * min(indent + 2, 20),
        break_long_words=False,
        break_on_hyphens=False,
    )


def build_terminal(title: str, lines: list[str], filename: str, status_color: str):
    width, height = 1200, 600
    img = Image.new("RGB", (width, height), rgb("#0B1220"))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, width - 1, height - 1), radius=16, fill=rgb("#0B1220"), outline=rgb("#263445"), width=3)
    d.rounded_rectangle((0, 0, width - 1, 52), radius=16, fill=rgb("#162232"))
    d.rectangle((0, 30, width - 1, 52), fill=rgb("#162232"))
    for i, color in enumerate(["#FF5F56", "#FFBD2E", "#27C93F"]):
        d.ellipse((22 + i * 26, 18, 36 + i * 26, 32), fill=rgb(color))
    d.text((140, 15), title, font=pil_font(20, True), fill=rgb("#C9D6E2"))

    mono = pil_font(28, mono=True)
    y = 76
    for raw in lines:
        for line in wrap_terminal(raw):
            color = "#DCE6F0"
            stripped = line.lstrip()
            if stripped.startswith("HTTP/1.1"):
                color = status_color
            elif stripped.startswith("$"):
                color = "#7DD3FC"
            elif stripped.startswith('"code"') or stripped.startswith('"message"'):
                color = "#F8C471"
            d.text((30, y), line, font=mono, fill=rgb(color))
            y += 35
    img.save(SHOTS / filename)


def build_screenshots():
    build_terminal(
        "POST /events → 201 Created",
        [
            "$ POST /events  ·  Authorization: Bearer <ORG_TOKEN>",
            "",
            "HTTP/1.1 201 CREATED",
            "Content-Type: application/json",
            "",
            "{",
            '  "id": "0f7c2a9e-4b1d-...",',
            '  "title": "Концерт в парке",',
            '  "organizer_id": "b3e1a7c2-...",',
            '  "category": "concert",',
            '  "starts_at": "2026-10-01T19:00:00Z"',
            "}",
            "",
            "organizer_id взят из проверенного JWT",
        ],
        "success_201.png",
        "#4ADE80",
    )
    build_terminal(
        "POST /events → 400 Bad Request",
        [
            "$ POST /events  ·  Authorization: Bearer <ORG_TOKEN>",
            "",
            "HTTP/1.1 400 BAD REQUEST",
            "",
            "{",
            '  "error": {',
            '    "code": "ValidationError",',
            '    "message": "Ошибка валидации",',
            '    "details": [',
            '      {"field": "lat", "message": "должно быть числом"},',
            '      {"field": "lng", "message": "диапазон -180..180"}',
            "    ]",
            "  }",
            "}",
        ],
        "validation_400.png",
        "#FBBF24",
    )
    build_terminal(
        "DELETE /events/{id} → 403 Forbidden",
        [
            "$ DELETE /events/<ID>  ·  Bearer <USER_TOKEN>",
            "",
            "HTTP/1.1 403 FORBIDDEN",
            "",
            "{",
            '  "error": {',
            '    "code": "Forbidden",',
            '    "message": "Недостаточно прав",',
            '    "details": [',
            '      {"field": "role",',
            '       "message": "требуется organizer или admin"}',
            "    ]",
            "  }",
            "}",
        ],
        "forbidden_403.png",
        "#F87171",
    )
    build_terminal(
        "DELETE /events/{id} → 204 No Content",
        [
            "$ DELETE /events/<ID>  ·  Bearer <ADMIN_TOKEN>",
            "",
            "HTTP/1.1 204 NO CONTENT",
            "Date: Fri, 23 Oct 2026 12:00:00 GMT",
            "",
            "<тело ответа отсутствует>",
            "",
            "admin: роль + owner-check пройдены",
        ],
        "admin_204.png",
        "#4ADE80",
    )


SLIDES = [
    {
        "type": "title",
        "title": "Event Map App",
        "subtitle": "Сервис поиска и публикации локальных мероприятий",
        "meta": [
            "СРС №1 · Архитектура, API и безопасность",
            "Дисциплина: Разработка веб-приложений",
            "Студент: Фамилия Имя, группа ____",
            "Преподаватель: Самат Илияс Мырзабекулы",
            "Алматы, 2026",
        ],
    },
    {
        "type": "bullets",
        "title": "Предметная область и бизнес-задача",
        "lead": "Локальные события — на карте, с фильтрами и понятной регистрацией",
        "bullets": [
            "Пользователь | находит концерты, лекции, выставки и встречи рядом с собой",
            "Организатор | публикует мероприятие и видит отклик аудитории",
            "Ключевая ценность | геолокация, категория и дата в одном поиске",
            "Аудитория | жители города и небольшие организаторы",
            "MVP | три сервиса, REST + JWT, единые ошибки и контракт OpenAPI",
        ],
        "callout": "Сценарий MVP: найти событие → опубликовать → отметить участие → увидеть статистику",
    },
    {
        "type": "two_col",
        "title": "Пользовательские истории",
        "left_title": "Основные истории",
        "left": [
            "US-1 | карта: маркеры событий в радиусе 10 км",
            "US-2 | фильтр по категории и дате",
            "US-3 | публикация события организатором",
            "US-4 | отметка «пойду» → счётчик +1",
            "US-5 | статистика «пойду» / «интересно»",
            "US-6 | регистрация и выбор роли",
        ],
        "right_title": "Definition of Done",
        "right": [
            "US-3: organizer заполняет форму → событие видно всем",
            "US-4: отметка сохраняется, счётчик обновляется",
            "US-6: user или organizer; admin — отдельно",
            "Критерий | 401/403/400 возвращаются в едином формате",
            "Проверка | ручной чек-лист + автотесты сервисов",
        ],
    },
    {
        "type": "table",
        "title": "Выбор технологий",
        "columns": ["Критерий", "Flask", "Django", "FastAPI"],
        "widths": [2.6, 3.2, 3.2, 3.2],
        "rows": [
            ["ORM и миграции", "нет из коробки", "ORM + миграции", "SQLAlchemy / Alembic"],
            ["Auth и admin", "собрать вручную", "готовые auth + admin", "собрать вручную"],
            ["Скорость MVP", "высокая", "средняя", "высокая"],
            ["Async", "нет", "нет", "да"],
            ["Решение", "events, attendance", "users-service", "не выбран для MVP"],
        ],
        "note": "Единый стек Python 3.12; SQLite локально, PostgreSQL через DATABASE_URL.",
    },
    {
        "type": "image",
        "title": "Архитектура приложения",
        "image": "architecture.png",
        "bullets": [
            "Клиент → REST + JWT Bearer → три сервиса",
            "users-service — источник токенов и ролей",
            "events-service — доменная логика и events.db",
            "attendance-service — отметки участия, in-memory MVP",
        ],
    },
    {
        "type": "two_col",
        "title": "Структура репозитория и конфигурация",
        "left_title": "Структура",
        "left": [
            "users-service/ | Django: auth, JWT, admin",
            "events-service/ | Flask: events, Alembic, OpenAPI",
            "attendance-service/ | Flask: отметки участия",
            "docs/ | требования, auth, security, СРС1",
            "README.md | запуск, тесты, PR1–PR4",
        ],
        "right_title": "Переменные окружения",
        "right": [
            "JWT_SECRET | общий секрет подписи",
            "JWT_ISSUER | event-map-users-service",
            "JWT_EXPIRES_MINUTES | 60",
            "DJANGO_SECRET_KEY / DJANGO_DEBUG | секрет / 0",
            "DATABASE_URL | SQLite или PostgreSQL",
            "FLASK_DEBUG | 0",
        ],
        "callout": "Секреты не хранятся в коде; .env.example содержит только шаблон.",
    },
    {
        "type": "image",
        "title": "ER-модель и связи",
        "image": "er.png",
        "bullets": [
            "categories 1:N events — RESTRICT",
            "users N:M events через event_participants — CASCADE",
            "Составной PK (event_id, user_id) исключает дубли",
            "users в events-service — проекция для FK и регистраций",
        ],
    },
    {
        "type": "bullets",
        "title": "Миграции, ограничения и индексы",
        "lead": "Схема создаётся только Alembic; ограничения проверяются на уровне БД",
        "bullets": [
            "0001 | categories и events — базовые таблицы",
            "0002 | categories.slug + составной индекс",
            "0003 | users и event_participants — связь N:M",
            "CHECK | title 2..100, description ≤ 2000, lat/lng, role/status",
            "Индексы | ix_events_category_id, ix_events_category_starts_at, ix_event_participants_user_id",
            "Транзакции | commit/rollback в database.db_session; verify_tx.py",
        ],
        "callout": "Проверка: alembic upgrade head → downgrade -1 → upgrade head.",
    },
    {
        "type": "table",
        "title": "Контракт REST API",
        "columns": ["Метод и путь", "Доступ", "Назначение"],
        "widths": [4.8, 2.6, 4.8],
        "rows": [
            ["POST /auth/register", "public", "регистрация user / organizer"],
            ["POST /auth/login", "public", "проверка пароля и выдача JWT"],
            ["GET /auth/me", "auth", "текущий пользователь"],
            ["GET /users", "admin", "список пользователей"],
            ["GET /events", "public", "список + фильтры и пагинация"],
            ["POST /events", "organizer / admin", "создание события"],
            ["PUT/PATCH/DELETE /events/{id}", "owner / admin", "изменение или удаление"],
            ["POST /attendance", "auth", "отметка участия"],
            ["GET /attendance/event/{id}", "public", "статистика события"],
            ["GET /attendance/user/{id}", "self / admin", "отметки пользователя"],
        ],
        "note": "OpenAPI 3.0: events-service/openapi.yaml · версия 4.0.0 · BearerAuth.",
    },
    {
        "type": "two_col",
        "title": "Валидация и единый формат ошибок",
        "left_title": "Правила валидации",
        "left": [
            "title | 2..100 символов",
            "description | не более 2000",
            "lat / lng | -90..90 / -180..180",
            "starts_at | ISO 8601",
            "category | значение из справочника",
            "limit / page | 1..100 / ≥ 1",
        ],
        "right_title": "Пример ошибки",
        "right": [
            "HTTP/1.1 400 BAD REQUEST",
            "{",
            '  "error": {',
            '    "code": "ValidationError",',
            '    "message": "Ошибка валидации",',
            '    "details": [{"field": "lat", "message": "..."}]',
            "  }",
            "}",
        ],
        "callout": "Один формат для users, events и attendance; stack trace не возвращается.",
    },
    {
        "type": "two_col",
        "title": "Пагинация, фильтрация и пример ответа",
        "left_title": "Запрос",
        "left": [
            "GET /events",
            "  ?category=concert",
            "  &date_from=2026-10-01",
            "  &date_to=2026-10-31",
            "  &limit=2&page=1",
        ],
        "right_title": "Ответ 200 OK",
        "right": [
            "{",
            '  "items": [',
            '    {"id": "...", "title": "Концерт в парке",',
            '     "category": "concert",',
            '     "starts_at": "2026-10-01T19:00:00Z"}',
            "  ],",
            '  "page": 1, "limit": 2, "total": 1',
            "}",
        ],
        "callout": "Фильтр по категории и датам, сортировка по starts_at, limit ≤ 100.",
    },
    {
        "type": "two_col",
        "title": "Аутентификация: Argon2 + JWT",
        "left_title": "Поток входа",
        "left": [
            "1 | POST /auth/register → Argon2-хеш пароля",
            "2 | POST /auth/login → проверка Argon2",
            "3 | users-service выдаёт JWT HS256",
            "4 | клиент передаёт Authorization: Bearer <token>",
            "5 | сервис проверяет подпись, exp, iss",
            "6 | sub и role → g.current_user",
        ],
        "right_title": "Claims",
        "right": [
            "{",
            '  "sub": "user-uuid",',
            '  "role": "organizer",',
            '  "iss": "event-map-users-service",',
            '  "exp": 1760000000,',
            '  "iat": 1759996400',
            "}",
        ],
        "callout": "TTL 60 минут; пароль не хранится в открытом виде; ошибка входа не раскрывает пользователя.",
    },
    {
        "type": "table",
        "title": "Авторизация и матрица ролей",
        "columns": ["Операция", "user", "organizer", "admin"],
        "widths": [6.2, 1.7, 1.9, 1.7],
        "rows": [
            ["GET /events", "да", "да", "да"],
            ["POST /events", "нет", "да", "да"],
            ["PUT/PATCH/DELETE своего события", "нет", "да", "да"],
            ["PUT/PATCH/DELETE любого события", "нет", "нет", "да"],
            ["POST /attendance", "да", "да", "да"],
            ["GET /users", "нет", "нет", "да"],
            ["GET /attendance/user/{id}", "self", "self", "любой"],
        ],
        "note": "401 — нет или просрочен токен; 403 — роль или объект запрещён. Проверки: require_role + _authorize_event.",
    },
    {
        "type": "table",
        "title": "Угрозы API и меры защиты (OWASP)",
        "columns": ["Угроза", "Мера", "Проверка"],
        "widths": [3.1, 5.0, 4.1],
        "rows": [
            ["API1 BOLA", "owner-check + admin override", "чужое событие → 403"],
            ["API2 Broken Auth", "Argon2, JWT exp/iss, 401", "неверный пароль → 401"],
            ["API3 Mass Assignment", "id и role только из JWT", "подмена organizer_id игнорируется"],
            ["API4 Resource Consumption", "limit 1..100, длины полей", "limit=1000 → 400"],
            ["API5 BFLA", "require_role, admin-only /users", "user → /users 403"],
            ["API8 Misconfiguration", "секреты в .env, DEBUG=0", "500 без stack trace"],
        ],
        "note": "Подробнее: docs/security.md. Rate limiting и refresh-токены — план до СРС №2.",
    },
    {
        "type": "screenshots",
        "title": "Демонстрация работы API",
        "items": [
            ("success_201.png", "201 Created — создание события организатором"),
            ("validation_400.png", "400 Bad Request — ошибка валидации"),
            ("forbidden_403.png", "403 Forbidden — роль user не может удалить"),
            ("admin_204.png", "204 No Content — admin удаляет событие"),
        ],
        "note": "Фрагменты реальных HTTP-ответов; тесты: users 10, events 31, attendance 10 — все проходят.",
    },
    {
        "type": "two_col",
        "title": "Статус проекта и план до СРС №2",
        "left_title": "Сделано: PR1–PR4",
        "left": [
            "PR1 | бизнес-задача, US, архитектура, /health",
            "PR2 | OpenAPI, примеры, пагинация, ошибки",
            "PR3 | ER, миграции, индексы, N:M, транзакции",
            "PR4 | JWT, Argon2, роли, owner-check",
            "Тесты | 10 + 31 + 10, все проходят",
        ],
        "right_title": "План и риски",
        "right": [
            "PR5 | attendance в БД, синхронизация users",
            "PR6 | rate limiting, refresh-токены, HTTPS",
            "PR7 | docker-compose, CI, финальная защита",
            "Риск | JWT без отзыва; attendance in-memory",
            "Риск | users-проекция не синхронизируется автоматически",
        ],
        "callout": "Репозиторий: github.com/banumm/event-map-app · ветка main · коммит: <вставить SHA>",
    },
    {
        "type": "closing",
        "title": "Заключение",
        "bullets": [
            "MVP покрывает ключевой сценарий: найти событие → опубликовать → отметить участие.",
            "Контракт зафиксирован в OpenAPI; ошибки и доступ проверяются тестами.",
            "Безопасность: Argon2, JWT, RBAC + owner-check, анализ OWASP API Top 10.",
            "Дальше: persistence для attendance, rate limiting, CI/CD и production-конфигурация.",
        ],
        "question": "Вопросы?",
        "footer": "github.com/banumm/event-map-app · СРС №1 · 2026",
    },
]


def add_textbox(slide, left, top, width, height, text, size, bold=False, color=DARK, font=FONT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
    run.font.name = font
    return box


def add_footer(slide, number):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(7.18), Inches(11.93), Pt(1))
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor.from_string(MUTED.lstrip("#"))
    line.line.fill.background()
    add_textbox(slide, 0.7, 7.22, 6.0, 0.2, "Event Map App · СРС №1", 9.5, color=GRAY)
    add_textbox(slide, 11.9, 7.22, 0.7, 0.2, str(number), 9.5, color=GRAY, align=PP_ALIGN.RIGHT)


def add_title(slide, title, subtitle=None):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = RGBColor.from_string(TEAL.lstrip("#"))
    bar.line.fill.background()
    add_textbox(slide, 0.7, 0.38, 11.9, 0.62, title, 29, bold=True, color=NAVY)
    if subtitle:
        add_textbox(slide, 0.72, 1.0, 11.6, 0.4, subtitle, 15, color=GRAY)


def add_bullets(slide, items, left=0.85, top=1.55, width=11.6, height=4.8, size=19, gap=7):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for index, item in enumerate(items):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.08
        if " | " in item:
            lead, rest = item.split(" | ", 1)
            r1 = p.add_run()
            r1.text = "• " + lead
            r1.font.bold = True
            r1.font.size = Pt(size)
            r1.font.name = FONT
            r1.font.color.rgb = RGBColor.from_string(NAVY.lstrip("#"))
            r2 = p.add_run()
            r2.text = " — " + rest
            r2.font.size = Pt(size)
            r2.font.name = FONT
            r2.font.color.rgb = RGBColor.from_string(DARK.lstrip("#"))
        else:
            r = p.add_run()
            r.text = "• " + item
            r.font.size = Pt(size)
            r.font.name = FONT
            r.font.color.rgb = RGBColor.from_string(DARK.lstrip("#"))
    return box


def add_callout(slide, text, top=6.35, left=0.85, width=11.6, height=0.55, color=LIGHT):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(color.lstrip("#"))
    shape.line.color.rgb = RGBColor.from_string(MUTED.lstrip("#"))
    shape.line.width = Pt(1)
    shape.adjustments[0] = 0.12
    add_textbox(slide, left + 0.18, top + 0.11, width - 0.36, height - 0.16, text, 13.2, color=GRAY, anchor=MSO_ANCHOR.MIDDLE)


def add_code_box(slide, lines, left, top, width, height, size=13, title=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string("#0B1220".lstrip("#"))
    shape.line.fill.background()
    shape.adjustments[0] = 0.06
    if title:
        add_textbox(slide, left + 0.2, top + 0.12, width - 0.4, 0.25, title, 11, bold=True, color="#8BD3C7")
    box = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + (0.45 if title else 0.2)), Inches(width - 0.4), Inches(height - (0.55 if title else 0.3)))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for index, line in enumerate(lines):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.space_after = Pt(0)
        p.line_spacing = 1.0
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.name = MONO
        r.font.color.rgb = RGBColor.from_string(("#F8C471" if line.lstrip().startswith('"code"') or line.lstrip().startswith('"message"') else "#DCE6F0").lstrip("#"))


def add_image_fit(slide, path, left, top, max_width, max_height):
    with Image.open(path) as img:
        w, h = img.size
    scale = min(max_width / w, max_height / h)
    width, height = w * scale, h * scale
    x = left + (max_width - width) / 2
    y = top + (max_height - height) / 2
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(width), height=Inches(height))


def add_table(slide, columns, rows, widths, top=1.55, left=0.85, font_size=12.5, header_size=13, row_height=0.38):
    shape = slide.shapes.add_table(len(rows) + 1, len(columns), Inches(left), Inches(top), Inches(sum(widths)), Inches(row_height * (len(rows) + 1)))
    table = shape.table
    for i, width in enumerate(widths):
        table.columns[i].width = Inches(width)
    for r in range(len(rows) + 1):
        table.rows[r].height = Inches(row_height)
    for c, text in enumerate(columns):
        cell = table.cell(0, c)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(NAVY.lstrip("#"))
        cell.margin_left = Inches(0.08)
        cell.margin_right = Inches(0.08)
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.LEFT
            for run in p.runs:
                run.font.size = Pt(header_size)
                run.font.bold = True
                run.font.name = FONT
                run.font.color.rgb = RGBColor.from_string(WHITE.lstrip("#"))
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(text)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor.from_string((WHITE if r % 2 else "#EEF4F7").lstrip("#"))
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT
                for run in p.runs:
                    run.font.size = Pt(font_size)
                    run.font.name = FONT
                    run.font.color.rgb = RGBColor.from_string(DARK.lstrip("#"))
    return shape


def render_pptx(path: Path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Event Map App — СРС №1"
    prs.core_properties.author = "Фамилия Имя"
    prs.core_properties.subject = "Архитектура, API и безопасность"
    blank = prs.slide_layouts[6]

    for number, item in enumerate(SLIDES, start=1):
        slide = prs.slides.add_slide(blank)
        if item["type"] == "title":
            bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
            bg.fill.solid()
            bg.fill.fore_color.rgb = RGBColor.from_string(NAVY.lstrip("#"))
            bg.line.fill.background()
            accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.14), prs.slide_height)
            accent.fill.solid()
            accent.fill.fore_color.rgb = RGBColor.from_string(TEAL.lstrip("#"))
            accent.line.fill.background()
            add_textbox(slide, 0.9, 1.25, 11.5, 1.1, item["title"], 44, bold=True, color=WHITE)
            add_textbox(slide, 0.95, 2.35, 11.0, 0.6, item["subtitle"], 21, color="#BFD3DF")
            y = 3.45
            for line in item["meta"]:
                add_textbox(slide, 0.95, y, 11.0, 0.35, line, 15.5, color="#DCE6F0")
                y += 0.43
            add_textbox(slide, 0.95, 6.7, 11.0, 0.3, "MVP · Python 3.12 · Flask / Django · JWT", 12.5, color="#8BD3C7")
            continue

        add_title(slide, item["title"])
        if item["type"] == "bullets":
            if item.get("lead"):
                add_textbox(slide, 0.85, 1.02, 11.5, 0.42, item["lead"], 16, color=TEAL)
            add_bullets(slide, item["bullets"], top=1.6 if item.get("lead") else 1.55, size=19)
            if item.get("callout"):
                add_callout(slide, item["callout"], top=6.35)
        elif item["type"] == "two_col":
            add_textbox(slide, 0.85, 1.28, 5.5, 0.35, item["left_title"], 14.5, bold=True, color=TEAL)
            add_textbox(slide, 6.85, 1.28, 5.5, 0.35, item["right_title"], 14.5, bold=True, color=TEAL)
            add_bullets(slide, item["left"], left=0.85, top=1.75, width=5.55, height=4.2, size=16.5, gap=5)
            add_bullets(slide, item["right"], left=6.85, top=1.75, width=5.55, height=4.2, size=16.5, gap=5)
            if item.get("callout"):
                add_callout(slide, item["callout"], top=6.35)
        elif item["type"] == "table":
            add_table(slide, item["columns"], item["rows"], item["widths"], top=1.5)
            if item.get("note"):
                add_callout(slide, item["note"], top=6.35)
        elif item["type"] == "image":
            add_image_fit(slide, ASSETS / item["image"], 0.65, 1.25, 12.05, 4.55)
            add_bullets(slide, item["bullets"], top=5.95, size=13.5, gap=1, height=0.95)
        elif item["type"] == "screenshots":
            coords = [(0.72, 1.15), (6.82, 1.15), (0.72, 3.78), (6.82, 3.78)]
            for (filename, caption), (x, y) in zip(item["items"], coords):
                add_image_fit(slide, SHOTS / filename, x, y, 5.65, 2.28)
                add_textbox(slide, x, y + 2.36, 5.65, 0.28, caption, 11.5, bold=True, color=GRAY, align=PP_ALIGN.CENTER)
            add_callout(slide, item["note"], top=6.62, height=0.42)
        elif item["type"] == "closing":
            add_bullets(slide, item["bullets"], top=1.55, size=20, gap=12, height=3.9)
            add_textbox(slide, 0.85, 5.7, 11.4, 0.55, item["question"], 30, bold=True, color=TEAL)
            add_callout(slide, item["footer"], top=6.55)
        add_footer(slide, number)

    prs.save(str(path))


PDF_W, PDF_H = landscape((13.333 * inch, 7.5 * inch))


def register_pdf_fonts():
    pdfmetrics.registerFont(TTFont("Arial", str(FONT_DIR / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_DIR / "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("Consolas", str(FONT_DIR / "consola.ttf")))
    pdfmetrics.registerFont(TTFont("Consolas-Bold", str(FONT_DIR / "consolab.ttf")))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")


def pdf_style(size=19, leading=None, color=DARK, bold=False, left_indent=0, bullet_indent=0):
    return ParagraphStyle(
        "body",
        fontName="Arial-Bold" if bold else "Arial",
        fontSize=size,
        leading=leading or (size * 1.22),
        textColor=colors.HexColor(color),
        leftIndent=left_indent,
        bulletIndent=bullet_indent,
        spaceAfter=5,
        alignment=TA_LEFT,
    )


def pdf_header(c, title, number, subtitle=None):
    c.setFillColor(colors.white)
    c.rect(0, 0, PDF_W, PDF_H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(TEAL))
    c.rect(0, PDF_H - 0.11 * inch, PDF_W, 0.11 * inch, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(NAVY))
    c.setFont("Arial-Bold", 29)
    c.drawString(0.7 * inch, PDF_H - 0.82 * inch, title)
    if subtitle:
        c.setFont("Arial", 15)
        c.setFillColor(colors.HexColor(GRAY))
        c.drawString(0.72 * inch, PDF_H - 1.14 * inch, subtitle)
    c.setStrokeColor(colors.HexColor(MUTED))
    c.setLineWidth(0.6)
    c.line(0.7 * inch, 0.32 * inch, PDF_W - 0.7 * inch, 0.32 * inch)
    c.setFont("Arial", 9)
    c.setFillColor(colors.HexColor(GRAY))
    c.drawString(0.7 * inch, 0.18 * inch, "Event Map App · СРС №1")
    c.drawRightString(PDF_W - 0.7 * inch, 0.18 * inch, str(number))


def pdf_bullets(c, items, x, y_top, width, size=19, gap=7):
    y = y_top
    for item in items:
        if " | " in item:
            lead, rest = item.split(" | ", 1)
            text = f"<b>{escape(lead)}</b> — {escape(rest)}"
        else:
            text = escape(item)
        p = Paragraph(text, pdf_style(size=size, leading=size * 1.22), bulletText="•")
        _, h = p.wrap(width, PDF_H)
        p.drawOn(c, x, y - h)
        y -= h + gap
    return y


def pdf_callout(c, text, top, height=0.55, left=0.85, width=11.6):
    x = left * inch
    y = PDF_H - top * inch - height * inch
    c.setFillColor(colors.HexColor(LIGHT))
    c.setStrokeColor(colors.HexColor(MUTED))
    c.roundRect(x, y, width * inch, height * inch, 7, fill=1, stroke=1)
    p = Paragraph(escape(text), pdf_style(size=13, color=GRAY, leading=16))
    tx = x + 0.16 * inch
    ty = y + height * inch - 0.14 * inch
    _, h = p.wrap(width * inch - 0.32 * inch, height * inch)
    p.drawOn(c, tx, ty - h)


def pdf_code(c, lines, left, top, width, height, size=12):
    x = left * inch
    y = PDF_H - top * inch - height * inch
    c.setFillColor(colors.HexColor("#0B1220"))
    c.roundRect(x, y, width * inch, height * inch, 7, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#DCE6F0"))
    c.setFont("Consolas", size)
    ty = y + height * inch - 0.22 * inch
    for line in lines:
        color = "#F8C471" if line.lstrip().startswith('"code"') or line.lstrip().startswith('"message"') else "#DCE6F0"
        c.setFillColor(colors.HexColor(color))
        c.drawString(x + 0.18 * inch, ty, line)
        ty -= size * 1.26


def pdf_table(c, columns, rows, widths, top=1.5, left=0.85, font_size=12.5, header_size=13, row_height=0.38):
    data = []
    data.append([Paragraph(f"<b>{escape(str(v))}</b>", pdf_style(size=header_size, color=WHITE, leading=15)) for v in columns])
    for row in rows:
        data.append([Paragraph(escape(str(v)), pdf_style(size=font_size, leading=font_size * 1.15)) for v in row])
    table = Table(data, colWidths=[w * inch for w in widths], rowHeights=[row_height * inch] * len(data))
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCE6EC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    for i in range(1, len(data)):
        style.append(("BACKGROUND", (0, i), (-1, i), colors.white if i % 2 else colors.HexColor("#EEF4F7")))
    table.setStyle(TableStyle(style))
    _, h = table.wrapOn(c, PDF_W, PDF_H)
    table.drawOn(c, left * inch, PDF_H - top * inch - h)
    return h


def pdf_image(c, path, left, top, max_width, max_height):
    with Image.open(path) as img:
        iw, ih = img.size
    scale = min((max_width * inch) / iw, (max_height * inch) / ih)
    width, height = iw * scale, ih * scale
    x = left * inch + (max_width * inch - width) / 2
    y = PDF_H - top * inch - max_height * inch + (max_height * inch - height) / 2
    c.drawImage(str(path), x, y, width=width, height=height, preserveAspectRatio=True, mask="auto")


def render_pdf(path: Path):
    register_pdf_fonts()
    c = canvas.Canvas(str(path), pagesize=(PDF_W, PDF_H))
    c.setTitle("Event Map App — СРС №1")

    for number, item in enumerate(SLIDES, start=1):
        if item["type"] == "title":
            c.setFillColor(colors.HexColor(NAVY))
            c.rect(0, 0, PDF_W, PDF_H, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(TEAL))
            c.rect(0, 0, 0.14 * inch, PDF_H, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Arial-Bold", 44)
            c.drawString(0.9 * inch, PDF_H - 1.7 * inch, item["title"])
            c.setFillColor(colors.HexColor("#BFD3DF"))
            c.setFont("Arial", 21)
            c.drawString(0.95 * inch, PDF_H - 2.35 * inch, item["subtitle"])
            c.setFont("Arial", 15.5)
            c.setFillColor(colors.HexColor("#DCE6F0"))
            y = PDF_H - 3.45 * inch
            for line in item["meta"]:
                c.drawString(0.95 * inch, y, line)
                y -= 0.43 * inch
            c.setFont("Arial", 12.5)
            c.setFillColor(colors.HexColor("#8BD3C7"))
            c.drawString(0.95 * inch, 0.8 * inch, "MVP · Python 3.12 · Flask / Django · JWT")
        else:
            pdf_header(c, item["title"], number)
            if item["type"] == "bullets":
                if item.get("lead"):
                    c.setFont("Arial", 16)
                    c.setFillColor(colors.HexColor(TEAL))
                    c.drawString(0.85 * inch, PDF_H - 1.1 * inch, item["lead"])
                pdf_bullets(c, item["bullets"], 0.85 * inch, PDF_H - (1.65 if item.get("lead") else 1.55) * inch, 11.5 * inch, size=19)
                if item.get("callout"):
                    pdf_callout(c, item["callout"], 6.35)
            elif item["type"] == "two_col":
                c.setFont("Arial-Bold", 14.5)
                c.setFillColor(colors.HexColor(TEAL))
                c.drawString(0.85 * inch, PDF_H - 1.28 * inch, item["left_title"])
                c.drawString(6.85 * inch, PDF_H - 1.28 * inch, item["right_title"])
                pdf_bullets(c, item["left"], 0.85 * inch, PDF_H - 1.75 * inch, 5.55 * inch, size=16.5, gap=5)
                pdf_bullets(c, item["right"], 6.85 * inch, PDF_H - 1.75 * inch, 5.55 * inch, size=16.5, gap=5)
                if item.get("callout"):
                    pdf_callout(c, item["callout"], 6.35)
            elif item["type"] == "table":
                pdf_table(c, item["columns"], item["rows"], item["widths"], top=1.5, font_size=12.5, header_size=13, row_height=0.38)
                if item.get("note"):
                    pdf_callout(c, item["note"], 6.35)
            elif item["type"] == "image":
                pdf_image(c, ASSETS / item["image"], 0.65, 1.25, 12.05, 4.55)
                pdf_bullets(c, item["bullets"], 0.85 * inch, PDF_H - 5.95 * inch, 11.5 * inch, size=13.5, gap=1)
            elif item["type"] == "screenshots":
                coords = [(0.72, 1.15), (6.82, 1.15), (0.72, 3.78), (6.82, 3.78)]
                for (filename, caption), (x, y) in zip(item["items"], coords):
                    pdf_image(c, SHOTS / filename, x, y, 5.65, 2.28)
                    c.setFont("Arial-Bold", 11.5)
                    c.setFillColor(colors.HexColor(GRAY))
                    c.drawCentredString((x + 5.65 / 2) * inch, PDF_H - (y + 2.44) * inch, caption)
                pdf_callout(c, item["note"], 6.62, height=0.42)
            elif item["type"] == "closing":
                pdf_bullets(c, item["bullets"], 0.85 * inch, PDF_H - 1.55 * inch, 11.4 * inch, size=20, gap=12)
                c.setFont("Arial-Bold", 30)
                c.setFillColor(colors.HexColor(TEAL))
                c.drawString(0.85 * inch, PDF_H - 5.75 * inch, item["question"])
                pdf_callout(c, item["footer"], 6.55)
        c.showPage()
    c.save()


def main():
    build_architecture()
    build_er()
    build_screenshots()
    render_pptx(BASE / "СРС1_Фамилия_Имя_Группа.pptx")
    render_pdf(BASE / "СРС1_Фамилия_Имя_Группа.pdf")
    print(f"Built: {BASE / 'СРС1_Фамилия_Имя_Группа.pptx'}")
    print(f"Built: {BASE / 'СРС1_Фамилия_Имя_Группа.pdf'}")


if __name__ == "__main__":
    main()
