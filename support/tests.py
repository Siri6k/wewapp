from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import User
from rides.models import Ride

from .admin import ReportAdmin
from .models import Report

API = "/api"


class ReportTests(APITestCase):
    def setUp(self):
        cache.clear()  # le compteur de limite est conservé en mémoire
        self.passenger = User.objects.create_user(
            phone="+243822222222", name="Pax", password="secret12", role="passenger"
        )
        self.driver = User.objects.create_user(
            phone="+243811111111", name="Moto", password="secret12", role="driver"
        )
        self.stranger = User.objects.create_user(
            phone="+243833333333", name="Autre", password="secret12", role="passenger"
        )
        self.ride = Ride.objects.create(
            passenger=self.passenger,
            driver=self.driver,
            status=Ride.Status.COMPLETED,
            origin_lat=-10.98,
            origin_lng=26.74,
            dest_lat=-10.99,
            dest_lng=26.75,
            distance_km=2,
            price=1500,
            currency="CDF",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.passenger)

    def as_user(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def post(self, client=None, **extra):
        payload = {
            "category": "price",
            "message": "Le motard a demandé plus cher.",
            **extra,
        }
        return (client or self.client).post(f"{API}/reports/", payload, format="json")

    def test_requires_authentication(self):
        res = APIClient().post(
            f"{API}/reports/", {"category": "bug", "message": "Un bug."}, format="json"
        )
        self.assertEqual(res.status_code, 401)

    def test_create_report_without_ride(self):
        res = self.post()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "open")
        self.assertIsNone(res.data["ride"])
        self.assertEqual(Report.objects.get().user, self.passenger)

    def test_create_report_about_my_ride(self):
        res = self.post(ride=self.ride.id)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["ride"], self.ride.id)

    def test_driver_can_report_about_his_ride(self):
        res = self.post(
            client=self.as_user(self.driver), category="behavior", ride=self.ride.id
        )
        self.assertEqual(res.status_code, 201)

    def test_cannot_report_someone_elses_ride(self):
        res = self.post(client=self.as_user(self.stranger), ride=self.ride.id)
        self.assertEqual(res.status_code, 400)

    def test_unknown_ride_gets_the_same_error(self):
        unknown = self.post(ride=999999)
        foreign = self.post(client=self.as_user(self.stranger), ride=self.ride.id)
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.data["ride"][0], "Course introuvable.")
        self.assertEqual(foreign.data["ride"][0], "Course introuvable.")

    def test_invalid_category(self):
        self.assertEqual(self.post(category="nimporte").status_code, 400)

    def test_message_validation(self):
        self.assertEqual(self.post(message="").status_code, 400)
        self.assertEqual(self.post(message="abc").status_code, 400)
        self.assertEqual(self.post(message="x" * 1001).status_code, 400)

    def test_list_shows_only_my_reports_with_the_response(self):
        mine = self.post().data["id"]
        Report.objects.create(user=self.stranger, category="bug", message="Pas à moi.")
        Report.objects.filter(pk=mine).update(
            admin_response="Nous avons contacté le motard.", status="resolved"
        )
        res = self.client.get(f"{API}/reports/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            res.data[0]["admin_response"], "Nous avons contacté le motard."
        )
        self.assertEqual(res.data[0]["status"], "resolved")

    def test_sending_is_limited_but_reading_is_not(self):
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"reports": "2/day"}):
            self.assertEqual(self.post().status_code, 201)
            self.assertEqual(self.post().status_code, 201)
            self.assertEqual(self.post().status_code, 429)
            self.assertEqual(self.client.get(f"{API}/reports/").status_code, 200)

    def test_admin_records_the_time_of_the_first_response_only(self):
        report = Report.objects.create(
            user=self.passenger, category="price", message="Message test."
        )
        admin = ReportAdmin(Report, AdminSite())

        report.admin_response = "Nous avons contacté le motard."
        admin.save_model(None, report, None, True)
        report.refresh_from_db()
        first = report.responded_at
        self.assertIsNotNone(first)

        report.admin_response = "Réponse mise à jour."
        admin.save_model(None, report, None, True)
        report.refresh_from_db()
        self.assertEqual(report.responded_at, first)
