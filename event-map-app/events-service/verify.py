"""
Автотест API events-service (ПР3 + ПР4).

Проверяет CRUD поверх реляционной БД, а также JWT-аутентификацию,
разграничение ролей и владельца события.
Запуск: python verify.py
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone

import jwt

HERE = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(HERE, "verify_events.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"
for suffix in ("-journal", "-wal", "-shm"):
    if os.path.exists(DB_FILE + suffix):
        os.remove(DB_FILE + suffix)
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=HERE,
    check=True,
    capture_output=True,
)

from app import app  # noqa: E402

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


ORG_ID = str(uuid.uuid4())
OTHER_ORG_ID = str(uuid.uuid4())
ADMIN_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())

ORG = {"Authorization": f"Bearer {make_token('organizer', ORG_ID)}"}
OTHER_ORG = {"Authorization": f"Bearer {make_token('organizer', OTHER_ORG_ID)}"}
ADMIN = {"Authorization": f"Bearer {make_token('admin', ADMIN_ID)}"}
USER = {"Authorization": f"Bearer {make_token('user', USER_ID)}"}

c = app.test_client()
passed = 0
failed = 0


def show(label, resp, expected=None):
    global passed, failed
    ok = resp.status_code in (200, 201, 204, 400, 401, 403, 404, 405, 409, 500)
    if expected is not None:
        ok = resp.status_code == expected
    if ok:
        passed += 1
    else:
        failed += 1
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {label} -> {resp.status_code}")
    if not ok:
        print(resp.get_data(as_text=True))
    return resp


EVENT = {
    "title": "Концерт в парке",
    "description": "Живая музыка на открытой площадке",
    "lat": 55.7558,
    "lng": 37.6176,
    "starts_at": "2026-10-01T19:00:00Z",
    "category": "concert",
    "organizer_id": ORG_ID,
}
EVENT2 = {
    "title": "Лекция о REST API",
    "description": "Обзор принципов проектирования REST",
    "lat": 59.9390,
    "lng": 30.3158,
    "starts_at": "2026-11-05T18:00:00Z",
    "category": "lecture",
    "organizer_id": ORG_ID,
}

show("GET /", c.get("/"), 200)
show("GET /health", c.get("/health"), 200)
show("GET /events (empty)", c.get("/events"), 200)

show("POST /events without token -> 401", c.post("/events", json=EVENT), 401)
show("POST /events user role -> 403", c.post("/events", json=EVENT, headers=USER), 403)

r = show("POST /events organizer -> 201", c.post("/events", json=EVENT, headers=ORG), 201)
e1 = r.get_json()
r2 = show("POST /events (create 2)", c.post("/events", json=EVENT2, headers=ORG), 201)
e2 = r2.get_json()
r3 = show(
    "POST /events admin -> 201",
    c.post("/events", json={**EVENT, "title": "Событие администратора"}, headers=ADMIN),
    201,
)
e3 = r3.get_json()

show("GET /events/{id}", c.get(f"/events/{e1['id']}"), 200)
show(
    "GET /events/{missing}",
    c.get("/events/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    404,
)

show(
    "POST missing title -> 400",
    c.post("/events", json={k: v for k, v in EVENT.items() if k != "title"}, headers=ORG),
    400,
)
show(
    "POST wrong types -> 400",
    c.post(
        "/events",
        json={
            **EVENT,
            "lat": "не-число",
            "lng": 999,
            "starts_at": "не дата",
            "category": "футбол",
        },
        headers=ORG,
    ),
    400,
)
show("POST unknown field -> 400", c.post("/events", json={**EVENT, "fake": True}, headers=ORG), 400)
show(
    "POST bad json -> 400",
    c.post("/events", data="{ это не json", content_type="application/json", headers=ORG),
    400,
)

show("GET filter category=concert", c.get("/events?category=concert"), 200)
show(
    "GET filter date range",
    c.get("/events?date_from=2026-10-01T00:00:00Z&date_to=2026-10-31T23:59:59Z"),
    200,
)
show("GET pagination page=1 limit=1", c.get("/events?page=1&limit=1"), 200)
show("GET bad limit -> 400", c.get("/events?page=0&limit=1000"), 400)
show("GET bad category -> 400", c.get("/events?category=спорт"), 400)

show(
    "PUT /events/{id} owner -> 200",
    c.put(f"/events/{e1['id']}", json={**EVENT, "title": "Обновлённый концерт"}, headers=ORG),
    200,
)
show(
    "PUT /events/{id} non-owner organizer -> 403",
    c.put(f"/events/{e2['id']}", json={**EVENT, "title": "Чужое событие"}, headers=OTHER_ORG),
    403,
)
show(
    "PUT missing field -> 400",
    c.put(f"/events/{e1['id']}", json={**EVENT, "title": "", "description": ""}, headers=ORG),
    400,
)
show(
    "PUT missing resource -> 404",
    c.put("/events/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", json=EVENT, headers=ORG),
    404,
)
show(
    "PATCH /events/{id} -> 200",
    c.patch(f"/events/{e1['id']}", json={"category": "meetup"}, headers=ORG),
    200,
)
show(
    "PATCH wrong type -> 400",
    c.patch(f"/events/{e1['id']}", json={"lat": "abc"}, headers=ORG),
    400,
)

show("DELETE user role -> 403", c.delete(f"/events/{e1['id']}", headers=USER), 403)
show("DELETE owner -> 204", c.delete(f"/events/{e1['id']}", headers=ORG), 204)
show("DELETE again -> 404", c.delete(f"/events/{e1['id']}", headers=ORG), 404)
show("DELETE non-owner organizer -> 403", c.delete(f"/events/{e2['id']}", headers=OTHER_ORG), 403)
show("DELETE admin -> 204", c.delete(f"/events/{e2['id']}", headers=ADMIN), 204)
show("DELETE admin event (own) -> 204", c.delete(f"/events/{e3['id']}", headers=ADMIN), 204)

print(f"\nИтого: {passed} passed, {failed} failed")
print(f"База данных: {DB_FILE}")
sys.exit(1 if failed else 0)
