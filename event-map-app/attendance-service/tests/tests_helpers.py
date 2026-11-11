"""Общие помощники тестов attendance-service."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

USER_ID = str(uuid.uuid4())
EVENT_ID = str(uuid.uuid4())


def make_token(role, user_id=USER_ID, expires_minutes=30):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "iss": os.environ.get("JWT_ISSUER", "event-map-users-service"),
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        },
        os.environ["JWT_SECRET"],
        algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
    )


def auth(role, user_id=USER_ID):
    return {"Authorization": f"Bearer {make_token(role, user_id)}"}


def payload(**overrides):
    return {"event_id": EVENT_ID, "status": "going", **overrides}
