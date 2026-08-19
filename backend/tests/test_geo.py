import pytest
from app.utils.geo import haversine_distance, validate_coordinates


def test_haversine_distance_same_point():
    """
    Distance between identical coordinates must be 0 meters.
    """
    lat, lon = 40.7128, -74.0060
    distance = haversine_distance(lat, lon, lat, lon)
    assert distance == 0.0


def test_haversine_distance_known_points():
    """
    Test distance between London (51.5074, -0.1278) and Paris (48.8566, 2.3522).
    Ground truth great-circle distance is approx 343.5 km (+- 2km).
    """
    london_lat, london_lon = 51.5074, -0.1278
    paris_lat, paris_lon = 48.8566, 2.3522

    distance_meters = haversine_distance(london_lat, london_lon, paris_lat, paris_lon)
    # Expected approx 343500 meters
    assert 340000 <= distance_meters <= 350000


def test_haversine_short_distance():
    """
    Test short distance across two nearby points (approx 111 meters for 0.001 deg latitude).
    """
    lat1, lon1 = 37.7749, -122.4194
    lat2, lon2 = 37.7759, -122.4194

    dist = haversine_distance(lat1, lon1, lat2, lon2)
    assert 100 <= dist <= 120


def test_invalid_coordinates_range():
    """
    Test out of bound coordinates raise ValueError.
    """
    with pytest.raises(ValueError, match="Latitude 95.0 out of range"):
        validate_coordinates(95.0, 0.0)

    with pytest.raises(ValueError, match="Latitude -95.0 out of range"):
        validate_coordinates(-95.0, 0.0)

    with pytest.raises(ValueError, match="Longitude 190.0 out of range"):
        validate_coordinates(0.0, 190.0)

    with pytest.raises(ValueError, match="Longitude -190.0 out of range"):
        validate_coordinates(0.0, -190.0)
