"""
Проверка расширенной схемы (ПР3): таблицы users и event_participants.

Демонстрирует:
  1) создание пользователя, события, регистраций (связь N:M);
  2) агрегатный запрос — число участников по каждому событию;
  3) составной первичный ключ — повторная регистрация того же пользователя
     на то же событие невозможна (IntegrityError);
  4) CASCADE — при удалении пользователя его регистрации удаляются автоматически.

Запуск: python verify_schema.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(HERE, "schema_events.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
               cwd=HERE, check=True, capture_output=True)

from sqlalchemy.exc import IntegrityError  # noqa: E402

from database import db_session, utcnow  # noqa: E402
from models import Event  # noqa: E402
from repository.categories import CategoryRepository  # noqa: E402
from repository.events import EventRepository  # noqa: E402
from repository.participants import ParticipantRepository  # noqa: E402
from repository.users import UserRepository  # noqa: E402

ok = True


def check(label, value):
    global ok
    status = "PASS" if value else "FAIL"
    if not value:
        ok = False
    print(f"[{status}] {label}")
    return value


# 1) Данные: категория, два события, два пользователя, регистрации.
with db_session() as session:
    events_repo = EventRepository(session)
    cats = CategoryRepository(session)
    users = UserRepository(session)
    parts = ParticipantRepository(session)

    cat = cats.get_or_create("concert")

    e1 = events_repo.add(Event(
        title="Концерт в парке", description="Живая музыка",
        lat=55.7558, lng=37.6176, starts_at=utcnow(),
        category_id=cat.id, organizer_id="org",
    ))
    session.flush()
    e2 = events_repo.add(Event(
        title="Рок-фестиваль", description="День открытого рока",
        lat=55.8, lng=37.6, starts_at=utcnow(),
        category_id=cat.id, organizer_id="org",
    ))
    session.flush()

    alice = users.create("Алиса", "alice@map.app", role="user")
    bob = users.create("Боб", "bob@map.app", role="user")
    _ = users.create("Организатор", "org@map.app", role="organizer")
    session.flush()

    parts.register(e1.id, alice.id)
    parts.register(e1.id, bob.id)
    parts.register(e2.id, alice.id)

print("== step 1: созданы 2 события, 3 пользователя, 3 регистрации ==")

# 2) Агрегат: участники по каждому событию.
with db_session() as session:
    parts = ParticipantRepository(session)
    counts = parts.counts_per_event()
    print("   участников по событиям:", counts)
    check("агрегат: у 1-го события 2 участника, у 2-го — 1",
          counts == {e1.id: 2, e2.id: 1})
    total_users = len(UserRepository(session).all())
    check("всего пользователей = 3", total_users == 3)

# 3) Составной первичный ключ: дубль регистрации запрещён.
try:
    with db_session() as session:
        ParticipantRepository(session).register(e1.id, alice.id)
    print("[FAIL] повторная регистрация прошла без ошибки")
    ok = False
except IntegrityError:
    print("[PASS] повторная регистрация (event_id, user_id) отклонена — составной PK")

# 4) CASCADE: удаляем пользователя — его регистрации удаляются автоматически.
with db_session() as session:
    users = UserRepository(session)
    parts = ParticipantRepository(session)
    users.remove(alice.id)
print("== step 4: пользователь Алиса удалён (CASCADE) ==")

with db_session() as session:
    parts = ParticipantRepository(session)
    counts = parts.counts_per_event()
    alice_regs = len(parts.events_of_user(alice.id))
    print("   участников после удаления:", counts)
    check("регистрации Алисы удалены каскадом", alice_regs == 0)
    check("у 1-го события остался только Боб", counts.get(e1.id) == 1)
    check("у 2-го события участников нет", counts.get(e2.id, 0) == 0)

print("\nИТОГ: расширенная схема (users, event_participants) работает.")
sys.exit(0 if ok else 1)