"""
Автотест API поверх реляционной БД (ПР3).

Проверяет все CRUD-операции из ПР2, работающие теперь поверх базы данных:
миграции применяются через Alembic, данные хранятся в SQLite-файле.
Запуск: python verify.py
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(HERE, "verify_events.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"
for suffix in ("-journal", "-wal", "-shm"):
    if os.path.exists(DB_FILE + suffix):
        os.remove(DB_FILE + suffix)
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
               cwd=HERE, check=True, capture_output=True)

from app import app  # noqa: E402

c = app.test_client()
passed = 0
failed = 0


def show(label, resp):
    global passed, failed
    ok = False
    body = resp.get_data(as_text=True)
    try:
        parsed = json.loads(body)
        body = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        pass
    if resp.status_code in (200, 201, 204, 400, 404, 405, 500):
        ok = True
    if ok:
        passed += 1
    else:
        failed += 1
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {label} -> {resp.status_code}")
    if not ok:
        print(body)
    return resp


EVENT = {
    "title": "Концерт в парке",
    "description": "Живая музыка на открытой площадке",
    "lat": 55.7558,
    "lng": 37.6176,
    "starts_at": "2026-10-01T19:00:00Z",
    "category": "concert",
    "organizer_id": "3f2a7c10-0000-4000-8000-000000000001",
}
EVENT2 = {
    "title": "Лекция о REST API",
    "description": "Обзор принципов проектирования REST",
    "lat": 59.9390,
    "lng": 30.3158,
    "starts_at": "2026-11-05T18:00:00Z",
    "category": "lecture",
    "organizer_id": "3f2a7c10-0000-4000-8000-000000000001",
}

show("GET /", c.get("/"))
show("GET /health", c.get("/health"))
show("GET /events (empty)", c.get("/events"))

r = show("POST /events (create 1)", c.post("/events", json=EVENT))
e1 = r.get_json()
r2 = show("POST /events (create 2)", c.post("/events", json=EVENT2))
e2 = r2.get_json()

show("GET /events/{id}", c.get(f"/events/{e1['id']}"))
show("GET /events/{missing}", c.get("/events/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

show("POST missing title", c.post("/events", json={k: v for k, v in EVENT.items() if k != "title"}))
show("POST wrong types", c.post("/events", json={**EVENT, "lat": "не-число", "lng": 999, "starts_at": "не дата", "category": "футбол"}))
show("POST unknown field", c.post("/events", json={**EVENT, "fake": True}))
show("POST bad json", c.post("/events", data="{ это не json", content_type="application/json"))

show("GET filter category=concert", c.get("/events?category=concert"))
show("GET filter date range", c.get("/events?date_from=2026-10-01T00:00:00Z&date_to=2026-10-31T23:59:59Z"))
show("GET pagination page=1 limit=1", c.get("/events?page=1&limit=1"))
show("GET bad limit", c.get("/events?page=0&limit=1000"))
show("GET bad category", c.get("/events?category=спорт"))

show("PUT /events/{id}", c.put(f"/events/{e1['id']}", json={**EVENT, "title": "Обновлённый концерт"}))
show("PUT missing field", c.put(f"/events/{e1['id']}", json={**EVENT, "title": "", "description": ""}))
show("PUT missing resource", c.put("/events/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", json=EVENT))
show("PATCH /events/{id}", c.patch(f"/events/{e1['id']}", json={"category": "meetup"}))
show("PATCH wrong type", c.patch(f"/events/{e1['id']}", json={"lat": "abc"}))
show("DELETE /events/{id}", c.delete(f"/events/{e1['id']}"))
show("DELETE again -> 404", c.delete(f"/events/{e1['id']}"))

print(f"\nИтого: {passed} passed, {failed} failed")
print(f"База данных: {DB_FILE}")
sys.exit(1 if failed else 0)