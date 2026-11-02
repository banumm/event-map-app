"""Автотест attendance-service: JWT, роли и единый формат ошибок."""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app import app

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-jwt-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "event-map-users-service")


def make_token(role, user_id):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "iss": JWT_ISSUER,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


USER_ID = str(uuid.uuid4())
OTHER_ID = str(uuid.uuid4())
ADMIN_ID = str(uuid.uuid4())
EVENT_ID = str(uuid.uuid4())

USER = {"Authorization": f"Bearer {make_token('user', USER_ID)}"}
OTHER = {"Authorization": f"Bearer {make_token('user', OTHER_ID)}"}
ADMIN = {"Authorization": f"Bearer {make_token('admin', ADMIN_ID)}"}

c = app.test_client()
passed = 0
failed = 0


def show(label, resp, expected):
    global passed, failed
    ok = resp.status_code == expected
    passed += ok
    failed += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] {label} -> {resp.status_code}")
    if not ok:
        print(resp.get_data(as_text=True))
    return resp


payload = {"event_id": EVENT_ID, "status": "going"}

show("POST without token -> 401", c.post("/attendance", json=payload), 401)
show("POST invalid status -> 400", c.post("/attendance", json={**payload, "status": "maybe"}, headers=USER), 400)
show("POST self -> 201", c.post("/attendance", json=payload, headers=USER), 201)
show(
    "POST for another user -> 403",
    c.post("/attendance", json={**payload, "user_id": OTHER_ID}, headers=USER),
    403,
)
show(
    "POST admin for another user -> 201",
    c.post("/attendance", json={**payload, "user_id": OTHER_ID}, headers=ADMIN),
    201,
)
show("GET own attendance -> 200", c.get(f"/attendance/user/{USER_ID}", headers=USER), 200)
show("GET another attendance -> 403", c.get(f"/attendance/user/{OTHER_ID}", headers=USER), 403)
show(
    "GET another attendance as admin -> 200",
    c.get(f"/attendance/user/{OTHER_ID}", headers=ADMIN),
    200,
)
r = show("GET event attendance -> 200", c.get(f"/attendance/event/{EVENT_ID}"), 200)
data = r.get_json()
assert data["going_count"] == 2, json.dumps(data, ensure_ascii=False)
show("GET unknown route -> 404", c.get("/unknown-route"), 404)

print(f"\nИтого: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
