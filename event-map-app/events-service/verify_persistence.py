"""
Доказательство сохранности данных между перезапусками сервера (ПР3).

Процесс A создаёт событие (отдельный интерпретатор Python), процесс B
(новый запуск — «перезапуск сервера») читает список и находит событие.
Данные лежат в SQLite-файле, поэтому переживают перезапуски.

Запуск: python verify_persistence.py
"""

import json
import os
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(HERE, "persist_events.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
               cwd=HERE, check=True, capture_output=True)

SUB_ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

MARK = f"Persistence-{uuid.uuid4().hex[:8]}"

CREATE_SNIPPET = f"""
import json
from app import app
c = app.test_client()
r = c.post("/events", json={json.dumps({
    "title": MARK,
    "description": "проверка персистентности",
    "lat": 43.2567, "lng": 76.9286,
    "starts_at": "2026-12-01T18:00:00Z",
    "category": "meetup",
    "organizer_id": "3f2a7c10-0000-4000-8000-000000000001",
})})
data = r.get_json()
print("CREATE", r.status_code, data["id"])
"""

LIST_SNIPPET = f"""
import json
from app import app
c = app.test_client()
r = c.get("/events?limit=100")
items = r.get_json()["items"]
found = [e for e in items if e["title"] == "{MARK}"]
print("LIST", r.status_code, "found=" + str(len(found)))
"""

print("Шаг 1: запуск сервера (процесс A) и создание события...")
out1 = subprocess.run([sys.executable, "-c", CREATE_SNIPPET], cwd=HERE,
                      capture_output=True, text=True, encoding="utf-8", errors="replace", env=SUB_ENV)
print("  ", out1.stdout.strip())

print("Шаг 2: «перезапуск» — новый процесс B читает список...")
time.sleep(1)
out2 = subprocess.run([sys.executable, "-c", LIST_SNIPPET], cwd=HERE,
                      capture_output=True, text=True, encoding="utf-8", errors="replace", env=SUB_ENV)
print("  ", out2.stdout.strip())

created = "CREATE 201" in out1.stdout
found = "found=1" in out2.stdout

if created and found:
    print(f"\nИТОГ: событие '{MARK}' сохранено в базе и доступно после "
          f"перезапуска сервера (файл {DB_FILE}).")
    sys.exit(0)
else:
    print("\nИТОГ: проверка персистентности НЕ прошла.")
    sys.exit(1)