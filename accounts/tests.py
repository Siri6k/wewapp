from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from .models import User
from .utils import normalize_phone


class NormalizePhoneTests(SimpleTestCase):
    def test_formats(self):
        for raw in ["0812345678", "+243812345678", "243812345678", "081 234 5678"]:
            self.assertEqual(normalize_phone(raw), "+243812345678")


class AuthTests(APITestCase):
    def register(self, phone="0812345678", **extra):
        payload = {"phone": phone, "name": "Jean", "password": "secret12", **extra}
        return self.client.post("/auth/register/", payload, format="json")

    def test_register_normalizes_phone(self):
        res = self.register()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["phone"], "+243812345678")
        self.assertNotIn("password", res.data)

    def test_register_duplicate_in_other_format_rejected(self):
        self.register("0812345678")
        res = self.register("+243812345678")
        self.assertEqual(res.status_code, 400)

    def test_register_invalid_phone_rejected(self):
        self.assertEqual(self.register("12").status_code, 400)

    def test_login_with_local_format(self):
        self.register(role="driver")
        res = self.client.post(
            "/auth/login/",
            {"phone": "0812345678", "password": "secret12"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertEqual(res.data["role"], "driver")

    def test_login_wrong_password(self):
        self.register()
        res = self.client.post(
            "/auth/login/",
            {"phone": "0812345678", "password": "mauvais"},
            format="json",
        )
        self.assertEqual(res.status_code, 401)

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/me/").status_code, 401)

    def test_me_returns_profile(self):
        self.register()
        token = self.client.post(
            "/auth/login/",
            {"phone": "0812345678", "password": "secret12"},
            format="json",
        ).data["access"]
        res = self.client.get("/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["phone"], "+243812345678")
        self.assertEqual(User.objects.count(), 1)
