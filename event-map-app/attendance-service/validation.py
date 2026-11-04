"""Валидация тела запроса attendance-service (чистые функции, без HTTP и БД)."""

ALLOWED_STATUSES = {"going", "interested", "cancelled"}


def validate_attendance_payload(data):
    """
    Проверяет тело POST /attendance.

    Возвращает список details в едином формате:
        [{"field": "status", "message": "..."}]
    Пустой список означает, что данные корректны.
    """
    if not isinstance(data, dict):
        return [{"field": None, "message": "Тело запроса должно быть JSON-объектом"}]

    details = []

    for field in ("event_id", "status"):
        if field not in data:
            details.append({"field": field, "message": "обязательное поле отсутствует"})

    event_id = data.get("event_id")
    if "event_id" in data and (not isinstance(event_id, str) or not event_id.strip()):
        details.append({"field": "event_id", "message": "должно быть непустой строкой"})

    status = data.get("status")
    if "status" in data and status not in ALLOWED_STATUSES:
        details.append({
            "field": "status",
            "message": f"допустимые значения: {', '.join(sorted(ALLOWED_STATUSES))}",
        })

    return details
