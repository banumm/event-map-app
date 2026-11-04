"""Модульные тесты бизнес-логики users-service (без сети и базы данных)."""

from types import SimpleNamespace

import jwt
from django.test import RequestFactory, SimpleTestCase

from .auth import create_access_token, decode_token
from .errors import ApiError
from .ratelimit import SlidingWindowLimiter
from .views import _json_body, _user_payload, _validate_registration


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class RegistrationValidationTests(SimpleTestCase):
    def test_valid_payload_returns_no_errors(self):
        details, username, email, role = _validate_registration({
            "username": "  organizer1 ",
            "email": " organizer1@example.com ",
            "password": "StrongPass123",
            "role": "organizer",
        })
        self.assertEqual(details, [])
        self.assertEqual(username, "organizer1")
        self.assertEqual(email, "organizer1@example.com")
        self.assertEqual(role, "organizer")

    def test_invalid_username_email_password_and_role(self):
        details, *_ = _validate_registration({
            "username": "ab",
            "email": "not-an-email",
            "password": "123",
            "role": "admin",
        })
        self.assertEqual(
            {item["field"] for item in details},
            {"username", "email", "password", "role"},
        )

    def test_password_length_boundaries(self):
        short, *_ = _validate_registration({
            "username": "alice",
            "email": "alice@example.com",
            "password": "1234567",
        })
        self.assertEqual(short[0]["field"], "password")

        long, *_ = _validate_registration({
            "username": "alice",
            "email": "alice@example.com",
            "password": "x" * 129,
        })
        self.assertEqual(long[0]["field"], "password")

    def test_role_defaults_to_user(self):
        details, _, _, role = _validate_registration({
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPass123",
        })
        self.assertEqual(details, [])
        self.assertEqual(role, "user")

    def test_unknown_role_is_rejected(self):
        details, *_ = _validate_registration({
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPass123",
            "role": "superadmin",
        })
        self.assertEqual(details[0]["field"], "role")


class JsonBodyTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_empty_body_raises_bad_request(self):
        request = self.factory.post("/auth/register", data="", content_type="application/json")
        with self.assertRaises(ApiError) as ctx:
            _json_body(request)
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(ctx.exception.code, "BadRequest")

    def test_invalid_json_raises_bad_request(self):
        request = self.factory.post(
            "/auth/register", data="{ not json", content_type="application/json"
        )
        with self.assertRaises(ApiError) as ctx:
            _json_body(request)
        self.assertEqual(ctx.exception.code, "BadRequest")

    def test_json_array_is_rejected(self):
        request = self.factory.post(
            "/auth/register", data="[]", content_type="application/json"
        )
        with self.assertRaises(ApiError) as ctx:
            _json_body(request)
        self.assertEqual(ctx.exception.code, "BadRequest")


class TokenTests(SimpleTestCase):
    def test_token_contains_required_claims(self):
        user = SimpleNamespace(
            pk=7,
            username="alice",
            email="alice@example.com",
            role="organizer",
        )
        token = create_access_token(user)
        claims = decode_token(token)
        self.assertEqual(claims["sub"], "7")
        self.assertEqual(claims["role"], "organizer")
        self.assertEqual(claims["iss"], "event-map-users-service")
        self.assertIn("exp", claims)
        self.assertIn("jti", claims)

    def test_token_signed_with_other_secret_is_rejected(self):
        user = SimpleNamespace(pk=1, username="a", email="a@example.com", role="user")
        token = create_access_token(user)
        with self.assertRaises(jwt.InvalidTokenError):
            jwt.decode(
                token,
                "another-secret",
                algorithms=["HS256"],
                issuer="event-map-users-service",
            )


class UserPayloadTests(SimpleTestCase):
    def test_payload_has_no_password_or_hash(self):
        from datetime import datetime, timezone

        user = SimpleNamespace(
            id=1,
            username="alice",
            email="alice@example.com",
            role="user",
            date_joined=datetime.now(timezone.utc),
        )
        payload = _user_payload(user)
        self.assertNotIn("password", payload)
        self.assertNotIn("password_hash", payload)
        self.assertEqual(
            set(payload),
            {"id", "username", "email", "role", "created_at"},
        )


class RateLimiterTests(SimpleTestCase):
    def test_allows_requests_up_to_limit(self):
        clock = FakeClock()
        limiter = SlidingWindowLimiter(limit=3, window_seconds=60, clock=clock)
        for _ in range(3):
            allowed, retry = limiter.hit("login:127.0.0.1")
            self.assertTrue(allowed)
            self.assertEqual(retry, 0)

        allowed, retry = limiter.hit("login:127.0.0.1")
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry, 1)

    def test_window_slides_and_allows_again(self):
        clock = FakeClock()
        limiter = SlidingWindowLimiter(limit=2, window_seconds=10, clock=clock)
        limiter.hit("k")
        clock.advance(1)
        limiter.hit("k")
        self.assertFalse(limiter.hit("k")[0])

        clock.advance(10)
        self.assertTrue(limiter.hit("k")[0])

    def test_keys_are_isolated(self):
        limiter = SlidingWindowLimiter(limit=1, window_seconds=60, clock=FakeClock())
        self.assertTrue(limiter.hit("login:1.1.1.1")[0])
        self.assertFalse(limiter.hit("login:1.1.1.1")[0])
        self.assertTrue(limiter.hit("login:2.2.2.2")[0])
        self.assertTrue(limiter.hit("register:1.1.1.1")[0])
