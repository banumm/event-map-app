"""API/интеграционные тесты attendance-service через Flask test client."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "event-map-users-service")

USER_ID = str(uuid.uuid4())
OTHER_ID = str(uuid.uuid4())
ADMIN_ID = str(uuid.uuid4())
EVENT_ID = str(uuid.uuid4())


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


def payload(**overrides):
    return {"event_id": EVENT_ID, "status": "going", **overrides}


def test_mark_without_token_returns_401(client):
    response = client.post("/attendance", json=payload())
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "Unauthorized"


def test_mark_with_invalid_status_returns_400(client):
    response = client.post(
        "/attendance", json=payload(status="maybe"), headers=auth("user", USER_ID)
    )
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "ValidationError"
    assert error["details"][0]["field"] == "status"


def test_user_marks_self(client):
    response = client.post(
        "/attendance", json=payload(), headers=auth("user", USER_ID)
    )
    assert response.status_code == 201
    assert response.get_json()["user_id"] == USER_ID


def test_user_cannot_mark_for_another(client):
    response = client.post(
        "/attendance",
        json=payload(user_id=OTHER_ID),
        headers=auth("user", USER_ID),
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "Forbidden"


def test_admin_can_mark_for_another(client):
    response = client.post(
        "/attendance",
        json=payload(user_id=OTHER_ID),
        headers=auth("admin", ADMIN_ID),
    )
    assert response.status_code == 201
    assert response.get_json()["user_id"] == OTHER_ID


def test_user_sees_only_own_attendance(client):
    client.post("/attendance", json=payload(), headers=auth("user", USER_ID))
    client.post(
        "/attendance",
        json=payload(user_id=OTHER_ID),
        headers=auth("admin", ADMIN_ID),
    )

    response = client.get(f"/attendance/user/{USER_ID}", headers=auth("user", USER_ID))
    assert response.status_code == 200
    assert [item["user_id"] for item in response.get_json()] == [USER_ID]

    response = client.get(f"/attendance/user/{OTHER_ID}", headers=auth("user", USER_ID))
    assert response.status_code == 403

    response = client.get(f"/attendance/user/{OTHER_ID}", headers=auth("admin", ADMIN_ID))
    assert response.status_code == 200
    assert response.get_json()[0]["user_id"] == OTHER_ID


def test_public_event_counters(client):
    client.post("/attendance", json=payload(), headers=auth("user", USER_ID))
    client.post(
        "/attendance",
        json=payload(status="interested"),
        headers=auth("user", OTHER_ID),
    )

    response = client.get(f"/attendance/event/{EVENT_ID}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["going_count"] == 1
    assert data["interested_count"] == 1


def test_invalid_token_returns_401(client):
    response = client.post(
        "/attendance",
        json=payload(),
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "InvalidToken"


def test_expired_token_returns_401(client):
    token = make_token("user", USER_ID, expires_minutes=-1)
    response = client.post(
        "/attendance", json=payload(), headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "TokenExpired"


def test_unknown_route_returns_unified_error(client):
    response = client.get("/unknown-route")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NotFound"
