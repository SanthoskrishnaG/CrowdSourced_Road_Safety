import pytest


@pytest.fixture
def map_test_data(client):
    """
    Seeds a set of sample reports at distinct geographic coordinates.
    """
    # Register a citizen
    email = "map_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Map Citizen",
            "password": "securepassword123",
            "role": "CITIZEN"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "securepassword123"
        }
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Point 1: Bangalore (12.9716, 77.5946)
    client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "MG Road Pothole",
            "description": "Deep pothole near junction",
            "severity": "CRITICAL",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "MG Road, Bangalore"
        },
        headers=headers
    )

    # Point 2: Delhi (28.6139, 77.2090)
    client.post(
        "/api/v1/reports",
        json={
            "category": "BROKEN_STREETLIGHT",
            "title": "Connaught Place Dark Street",
            "description": "Streetlight pole broken",
            "severity": "MEDIUM",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "address": "CP, Delhi"
        },
        headers=headers
    )

    # Point 3: Mumbai (19.0760, 72.8777)
    client.post(
        "/api/v1/reports",
        json={
            "category": "FLOODING",
            "title": "Marine Drive Waterlog",
            "description": "Water accumulated",
            "severity": "HIGH",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "address": "Marine Drive, Mumbai"
        },
        headers=headers
    )


def test_public_map_endpoint_accessibility(client, map_test_data):
    """
    Public map endpoint must be accessible without authentication headers.
    """
    response = client.get("/api/v1/reports/map")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_public_map_privacy(client, map_test_data):
    """
    Public map data must not expose citizen emails or password hashes.
    """
    response = client.get("/api/v1/reports/map")
    assert response.status_code == 200
    for point in response.json():
        assert "email" not in point
        assert "password" not in point
        assert "password_hash" not in point
        assert "reporter" not in point
        assert "reporter_id" not in point
        assert "latitude" in point
        assert "longitude" in point
        assert "category" in point
        assert "severity" in point
        assert "status" in point


def test_map_filtering_by_category_and_severity(client, map_test_data):
    """
    Tests category and severity filters on map data.
    """
    # Category filter
    resp = client.get("/api/v1/reports/map?category=POTHOLE")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["category"] == "POTHOLE" for p in data)

    # Severity filter
    resp_sev = client.get("/api/v1/reports/map?severity=CRITICAL")
    assert resp_sev.status_code == 200
    data_sev = resp_sev.json()
    assert all(p["severity"] == "CRITICAL" for p in data_sev)


def test_map_bounding_box_filtering(client, map_test_data):
    """
    Tests geographic bounding box query limits points to south India region.
    """
    # Box around south India (lat 8.0 to 15.0, lon 75.0 to 80.0) -> Should include Bangalore, exclude Delhi and Mumbai
    resp = client.get("/api/v1/reports/map?min_lat=8.0&max_lat=15.0&min_lon=75.0&max_lon=80.0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    for point in data:
        assert 8.0 <= point["latitude"] <= 15.0
        assert 75.0 <= point["longitude"] <= 80.0
