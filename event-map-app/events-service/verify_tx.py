"""
Демонстрация транзакционности (ПР3).

Два сценария атомарности:
  1) «категория + событие» в одной транзакции: при нарушении CHECK на событии
     откатывается и вставка категории;
  2) пакетная вставка нескольких событий: при сбое одной записи откатывается
     вся пакетная операция.

Запуск: python verify_tx.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(HERE, "tx_events.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
               cwd=HERE, check=True, capture_output=True)

from sqlalchemy.exc import IntegrityError  # noqa: E402

from database import SessionLocal, db_session, utcnow  # noqa: E402
from models import Event  # noqa: E402
from repository.categories import CategoryRepository  # noqa: E402
from repository.events import EventRepository  # noqa: E402


def count_categories():
    with db_session() as session:
        return len(CategoryRepository(session).all())


def count_events():
    with db_session() as session:
        return EventRepository(session).count(EventRepository(session).base_query())


print("=== Сценарий 1: категория + событие в одной транзакции ===")
base_categories = count_categories()

try:
    session = SessionLocal()
    with session.begin():
        CategoryRepository(session).create("blockchain", slug="blockchain")
        session.flush()
        EventRepository(session).add(Event(
            title="Концерт", description="x", lat=999, lng=1,  # CHECK lat -> ошибка
            starts_at=utcnow(), category_id="none", organizer_id="o",
        ))
        session.flush()
    print("НЕ ОЖИДАЛОСЬ: транзакция завершилась успешно")
    sys.exit(1)
except IntegrityError as exc:
    print(f"IntegrityError получен на событии (CHECK lat): {exc}")
except Exception as exc:
    print(f"Ошибка: {type(exc).__name__}: {exc}")
finally:
    session.close()

after_categories = count_categories()
rolled_back = after_categories == base_categories
print(f"Категорий до: {base_categories}, после: {after_categories}")
print(f"Категория 'blockchain' откатилась вместе с событием: {rolled_back}")

print("\n=== Сценарий 2: пакетная вставка ==")
before = count_events()

try:
    session = SessionLocal()
    with session.begin():
        for i in range(2):
            EventRepository(session).add(Event(
                title=f"Пакет #{i}", description="x", lat=50, lng=50,
                starts_at=utcnow(), category_id="oops", organizer_id="o",
            ))
        session.flush()
        bad = Event(title="Плохая запись", description="x", lat=400, lng=1,
                    starts_at=utcnow(), category_id="oops", organizer_id="o")
        EventRepository(session).add(bad)
        session.flush()
    print("НЕ ОЖИДАЛОСЬ: пакет сохранён")
    sys.exit(1)
except IntegrityError:
    print("IntegrityError получен на третьей записи (CHECK lat)")
except Exception as exc:
    print(f"Ошибка: {type(exc).__name__}: {exc}")
finally:
    session.close()

after = count_events()
batch_rolled_back = after == before
print(f"Событий до: {before}, после: {after}")
print(f"Пакет откатился целиком (все три записи): {batch_rolled_back}")

if rolled_back and batch_rolled_back:
    print("\nИТОГ: оба транзакционных сценария продемонстрированы и прошли.")
    sys.exit(0)
else:
    print("\nИТОГ: транзакционные сценарии НЕ прошли.")
    sys.exit(1)