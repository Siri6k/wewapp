from django.db import transaction
from django.db.models import Avg, F
from django.utils import timezone

from accounts.models import User
from drivers.models import DriverProfile

from .dispatch import advance_ride
from .models import Rating, Ride, RideOffer


class RideError(Exception):
    pass


def _locked(ride_id):
    return Ride.objects.select_for_update().get(pk=ride_id)


def _count_cancellation(user):
    User.objects.filter(pk=user.pk).update(cancellation_count=F("cancellation_count") + 1)


@transaction.atomic
def start_ride(ride_id, driver):
    ride = _locked(ride_id)
    if ride.driver_id != driver.id or ride.status != Ride.Status.ACCEPTED:
        raise RideError("Cette course ne peut pas être démarrée.")
    ride.status = Ride.Status.IN_PROGRESS
    ride.started_at = timezone.now()
    ride.save(update_fields=["status", "started_at"])
    return ride


@transaction.atomic
def complete_ride(ride_id, driver):
    ride = _locked(ride_id)
    if ride.driver_id != driver.id or ride.status != Ride.Status.IN_PROGRESS:
        raise RideError("Cette course ne peut pas être terminée.")
    ride.status = Ride.Status.COMPLETED
    ride.completed_at = timezone.now()
    ride.save(update_fields=["status", "completed_at"])
    DriverProfile.objects.filter(user=driver).update(rides_count=F("rides_count") + 1)
    return ride


@transaction.atomic
def cancel_ride(ride_id, user):
    ride = _locked(ride_id)

    if user.id == ride.passenger_id:
        if ride.status == Ride.Status.SEARCHING:
            ride.offers.filter(status=RideOffer.Status.PENDING).update(
                status=RideOffer.Status.EXPIRED
            )
        elif ride.status == Ride.Status.ACCEPTED:
            _count_cancellation(user)
        else:
            raise RideError("Cette course ne peut plus être annulée.")
        ride.status = Ride.Status.CANCELLED
        ride.save(update_fields=["status"])
        return ride

    if user.id == ride.driver_id and ride.status == Ride.Status.ACCEPTED:
        RideOffer.objects.filter(
            ride=ride, driver=user, status=RideOffer.Status.ACCEPTED
        ).update(status=RideOffer.Status.DECLINED)
        _count_cancellation(user)
        ride.driver = None
        ride.status = Ride.Status.SEARCHING
        ride.search_started_at = timezone.now()
        ride.save(update_fields=["driver", "status", "search_started_at"])
        return advance_ride(ride.pk)

    raise RideError("Cette course ne peut plus être annulée.")


@transaction.atomic
def rate_ride(ride_id, passenger, stars):
    ride = _locked(ride_id)
    if (
        ride.passenger_id != passenger.id
        or ride.status != Ride.Status.COMPLETED
        or ride.driver_id is None
    ):
        raise RideError("Cette course ne peut pas être notée.")
    if Rating.objects.filter(ride=ride).exists():
        raise RideError("Cette course a déjà été notée.")

    rating = Rating.objects.create(ride=ride, stars=stars)
    average = Rating.objects.filter(ride__driver_id=ride.driver_id).aggregate(
        average=Avg("stars")
    )["average"]
    DriverProfile.objects.filter(user_id=ride.driver_id).update(rating_avg=round(average, 2))
    return rating