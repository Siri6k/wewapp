from rest_framework.test import APIClient, APITestCase

from accounts.models import User


class DriverTests(APITestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            phone="+243811111111", name="Moto", password="secret12", role="driver"
        )
        self.passenger = User.objects.create_user(
            phone="+243822222222", name="Pax", password="secret12", role="passenger"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.driver)

    def go_online(self, **extra):
        payload = {"latitude": -10.98, "longitude": 26.74, **extra}
        return self.client.post("/driver/online/", payload, format="json")

    def set_plate(self, plate="ab 123 cd"):
        return self.client.patch("/driver/profile/", {"plate": plate}, format="json")

    def test_unauthenticated_refused(self):
        self.assertEqual(APIClient().get("/driver/profile/").status_code, 401)

    def test_passenger_forbidden(self):
        client = APIClient()
        client.force_authenticate(self.passenger)
        self.assertEqual(client.get("/driver/profile/").status_code, 403)

    def test_profile_created_on_first_get(self):
        res = self.client.get("/driver/profile/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_online"])
        self.assertEqual(res.data["plate"], "")

    def test_plate_is_normalized(self):
        res = self.set_plate("ab 123 cd")
        self.assertEqual(res.data["plate"], "AB 123 CD")

    def test_cannot_set_online_flag_via_profile(self):
        self.client.patch("/driver/profile/", {"is_online": True}, format="json")
        self.assertFalse(self.client.get("/driver/profile/").data["is_online"])

    def test_online_requires_plate(self):
        self.assertEqual(self.go_online().status_code, 400)

    def test_online_requires_location(self):
        self.set_plate()
        res = self.client.post("/driver/online/", {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_online_rejects_invalid_latitude(self):
        self.set_plate()
        self.assertEqual(self.go_online(latitude=95).status_code, 400)

    def test_online_saves_position(self):
        self.set_plate()
        res = self.go_online()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_online"])
        self.assertEqual(res.data["latitude"], -10.98)
        self.assertIsNotNone(res.data["last_location_at"])

    def test_location_refused_when_offline(self):
        res = self.client.post(
            "/driver/location/", {"latitude": -10.9, "longitude": 26.7}, format="json"
        )
        self.assertEqual(res.status_code, 409)

    def test_location_updates_when_online(self):
        self.set_plate()
        self.go_online()
        res = self.client.post(
            "/driver/location/", {"latitude": -10.99, "longitude": 26.75}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["latitude"], -10.99)

    def test_offline(self):
        self.set_plate()
        self.go_online()
        res = self.client.post("/driver/offline/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_online"])
