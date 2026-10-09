from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase
from rest_framework.test import APIClient, APITestCase

from accounts.models import User

from .geo import haversine_km, route_distance_km
from .models import PricingConfig, Ride
from .pricing import compute_price

POINTS = {
    "origin_lat": -10.98,
    "origin_lng": 26.74,
    "dest_lat": -10.99,
    "dest_lng": 26.75,
}


class GeoTests(SimpleTestCase):
    def test_haversine_one_degree_of_latitude(self):
        self.assertAlmostEqual(haversine_km(0, 0, 1, 0), 111.19, places=1)

    def test_route_distance_from_osrm(self):
        fake = Mock()
        fake.raise_for_status.return_value = None
        fake.json.return_value = {"code": "Ok", "routes": [{"distance": 2500.0}]}
        with patch("rides.geo.requests.get", return_value=fake):
            km, source = route_distance_km(-10.98, 26.74, -10.99, 26.75)
        self.assertEqual(km, 2.5)
        self.assertEqual(source, "route")

    def test_route_distance_falls_back_on_network_error(self):
        with patch("rides.geo.requests.get", side_effect=requests.ConnectionError):
            km, source = route_distance_km(-10.98, 26.74, -10.99, 26.75)
        self.assertEqual(source, "estimation")
        self.assertAlmostEqual(km, haversine_km(-10.98, 26.74, -10.99, 26.75) * 1.3)


class PricingTests(SimpleTestCase):
    config = PricingConfig(
        base_fare=Decimal("1000"),
        price_per_km=Decimal("500"),
        min_fare=Decimal("1500"),
        rounding_step=Decimal("100"),
    )

    def test_minimum_fare(self):
        self.assertEqual(compute_price(Decimal("0.8"), self.config), Decimal("1500"))

    def test_exact_price(self):
        self.assertEqual(compute_price(Decimal("3.0"), self.config), Decimal("2500"))

    def test_rounds_up_to_step(self):
        self.assertEqual(compute_price(Decimal("3.1"), self.config), Decimal("2600"))

    def test_longer_ride(self):
        self.assertEqual(compute_price(Decimal("10.0"), self.config), Decimal("6000"))


class RideApiTests(APITestCase):
    def setUp(self):
        patcher = patch("rides.geo.requests.get", side_effect=requests.ConnectionError)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.passenger = User.objects.create_user(
            phone="+243822222222", name="Pax", password="secret12", role="passenger"
        )
        self.other = User.objects.create_user(
            phone="+243833333333", name="Autre", password="secret12", role="passenger"
        )
        self.driver = User.objects.create_user(
            phone="+243811111111", name="Moto", password="secret12", role="driver"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.passenger)

    def estimate(self, **extra):
        return self.client.post(
            "/api/rides/estimate/", {**POINTS, **extra}, format="json"
        )

    def create(self, **extra):
        return self.client.post("/api/rides/", {**POINTS, **extra}, format="json")

    def test_estimate_requires_auth(self):
        res = APIClient().post("/api/rides/estimate/", POINTS, format="json")
        self.assertEqual(res.status_code, 401)

    def test_estimate_forbidden_for_driver(self):
        client = APIClient()
        client.force_authenticate(self.driver)
        res = client.post("/api/rides/estimate/", POINTS, format="json")
        self.assertEqual(res.status_code, 403)

    def test_estimate_returns_price(self):
        res = self.estimate()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["distance_source"], "estimation")
        self.assertEqual(res.data["currency"], "CDF")
        self.assertGreaterEqual(res.data["price"], Decimal("1500"))

    def test_estimate_rejects_too_close_points(self):
        res = self.estimate(dest_lat=-10.98, dest_lng=26.74)
        self.assertEqual(res.status_code, 400)

    def test_estimate_rejects_invalid_latitude(self):
        self.assertEqual(self.estimate(origin_lat=95).status_code, 400)

    def test_create_ride(self):
        res = self.create(dest_label="Marché central")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "searching")
        self.assertEqual(res.data["dest_label"], "Marché central")
        ride = Ride.objects.get()
        self.assertEqual(ride.passenger, self.passenger)

    def test_create_ignores_client_price(self):
        res = self.create(price=1)
        self.assertEqual(res.status_code, 201)
        self.assertGreaterEqual(Decimal(res.data["price"]), Decimal("1500"))

    def test_created_price_matches_estimate(self):
        estimated = self.estimate().data["price"]
        created = self.create().data["price"]
        self.assertEqual(Decimal(str(estimated)), Decimal(created))

    def test_second_active_ride_refused(self):
        first = self.create()
        second = self.create()
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["ride_id"], first.data["id"])
        self.assertEqual(Ride.objects.count(), 1)

    def test_detail_own_ride(self):
        ride_id = self.create().data["id"]
        res = self.client.get(f"/api/rides/{ride_id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], ride_id)

    def test_detail_other_passenger_gets_404(self):
        ride_id = self.create().data["id"]
        client = APIClient()
        client.force_authenticate(self.other)
        self.assertEqual(client.get(f"/api/rides/{ride_id}/").status_code, 404)
