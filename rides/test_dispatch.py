from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import requests
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from drivers.models import DriverProfile

from .models import Ride, RideOffer

API = "/api"
POINTS = {
    "origin_lat": -10.98,
    "origin_lng": 26.74,
    "dest_lat": -10.99,
    "dest_lng": 26.75,
}
NEAR = (-10.981, 26.741)  # environ 150 m du départ
FAR = (-10.99, 26.75)  # environ 1,6 km du départ
TOO_FAR = (-11.08, 26.74)  # environ 11 km du départ


class DispatchTests(APITestCase):
    def setUp(self):
        patcher = patch("rides.geo.requests.get", side_effect=requests.ConnectionError)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.passenger = self.make_user("+243822222222", "passenger")
        self.other_passenger = self.make_user("+243833333333", "passenger")
        self.client = APIClient()
        self.client.force_authenticate(self.passenger)

    def make_user(self, phone, role):
        return User.objects.create_user(
            phone=phone, name=f"User{phone[-3:]}", password="secret12", role=role
        )

    def make_driver(self, phone, position, online=True, age_seconds=0):
        user = self.make_user(phone, "driver")
        DriverProfile.objects.create(
            user=user,
            plate="AB 123",
            is_online=online,
            latitude=position[0],
            longitude=position[1],
            last_location_at=timezone.now() - timedelta(seconds=age_seconds),
        )
        return user

    def make_accepted_ride(self, driver):
        return Ride.objects.create(
            passenger=self.other_passenger,
            driver=driver,
            status=Ride.Status.ACCEPTED,
            origin_lat=-10.98,
            origin_lng=26.74,
            dest_lat=-10.99,
            dest_lng=26.75,
            distance_km=2,
            price=1500,
            currency="CDF",
        )

    def as_user(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def book(self):
        return self.client.post(f"{API}/rides/", POINTS, format="json")

    def expire_offers(self):
        RideOffer.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

    def test_create_ride_offers_nearest_driver(self):
        near = self.make_driver("+243811111111", NEAR)
        self.make_driver("+243812222222", FAR)
        res = self.book()
        self.assertEqual(res.status_code, 201)
        offer = RideOffer.objects.get()
        self.assertEqual(offer.driver, near)
        self.assertEqual(offer.status, RideOffer.Status.PENDING)
        seconds = (offer.expires_at - timezone.now()).total_seconds()
        self.assertTrue(55 < seconds <= 60)

    def test_offline_driver_gets_no_offer(self):
        self.make_driver("+243811111111", NEAR, online=False)
        res = self.book()
        self.assertEqual(res.data["status"], "searching")
        self.assertEqual(RideOffer.objects.count(), 0)

    def test_stale_location_driver_skipped(self):
        self.make_driver("+243811111111", NEAR, age_seconds=300)
        fresh = self.make_driver("+243812222222", FAR)
        self.book()
        self.assertEqual(RideOffer.objects.get().driver, fresh)

    def test_driver_too_far_skipped(self):
        self.make_driver("+243811111111", TOO_FAR)
        self.book()
        self.assertEqual(RideOffer.objects.count(), 0)

    def test_busy_driver_skipped(self):
        near = self.make_driver("+243811111111", NEAR)
        far = self.make_driver("+243812222222", FAR)
        self.make_accepted_ride(near)
        self.book()
        self.assertEqual(RideOffer.objects.get().driver, far)

    def test_pending_offers_listed_for_the_right_driver(self):
        near = self.make_driver("+243811111111", NEAR)
        far = self.make_driver("+243812222222", FAR)
        self.book()
        res = self.as_user(near).get(f"{API}/rides/driver/offers/pending/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        offer = res.data[0]
        self.assertLess(offer["pickup_distance_km"], 1)
        self.assertTrue(0 < offer["seconds_left"] <= 60)
        self.assertEqual(offer["passenger_name"], self.passenger.name)
        self.assertGreaterEqual(offer["ride"]["price"], Decimal("1500"))
        self.assertEqual(
            self.as_user(far).get(f"{API}/rides/driver/offers/pending/").data, []
        )

    def test_accept_assigns_driver(self):
        near = self.make_driver("+243811111111", NEAR)
        self.book()
        offer = RideOffer.objects.get()
        res = self.as_user(near).post(f"{API}/rides/offers/{offer.id}/accept/")
        self.assertEqual(res.status_code, 200)
        ride = Ride.objects.get()
        self.assertEqual(ride.status, Ride.Status.ACCEPTED)
        self.assertEqual(ride.driver, near)
        offer.refresh_from_db()
        self.assertEqual(offer.status, RideOffer.Status.ACCEPTED)

        detail = self.client.get(f"{API}/rides/{ride.id}/")
        self.assertEqual(detail.data["status"], "accepted")
        self.assertEqual(detail.data["driver"]["plate"], "AB 123")
        self.assertEqual(detail.data["driver"]["name"], near.name)

    def test_accept_expired_offer_refused(self):
        near = self.make_driver("+243811111111", NEAR)
        self.book()
        self.expire_offers()
        offer = RideOffer.objects.get()
        res = self.as_user(near).post(f"{API}/rides/offers/{offer.id}/accept/")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(Ride.objects.get().status, Ride.Status.SEARCHING)

    def test_other_driver_cannot_accept_offer(self):
        self.make_driver("+243811111111", NEAR)
        far = self.make_driver("+243812222222", FAR)
        self.book()
        offer = RideOffer.objects.get()
        res = self.as_user(far).post(f"{API}/rides/offers/{offer.id}/accept/")
        self.assertEqual(res.status_code, 404)

    def test_accept_requires_online_driver(self):
        near = self.make_driver("+243811111111", NEAR)
        self.book()
        offer = RideOffer.objects.get()
        DriverProfile.objects.filter(user=near).update(is_online=False)
        res = self.as_user(near).post(f"{API}/rides/offers/{offer.id}/accept/")
        self.assertEqual(res.status_code, 409)

    def test_accept_twice_refused(self):
        near = self.make_driver("+243811111111", NEAR)
        self.book()
        offer = RideOffer.objects.get()
        client = self.as_user(near)
        self.assertEqual(
            client.post(f"{API}/rides/offers/{offer.id}/accept/").status_code, 200
        )
        self.assertEqual(
            client.post(f"{API}/rides/offers/{offer.id}/accept/").status_code, 409
        )

    def test_busy_driver_cannot_accept(self):
        near = self.make_driver("+243811111111", NEAR)
        self.book()
        offer = RideOffer.objects.get()
        self.make_accepted_ride(near)
        res = self.as_user(near).post(f"{API}/rides/offers/{offer.id}/accept/")
        self.assertEqual(res.status_code, 409)

    def test_decline_passes_to_next_driver(self):
        near = self.make_driver("+243811111111", NEAR)
        far = self.make_driver("+243812222222", FAR)
        self.book()
        offer = RideOffer.objects.get(driver=near)
        res = self.as_user(near).post(f"{API}/rides/offers/{offer.id}/decline/")
        self.assertEqual(res.status_code, 200)
        offer.refresh_from_db()
        self.assertEqual(offer.status, RideOffer.Status.DECLINED)
        self.assertTrue(
            RideOffer.objects.filter(
                driver=far, status=RideOffer.Status.PENDING
            ).exists()
        )

    def test_expired_offer_passes_to_next_driver_on_poll(self):
        near = self.make_driver("+243811111111", NEAR)
        far = self.make_driver("+243812222222", FAR)
        ride_id = self.book().data["id"]
        self.expire_offers()
        self.client.get(f"{API}/rides/{ride_id}/")
        self.assertEqual(
            RideOffer.objects.get(driver=near).status, RideOffer.Status.EXPIRED
        )
        self.assertEqual(
            RideOffer.objects.get(driver=far).status, RideOffer.Status.PENDING
        )

    def test_driver_never_offered_twice(self):
        near = self.make_driver("+243811111111", NEAR)
        ride_id = self.book().data["id"]
        offer = RideOffer.objects.get()
        self.as_user(near).post(f"{API}/rides/offers/{offer.id}/decline/")
        res = self.client.get(f"{API}/rides/{ride_id}/")
        self.assertEqual(res.data["status"], "searching")
        self.assertEqual(RideOffer.objects.count(), 1)

    def test_no_driver_after_search_timeout(self):
        near = self.make_driver("+243811111111", NEAR)
        ride_id = self.book().data["id"]
        offer = RideOffer.objects.get()
        self.as_user(near).post(f"{API}/rides/offers/{offer.id}/decline/")
        Ride.objects.update(created_at=timezone.now() - timedelta(minutes=5))
        res = self.client.get(f"{API}/rides/{ride_id}/")
        self.assertEqual(res.data["status"], "no_driver")

    def test_passenger_can_book_again_after_timeout(self):
        self.book()
        Ride.objects.update(created_at=timezone.now() - timedelta(minutes=5))
        res = self.book()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Ride.objects.count(), 2)
        self.assertEqual(
            Ride.objects.order_by("id").first().status, Ride.Status.NO_DRIVER
        )
