from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from drivers.models import DriverProfile

from .geo import haversine_km
from .models import Ride, RideOffer

OFFER_TIMEOUT_SECONDS = 60
LOCATION_MAX_AGE_SECONDS = 30
MAX_PICKUP_KM = 5
SEARCH_TIMEOUT_SECONDS = 180

BUSY_STATUSES = [Ride.Status.ACCEPTED, Ride.Status.IN_PROGRESS]


class OfferError(Exception):
    pass


def find_next_driver(ride):
    now = timezone.now()
    fresh_after = now - timedelta(seconds=LOCATION_MAX_AGE_SECONDS)

    already_offered = ride.offers.values_list("driver_id", flat=True)
    busy = Ride.objects.filter(
        status__in=BUSY_STATUSES, driver__isnull=False
    ).values_list("driver_id", flat=True)
    with_pending_offer = RideOffer.objects.filter(
        status=RideOffer.Status.PENDING, expires_at__gt=now
    ).values_list("driver_id", flat=True)

    candidates = (
        DriverProfile.objects.filter(
            is_online=True,
            last_location_at__gte=fresh_after,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .exclude(user_id__in=already_offered)
        .exclude(user_id__in=busy)
        .exclude(user_id__in=with_pending_offer)
        .select_related("user")
    )

    best, best_km = None, None
    for profile in candidates:
        km = haversine_km(
            profile.latitude, profile.longitude, ride.origin_lat, ride.origin_lng
        )
        if km <= MAX_PICKUP_KM and (best_km is None or km < best_km):
            best, best_km = profile, km
    return best


@transaction.atomic
def advance_ride(ride_id):
    """Fait avancer la recherche d'un motard ; peut être rappelée sans risque."""
    ride = Ride.objects.select_for_update().get(pk=ride_id)
    if ride.status != Ride.Status.SEARCHING:
        return ride

    now = timezone.now()
    ride.offers.filter(status=RideOffer.Status.PENDING, expires_at__lte=now).update(
        status=RideOffer.Status.EXPIRED
    )

    if ride.offers.filter(status=RideOffer.Status.PENDING).exists():
        return ride

    profile = find_next_driver(ride)
    if profile is not None:
        RideOffer.objects.create(
            ride=ride,
            driver=profile.user,
            expires_at=now + timedelta(seconds=OFFER_TIMEOUT_SECONDS),
        )
    elif now - ride.created_at > timedelta(seconds=SEARCH_TIMEOUT_SECONDS):
        ride.status = Ride.Status.NO_DRIVER
        ride.save(update_fields=["status"])
    return ride


@transaction.atomic
def accept_offer(offer, driver):
    ride = Ride.objects.select_for_update().get(pk=offer.ride_id)
    offer.refresh_from_db()

    if not DriverProfile.objects.filter(user=driver, is_online=True).exists():
        raise OfferError("Vous êtes hors ligne.")
    if (
        offer.status != RideOffer.Status.PENDING
        or offer.expires_at <= timezone.now()
        or ride.status != Ride.Status.SEARCHING
    ):
        raise OfferError("Cette demande n'est plus disponible.")
    if Ride.objects.filter(driver=driver, status__in=BUSY_STATUSES).exists():
        raise OfferError("Vous avez déjà une course en cours.")

    offer.status = RideOffer.Status.ACCEPTED
    offer.save(update_fields=["status"])
    ride.driver = driver
    ride.status = Ride.Status.ACCEPTED
    ride.save(update_fields=["driver", "status"])
    return ride


def decline_offer(offer):
    updated = RideOffer.objects.filter(
        pk=offer.pk, status=RideOffer.Status.PENDING
    ).update(status=RideOffer.Status.DECLINED)
    if not updated:
        raise OfferError("Cette demande n'est plus disponible.")
    advance_ride(offer.ride_id)
