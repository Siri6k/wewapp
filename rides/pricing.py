from decimal import ROUND_CEILING, Decimal

from .geo import route_distance_km
from .models import PricingConfig


def compute_price(distance_km, config):
    raw = config.base_fare + config.price_per_km * Decimal(str(distance_km))
    raw = max(raw, config.min_fare)
    step = config.rounding_step
    return (raw / step).to_integral_value(rounding=ROUND_CEILING) * step


def quote(origin_lat, origin_lng, dest_lat, dest_lng):
    config = PricingConfig.get_active()
    km, source = route_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
    distance = Decimal(str(round(km, 2)))
    return {
        "distance_km": distance,
        "price": compute_price(distance, config),
        "currency": config.currency,
        "distance_source": source,
    }
