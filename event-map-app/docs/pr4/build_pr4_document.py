#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the PR4 Word report."""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

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
OUT_NAME = "ПР4_Фамилия_Имя_Группа_документ.docx"


def add_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_ALIGN_PARAGRAPH.RIGHT)
    run = p.add_run("Event Map App · ПР4\t")
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
    run = p.add_run("ПР4")
    set_run_font(run, size=18, bold=True, color=TEAL)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    run = p.add_run("Аутентификация, авторизация,\nвалидация и обработка ошибок")
    set_run_font(run, size=26, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run("Отчёт по практической работе №4")
    set_run_font(run, size=16, color=DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    run = p.add_run("Проект Event Map App")
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
        set_run_font(run, size=12, bold=("Студент" in line), color=(ORANGE if "Студент" in line else DARK))
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
        "Отчёт описывает практическую работу №4 проекта Event Map App: "
        "модель пользователя, регистрацию и вход, JWT-аутентификацию, "
        "ролевую авторизацию, проверку владельца объекта, валидацию и "
        "единый формат ошибок. Приведены результаты автотестов и ручного "
        "протокола проверки доступа.",
    )

    doc.add_heading("Содержание", level=1)
    for item in [
        "1. Цель работы",
        "2. Модель пользователя",
        "3. Регистрация",
        "4. Вход и JWT",
        "5. Защита маршрутов",
        "6. Роли и матрица доступа",
        "7. Проверка владельца и защита от mass assignment",
        "8. Единый формат ошибок",
        "9. Валидация",
        "10. Тестирование",
        "11. Ручной протокол проверки доступа",
        "12. Выводы",
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(item)
        set_run_font(run, size=11.5, color=DARK)
    doc.add_page_break()

    doc.add_heading("1. Цель работы", level=1)
    add_par(doc, "Цель ПР4 — добавить в Event Map App сквозную аутентификацию, авторизацию, валидацию и единообразную обработку ошибок.")
    for text in [
        "реализовать модель пользователя с ролями user / organizer / admin;",
        "добавить регистрацию и вход с безопасным хранением паролей;",
        "выдавать и проверять JWT во всех трёх сервисах;",
        "ограничить операции по роли и владельцу объекта;",
        "привести ошибки к единому JSON-формату;",
        "проверить сценарии 401/403/400 автотестами и вручную.",
    ]:
        add_bullet(doc, text)

    doc.add_heading("2. Модель пользователя", level=1)
    add_par(doc, "Модель реализована в users-service/accounts/models.py, миграция — accounts/migrations/0001_initial.py.")
    add_table(
        doc,
        ["Поле", "Назначение", "Ограничения"],
        [
            ["id", "идентификатор", "первичный ключ"],
            ["username", "логин", "уникальный, 3–150 символов"],
            ["email", "email", "уникальный, валидируется"],
            ["password", "хеш пароля", "Argon2, открытый пароль не хранится"],
            ["role", "роль", "user / organizer / admin, по умолчанию user"],
            ["date_joined", "дата регистрации", "заполняется автоматически"],
        ],
        widths=[3.5, 5.5, 8.5],
    )
    add_caption(doc, "Таблица 1 — Поля модели пользователя")
    add_par(
        doc,
        "Пароли хешируются Argon2PasswordHasher. Администратор создаётся только доверенной management-командой create_admin, а не через публичную регистрацию.",
    )
    add_code(
        doc,
        "cd users-service\n"
        "python manage.py create_admin --username admin --email admin@example.com --password 'StrongPass123'\n"
        "python manage.py shell -c \"from accounts.models import User; u=User.objects.get(username='user1'); print(u.password[:20])\"\n"
        "# argon2$argon2id$v=19...",
    )

    doc.add_heading("3. Регистрация", level=1)
    add_par(doc, "Запрос POST /auth/register:")
    add_code(
        doc,
        '{\n'
        '  "username": "organizer1",\n'
        '  "email": "organizer1@example.com",\n'
        '  "password": "StrongPass123",\n'
        '  "role": "organizer"\n'
        '}',
    )
    add_par(doc, "Проверки при регистрации:")
    for text in [
        "username: 3–150 символов, латиница, цифры, _, ., -;",
        "email: корректный формат и уникальность без учёта регистра;",
        "password: 8–128 символов, сохраняется только Argon2-хеш;",
        "role: публично разрешены только user и organizer; admin запрещён;",
        "дубликат username или email возвращает 409 Conflict.",
    ]:
        add_bullet(doc, text)
    add_par(doc, "Ответы: 201 — пользователь создан; 400 ValidationError — ошибки полей; 409 Conflict — дубликат.")

    doc.add_heading("4. Вход и JWT", level=1)
    add_par(doc, "POST /auth/login принимает username или email и пароль. При успехе возвращается access_token.")
    add_code(
        doc,
        '{\n'
        '  "access_token": "eyJ...",\n'
        '  "token_type": "Bearer",\n'
        '  "expires_in": 3600,\n'
        '  "user": {"id": 2, "username": "organizer1", "role": "organizer", ...}\n'
        '}',
    )
    add_par(doc, "JWT содержит:")
    for text in [
        "sub — идентификатор пользователя;",
        "username, email, role — данные для авторизации;",
        "iss = event-map-users-service;",
        "iat, exp, jti — время выпуска, срок действия и идентификатор токена.",
    ]:
        add_bullet(doc, text)
    add_par(
        doc,
        "Подпись HS256, секрет JWT_SECRET, срок жизни 60 минут (JWT_EXPIRES_MINUTES). Токен передаётся в заголовке Authorization: Bearer <access_token>. JWT выбран потому, что сервисы разделены и должны проверять пользователя локально, без общей сессии.",
    )
    add_par(
        doc,
        "Ограничение: токен нельзя отозвать до истечения срока без blacklist по jti. Refresh-токены и отзыв вынесены в план PR6.",
    )

    doc.add_heading("5. Защита маршрутов", level=1)
    add_table(
        doc,
        ["Сервис", "Защищённые маршруты", "Механизм"],
        [
            ["users-service", "GET /auth/me, GET /users", "require_auth, затем require_role"],
            ["events-service", "POST /events, PUT/PATCH/DELETE /events/{id}", "require_auth + require_role + owner-check"],
            ["attendance-service", "POST /attendance, GET /attendance/user/{id}", "require_auth + проверка пользователя/роли"],
        ],
        widths=[4.0, 7.0, 6.5],
    )
    add_caption(doc, "Таблица 2 — Защищённые маршруты")
    add_par(doc, "Порядок проверок:")
    for index, text in enumerate([
        "нет, испорчен или истёк токен → 401;",
        "токен валиден, но роль или владелец не подходят → 403;",
        "ресурс не найден → 404;",
        "данные не проходят валидацию → 400;",
        "непредвиденная ошибка → 500 без stack trace.",
    ], start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{index}. {text}")
        set_run_font(run, size=12, color=DARK)

    doc.add_heading("6. Роли и матрица доступа", level=1)
    add_table(
        doc,
        ["Действие", "user", "organizer", "admin"],
        [
            ["Просмотр событий", "да", "да", "да"],
            ["Создание события", "нет (403)", "да", "да"],
            ["Изменение своего события", "нет (403)", "да", "да"],
            ["Изменение чужого события", "нет (403)", "нет (403)", "да"],
            ["Удаление своего события", "нет (403)", "да", "да"],
            ["Удаление чужого события", "нет (403)", "нет (403)", "да"],
            ["Отметка своего участия", "да", "да", "да"],
            ["Отметка за другого", "нет (403)", "нет (403)", "да"],
            ["Просмотр чужих отметок", "нет (403)", "нет (403)", "да"],
            ["GET /users", "нет (403)", "нет (403)", "да"],
        ],
        widths=[8.0, 2.7, 3.0, 3.0],
    )
    add_caption(doc, "Таблица 3 — Матрица ролей")

    doc.add_heading("7. Проверка владельца и защита от mass assignment", level=1)
    add_par(
        doc,
        "Для организатора organizer_id при создании события принудительно берётся из sub проверенного JWT, а не из тела запроса. Admin может передать organizer_id явно. При изменении и удалении organizer_id события сравнивается с sub; при несовпадении возвращается 403.",
    )
    add_par(
        doc,
        "Аналогично user_id в attendance-service берётся из JWT. Пользователь не может отметить участие за другого или прочитать чужие отметки. Это защищает от mass assignment и подмены идентификаторов.",
    )

    doc.add_heading("8. Единый формат ошибок", level=1)
    add_par(doc, "Все сервисы возвращают ошибки в одном формате:")
    add_code(
        doc,
        '{\n'
        '  "error": {\n'
        '    "code": "Forbidden",\n'
        '    "message": "Недостаточно прав для выполнения операции",\n'
        '    "details": [\n'
        '      {"field": "role", "message": "требуется organizer или admin"}\n'
        '    ]\n'
        '  }\n'
        '}',
    )
    add_table(
        doc,
        ["HTTP", "code", "Когда"],
        [
            ["400", "ValidationError", "поля не прошли проверку"],
            ["400", "BadRequest", "пустое тело или некорректный JSON"],
            ["401", "Unauthorized", "нет заголовка Authorization"],
            ["401", "InvalidToken", "неверная подпись/issuer"],
            ["401", "TokenExpired", "истёк срок действия"],
            ["401", "InvalidCredentials", "неверный логин или пароль"],
            ["403", "Forbidden", "недостаточно роли или владельца"],
            ["404", "NotFound", "ресурс не найден"],
            ["405", "MethodNotAllowed", "метод не поддерживается"],
            ["409", "Conflict", "дубликат пользователя"],
            ["500", "InternalServerError", "необработанная ошибка"],
        ],
        widths=[2.5, 5.0, 9.5],
    )
    add_caption(doc, "Таблица 4 — Коды ошибок")
    add_par(
        doc,
        "Реализация: users-service — accounts/errors.py и accounts/middleware.py; events-service и attendance-service — errors.py с ApiError, register_error_handlers и обработчиками HTTPException/Exception. Клиент не получает stack trace.",
    )

    doc.add_heading("9. Валидация", level=1)
    add_table(
        doc,
        ["Объект", "Правила"],
        [
            ["username", "3–150 символов, латиница, цифры, _, ., -"],
            ["email", "корректный формат, уникальность"],
            ["password", "8–128 символов"],
            ["role при регистрации", "только user или organizer"],
            ["title события", "2–100 символов"],
            ["description", "не более 2000 символов"],
            ["lat / lng", "-90..90 / -180..180"],
            ["starts_at", "ISO 8601"],
            ["category", "значение из справочника"],
            ["limit / page", "1..100 / ≥ 1"],
        ],
        widths=[5.5, 11.0],
    )
    add_caption(doc, "Таблица 5 — Правила валидации")

    doc.add_heading("10. Тестирование", level=1)
    add_par(doc, "Результаты автоматических проверок:")
    add_table(
        doc,
        ["Сервис", "Команда", "Результат"],
        [
            ["users-service", "python manage.py test", "10 тестов, OK"],
            ["events-service", "python verify.py", "31 проверка, 0 ошибок"],
            ["attendance-service", "python verify.py", "10 проверок, 0 ошибок"],
        ],
        widths=[4.5, 7.0, 4.5],
    )
    add_caption(doc, "Таблица 6 — Результаты автотестов")
    add_par(doc, "Покрытые сценарии:")
    for text in [
        "хеширование пароля Argon2 и отсутствие открытого пароля;",
        "дубликаты username/email → 409;",
        "некорректные email, password, role → 400;",
        "вход по username и email, неверный пароль → 401;",
        "GET /auth/me без токена → 401, с токеном → 200;",
        "GET /users для user → 403, для admin → 200;",
        "неизвестный маршрут и некорректный JSON → единый формат;",
        "необработанное исключение → 500 без stack trace.",
    ]:
        add_bullet(doc, text)

    doc.add_heading("11. Ручной протокол проверки доступа", level=1)
    add_par(doc, "Проверялась операция DELETE /events/{id} от имени трёх субъектов:")
    add_table(
        doc,
        ["Субъект", "Заголовок", "Код", "Вывод"],
        [
            ["без токена", "нет", "401", "не аутентифицирован"],
            ["user1", "Bearer USER_TOKEN", "403", "роль не позволяет"],
            ["admin", "Bearer ADMIN_TOKEN", "204", "операция выполнена"],
            ["organizer1 (владелец)", "Bearer ORG_TOKEN", "204", "операция выполнена"],
            ["organizer2 (чужой)", "Bearer OTHER_TOKEN", "403", "нет прав на объект"],
        ],
        widths=[5.0, 5.0, 2.2, 5.3],
    )
    add_caption(doc, "Таблица 7 — Проверка доступа к DELETE /events/{id}")
    add_par(doc, "Дополнительно проверены:")
    add_table(
        doc,
        ["Запрос", "Код"],
        [
            ["POST /auth/register (organizer1, user1, organizer2)", "201"],
            ["POST /auth/register с дубликатом username", "409"],
            ["POST /auth/register с bad email, short password, role=admin", "400"],
            ["POST /auth/login с верным паролем", "200"],
            ["POST /auth/login с неверным паролем", "401"],
            ["GET /auth/me без токена", "401"],
            ["GET /auth/me с токеном", "200"],
            ["GET /users с токеном user1", "403"],
            ["GET /users с токеном admin", "200"],
        ],
        widths=[12.0, 4.0],
    )
    add_caption(doc, "Таблица 8 — Дополнительные проверки")
    add_par(doc, "Полный протокол с curl-командами и ответами: docs/auth-check.md.")

    doc.add_heading("12. Выводы", level=1)
    add_par(
        doc,
        "В ПР4 реализована сквозная аутентификация и авторизация для трёх сервисов. Пароли хранятся только в виде Argon2-хеша, JWT проверяется локально по подписи, сроку и issuer, роли и владелец объекта проверяются отдельно. Ошибки приведены к единому формату, а сценарии 401/403/400 покрыты автотестами и ручным протоколом.",
    )
    add_par(
        doc,
        "Остаточные ограничения: нет rate limiting и отзыва JWT, refresh-токены не реализованы, attendance-service хранит данные в памяти. Эти пункты вынесены в план следующих работ.",
    )

    doc.add_heading("Использованные файлы", level=1)
    for text in [
        "users-service/accounts/models.py, migrations/0001_initial.py;",
        "users-service/accounts/auth.py, errors.py, middleware.py, views.py, urls.py, tests.py;",
        "users-service/accounts/management/commands/create_admin.py;",
        "events-service/auth.py, errors.py, api.py, services.py, validation.py, verify.py;",
        "attendance-service/auth.py, errors.py, app.py, verify.py;",
        "docs/auth.md, docs/auth-check.md.",
    ]:
        add_bullet(doc, text)

    doc.core_properties.title = "Event Map App — ПР4"
    doc.core_properties.author = "Фамилия Имя"
    doc.core_properties.subject = "Аутентификация, авторизация, валидация и обработка ошибок"
    doc.save(str(path))


def main():
    out = BASE / OUT_NAME
    build(out)
    print(f"Built: {out}")


if __name__ == "__main__":
    main()
