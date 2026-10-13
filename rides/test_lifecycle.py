from datetime import timedelta
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
NEAR = (-10.981, 26.741)
FAR = (-10.99, 26.75)


class LifecycleTests(APITestCase):
    def setUp(self):
        patcher = patch("rides.geo.requests.get", side_effect=requests.ConnectionError)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.passenger = self.make_user("+243822222222", "passenger")
        self.other_passenger = self.make_user("+243833333333", "passenger")
        self.near = self.make_driver("+243811111111", NEAR)
        self.client = APIClient()
        self.client.force_authenticate(self.passenger)

    def make_user(self, phone, role):
        return User.objects.create_user(
            phone=phone, name=f"User{phone[-3:]}", password="secret12", role=role
        )

    def make_driver(self, phone, position):
        user = self.make_user(phone, "driver")
        DriverProfile.objects.create(
            user=user,
            plate="AB 123",
            is_online=True,
            latitude=position[0],
            longitude=position[1],
            last_location_at=timezone.now(),
        )
        return user

    def as_user(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def book(self, client=None):
        return (client or self.client).post(f"{API}/rides/", POINTS, format="json")

    def accept(self, driver=None):
        driver = driver or self.near
        offer = RideOffer.objects.filter(
            driver=driver, status=RideOffer.Status.PENDING
        ).latest("id")
        return self.as_user(driver).post(f"{API}/rides/offers/{offer.id}/accept/")

    def action(self, user, ride_id, name, data=None):
        return self.as_user(user).post(
            f"{API}/rides/{ride_id}/{name}/", data or {}, format="json"
        )

    def accepted_ride(self):
        ride_id = self.book().data["id"]
        self.accept()
        return ride_id

    def in_progress_ride(self):
        ride_id = self.accepted_ride()
        self.action(self.near, ride_id, "start")
        return ride_id

    def completed_ride(self):
        ride_id = self.in_progress_ride()
        self.action(self.near, ride_id, "complete")
        return ride_id

    # --- démarrer et terminer ---

    def test_start_ride(self):
        ride_id = self.accepted_ride()
        res = self.action(self.near, ride_id, "start")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "in_progress")
        self.assertIsNotNone(res.data["started_at"])

    def test_start_twice_refused(self):
        ride_id = self.accepted_ride()
        self.action(self.near, ride_id, "start")
        self.assertEqual(self.action(self.near, ride_id, "start").status_code, 409)

    def test_other_driver_cannot_start(self):
        far = self.make_driver("+243812222222", FAR)
        ride_id = self.accepted_ride()
        self.assertEqual(self.action(far, ride_id, "start").status_code, 404)

    def test_complete_ride(self):
        ride_id = self.in_progress_ride()
        res = self.action(self.near, ride_id, "complete")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "completed")
        self.assertIsNotNone(res.data["completed_at"])
        self.assertEqual(DriverProfile.objects.get(user=self.near).rides_count, 1)

    def test_complete_requires_start(self):
        ride_id = self.accepted_ride()
        self.assertEqual(self.action(self.near, ride_id, "complete").status_code, 409)

    # --- annulation ---

    def test_passenger_cancel_while_searching_is_free(self):
        ride_id = self.book().data["id"]
        res = self.action(self.passenger, ride_id, "cancel")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "cancelled")
        self.passenger.refresh_from_db()
        self.assertEqual(self.passenger.cancellation_count, 0)
        self.assertFalse(
            RideOffer.objects.filter(status=RideOffer.Status.PENDING).exists()
        )
        self.assertEqual(self.book().status_code, 201)

    def test_passenger_cancel_after_accept_is_counted(self):
        ride_id = self.accepted_ride()
        res = self.action(self.passenger, ride_id, "cancel")
        self.assertEqual(res.data["status"], "cancelled")
        self.passenger.refresh_from_db()
        self.assertEqual(self.passenger.cancellation_count, 1)
        driver_active = self.as_user(self.near).get(f"{API}/rides/driver/active/")
        self.assertEqual(driver_active.status_code, 204)

    def test_passenger_cannot_cancel_in_progress_ride(self):
        ride_id = self.in_progress_ride()
        self.assertEqual(
            self.action(self.passenger, ride_id, "cancel").status_code, 409
        )

    def test_driver_cancel_sends_ride_to_next_driver(self):
        far = self.make_driver("+243812222222", FAR)
        ride_id = self.accepted_ride()
        res = self.action(self.near, ride_id, "cancel")
        self.assertEqual(res.status_code, 200)

        ride = Ride.objects.get(pk=ride_id)
        self.assertEqual(ride.status, Ride.Status.SEARCHING)
        self.assertIsNone(ride.driver)
        self.near.refresh_from_db()
        self.assertEqual(self.near.cancellation_count, 1)
        self.assertEqual(
            RideOffer.objects.get(ride=ride, driver=self.near).status,
            RideOffer.Status.DECLINED,
        )
        self.assertTrue(
            RideOffer.objects.filter(
                driver=far, status=RideOffer.Status.PENDING
            ).exists()
        )
        self.assertEqual(RideOffer.objects.filter(driver=self.near).count(), 1)

    def test_driver_cancel_restarts_the_search_window(self):
        ride_id = self.accepted_ride()
        Ride.objects.update(created_at=timezone.now() - timedelta(minutes=10))
        res = self.action(self.near, ride_id, "cancel")
        self.assertEqual(res.data["status"], "searching")

    def test_stranger_cannot_cancel(self):
        ride_id = self.book().data["id"]
        self.assertEqual(
            self.action(self.other_passenger, ride_id, "cancel").status_code, 404
        )

    # --- notes ---

    def test_rating_updates_driver_average(self):
        ride_id = self.completed_ride()
        res = self.action(self.passenger, ride_id, "rating", {"stars": 5})
        self.assertEqual(res.status_code, 201)
        self.assertAlmostEqual(
            DriverProfile.objects.get(user=self.near).rating_avg, 5.0
        )
        detail = self.client.get(f"{API}/rides/{ride_id}/")
        self.assertEqual(detail.data["rating"], 5)

    def test_rating_average_over_several_rides(self):
        first = self.completed_ride()
        self.action(self.passenger, first, "rating", {"stars": 5})
        second = self.completed_ride()
        self.action(self.passenger, second, "rating", {"stars": 3})
        self.assertAlmostEqual(
            DriverProfile.objects.get(user=self.near).rating_avg, 4.0
        )

    def test_rating_only_after_completion(self):
        ride_id = self.accepted_ride()
        self.assertEqual(
            self.action(self.passenger, ride_id, "rating", {"stars": 5}).status_code,
            409,
        )

    def test_rating_twice_refused(self):
        ride_id = self.completed_ride()
        self.assertEqual(
            self.action(self.passenger, ride_id, "rating", {"stars": 4}).status_code,
            201,
        )
        self.assertEqual(
            self.action(self.passenger, ride_id, "rating", {"stars": 5}).status_code,
            409,
        )

    def test_rating_invalid_stars(self):
        ride_id = self.completed_ride()
        self.assertEqual(
            self.action(self.passenger, ride_id, "rating", {"stars": 6}).status_code,
            400,
        )
        self.assertEqual(
            self.action(self.passenger, ride_id, "rating", {"stars": 0}).status_code,
            400,
        )

    def test_only_the_ride_passenger_can_rate(self):
        ride_id = self.completed_ride()
        res = self.action(self.other_passenger, ride_id, "rating", {"stars": 5})
        self.assertEqual(res.status_code, 404)

    # --- course active et suivi ---

    def test_passenger_active_ride(self):
        self.assertEqual(self.client.get(f"{API}/rides/active/").status_code, 204)
        ride_id = self.book().data["id"]
        res = self.client.get(f"{API}/rides/active/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], ride_id)
        self.accept()
        self.action(self.near, ride_id, "start")
        self.action(self.near, ride_id, "complete")
        self.assertEqual(self.client.get(f"{API}/rides/active/").status_code, 204)

    def test_driver_active_ride_shows_passenger_only_to_the_driver(self):
        driver_client = self.as_user(self.near)
        self.assertEqual(
            driver_client.get(f"{API}/rides/driver/active/").status_code, 204
        )
        ride_id = self.accepted_ride()

        res = driver_client.get(f"{API}/rides/driver/active/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["passenger"]["name"], self.passenger.name)
        self.assertEqual(res.data["passenger"]["phone"], self.passenger.phone)

        detail = self.client.get(f"{API}/rides/{ride_id}/")
        self.assertIsNone(detail.data["passenger"])

    def test_driver_position_visible_to_passenger_once_accepted(self):
        ride_id = self.book().data["id"]
        self.assertIsNone(self.client.get(f"{API}/rides/{ride_id}/").data["driver"])
        self.accept()
        driver = self.client.get(f"{API}/rides/{ride_id}/").data["driver"]
        self.assertEqual(driver["latitude"], NEAR[0])
        self.assertEqual(driver["longitude"], NEAR[1])
