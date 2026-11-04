import json

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from .middleware import UnifiedErrorMiddleware
from .ratelimit import reset_limiter

User = get_user_model()


class AuthApiTests(TestCase):
    def setUp(self):
        reset_limiter()
    def post(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def register(self, **overrides):
        payload = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPass123",
            "role": "user",
        }
        payload.update(overrides)
        return self.post("/auth/register", payload)

    def login(self, **overrides):
        payload = {"username": "alice", "password": "StrongPass123"}
        payload.update(overrides)
        return self.post("/auth/login", payload)

    def token_for(self, user):
        response = self.login(username=user.username)
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def test_register_hashes_password_and_returns_user(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["role"], "user")
        user = User.objects.get(username="alice")
        self.assertTrue(user.password.startswith("argon2$"))
        self.assertNotEqual(user.password, "StrongPass123")

    def test_register_rejects_duplicate_username_and_email(self):
        self.register()
        response = self.register(email="other@example.com")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "Conflict")

        response = self.register(username="bob")
        self.assertEqual(response.status_code, 409)

    def test_register_validates_email_password_and_role(self):
        response = self.register(
            email="not-an-email",
            password="123",
            role="admin",
        )
        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual(error["code"], "ValidationError")
        fields = {item["field"] for item in error["details"]}
        self.assertEqual(fields, {"email", "password", "role"})

    def test_login_by_username_and_email_returns_jwt(self):
        self.register()
        for identifier in ("alice", "alice@example.com"):
            response = self.login(username=identifier)
            self.assertEqual(response.status_code, 200)
            token = response.json()["access_token"]
            claims = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
            )
            self.assertEqual(claims["role"], "user")
            self.assertEqual(claims["sub"], str(User.objects.get(username="alice").id))

    def test_login_wrong_password_returns_401(self):
        self.register()
        response = self.login(password="wrong-password")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "InvalidCredentials")

    def test_me_requires_valid_token(self):
        self.register()
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "Unauthorized")

        user = User.objects.get(username="alice")
        response = self.client.get(
            "/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {self.token_for(user)}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "alice")

    def test_admin_route_distinguishes_403_and_200(self):
        self.register()
        normal = User.objects.get(username="alice")
        response = self.client.get(
            "/users",
            HTTP_AUTHORIZATION=f"Bearer {self.token_for(normal)}",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "Forbidden")

        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123",
            role="admin",
        )
        response = self.client.get(
            "/users",
            HTTP_AUTHORIZATION=f"Bearer {self.token_for(admin)}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)

    def test_unknown_route_uses_unified_format(self):
        response = self.client.get("/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NotFound")
        self.assertIn("details", response.json()["error"])

    def test_invalid_json_uses_unified_format(self):
        response = self.client.post(
            "/auth/register",
            data="{ not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "BadRequest")

    def test_register_and_login_do_not_return_password_hash(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.json())
        self.assertNotIn("argon2", response.content.decode())

        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", response.json()["user"])
        self.assertNotIn("argon2", response.content.decode())

    def test_invalid_token_returns_401(self):
        response = self.client.get(
            "/auth/me",
            HTTP_AUTHORIZATION="Bearer not-a-jwt",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "InvalidToken")

    @override_settings(AUTH_RATE_LIMIT=2, AUTH_RATE_WINDOW_SECONDS=60)
    def test_register_rate_limit_returns_429(self):
        reset_limiter()
        self.register()
        self.register(email="other@example.com")
        response = self.register(username="third", email="third@example.com")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "TooManyRequests")
        self.assertIn("Retry-After", response)

    @override_settings(AUTH_RATE_LIMIT=1, AUTH_RATE_WINDOW_SECONDS=60)
    def test_login_rate_limit_returns_429(self):
        reset_limiter()
        self.register()
        self.assertEqual(self.login().status_code, 200)
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "TooManyRequests")

    def test_unhandled_exception_returns_unified_500(self):
        request = RequestFactory().get("/boom")

        def broken_view(_request):
            raise RuntimeError("boom")

        middleware = UnifiedErrorMiddleware(broken_view)
        response = middleware(request)
        payload = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["error"]["code"], "InternalServerError")
        self.assertNotIn("boom", response.content.decode())
