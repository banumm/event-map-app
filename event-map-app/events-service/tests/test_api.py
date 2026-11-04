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
