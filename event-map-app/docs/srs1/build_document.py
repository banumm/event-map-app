#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the SRS1 Word document and its PDF version."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
SHOTS = ASSETS / "screenshots"

NAVY = "152238"
TEAL = "1F8A70"
ORANGE = "E76F51"
DARK = "17212B"
GRAY = "5B6770"
MUTED = "D9E2E8"
LIGHT = "F4F7FA"
WHITE = "FFFFFF"

DOCX_NAME = "СРС1_Фамилия_Имя_Группа_документ.docx"


def set_run_font(run, name="Times New Roman", size=12, bold=False, italic=False, color=DARK):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), name)
    rFonts.set(qn("w:hAnsi"), name)
    rFonts.set(qn("w:cs"), name)


def set_style(doc: Document, name: str, size: int, bold: bool = False, color: str = DARK):
    style = doc.styles[name]
    style.font.name = "Times New Roman"
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
    style.paragraph_format.keep_with_next = True
    style.paragraph_format.space_before = Pt(10)
    style.paragraph_format.space_after = Pt(4)


def add_par(doc: Document, text: str, bold: str | None = None, indent: bool = True, size: int = 12):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(4)
    if indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    if bold and text.startswith(bold):
        r1 = p.add_run(bold)
        set_run_font(r1, size=size, bold=True, color=NAVY)
        r2 = p.add_run(text[len(bold):])
        set_run_font(r2, size=size, color=DARK)
    else:
        run = p.add_run(text)
        set_run_font(run, size=size, color=DARK)
    return p


def add_bullet(doc: Document, text: str, size: int = 12):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.first_line_indent = Cm(-0.35)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run("• " + text)
    set_run_font(run, size=size, color=DARK)
    return p


def add_caption(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(7)
    run = p.add_run(text)
    set_run_font(run, size=10, italic=True, color=GRAY)
    return p


def add_code(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.25)
    p.paragraph_format.right_indent = Cm(0.25)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.line_spacing = 1.0
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "0B1220")
    pPr.append(shd)
    run = p.add_run(text)
    set_run_font(run, name="Consolas", size=9, color="DCE6F0")
    return p


