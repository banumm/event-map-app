"""Модульные тесты валидации events-service (без БД и HTTP)."""

from validation import (
    parse_query_int,
    validate_event,
    validate_query_params,
)

VALID = {
    "title": "Концерт",
    "description": "Живая музыка",
    "lat": 55.75,
    "lng": 37.61,
    "starts_at": "2026-10-01T19:00:00Z",
    "category": "concert",
}


def fields(details):
    return {item["field"] for item in details}


def test_valid_event_has_no_errors():
    assert validate_event(dict(VALID)) == []


def test_missing_required_fields():
    details = validate_event({"title": "Концерт"})
    assert {"description", "lat", "lng", "starts_at", "category"} <= fields(details)


def test_title_length_boundaries():
    assert fields(validate_event({**VALID, "title": "x"})) == {"title"}
    assert fields(validate_event({**VALID, "title": "x" * 101})) == {"title"}
    assert validate_event({**VALID, "title": "x" * 100}) == []


def test_coordinates_range():
    details = validate_event({**VALID, "lat": 91, "lng": -181})
    assert fields(details) == {"lat", "lng"}


def test_coordinates_must_be_numbers_not_booleans():
    details = validate_event({**VALID, "lat": True, "lng": "37.6"})
    assert fields(details) == {"lat", "lng"}


def test_invalid_datetime_and_category():
    details = validate_event({**VALID, "starts_at": "не дата", "category": "футбол"})
    assert fields(details) == {"starts_at", "category"}


def test_unknown_field_is_rejected():
    details = validate_event({**VALID, "is_admin": True})
    assert details == [{"field": "is_admin", "message": "неизвестное поле"}]


def test_partial_requires_at_least_one_field():
    assert validate_event({}, partial=True) == [
        {"field": None, "message": "пустое тело: укажите хотя бы одно поле для обновления"}
    ]


def test_partial_checks_only_present_fields():
    assert validate_event({"title": "Новое"}, partial=True) == []
    assert fields(validate_event({"lat": 100}, partial=True)) == {"lat"}


def test_query_params_validation():
    details = validate_query_params(
        page=0, limit=1000, category="спорт",
        date_from="not-a-date", date_to=None,
    )
    assert fields(details) == {"page", "limit", "category", "date_from"}


def test_query_params_accept_valid_values():
    assert validate_query_params(
        page=1, limit=100, category="concert",
        date_from="2026-01-01T00:00:00Z", date_to="2026-12-31T23:59:59Z",
    ) == []


def test_parse_query_int():
    assert parse_query_int("page", None) is None
    assert parse_query_int("page", "") is None
    assert parse_query_int("page", "3") == 3
    assert parse_query_int("page", "abc") == "abc"
