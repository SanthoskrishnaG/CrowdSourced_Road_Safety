import math
from typing import Tuple

# Earth mean radius in meters
EARTH_RADIUS_METERS = 6371000.0


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculates the great-circle distance between two geographic points
    on the Earth using the Haversine formula.

    :param lat1: Latitude of point 1 in degrees (-90 to 90)
    :param lon1: Longitude of point 1 in degrees (-180 to 180)
    :param lat2: Latitude of point 2 in degrees (-90 to 90)
    :param lon2: Longitude of point 2 in degrees (-180 to 180)
    :return: Distance between the two points in meters
    """
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)

    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine calculation
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance = EARTH_RADIUS_METERS * c
    return round(distance, 2)


def validate_coordinates(lat: float, lon: float) -> None:
    """
    Validates that latitude and longitude are within standard geographical bounds.
    """
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} out of range [-90, 90].")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} out of range [-180, 180].")