def set_cell_background(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    trPr.append(header)
    cant_split = OxmlElement("w:cantSplit")
    trPr.append(cant_split)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None, font_size: float = 9.5):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    header_row = table.rows[0]
    set_repeat_header(header_row)
    for index, text in enumerate(headers):
        cell = header_row.cells[index]
        cell.text = ""
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(cell, NAVY)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(text)
        set_run_font(run, size=font_size, bold=True, color=WHITE)
        if widths:
            cell.width = Cm(widths[index])
    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for index, text in enumerate(row):
            cell = cells[index]
            cell.text = ""
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index % 2 == 1:
                set_cell_background(cell, "EEF4F7")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(str(text))
            set_run_font(run, size=font_size, color=DARK)
            if widths:
                cell.width = Cm(widths[index])
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_figure(doc: Document, path: Path, width_cm: float, caption: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    add_caption(doc, caption)


def add_screenshot_grid(doc: Document):
    items = [
        ("success_201.png", "Рисунок 4 — 201 Created: создание события организатором"),
        ("validation_400.png", "Рисунок 5 — 400 Bad Request: ошибка валидации"),
        ("forbidden_403.png", "Рисунок 6 — 403 Forbidden: роль user не может удалить событие"),
        ("admin_204.png", "Рисунок 7 — 204 No Content: admin удаляет событие"),
    ]
    table = doc.add_table(rows=2, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, (filename, caption) in enumerate(items):
        cell = table.cell(index // 2, index % 2)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(str(SHOTS / filename), width=Cm(7.8))
        cap = cell.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(5)
        cap_run = cap.add_run(caption)
        set_run_font(cap_run, size=8.5, italic=True, color=GRAY)


def add_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_ALIGN_PARAGRAPH.RIGHT)
    run = p.add_run("Event Map App · СРС №1\t")
    set_run_font(run, size=9, color=GRAY)
    run2 = p.add_run()
    set_run_font(run2, size=9, color=GRAY)
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run2._r.append(fld_begin)
    run2._r.append(instr)
    run2._r.append(fld_end)


def build_docx(path: Path):
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(1.5)
    add_footer(section)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(4)

    set_style(doc, "Heading 1", 16, True, NAVY)
    set_style(doc, "Heading 2", 13, True, TEAL)
    set_style(doc, "Heading 3", 12, True, DARK)

    # ---------- Title page ----------
    for _ in range(5):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("СРС №1")
    set_run_font(run, size=18, bold=True, color=TEAL)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    run = p.add_run("Event Map App")
    set_run_font(run, size=30, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run("Сервис поиска и публикации локальных мероприятий")
    set_run_font(run, size=16, color=DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    run = p.add_run("Архитектура, REST API, база данных и безопасность")
    set_run_font(run, size=14, color=GRAY)

    for _ in range(5):
        doc.add_paragraph()
    for line in [
        "Дисциплина: Разработка веб-приложений",
        "Студент: Фамилия Имя, группа ____",
        "Преподаватель: Самат Илияс Мырзабекулы",
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(line)
        set_run_font(run, size=12, color=DARK) if "Студент" not in line else set_run_font(run, size=12, color=ORANGE)
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Алматы, 2026")
    set_run_font(run, size=12, color=GRAY)
    doc.add_page_break()

    # ---------- Annotation and contents ----------
    doc.add_heading("Аннотация", level=1)
    add_par(
        doc,
        "Документ описывает MVP Event Map App: предметную область, требования, "
        "архитектуру трёх сервисов, модель данных, контракт REST API, "
        "аутентификацию и авторизацию, единый формат ошибок и анализ угроз "
        "OWASP API Security Top 10. Материалы соответствуют ПР1–ПР4 и "
        "используются как пояснительная записка к презентации СРС №1.",
    )

    doc.add_heading("Содержание", level=1)
    contents = [
        "1. Введение",
        "2. Требования и пользовательские истории",
        "3. Выбор технологий",
        "4. Архитектура приложения",
        "5. Структура репозитория и конфигурация",
        "6. Модель данных",
        "7. Миграции, ограничения и индексы",
        "8. Контракт REST API",
        "9. Валидация и единый формат ошибок",
        "10. Пагинация и фильтрация",
        "11. Аутентификация",
        "12. Авторизация и роли",
        "13. Безопасность API",
        "14. Демонстрация работы",
        "15. Статус проекта и план",
        "16. Заключение",
        "17. Список использованных источников",
        "Приложение А. Команды запуска и проверки",
    ]
    for item in contents:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(item)
        set_run_font(run, size=11.5, color=DARK)
    doc.add_page_break()

    # ---------- 1. Introduction ----------
    doc.add_heading("1. Введение", level=1)
    doc.add_heading("1.1. Предметная область", level=2)
    add_par(
        doc,
        "Event Map App помогает жителям города находить локальные мероприятия "
        "на карте: концерты, лекции, выставки и встречи. Пользователь может "
        "фильтровать события по категории и дате, отмечать «пойду» или "
        "«интересно». Организаторы публикуют мероприятия и видят отклик "
        "аудитории.",
    )
    add_par(
        doc,
        "Ключевая ценность продукта — быстрый поиск событий рядом с собой и "
        "простой способ публикации без сложной инфраструктуры. Для MVP "
        "достаточно трёх независимых сервисов и единого контракта API.",
        bold="Ключевая ценность продукта",
    )
    doc.add_heading("1.2. Цель и задачи", level=2)
    add_par(doc, "Цель работы — спроектировать и реализовать MVP сервиса, в котором:")
    for text in [
        "пользователь находит события на карте и фильтрует их;",
        "организатор публикует событие и видит статистику отметок;",
        "аутентификация и роли едины для всех сервисов;",
        "контракт API зафиксирован в OpenAPI, а ошибки имеют единый формат.",
    ]:
        add_bullet(doc, text)
    add_par(doc, "Для достижения цели решаются задачи:")
    for text in [
        "сформулировать бизнес-задачу и пользовательские истории;",
        "выбрать стек и спроектировать архитектуру из трёх сервисов;",
        "описать модель данных, миграции, ограничения и индексы;",
        "реализовать REST API, валидацию, пагинацию и обработку ошибок;",
        "добавить JWT-аутентификацию, RBAC и проверку владельца объекта;",
        "проверить сценарии доступа автотестами и проанализировать угрозы OWASP.",
    ]:
        add_bullet(doc, text)

    doc.add_heading("1.3. Целевая аудитория", level=2)
    add_par(
        doc,
        "Основные пользователи — жители города, которые ищут локальные события, "
        "и небольшие организаторы: клубы, лекторы, образовательные проекты и "
        "локальные сообщества. Отдельная роль admin нужна для модерации и "
        "просмотра пользователей.",
    )

    # ---------- 2. Requirements ----------
    doc.add_heading("2. Требования и пользовательские истории", level=1)
    add_par(
        doc,
        "Требования сформулированы в формате пользовательских историй. Для "
        "каждой истории задан критерий приёмки, который проверяется вручную "
        "или автотестами.",
    )
    add_table(
        doc,
        ["ID", "Пользовательская история", "Критерий приёмки"],
        [
            ["US-1", "Просмотр мероприятий на карте", "Пользователь видит маркеры событий в радиусе 10 км"],
            ["US-2", "Фильтрация по категории и дате", "В списке остаются только подходящие события"],
            ["US-3", "Публикация мероприятия", "Organizer заполняет форму, событие видно всем"],
            ["US-4", "Отметка участия", "Отметка сохраняется, счётчик увеличивается на 1"],
            ["US-5", "Статистика организатора", "«Пойду» и «интересно» показаны отдельно"],
            ["US-6", "Регистрация и выбор роли", "Создаётся user или organizer; admin — отдельно"],
        ],
        widths=[1.5, 6.2, 9.5],
    )
    add_caption(doc, "Таблица 1 — Пользовательские истории MVP")
    add_par(doc, "Definition of Done для MVP:", bold="Definition of Done для MVP:")
    for text in [
        "все шесть историй покрыты API и проверены вручную;",
        "для успешных и ошибочных сценариев возвращаются корректные HTTP-коды;",
        "изменяющие запросы защищены JWT, роли и проверкой владельца;",
        "контракт API описан в OpenAPI, примеры запросов лежат в docs/examples.http;",
        "автотесты users-service, events-service и attendance-service проходят.",
    ]:
        add_bullet(doc, text)

    # ---------- 3. Technology choice ----------
    doc.add_heading("3. Выбор технологий", level=1)
    add_par(
        doc,
        "Для реализации рассматривались Flask, Django и FastAPI. Сравнение "
        "проводилось по наличию ORM и миграций, готовой аутентификации, "
        "админ-панели, скорости разработки MVP и поддержке async.",
    )
    add_table(
        doc,
        ["Критерий", "Flask", "Django", "FastAPI"],
        [
            ["ORM и миграции", "нет из коробки", "ORM + миграции", "SQLAlchemy / Alembic"],
            ["Auth и admin", "собрать вручную", "готовые auth + admin", "собрать вручную"],
            ["Скорость MVP", "высокая", "средняя", "высокая"],
            ["Async", "нет", "нет", "да"],
            ["Решение", "events, attendance", "users-service", "не выбран для MVP"],
        ],
        widths=[4.0, 4.0, 4.0, 4.5],
    )
    add_caption(doc, "Таблица 2 — Сравнение вариантов стека")
    add_par(
        doc,
        "Для events-service и attendance-service выбран Flask: обоим сервисам "
        "нужен компактный REST/CRUD без сложной админки. Для users-service "
        "выбран Django: он даёт готовую модель пользователя, хеширование "
        "паролей, миграции и админ-панель. FastAPI не выбран для MVP, потому "
        "что async не является критичным, а готовую аутентификацию и админку "
        "пришлось бы собирать отдельно.",
    )
    add_par(
        doc,
        "Итоговый стек: Python 3.12, Django 5.0.7, Flask 3.0.3, SQLAlchemy 2, "
        "Alembic, SQLite локально и PostgreSQL через DATABASE_URL, PyJWT, "
        "argon2-cffi, OpenAPI 3.0.",
    )

    # ---------- 4. Architecture ----------
    doc.add_page_break()
    doc.add_heading("4. Архитектура приложения", level=1)
    add_figure(doc, ASSETS / "architecture.png", 16.4, "Рисунок 1 — Архитектура Event Map App")
    add_table(
        doc,
        ["Сервис", "Ответственность", "Данные", "Порт"],
        [
            ["users-service", "Регистрация, вход, JWT, роли, профиль", "users, роли", "8000"],
            ["events-service", "CRUD мероприятий, фильтры, владелец", "events, categories, users-проекция", "5001"],
            ["attendance-service", "Отметки «пойду» / «интересно»", "attendance (in-memory MVP)", "5002"],
        ],
        widths=[4.0, 7.0, 5.0, 2.2],
    )
    add_caption(doc, "Таблица 3 — Сервисы и зоны ответственности")
    add_par(doc, "Основной сценарий взаимодействия:")
    for index, text in enumerate([
        "Клиент регистрируется или входит через users-service и получает JWT.",
        "Клиент передаёт токен в заголовке Authorization: Bearer <token>.",
        "Events и attendance проверяют подпись, exp и iss локально общим секретом.",
        "events-service дополнительно проверяет роль и владельца события.",
        "Ошибки всех сервисов приводятся к единому JSON-формату.",
    ], start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{index}. {text}")
        set_run_font(run, size=12, color=DARK)
    add_par(
        doc,
        "users-service — источник истины для аутентификации. В events-service "
        "есть отдельная таблица users как проекция для внешних ключей и "
        "регистраций; автоматическая синхронизация этой проекции с "
        "users-service пока не реализована и вынесена в план PR5.",
        bold="users-service — источник истины",
    )
    add_par(
        doc,
        "Внутри events-service используется слоистая структура: маршрут → "
        "валидация → сервис → репозиторий → база данных. Граница транзакции "
        "находится в database.db_session: commit при успехе и rollback при ошибке.",
    )

    # ---------- 5. Repository and config ----------
    doc.add_heading("5. Структура репозитория и конфигурация", level=1)
    add_code(
        doc,
        "event-map-app/\n"
        "├── users-service/        Django: auth, JWT, admin\n"
        "├── events-service/       Flask: events, Alembic, OpenAPI\n"
        "├── attendance-service/   Flask: отметки участия\n"
        "├── docs/                 требования, auth, security, СРС1\n"
        "└── README.md             запуск, тесты, PR1–PR4",
    )
    add_par(
        doc,
        "Секреты не хранятся в коде. В репозитории есть только .env.example "
        "с шаблоном переменных; реальные значения задаются в .env и не "
        "коммитятся. Для production DEBUG выключен.",
    )
    add_table(
        doc,
        ["Переменная", "Назначение", "Пример"],
        [
            ["JWT_SECRET", "общий секрет подписи JWT", "change-me-in-production"],
            ["JWT_ALGORITHM", "алгоритм подписи", "HS256"],
            ["JWT_ISSUER", "издатель токена", "event-map-users-service"],
            ["JWT_EXPIRES_MINUTES", "время жизни access-токена", "60"],
            ["DJANGO_SECRET_KEY", "секрет Django", "change-me"],
            ["DJANGO_DEBUG", "режим отладки", "0"],
            ["DATABASE_URL", "подключение к БД", "sqlite:///events.db"],
            ["FLASK_DEBUG", "режим отладки Flask", "0"],
        ],
        widths=[5.0, 7.0, 6.0],
    )
    add_caption(doc, "Таблица 4 — Основные переменные окружения")

    # ---------- 6. Data model ----------
    doc.add_page_break()
    doc.add_heading("6. Модель данных", level=1)
    add_figure(doc, ASSETS / "er.png", 16.4, "Рисунок 2 — ER-модель events-service")
    add_par(
        doc,
        "Модель данных включает справочник категорий, мероприятия, "
        "пользователей и регистрации. Связь categories → events имеет тип "
        "1:N с ограничением RESTRICT: категорию нельзя удалить, пока в ней "
        "есть события. Связь users ↔ events реализована через "
        "event_participants с типом N:M и каскадным удалением.",
    )
    add_table(
        doc,
        ["Таблица", "Ключевые поля", "Ограничения"],
        [
            ["categories", "id, name, slug, created_at", "name и slug уникальны"],
            ["events", "id, title, description, lat, lng, starts_at, category_id, organizer_id", "CHECK длины, координат; FK на categories"],
            ["users", "id, name, email, role, created_at", "email уникален; role ∈ admin/organizer/user"],
            ["event_participants", "event_id, user_id, registered_at, status", "составной PK; status ∈ registered/attended/cancelled"],
        ],
        widths=[4.3, 8.7, 5.0],
    )
    add_caption(doc, "Таблица 5 — Основные сущности и ограничения")
    add_par(
        doc,
        "Составной первичный ключ (event_id, user_id) в event_participants "
        "гарантирует, что один пользователь регистрируется на мероприятие "
        "только один раз. Внешние ключи event_id и user_id используют "
        "ON DELETE CASCADE, а category_id в events — ON DELETE RESTRICT.",
    )

    # ---------- 7. Migrations ----------
    doc.add_heading("7. Миграции, ограничения и индексы", level=1)
    add_par(
        doc,
        "Схема создаётся только миграциями Alembic, а не вручную через "
        "SQL-консоль. Это позволяет воспроизвести базу с нуля и "
        "продемонстрировать откат.",
    )
    add_table(
        doc,
        ["Миграция", "Что делает"],
        [
            ["0001", "Создаёт categories и events"],
            ["0002", "Добавляет categories.slug и составной индекс"],
            ["0003", "Создаёт users и event_participants (N:M)"],
        ],
        widths=[3.0, 13.5],
    )
    add_caption(doc, "Таблица 6 — Миграции events-service")
    add_par(doc, "Основные индексы и их назначение:")
    add_table(
        doc,
        ["Индекс", "Таблица", "Колонки", "Зачем"],
        [
            ["ix_events_category_id", "events", "category_id", "фильтр по категории, поддержка FK"],
            ["ix_events_category_starts_at", "events", "category_id, starts_at", "фильтр категория+даты и сортировка"],
            ["ix_event_participants_user_id", "event_participants", "user_id", "события пользователя, поддержка FK"],
        ],
        widths=[6.0, 4.0, 4.5, 5.0],
    )
    add_caption(doc, "Таблица 7 — Индексы и обоснование")
    add_par(
        doc,
        "Транзакции демонстрируются в verify_tx.py: при ошибке CHECK на "
        "событии откатывается и вставка категории; пакетная вставка событий "
        "при сбое одной записи откатывается целиком. verify_schema.py "
        "проверяет N:M, защиту от дублей и каскадное удаление.",
    )
    add_code(
        doc,
        "cd events-service\n"
        "alembic upgrade head      # 0001 -> 0002 -> 0003\n"
        "alembic downgrade -1      # откат последней миграции\n"
        "alembic upgrade head      # вернуть схему",
    )

    # ---------- 8. API ----------
    doc.add_page_break()
    doc.add_heading("8. Контракт REST API", level=1)
    add_par(
        doc,
        "Контракт описан в events-service/openapi.yaml (OpenAPI 3.0, версия "
        "4.0.0). Для защищённых операций используется BearerAuth. Примеры "
        "запросов находятся в events-service/docs/examples.http.",
    )
    add_table(
        doc,
        ["Метод и путь", "Доступ", "Назначение"],
        [
            ["POST /auth/register", "публично", "регистрация user / organizer"],
            ["POST /auth/login", "публично", "проверка пароля и выдача JWT"],
            ["GET /auth/me", "JWT", "текущий пользователь"],
            ["GET /users", "admin", "список пользователей"],
            ["GET /events", "публично", "список, фильтры и пагинация"],
            ["POST /events", "organizer / admin", "создание события"],
            ["PUT/PATCH/DELETE /events/{id}", "owner / admin", "изменение или удаление"],
            ["POST /attendance", "JWT", "отметка участия"],
            ["GET /attendance/event/{id}", "публично", "статистика события"],
            ["GET /attendance/user/{id}", "self / admin", "отметки пользователя"],
        ],
        widths=[6.3, 4.2, 7.0],
    )
    add_caption(doc, "Таблица 8 — Основные эндпоинты")
    add_par(doc, "Пример создания события:")
    add_code(
        doc,
        'POST /events\n'
        'Authorization: Bearer <ORG_TOKEN>\n'
        'Content-Type: application/json\n\n'
        '{\n'
        '  "title": "Концерт в парке",\n'
        '  "description": "Живая музыка на открытой площадке",\n'
        '  "lat": 55.7558,\n'
        '  "lng": 37.6176,\n'
        '  "starts_at": "2026-10-01T19:00:00Z",\n'
        '  "category": "concert"\n'
        '}\n\n'
        'HTTP/1.1 201 CREATED\n'
        '{"id":"...","title":"Концерт в парке","organizer_id":"..."}',
    )
    add_par(
        doc,
        "HTTP-коды: 200 — успешное чтение/обновление, 201 — создание, "
        "204 — удаление, 400 — валидация, 401 — нет или просрочен токен, "
        "403 — недостаточно прав, 404 — объект не найден, 409 — конфликт "
        "уникальности, 500 — внутренняя ошибка.",
    )

    # ---------- 9. Validation ----------
    doc.add_heading("9. Валидация и единый формат ошибок", level=1)
    add_par(
        doc,
        "Валидация выполняется до обращения к бизнес-логике. Ошибки "
        "собираются в details, чтобы клиент мог показать все проблемные поля "
        "сразу.",
    )
    add_table(
        doc,
        ["Поле", "Правило"],
        [
            ["title", "строка от 2 до 100 символов"],
            ["description", "строка не длиннее 2000 символов"],
            ["lat / lng", "числа в диапазонах -90..90 и -180..180"],
            ["starts_at", "ISO 8601"],
            ["category", "значение из справочника"],
            ["limit / page", "limit 1..100 (по умолчанию 20), page ≥ 1"],
        ],
        widths=[5.0, 11.5],
    )
    add_caption(doc, "Таблица 9 — Правила валидации")
    add_par(doc, "Единый формат ошибки:")
    add_code(
        doc,
        'HTTP/1.1 400 BAD REQUEST\n'
        '{\n'
        '  "error": {\n'
        '    "code": "ValidationError",\n'
        '    "message": "Ошибка валидации",\n'
        '    "details": [\n'
        '      {"field": "lat", "message": "должно быть числом"}\n'
        '    ]\n'
        '  }\n'
        '}',
    )
    add_par(
        doc,
        "Один и тот же формат используется в users-service, events-service и "
        "attendance-service. Глобальные обработчики не возвращают stack trace "
        "и приводят ответы 400/401/403/404/405/409/500 к общей схеме.",
    )

    # ---------- 10. Pagination ----------
    doc.add_heading("10. Пагинация и фильтрация", level=1)
    add_par(
        doc,
        "Список событий поддерживает фильтр по категории и диапазону дат, "
        "пагинацию и сортировку по starts_at. Значения limit и page "
        "проверяются; limit не может превышать 100.",
    )
    add_code(
        doc,
        'GET /events?category=concert&date_from=2026-10-01\n'
        '    &date_to=2026-10-31&limit=2&page=1\n\n'
        'HTTP/1.1 200 OK\n'
        '{\n'
        '  "items": [\n'
        '    {"id":"...","title":"Концерт в парке",\n'
        '     "category":"concert","starts_at":"2026-10-01T19:00:00Z"}\n'
        '  ],\n'
        '  "page": 1,\n'
        '  "limit": 2,\n'
        '  "total": 1\n'
        '}',
    )

    # ---------- 11. Authentication ----------
    doc.add_heading("11. Аутентификация", level=1)
    add_par(
        doc,
        "Выбран JWT (HS256, срок действия 60 минут, issuer "
        "event-map-users-service). Пароли хранятся только как Argon2-хеш. "
        "При входе users-service проверяет пароль и выдаёт access-токен; "
        "остальные сервисы проверяют токен локально общим секретом.",
    )
    add_par(doc, "Поток входа:")
    for index, text in enumerate([
        "POST /auth/register: валидация логина, email, пароля и роли.",
        "Пароль хешируется Argon2; роль ограничена user или organizer.",
        "POST /auth/login: проверка пароля, выдача JWT.",
        "Клиент передаёт Authorization: Bearer <token>.",
        "Сервис проверяет подпись, exp и iss; sub и role попадают в g.current_user.",
    ], start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{index}. {text}")
        set_run_font(run, size=12, color=DARK)
    add_code(
        doc,
        '{\n'
        '  "sub": "user-uuid",\n'
        '  "role": "organizer",\n'
        '  "iss": "event-map-users-service",\n'
        '  "exp": 1760000000,\n'
        '  "iat": 1759996400\n'
        '}',
    )
    add_par(
        doc,
        "JWT выбран потому, что сервисы разделены и должны проверять "
        "пользователя без обращения к сессионному хранилищу. Ограничение: "
        "отзыв токена до истечения срока не поддерживается; refresh-токены и "
        "blacklist вынесены в план PR6.",
    )

    # ---------- 12. Authorization ----------
    doc.add_heading("12. Авторизация и роли", level=1)
    add_par(
        doc,
        "Аутентификация (401) и авторизация (403) разделены. Роль проверяется "
        "декоратором require_role, а владелец объекта — функцией "
        "_authorize_event: organizer_id события сравнивается с sub из JWT. "
        "Admin обходит проверку владельца.",
    )
    add_table(
        doc,
        ["Операция", "user", "organizer", "admin"],
        [
            ["GET /events", "да", "да", "да"],
            ["POST /events", "нет", "да", "да"],
            ["PUT/PATCH/DELETE своего события", "нет", "да", "да"],
            ["PUT/PATCH/DELETE любого события", "нет", "нет", "да"],
            ["POST /attendance", "да", "да", "да"],
            ["GET /users", "нет", "нет", "да"],
            ["GET /attendance/user/{id}", "self", "self", "любой"],
        ],
        widths=[7.5, 3.0, 3.2, 3.0],
    )
    add_caption(doc, "Таблица 10 — Матрица ролей")
    add_par(
        doc,
        "organizer_id и user_id никогда не берутся из тела запроса: они "
        "определяются по проверенному JWT. Это защищает от массового "
        "присвоения ролей и чужих идентификаторов.",
    )

    # ---------- 13. Security ----------
    doc.add_page_break()
    doc.add_heading("13. Безопасность API", level=1)
    add_par(
        doc,
        "Угрозы проанализированы по OWASP API Security Top 10 (2023). В "
        "таблице указаны реализованные меры и способ проверки; подробная "
        "версия находится в docs/security.md.",
    )
    add_table(
        doc,
        ["Угроза OWASP", "Мера", "Проверка"],
        [
            ["API1 BOLA", "owner-check + admin override", "чужое событие → 403"],
            ["API2 Broken Auth", "Argon2, JWT exp/iss, 401", "неверный пароль → 401"],
            ["API3 Mass Assignment", "id и role только из JWT", "подмена organizer_id игнорируется"],
            ["API4 Resource Consumption", "limit 1..100, длины полей", "limit=1000 → 400"],
            ["API5 BFLA", "require_role, admin-only /users", "user → /users 403"],
            ["API8 Misconfiguration", "секреты в .env, DEBUG=0", "500 без stack trace"],
        ],
        widths=[5.2, 6.5, 5.5],
    )
    add_caption(doc, "Таблица 11 — Угрозы API и меры защиты")
    add_par(doc, "Остаточные риски и план усиления:")
    for text in [
        "нет rate limiting на /auth/login и публичных GET;",
        "JWT нельзя отозвать до истечения срока;",
        "attendance-service хранит данные в памяти;",
        "проекция users в events-service не синхронизируется автоматически;",
        "для production нужны HTTPS-терминация и ограничение размера тела запроса.",
    ]:
        add_bullet(doc, text)

    # ---------- 14. Demo ----------
    doc.add_page_break()
    doc.add_heading("14. Демонстрация работы", level=1)
    add_par(
        doc,
        "Ниже приведены фрагменты HTTP-ответов для ключевых сценариев: "
        "создание события, ошибка валидации, запрет по роли и удаление "
        "администратором.",
    )
    add_screenshot_grid(doc)
    add_par(
        doc,
        "Результаты проверок: users-service — 10 тестов, events-service — "
        "31 проверка, attendance-service — 10 проверок. Все проверки проходят.",
        bold="Результаты проверок:",
    )

    # ---------- 15. Status ----------
    doc.add_heading("15. Статус проекта и план", level=1)
    add_table(
        doc,
        ["Этап", "Содержание", "Статус"],
        [
            ["PR1", "бизнес-задача, US, архитектура, каркас, /health", "выполнено"],
            ["PR2", "OpenAPI, примеры, пагинация, валидация, ошибки", "выполнено"],
            ["PR3", "ER, миграции, индексы, N:M, транзакции", "выполнено"],
            ["PR4", "JWT, Argon2, роли, owner-check, единые ошибки", "выполнено"],
            ["PR5", "attendance в БД, синхронизация users-проекции", "план"],
            ["PR6", "rate limiting, refresh-токены, HTTPS", "план"],
            ["PR7", "docker-compose, CI, финальная защита", "план"],
        ],
        widths=[2.5, 11.0, 3.0],
    )
    add_caption(doc, "Таблица 12 — Статус этапов проекта")
    add_par(
        doc,
        "Репозиторий: github.com/banumm/event-map-app. Ветка: main. "
        "Последний коммит: <вставить SHA>. Ссылка на Kanban: <вставить ссылку>.",
        bold="Репозиторий:",
    )
    add_par(doc, "Основные риски:")
    for text in [
        "JWT без отзыва и refresh-токенов;",
        "attendance-service не персистентен;",
        "users-проекция в events-service может рассинхронизироваться;",
        "SQLite подходит для локального MVP, но не для конкурентной нагрузки.",
    ]:
        add_bullet(doc, text)

    # ---------- 16. Conclusion ----------
    doc.add_heading("16. Заключение", level=1)
    add_par(
        doc,
        "В рамках СРС №1 спроектирован и реализован MVP Event Map App. "
        "Приложение покрывает ключевой сценарий: найти событие на карте, "
        "опубликовать мероприятие и отметить участие. Контракт API "
        "зафиксирован в OpenAPI, схема БД создаётся миграциями, а "
        "аутентификация и авторизация проверяются автотестами.",
    )
    add_par(
        doc,
        "Безопасность обеспечена Argon2-хешированием паролей, JWT с проверкой "
        "подписи/срока/издателя, RBAC и проверкой владельца объекта. "
        "Выполнен анализ угроз OWASP API Top 10 и зафиксированы остаточные "
        "риски. Дальнейшая работа — persistence для attendance, rate limiting, "
        "refresh-токены, CI/CD и production-конфигурация.",
    )

    # ---------- 17. Sources ----------
    doc.add_heading("17. Список использованных источников", level=1)
    sources = [
        "OWASP API Security Top 10, 2023. URL: https://owasp.org/API-Security/",
        "RFC 7519. JSON Web Token (JWT).",
        "RFC 9106. Argon2 Memory-Hard Function for Password Hashing.",
        "OpenAPI Specification 3.0.3.",
        "Django 5.0 Documentation. URL: https://docs.djangoproject.com/",
        "Flask 3.0 Documentation. URL: https://flask.palletsprojects.com/",
        "SQLAlchemy 2.0 и Alembic Documentation. URL: https://docs.sqlalchemy.org/",
        "Документация проекта: docs/requirements.md, docs/auth.md, docs/auth-check.md, docs/security.md.",
    ]
    for index, text in enumerate(sources, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{index}. {text}")
        set_run_font(run, size=12, color=DARK)

    # ---------- Appendix ----------
    doc.add_page_break()
    doc.add_heading("Приложение А. Команды запуска и проверки", level=1)
    add_par(doc, "Users Service (Django):")
    add_code(
        doc,
        "cd users-service\n"
        "python manage.py migrate\n"
        "python manage.py create_admin --username admin --email admin@example.com --password 'StrongPass123'\n"
        "python manage.py runserver 127.0.0.1:8000",
    )
    add_par(doc, "Events Service (Flask):")
    add_code(
        doc,
        "cd events-service\n"
        "alembic upgrade head\n"
        "python app.py\n"
        "python verify.py",
    )
    add_par(doc, "Attendance Service (Flask):")
    add_code(
        doc,
        "cd attendance-service\n"
        "python app.py\n"
        "python verify.py",
    )
    add_par(
        doc,
        "JWT_SECRET должен совпадать во всех трёх сервисах. Для локального "
        "запуска можно использовать значение по умолчанию, для реального "
        "окружения — только собственный секрет из .env.",
    )

    doc.core_properties.title = "Event Map App — СРС №1"
    doc.core_properties.author = "Фамилия Имя"
    doc.core_properties.subject = "Архитектура, REST API, база данных и безопасность"
    doc.save(str(path))


def main():
    out = BASE / DOCX_NAME
    build_docx(out)
    print(f"Built: {out}")


if __name__ == "__main__":
    main()
