import math
from typing import Tuple, Optional, Any
from sqlalchemy.orm import Session

# Earth mean radius in meters
EARTH_RADIUS_METERS = 6371000.0


def validate_coordinates(lat: float, lon: float) -> None:
    """
    Validates that latitude and longitude are within standard geographical bounds.
    """
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} out of range [-90, 90].")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} out of range [-180, 180].")


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


def point_to_segment_distance(
    p_lat: float,
    p_lon: float,
    a_lat: float,
    a_lon: float,
    b_lat: float,
    b_lon: float
) -> Tuple[float, float, float]:
    """
    Calculates the shortest distance from a point P to a line segment A -> B.
    Uses equirectangular projection onto local metric space to find projection parameter t,
    and returns (distance_in_meters, projected_latitude, projected_longitude).
    """
    validate_coordinates(p_lat, p_lon)
    validate_coordinates(a_lat, a_lon)
    validate_coordinates(b_lat, b_lon)

    # If endpoints are identical, return distance to point A
    if a_lat == b_lat and a_lon == b_lon:
        d = haversine_distance(p_lat, p_lon, a_lat, a_lon)
        return round(d, 2), a_lat, a_lon

    mid_lat_rad = math.radians((a_lat + b_lat) / 2.0)
    cos_mid = math.cos(mid_lat_rad)

    # Convert delta degrees to metric delta
    m_per_deg_lat = 111132.954
    m_per_deg_lon = 111412.84 * cos_mid

    dx = (b_lon - a_lon) * m_per_deg_lon
    dy = (b_lat - a_lat) * m_per_deg_lat
    px = (p_lon - a_lon) * m_per_deg_lon
    py = (p_lat - a_lat) * m_per_deg_lat

    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq <= 1e-6:
        d = haversine_distance(p_lat, p_lon, a_lat, a_lon)
        return round(d, 2), a_lat, a_lon

    # Parameter t of projection onto line segment [0.0, 1.0]
    t = (px * dx + py * dy) / seg_len_sq
    t_clamped = max(0.0, min(1.0, t))

    proj_lat = a_lat + t_clamped * (b_lat - a_lat)
    proj_lon = a_lon + t_clamped * (b_lon - a_lon)

    distance = haversine_distance(p_lat, p_lon, proj_lat, proj_lon)
    return round(distance, 2), round(proj_lat, 6), round(proj_lon, 6)


def find_nearest_road_segment(
    db: Session,
    latitude: float,
    longitude: float,
    max_distance_meters: float = 1000.0
) -> Optional[Any]:
    """
    Finds the closest municipal RoadSegment to a given GPS coordinate within max_distance_meters.
    """
    from app.models.road_segment import RoadSegment

    # Search bounding box: +/- delta degrees (~max_distance * 1.5)
    lat_delta = (max_distance_meters / 111000.0) * 1.5
    lon_delta = lat_delta / math.cos(math.radians(latitude)) if abs(latitude) < 89.0 else lat_delta

    min_lat, max_lat = latitude - lat_delta, latitude + lat_delta
    min_lon, max_lon = longitude - lon_delta, longitude + lon_delta

    candidates = (
        db.query(RoadSegment)
        .filter(
            (
                (RoadSegment.start_latitude.between(min_lat, max_lat)) &
                (RoadSegment.start_longitude.between(min_lon, max_lon))
            ) | (
                (RoadSegment.end_latitude.between(min_lat, max_lat)) &
                (RoadSegment.end_longitude.between(min_lon, max_lon))
            )
        )
        .all()
    )

    if not candidates:
        # Fallback to query all if few segments exist in DB
        candidates = db.query(RoadSegment).limit(200).all()

    if not candidates:
        return None

    best_segment = None
    min_dist = float("inf")

    for seg in candidates:
        dist, _, _ = point_to_segment_distance(
            latitude, longitude,
            seg.start_latitude, seg.start_longitude,
            seg.end_latitude, seg.end_longitude
        )
        if dist < min_dist and dist <= max_distance_meters:
            min_dist = dist
            best_segment = seg

    return best_segment
