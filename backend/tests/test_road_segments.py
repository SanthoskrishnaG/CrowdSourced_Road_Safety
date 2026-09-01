import pytest
from app.utils.geo import point_to_segment_distance, haversine_distance


@pytest.fixture
def auth_tokens(client):
    # Citizen
    c_email = "road_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": c_email, "full_name": "Road Citizen", "password": "password123", "role": "CITIZEN"}
    )
    c_token = client.post("/api/v1/auth/login", json={"email": c_email, "password": "password123"}).json()["access_token"]

    # Authority
    a_email = "road_auth@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": a_email, "full_name": "Road Authority", "password": "password123", "role": "AUTHORITY"}
    )
    a_token = client.post("/api/v1/auth/login", json={"email": a_email, "password": "password123"}).json()["access_token"]

    return {
        "citizen": {"Authorization": f"Bearer {c_token}"},
        "authority": {"Authorization": f"Bearer {a_token}"}
    }


def test_point_to_segment_distance_math():
    """
    Tests geometric projection distance from point to line segment.
    """
    # Line segment: (12.9000, 77.5000) -> (12.9000, 77.6000) (horizontal line on latitude 12.9)
    # Point exactly at midpoint: (12.9000, 77.5500) -> distance should be 0.0m
    dist, p_lat, p_lon = point_to_segment_distance(12.9000, 77.5500, 12.9000, 77.5000, 12.9000, 77.6000)
    assert dist == 0.0
    assert p_lat == 12.9000
    assert p_lon == 77.5500

    # Point offset north by ~111m: (12.9010, 77.5500)
    dist_offset, _, _ = point_to_segment_distance(12.9010, 77.5500, 12.9000, 77.5000, 12.9000, 77.6000)
    assert 100.0 < dist_offset < 125.0


def test_create_and_list_road_segments(client, auth_tokens):
    """
    Phase 10: Tests creating road segment and querying GET /api/v1/roads.
    """
    # 1. Citizen cannot create road segment
    forbidden_resp = client.post(
        "/api/v1/roads",
        headers=auth_tokens["citizen"],
        json={
            "name": "Outer Ring Road - Sector 1",
            "start_latitude": 12.9200,
            "start_longitude": 77.6000,
            "end_latitude": 12.9400,
            "end_longitude": 77.6200,
            "road_type": "HIGHWAY",
            "importance": "CRITICAL"
        }
    )
    assert forbidden_resp.status_code == 403

    # 2. Authority creates road segment
    create_resp = client.post(
        "/api/v1/roads",
        headers=auth_tokens["authority"],
        json={
            "name": "Outer Ring Road - Sector 1",
            "start_latitude": 12.9200,
            "start_longitude": 77.6000,
            "end_latitude": 12.9400,
            "end_longitude": 77.6200,
            "road_type": "HIGHWAY",
            "importance": "CRITICAL",
            "speed_limit_kmh": 80
        }
    )
    assert create_resp.status_code == 201
    segment_data = create_resp.json()
    assert segment_data["name"] == "Outer Ring Road - Sector 1"
    assert segment_data["road_type"] == "HIGHWAY"
    assert segment_data["importance"] == "CRITICAL"
    assert segment_data["length_meters"] > 0.0
    assert segment_data["health_score"] == 100.0
    segment_id = segment_data["id"]

    # 3. List road segments
    list_resp = client.get("/api/v1/roads")
    assert list_resp.status_code == 200
    segments = list_resp.json()
    assert len(segments) >= 1
    assert any(s["id"] == segment_id for s in segments)


def test_automatic_road_segment_association(client, auth_tokens):
    """
    Phase 10: Tests automatic association of incoming report/issue to nearest road segment.
    """
    # 1. Create a road corridor
    create_resp = client.post(
        "/api/v1/roads",
        headers=auth_tokens["authority"],
        json={
            "name": "Hosur Main Road Corridor",
            "start_latitude": 12.9300,
            "start_longitude": 77.6100,
            "end_latitude": 12.9350,
            "end_longitude": 77.6150,
            "road_type": "ARTERIAL",
            "importance": "HIGH"
        }
    )
    assert create_resp.status_code == 201
    road_id = create_resp.json()["id"]

    # 2. Submit a report near the corridor midpoint (12.9325, 77.6125)
    rep_resp = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Pothole on Hosur Road",
            "description": "Hazard on arterial corridor",
            "severity": "HIGH",
            "latitude": 12.9325,
            "longitude": 77.6125,
            "address": "Hosur Main Road"
        }
    )
    assert rep_resp.status_code == 201
    rep_data = rep_resp.json()
    assert rep_data["road_segment_id"] == road_id
    issue_id = rep_data["issue_id"]
    assert issue_id is not None

    # 3. Query GET /api/v1/roads/{id} and verify active issues & health score update
    road_detail_resp = client.get(f"/api/v1/roads/{road_id}")
    assert road_detail_resp.status_code == 200
    road_detail = road_detail_resp.json()

    assert road_detail["active_issues_count"] >= 1
    assert road_detail["health_score"] < 100.0  # Degraded due to HIGH severity pothole
    assert len(road_detail["issues"]) >= 1

    # 4. Query GET /api/v1/roads/{id}/issues
    issues_resp = client.get(f"/api/v1/roads/{road_id}/issues")
    assert issues_resp.status_code == 200
    issues_list = issues_resp.json()
    assert len(issues_list) >= 1
    assert any(i["id"] == issue_id for i in issues_list)
