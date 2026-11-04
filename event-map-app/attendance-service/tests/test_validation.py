"""Модульные тесты валидации attendance-service."""

from validation import ALLOWED_STATUSES, validate_attendance_payload


def fields(details):
    return {item["field"] for item in details}


def test_valid_payload():
    assert validate_attendance_payload({"event_id": "evt-1", "status": "going"}) == []


def test_all_allowed_statuses():
    for status in ALLOWED_STATUSES:
        assert validate_attendance_payload({"event_id": "evt-1", "status": status}) == []


def test_missing_required_fields():
    details = validate_attendance_payload({})
    assert fields(details) == {"event_id", "status"}


def test_empty_event_id():
    details = validate_attendance_payload({"event_id": "  ", "status": "going"})
    assert fields(details) == {"event_id"}


def test_invalid_status():
    details = validate_attendance_payload({"event_id": "evt-1", "status": "maybe"})
    assert details == [{
        "field": "status",
        "message": "допустимые значения: cancelled, going, interested",
    }]


def test_non_object_body():
    assert validate_attendance_payload([]) == [
        {"field": None, "message": "Тело запроса должно быть JSON-объектом"}
    ]
