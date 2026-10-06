"""
Валидация входных данных.

Все проверки выполняются ДО обработки запроса бизнес-логикой. Любая ошибка
валидации порождает структуру `details` вида:

    [{"field": "title", "message": "длина от 2 до 100 символов"}, ...]

Маршруты оборачивают её в единый формат ответа:
    {"error": "ValidationError", "details": [...]}
"""

from datetime import datetime

from werkzeug.exceptions import BadRequest

ALLOWED_CATEGORIES = {
    "concert",
    "lecture",
    "exhibition",
    "meetup",
    "workshop",
}

CATEGORIES = ALLOWED_CATEGORIES

REQUIRED_FIELDS = [
    "title",
    "description",
    "lat",
    "lng",
    "starts_at",
    "category",
    "organizer_id",
]


def validate_event(data, partial=False):
    """
    Проверяет тело запроса на создание/обновление события.

    partial=False — POST/PUT: обязательны все поля REQUIRED_FIELDS.
    partial=True  — PATCH:  проверяются только присутствующие поля.
    Возвращает список details. Пустой список — данные корректны.
    """
    details = []

    if data is None:
        return [{"field": None, "message": "тело запроса должно быть JSON-объектом"}]
    if not isinstance(data, dict):
        return [{"field": None, "message": "тело запроса должно быть JSON-объектом"}]

    if not partial:
        for field in REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                details.append({"field": field, "message": "обязательное поле отсутствует"})
    else:
        if not data:
            return [{"field": None, "message": "пустое тело: укажите хотя бы одно поле для обновления"}]

    for field in data:
        if field not in REQUIRED_FIELDS + ["id", "created_at", "updated_at"]:
            details.append({"field": field, "message": "неизвестное поле"})
            continue
        value = data[field]
        if value is None:
            details.append({"field": field, "message": "поле не может быть null"})
            continue
        if field == "title":
            _check_string("title", value, 2, 100, details)
        elif field == "description":
            _check_string("description", value, 1, 2000, details)
        elif field in ("lat", "lng"):
            _check_number(field, value, details)
        elif field == "starts_at":
            _check_datetime(value, details)
        elif field == "category":
            _check_category(value, details)
        elif field == "organizer_id":
            _check_string("organizer_id", value, 1, 64, details)

    return details


def validate_query_params(page, limit, category, date_from, date_to):
    """Проверяет query-параметры списка. Возвращает details."""
    details = []

    if page is not None:
        try:
            page = int(page)
            if page < 1:
                raise ValueError
        except (TypeError, ValueError):
            details.append({"field": "page", "message": "должно быть целым числом >= 1"})

    if limit is not None:
        try:
            limit = int(limit)
            if not 1 <= limit <= 100:
                raise ValueError
        except (TypeError, ValueError):
            details.append({"field": "limit", "message": "должно быть целым числом от 1 до 100"})

    if category is not None and category not in ALLOWED_CATEGORIES:
        details.append({
            "field": "category",
            "message": f"допустимые значения: {', '.join(sorted(ALLOWED_CATEGORIES))}",
        })

    for name in ("date_from", "date_to"):
        value = locals()[name]
        if value is not None:
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                details.append({"field": name, "message": "некорректный формат даты (ожидается ISO 8601)"})

    return details


def parse_query_int(name, raw):
    """Аккуратно приводит query-параметр к int (None, если не задан)."""
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return raw


def _check_string(field, value, min_len, max_len, details):
    if not isinstance(value, str) or not value.strip():
        details.append({"field": field, "message": "должно быть непустой строкой"})
    elif not min_len <= len(value.strip()) <= max_len:
        details.append({
            "field": field,
            "message": f"длина должна быть от {min_len} до {max_len} символов",
        })


def _check_number(field, value, details):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        details.append({"field": field, "message": "должно быть числом"})
        return
    if field == "lat" and not -90 <= value <= 90:
        details.append({"field": field, "message": "широта должна быть в диапазоне [-90, 90]"})
    if field == "lng" and not -180 <= value <= 180:
        details.append({"field": field, "message": "долгота должна быть в диапазоне [-180, 180]"})


def _check_datetime(value, details):
    if not isinstance(value, str) or not value.strip():
        details.append({"field": "starts_at", "message": "должно быть строкой в формате ISO 8601"})
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        details.append({"field": "starts_at", "message": "некорректный формат даты (ожидается ISO 8601)"})


def _check_category(value, details):
    if not isinstance(value, str) or value not in ALLOWED_CATEGORIES:
        details.append({
            "field": "category",
            "message": f"допустимые значения: {', '.join(sorted(ALLOWED_CATEGORIES))}",
        })


def json_body(request):
    """Читает JSON-тело, кидая BadRequest при невалидном JSON."""
    raw = request.get_data(as_text=True)
    if not raw.strip():
        raise BadRequest("тело запроса пустое")
    try:
        return request.get_json(force=True)
    except BadRequest:
        raise BadRequest("тело запроса не является корректным JSON")