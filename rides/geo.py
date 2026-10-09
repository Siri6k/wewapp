import math

import requests

OSRM_URL = (
    "https://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}"
)
DETOUR_FACTOR = 1.3


def haversine_km(lat1, lng1, lat2, lng2):
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def route_distance_km(lat1, lng1, lat2, lng2):
    """Retourne (distance en km, source) ; source = "route" ou "estimation"."""
    url = OSRM_URL.format(lat1=lat1, lng1=lng1, lat2=lat2, lng2=lng2)
    try:
        response = requests.get(url, params={"overview": "false"}, timeout=3)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == "Ok":
            return data["routes"][0]["distance"] / 1000, "route"
    except (requests.RequestException, ValueError, KeyError, IndexError):
        pass
    return haversine_km(lat1, lng1, lat2, lng2) * DETOUR_FACTOR, "estimation"
