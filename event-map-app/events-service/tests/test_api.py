"""API/интеграционные тесты events-service через Flask test client."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "event-map-users-service")

ORG_ID = str(uuid.uuid4())
OTHER_ORG_ID = str(uuid.uuid4())
ADMIN_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())

EVENT = {
    "title": "Концерт в парке",
    "description": "Живая музыка на открытой площадке",
    "lat": 55.7558,
    "lng": 37.6176,
    "starts_at": "2026-10-01T19:00:00Z",
    "category": "concert",
}


def make_token(role, user_id, expires_minutes=30):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "iss": JWT_ISSUER,
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def auth(role, user_id):
    return {"Authorization": f"Bearer {make_token(role, user_id)}"}


@pytest.fixture()
def org_headers():
    return auth("organizer", ORG_ID)


@pytest.fixture()
def other_org_headers():
    return auth("organizer", OTHER_ORG_ID)


@pytest.fixture()
def admin_headers():
    return auth("admin", ADMIN_ID)


@pytest.fixture()
def user_headers():
    return auth("user", USER_ID)


def create_event(client, headers, **overrides):
    payload = {**EVENT, **overrides}
    response = client.post("/events", json=payload, headers=headers)
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


def test_list_events_is_empty(client):
    response = client.get("/events")
    assert response.status_code == 200
    assert response.get_json()["total"] == 0


def test_create_without_token_returns_401(client):
    response = client.post("/events", json=EVENT)
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "Unauthorized"


def test_create_with_user_role_returns_403(client, user_headers):
    response = client.post("/events", json=EVENT, headers=user_headers)
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "Forbidden"


def test_create_organizer_ignores_foreign_organizer_id(client, org_headers):
    event = create_event(client, org_headers, organizer_id=OTHER_ORG_ID)
    assert event["organizer_id"] == ORG_ID
    assert event["title"] == EVENT["title"]
    assert event["category"] == "concert"


def test_create_validation_error_has_details(client, org_headers):
    response = client.post(
        "/events",
        json={**EVENT, "title": "", "lat": 999},
        headers=org_headers,
    )
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "ValidationError"
    assert {"title", "lat"} <= {item["field"] for item in error["details"]}


def test_get_event_and_not_found(client, org_headers):
    event = create_event(client, org_headers)

    response = client.get(f"/events/{event['id']}")
    assert response.status_code == 200
    assert response.get_json()["id"] == event["id"]

    response = client.get("/events/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NotFound"


def test_put_owner_updates_event(client, org_headers):
    event = create_event(client, org_headers)
    response = client.put(
        f"/events/{event['id']}",
        json={**EVENT, "title": "Обновлённый концерт"},
        headers=org_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["title"] == "Обновлённый концерт"


def test_put_non_owner_returns_403(client, org_headers, other_org_headers):
    event = create_event(client, org_headers)
    response = client.put(
        f"/events/{event['id']}",
        json={**EVENT, "title": "Чужое событие"},
        headers=other_org_headers,
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "Forbidden"


def test_patch_valid_and_invalid(client, org_headers):
    event = create_event(client, org_headers)

    response = client.patch(
        f"/events/{event['id']}", json={"category": "meetup"}, headers=org_headers
    )
    assert response.status_code == 200
    assert response.get_json()["category"] == "meetup"

    response = client.patch(
        f"/events/{event['id']}", json={"lat": "abc"}, headers=org_headers
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "ValidationError"


def test_delete_owner_then_not_found(client, org_headers):
    event = create_event(client, org_headers)
    assert client.delete(f"/events/{event['id']}", headers=org_headers).status_code == 204
    assert client.delete(f"/events/{event['id']}", headers=org_headers).status_code == 404


def test_delete_non_owner_returns_403(client, org_headers, other_org_headers):
    event = create_event(client, org_headers)
    response = client.delete(f"/events/{event['id']}", headers=other_org_headers)
    assert response.status_code == 403


def test_admin_can_delete_foreign_event(client, org_headers, admin_headers):
    event = create_event(client, org_headers)
    response = client.delete(f"/events/{event['id']}", headers=admin_headers)
    assert response.status_code == 204


def test_invalid_token_returns_401(client):
    response = client.post(
        "/events", json=EVENT, headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "InvalidToken"


def test_expired_token_returns_401(client):
    token = make_token("organizer", ORG_ID, expires_minutes=-1)
    response = client.post(
        "/events", json=EVENT, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "TokenExpired"


def test_bad_json_returns_unified_error(client, org_headers):
    response = client.post(
        "/events", data="{ not json", content_type="application/json", headers=org_headers
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "BadRequest"


def test_unknown_route_returns_unified_error(client):
    response = client.get("/unknown-route")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NotFound"


# ---------------------------------------------------------------------------
# ПР6: кэширование GET /events и GET /events/{id}
# ---------------------------------------------------------------------------

def _db_down(*args, **kwargs):
    from sqlalchemy.exc import OperationalError

    raise OperationalError("SELECT 1", {}, Exception("connection refused (test)"))


def _db_queries():
    from observability import metrics

    return metrics.value("db_queries_total")


def test_list_second_request_is_cache_hit_without_db_queries(client, org_headers):
    create_event(client, org_headers)

    first = client.get("/events")
    assert first.headers["X-Cache"] == "MISS"

    queries_before = _db_queries()
    second = client.get("/events")
    assert second.headers["X-Cache"] == "HIT"
    assert second.get_json() == first.get_json()
    assert _db_queries() == queries_before  # попадание в кэш не обращается к БД


def test_different_query_params_use_different_cache_keys(client, org_headers):
    create_event(client, org_headers)
    assert client.get("/events?page=1&limit=5").headers["X-Cache"] == "MISS"
    assert client.get("/events?page=1&limit=10").headers["X-Cache"] == "MISS"
    assert client.get("/events?page=1&limit=5").headers["X-Cache"] == "HIT"


def test_create_invalidates_cached_list(client, org_headers):
    assert client.get("/events").get_json()["total"] == 0
    assert client.get("/events").headers["X-Cache"] == "HIT"

    create_event(client, org_headers)
    response = client.get("/events")
    assert response.headers["X-Cache"] == "MISS"
    assert response.get_json()["total"] == 1


def test_patch_invalidates_cached_item_and_list(client, org_headers):
    event = create_event(client, org_headers)
    client.get(f"/events/{event['id']}")
    client.get("/events")
    assert client.get(f"/events/{event['id']}").headers["X-Cache"] == "HIT"

    client.patch(f"/events/{event['id']}", json={"title": "Новое название"}, headers=org_headers)

    item = client.get(f"/events/{event['id']}")
    assert item.headers["X-Cache"] == "MISS"
    assert item.get_json()["title"] == "Новое название"
    listing = client.get("/events")
    assert listing.headers["X-Cache"] == "MISS"
    assert listing.get_json()["items"][0]["title"] == "Новое название"


def test_delete_invalidates_cached_item(client, org_headers):
    event = create_event(client, org_headers)
    assert client.get(f"/events/{event['id']}").status_code == 200
    assert client.get(f"/events/{event['id']}").headers["X-Cache"] == "HIT"

    assert client.delete(f"/events/{event['id']}", headers=org_headers).status_code == 204
    assert client.get(f"/events/{event['id']}").status_code == 404


def test_not_found_is_not_cached(client):
    missing = str(uuid.uuid4())
    assert client.get(f"/events/{missing}").status_code == 404
    response = client.get(f"/events/{missing}")
    assert response.status_code == 404
    assert response.headers.get("X-Cache") is None


def test_database_down_without_cache_returns_503(client, monkeypatch):
    from repository.events import EventRepository

    monkeypatch.setattr(EventRepository, "count", _db_down)
    response = client.get("/events")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "ServiceUnavailable"


def test_database_down_serves_stale_cache(client, org_headers, monkeypatch):
    import time

    from cache import events_cache
    from repository.events import EventRepository

    create_event(client, org_headers)
    fresh = client.get("/events")
    assert fresh.headers["X-Cache"] == "MISS"

    # Запись просрочена (TTL 60 с), но ещё в окне stale (300 с), БД «упала».
    monkeypatch.setattr(events_cache, "_clock", lambda: time.monotonic() + 120)
    monkeypatch.setattr(EventRepository, "count", _db_down)
    response = client.get("/events")
    assert response.status_code == 200
    assert response.headers["X-Cache"] == "STALE"
    assert response.get_json() == fresh.get_json()


def test_write_with_database_down_returns_503(client, org_headers, monkeypatch):
    from repository.categories import CategoryRepository

    monkeypatch.setattr(CategoryRepository, "get_or_create", _db_down)
    response = client.post("/events", json=EVENT, headers=org_headers)
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "ServiceUnavailable"


# ---------------------------------------------------------------------------
# ПР7: /health, /metrics, X-Request-ID
# ---------------------------------------------------------------------------

def test_health_reports_database_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"


def test_health_returns_503_when_database_unavailable(client, monkeypatch):
    import importlib

    app_module = importlib.import_module("app")
    monkeypatch.setattr(app_module, "check_database", lambda: (False, "connection refused"))
    response = client.get("/health")
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "unavailable"
    assert body["checks"]["database"]["status"] == "error"


def test_metrics_endpoint_exposes_counters(client):
    client.get("/events")
    client.get("/events")
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert 'http_requests_total{method="GET",path="/events",status="200"}' in text
    assert "cache_hits_total" in text
    assert "cache_misses_total" in text
    assert "db_queries_total" in text


def test_request_id_is_propagated(client):
    response = client.get("/health", headers={"X-Request-ID": "demo-123"})
    assert response.headers["X-Request-ID"] == "demo-123"
    generated = client.get("/health").headers["X-Request-ID"]
    assert len(generated) == 32


def test_filter_by_category_missing_in_db_returns_empty(client, org_headers, monkeypatch):
    """Регрессия: отсутствующая в справочнике категория не должна отключать фильтр."""
    from repository.categories import CategoryRepository

    create_event(client, org_headers)
    monkeypatch.setattr(CategoryRepository, "get_by_name", lambda self, name: None)
    body = client.get("/events?category=lecture").get_json()
    assert body["total"] == 0
    assert body["items"] == []
