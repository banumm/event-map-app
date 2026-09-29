"""
Слой хранения (storage).

На этом этапе — in-memory хранилище в dict. В ПР3 будет заменено на
полноценную базу данных (например, PostgreSQL + PostGIS для гео-координат).
"""

import uuid
from datetime import datetime


class InMemoryEventsStorage:
    """Хранит события в памяти. Не знает про HTTP и валидацию."""

    def __init__(self):
        self._events = {}

    def next_id(self):
        return str(uuid.uuid4())

    def now_iso(self):
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def all(self):
        return list(self._events.values())

    def get(self, event_id):
        return self._events.get(event_id)

    def create(self, event):
        self._events[event["id"]] = event
        return event

    def replace(self, event_id, event):
        self._events[event_id] = event
        return event

    def delete(self, event_id):
        return self._events.pop(event_id, None) is not None