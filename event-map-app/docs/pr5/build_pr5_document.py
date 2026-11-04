#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генератор документа ПР5 (DOCX)."""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

SRS_DIR = Path(__file__).resolve().parents[1] / "srs1"
sys.path.insert(0, str(SRS_DIR))

from build_document import (  # noqa: E402
    DARK,
    GRAY,
    NAVY,
    ORANGE,
    TEAL,
    add_bullet,
    add_caption,
    add_code,
    add_par,
    add_table,
    set_run_font,
    set_style,
)

BASE = Path(__file__).resolve().parent
OUT_NAME = "ПР5_Фамилия_Имя_Группа_документ.docx"


def add_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_ALIGN_PARAGRAPH.RIGHT)
    run = p.add_run("Event Map App · ПР5\t")
    set_run_font(run, size=9, color=GRAY)
    run2 = p.add_run()
    set_run_font(run2, size=9, color=GRAY)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run2._r.append(begin)
    run2._r.append(instr)
    run2._r.append(end)


def title_page(doc: Document):
    for _ in range(5):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("ПР5")
    set_run_font(run, size=18, bold=True, color=TEAL)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    run = p.add_run("Автоматизированные тесты\nи безопасность API")
    set_run_font(run, size=26, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run("Отчёт по практической работе №5")
    set_run_font(run, size=16, color=DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    run = p.add_run("Проект Event Map App")
    set_run_font(run, size=14, color=GRAY)

    for _ in range(5):
        doc.add_paragraph()
    for line in [
        "Дисциплина: Проектирование и разработка серверной части приложений",
        "Студент: Фамилия Имя, группа ____",
        "Преподаватель: Самат Илияс Мырзабекулы",
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(line)
        set_run_font(
            run,
            size=12,
            bold=("Студент" in line),
            color=(ORANGE if "Студент" in line else DARK),
        )
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Алматы, 2026")
    set_run_font(run, size=12, color=GRAY)
    doc.add_page_break()


def build(path: Path):
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

    title_page(doc)

    doc.add_heading("Аннотация", level=1)
    add_par(
        doc,
        "Отчёт описывает практическую работу №5 проекта Event Map App: "
        "автоматизированные модульные и API-тесты, изоляцию тестовых данных, "
        "отчёт о покрытии и проверку типовых уязвимостей API. Приведены "
        "чек-лист безопасности, найденная проблема (отсутствие rate limiting) "
        "и её исправление.",
    )

    doc.add_heading("Содержание", level=1)
    for item in [
        "1. Цель работы",
        "2. Структура тестов",
        "3. Модульные тесты",
        "4. API и интеграционные тесты",
        "5. Изоляция тестовых данных",
        "6. Отчёт о покрытии",
        "7. Проверка безопасности API",
        "8. Найденная и исправленная проблема",
        "9. Дополнительный дефект, найденный тестами",
        "10. Как запустить тесты",
        "11. Выводы",
        "12. Использованные файлы",
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(item)
        set_run_font(run, size=11.5, color=DARK)
    doc.add_page_break()

    doc.add_heading("1. Цель работы", level=1)
    add_par(
        doc,
        "Цель ПР5 — покрыть проект автоматическими тестами (модульными и "
        "API/интеграционными, включая негативные сценарии) и проверить/устранить "
        "основные типовые уязвимости API.",
    )
    for text in [
        "написать не менее 5 модульных тестов бизнес-логики;",
        "написать не менее 10 API-тестов с позитивными и негативными сценариями;",
        "обеспечить изоляцию тестовых данных;",
        "подключить инструмент покрытия и зафиксировать результат;",
        "проверить проект по чек-листу безопасности API;",
        "исправить хотя бы одну реально найденную проблему;",
        "описать запуск тестов в README.",
    ]:
        add_bullet(doc, text)

    doc.add_heading("2. Структура тестов", level=1)
    add_par(
        doc,
        "Тесты разделены по сервисам. Модульные тесты проверяют чистые функции "
        "валидации и вспомогательную логику, API-тесты — реальные HTTP-маршруты "
        "через штатные test client'ы Django и Flask.",
    )
    add_table(
        doc,
        ["Сервис", "Файлы", "Что проверяется", "Тестов"],
        [
            ["users-service", "accounts/tests_unit.py", "валидация регистрации, JSON, JWT, payload пользователя, rate limiter", "14"],
            ["users-service", "accounts/tests.py", "регистрация, вход, /auth/me, /users, 401/403/409/429, единые ошибки", "14"],
            ["events-service", "tests/test_validation.py", "валидация события, координат, даты, категории, query-параметров", "12"],
            ["events-service", "tests/test_api.py", "CRUD, роли, владелец, JWT, 400/401/403/404", "16"],
            ["attendance-service", "tests/test_validation.py", "валидация тела отметки участия", "6"],
            ["attendance-service", "tests/test_api.py", "отметка себя/другого, роли, чтение записей, 401/403/404", "10"],
            ["Итого", "", "", "72"],
        ],
        widths=[3.4, 4.3, 8.0, 1.3],
        font_size=8.5,
    )
    add_caption(doc, "Таблица 1 — Наборы тестов")

    doc.add_heading("3. Модульные тесты", level=1)
    add_par(
        doc,
        "Модульные тесты не обращаются к сети. В users-service используется "
        "django.test.SimpleTestCase, который запрещает запросы к БД; в Flask-"
        "сервисах проверяются чистые функции из validation.py.",
    )
    add_table(
        doc,
        ["Проверка", "Ожидаемый результат"],
        [
            ["Корректные данные регистрации", "список ошибок пуст, значения нормализованы"],
            ["Неверные username/email/password/role", "400 ValidationError, ошибки по каждому полю"],
            ["Границы длины пароля (7 и 129 символов)", "ошибка поля password"],
            ["Пустое тело, невалидный JSON, JSON-массив", "400 BadRequest"],
            ["JWT: состав claims и подпись", "sub, role, iss, exp, jti; чужой секрет отклоняется"],
            ["Payload пользователя", "нет password и password_hash"],
            ["Rate limiter: лимит, окно, изоляция ключей", "после лимита allowed=False, окно освобождается"],
            ["Валидация события и query-параметров", "400 с details для неверных полей"],
            ["Валидация attendance", "400 для пустого event_id и недопустимого status"],
        ],
        widths=[8.5, 8.5],
    )
    add_caption(doc, "Таблица 2 — Модульные проверки")

    doc.add_heading("4. API и интеграционные тесты", level=1)
    add_par(
        doc,
        "API-тесты вызывают реальные маршруты через test client. Для каждой "
        "ключевой операции есть позитивный и негативный сценарий.",
    )
    add_table(
        doc,
        ["Операция", "Позитивный сценарий", "Негативный сценарий"],
        [
            ["Регистрация", "201, пароль хранится как Argon2-хеш", "409 дубликат; 400 неверные поля; 429 лимит"],
            ["Вход", "200, выдан JWT", "401 неверный пароль; 429 лимит"],
            ["Профиль", "200 с валидным токеном", "401 без токена; 401 невалидный токен"],
            ["Список пользователей", "200 для admin", "403 для user"],
            ["Создание события", "201 для organizer/admin", "401 без токена; 403 для user; 400 невалидные данные"],
            ["Чтение события", "200 по id", "404 для несуществующего id"],
            ["Изменение события", "200 владельцем", "403 чужим organizer; 400 неверные поля"],
            ["Удаление события", "204 владельцем или admin", "403 чужой organizer; 404 повторно"],
            ["Отметка участия", "201 для себя", "401 без токена; 403 за другого; 400 неверный status"],
            ["Чтение отметок", "200 свои или admin", "403 чужие для user"],
        ],
        widths=[4.0, 6.5, 6.5],
    )
    add_caption(doc, "Таблица 3 — API-сценарии")

    doc.add_heading("5. Изоляция тестовых данных", level=1)
    add_table(
        doc,
        ["Сервис", "Механизм", "Гарантия"],
        [
            ["users-service", "Django TestCase: отдельная тестовая БД SQLite in-memory, откат транзакции после каждого теста", "рабочая db.sqlite3 не затрагивается, тесты независимы"],
            ["events-service", "отдельный test_events.db, схема через alembic upgrade head, autouse-фикстура очищает events и event_participants", "тесты проходят в любом порядке и повторно"],
            ["attendance-service", "autouse-фикстура очищает in-memory attendance_db до и после теста", "нет зависимости от порядка выполнения"],
        ],
        widths=[3.5, 8.0, 5.5],
        font_size=8.5,
    )
    add_caption(doc, "Таблица 4 — Изоляция тестов")
    add_par(
        doc,
        "Тестовые БД и файлы покрытия исключены из Git через .gitignore "
        "(.coverage*, .coverage-data/, htmlcov/, .pytest_cache/, *.db).",
    )

    doc.add_heading("6. Отчёт о покрытии", level=1)
    add_par(doc, "Единая команда запуска и отчёта:")
    add_code(doc, "python -m pip install -r requirements-dev.txt\npython scripts/run_tests.py")
    add_table(
        doc,
        ["Сервис", "Покрытие", "Покрыто/всего", "Комментарий"],
        [
            ["users-service", "88%", "280 / 320", "не покрыты часть веток middleware, create_admin, внутренний GET /users/{id}"],
            ["events-service", "82%", "498 / 605", "0% у неиспользуемых storage.py, repository/participants.py, repository/users.py"],
            ["attendance-service", "93%", "130 / 140", "не покрыты root/health и часть обработчиков ошибок"],
            ["Итого", "≈85%", "908 / 1065", "покрытие по трём сервисам"],
        ],
        widths=[3.4, 2.0, 2.5, 9.1],
        font_size=8.5,
    )
    add_caption(doc, "Таблица 5 — Покрытие тестами")
    add_par(
        doc,
        "Покрытие считается по исходному коду без файлов тестов, миграций и "
        "management-команд. Жёсткого порога нет: важнее, что покрыты ключевые "
        "пользовательские сценарии и негативные ветки.",
    )

    doc.add_heading("7. Проверка безопасности API", level=1)
    add_par(
        doc,
        "Проверялись пункты из задания ПР5 и OWASP API Security Top 10 (2023). "
        "Статусы: выполнено / исправлено / не применимо.",
    )
    add_table(
        doc,
        ["№", "Проверка", "Статус", "Что сделано и чем подтверждено"],
        [
            ["1", "Параметризованные запросы вместо конкатенации SQL", "выполнено", "SQLAlchemy ORM и Django ORM; ручной SQL только SELECT 1; конкатенации пользовательских значений нет"],
            ["2", "API не возвращает лишние поля (хэш пароля)", "выполнено", "_user_payload возвращает id/username/email/role/created_at; тесты проверяют отсутствие password и argon2"],
            ["3", "Ограничение частоты на входе и регистрации", "исправлено", "было неограниченно; добавлен rate limiter 10 запросов/60 с на IP, 429 + Retry-After"],
            ["4", "Корректные 401/403 на защищённых маршрутах", "выполнено", "401 без токена/невалидный/просроченный; 403 при нехватке роли или чужом объекте; покрыто тестами"],
            ["5", "Mass assignment и подмена идентификаторов", "выполнено", "organizer_id и user_id берутся из JWT; role=admin при регистрации отклоняется"],
            ["6", "Валидация и ограничение размера входных данных", "выполнено", "limit 1..100, title 2..100, description ≤ 2000, координаты в диапазонах"],
            ["7", "Нет stack trace и секретов в ответах", "выполнено", "единый JSON ошибок; тест 500 проверяет отсутствие текста исключения; секреты в .env"],
            ["8", "Безопасность JWT", "выполнено", "HS256, обязательные exp/sub/iss, проверка issuer; чужой секрет и просроченный токен отклоняются"],
        ],
        widths=[0.9, 4.6, 2.2, 9.3],
        font_size=8,
    )
    add_caption(doc, "Таблица 6 — Чек-лист безопасности API")

    doc.add_heading("8. Найденная и исправленная проблема", level=1)
    doc.add_heading("8.1. Отсутствие rate limiting", level=2)
    add_par(
        doc,
        "До ПР5 эндпоинты /auth/login и /auth/register принимали неограниченное "
        "число запросов. Это позволяло перебирать пароли и массово создавать "
        "учётные записи.",
    )
    add_par(doc, "После исправления добавлен модуль users-service/accounts/ratelimit.py:", bold="После исправления")
    for text in [
        "скользящее окно в памяти процесса;",
        "ключ «действие + IP», при наличии прокси учитывается X-Forwarded-For;",
        "лимит по умолчанию — 10 запросов за 60 секунд;",
        "настройки AUTH_RATE_LIMIT и AUTH_RATE_WINDOW_SECONDS в settings.py и .env.example;",
        "ответ 429 TooManyRequests и заголовок Retry-After.",
    ]:
        add_bullet(doc, text)
    add_par(doc, "Пример ответа при превышении лимита:")
    add_code(
        doc,
        '{\n'
        '  "error": {\n'
        '    "code": "TooManyRequests",\n'
        '    "message": "Слишком много запросов. Попробуйте позже.",\n'
        '    "details": [{"field": null, "message": "повторите запрос через 43 с"}]\n'
        '  }\n'
        '}',
    )
    add_par(
        doc,
        "Проверка: test_register_rate_limit_returns_429 и "
        "test_login_rate_limit_returns_429, а также unit-тесты "
        "SlidingWindowLimiter. Ограничение in-memory и не общее для нескольких "
        "инстансов; для production нужен Redis или лимит на reverse proxy.",
    )

    doc.add_heading("9. Дополнительный дефект, найденный тестами", level=1)
    add_par(
        doc,
        "При изменении категории события services.py присваивал только "
        "event.category_id, а _serialize() читал уже загруженную связь "
        "event.category. В ответе оставалась старая категория, хотя в БД "
        "сохранялась новая.",
    )
    add_par(doc, "Исправление — присваивание связи в replace() и patch():")
    add_code(doc, "event.category = category")
    add_par(
        doc,
        "Регрессия закрыта тестом test_patch_valid_and_invalid: он проверяет "
        "не только статус 200, но и значение поля category.",
    )

    doc.add_heading("10. Как запустить тесты", level=1)
    add_par(doc, "Все сервисы сразу, с отчётом о покрытии:")
    add_code(doc, "python -m pip install -r requirements-dev.txt\npython scripts/run_tests.py")
    add_par(doc, "Или по отдельности:")
    add_code(
        doc,
        "cd users-service\npython manage.py test\n\n"
        "cd events-service\npython -m pytest -q\n\n"
        "cd attendance-service\npython -m pytest -q",
    )
    add_par(
        doc,
        "Данные coverage сохраняются в .coverage-data/, отчёт печатается в "
        "консоль командой coverage report -m.",
    )

    doc.add_heading("11. Выводы", level=1)
    add_par(
        doc,
        "В ПР5 добавлено 72 автоматических теста: 32 модульных и 40 API/"
        "интеграционных. Тесты покрывают валидацию, CRUD, регистрацию и вход, "
        "роли, проверку владельца и негативные сценарии 400/401/403/404/409/429.",
    )
    add_par(
        doc,
        "Тестовые данные изолированы, покрытие по трём сервисам составляет "
        "около 85%. По чек-листу безопасности найдена и устранена реальная "
        "проблема — отсутствие ограничения частоты запросов на аутентификации. "
        "Дополнительно тесты выявили и закрыли дефект сериализации категории "
        "после PATCH/PUT.",
    )
    add_par(
        doc,
        "Остаточные ограничения: rate limiter хранит счётчики в памяти процесса, "
        "нет отзыва JWT и refresh-токенов, attendance-service хранит данные в "
        "памяти. Эти пункты вынесены в следующие работы.",
    )

    doc.add_heading("12. Использованные файлы", level=1)
    for text in [
        "users-service/accounts/tests.py, tests_unit.py, ratelimit.py, errors.py, middleware.py, views.py;",
        "users-service/config/settings.py, .env.example;",
        "events-service/tests/conftest.py, test_validation.py, test_api.py;",
        "events-service/services.py, validation.py;",
        "attendance-service/tests/conftest.py, test_validation.py, test_api.py;",
        "attendance-service/validation.py, app.py;",
        "scripts/run_tests.py, requirements-dev.txt;",
        "README.md, docs/testing.md, docs/security.md.",
    ]:
        add_bullet(doc, text)

    doc.core_properties.title = "Event Map App — ПР5"
    doc.core_properties.author = "Фамилия Имя"
    doc.core_properties.subject = "Автоматизированные тесты и безопасность API"
    doc.save(str(path))


def main():
    out = BASE / OUT_NAME
    build(out)
    print(f"Built: {out}")


if __name__ == "__main__":
    main()
