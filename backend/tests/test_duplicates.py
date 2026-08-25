import pytest
from app.models.report import ReportCategory, ReportSeverity
from app.services.duplicate_detector import (
    calculate_location_score,
    calculate_category_score,
    calculate_time_score,
    calculate_image_similarity,
    calculate_dhash
)


@pytest.fixture
def auth_headers(client):
    email = "dup_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Duplicate Tester",
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
    return {"Authorization": f"Bearer {token}"}


def test_scoring_utilities():
    """
    Unit test core scoring components of the duplicate detection engine.
    """
    # Location score: 10m -> 1.0; 50m -> 0.0; 25m -> intermediate
    assert calculate_location_score(10.0, 50.0) == 1.0
    assert calculate_location_score(50.0, 50.0) == 0.0
    assert 0.6 <= calculate_location_score(25.0, 50.0) <= 0.8

    # Category score
    assert calculate_category_score(ReportCategory.POTHOLE, ReportCategory.POTHOLE) == 1.0
    assert calculate_category_score(ReportCategory.POTHOLE, ReportCategory.ROAD_DAMAGE) == 0.6
    assert calculate_category_score(ReportCategory.POTHOLE, ReportCategory.BROKEN_STREETLIGHT) == 0.0

    # Image similarity: identical hashes
    sample_hash = 0b1010101010101010
    assert calculate_image_similarity(sample_hash, sample_hash) == 1.0
    assert calculate_image_similarity(None, sample_hash) is None


def test_duplicate_reports_merge_into_same_issue(client, auth_headers):
    """
    Tests that two reports for the same category submitted 12 meters apart
    are automatically merged into the same canonical Issue.
    """
    # Report 1: First citizen report
    resp1 = client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "Pothole near Bus Stop",
            "description": "Deep hole on the left lane",
            "severity": "MEDIUM",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "MG Road"
        },
        headers=auth_headers
    )
    assert resp1.status_code == 201
    report1 = resp1.json()
    assert report1["issue_id"] is not None
    issue_id = report1["issue_id"]

    # Report 2: Second citizen report ~11 meters away for same pothole
    resp2 = client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "Bad Pothole MG Road",
            "description": "Saw this today, dangerous for two-wheelers",
            "severity": "HIGH",
            "latitude": 12.9717,
            "longitude": 77.5946,
            "address": "MG Road"
        },
        headers=auth_headers
    )
    assert resp2.status_code == 201
    report2 = resp2.json()

    # Both reports must reference the exact same canonical issue ID
    assert report2["issue_id"] == issue_id

    # Verify Issue details endpoint reflects both contributing reports
    issue_resp = client.get(f"/api/v1/issues/{issue_id}", headers=auth_headers)
    assert issue_resp.status_code == 200
    issue_data = issue_resp.json()
    assert issue_data["report_count"] == 2
    assert len(issue_data["reports"]) == 2
    # Severity should have upgraded to HIGH
    assert issue_data["severity"] == "HIGH"


def test_distant_reports_create_distinct_issues(client, auth_headers):
    """
    Tests that reports > 50 meters apart create distinct issues.
    """
    # Report A: Point 1
    resp1 = client.post(
        "/api/v1/reports",
        json={
            "category": "GARBAGE",
            "title": "Dump Site A",
            "description": "Piles of trash",
            "severity": "LOW",
            "latitude": 13.0827,
            "longitude": 80.2707
        },
        headers=auth_headers
    )
    # Report B: Point 2 (~500 meters away)
    resp2 = client.post(
        "/api/v1/reports",
        json={
            "category": "GARBAGE",
            "title": "Dump Site B",
            "description": "Trash near bridge",
            "severity": "LOW",
            "latitude": 13.0877,
            "longitude": 80.2707
        },
        headers=auth_headers
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["issue_id"] != resp2.json()["issue_id"]


def test_different_category_same_location_creates_distinct_issues(client, auth_headers):
    """
    Tests that unrelated categories at the same coordinates create distinct issues
    (e.g., a broken streetlight does not merge with a pothole).
    """
    lat, lon = 22.5726, 88.3639

    resp_pothole = client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "Pothole at intersection",
            "description": "Road damage",
            "severity": "MEDIUM",
            "latitude": lat,
            "longitude": lon
        },
        headers=auth_headers
    )

    resp_light = client.post(
        "/api/v1/reports",
        json={
            "category": "BROKEN_STREETLIGHT",
            "title": "Dark Streetlight at intersection",
            "description": "Lamp not working",
            "severity": "LOW",
            "latitude": lat,
            "longitude": lon
        },
        headers=auth_headers
    )

    assert resp_pothole.status_code == 201
    assert resp_light.status_code == 201
    assert resp_pothole.json()["issue_id"] != resp_light.json()["issue_id"]


def test_multiple_sequential_reports_merge(client, auth_headers):
    """
    Tests that 4 citizens reporting the same problem within 15 meters sequentially
    merge into 1 canonical issue with report_count = 4.
    """
    base_lat, base_lon = 18.5204, 73.8567
    issue_id = None

    for i in range(4):
        resp = client.post(
            "/api/v1/reports",
            json={
                "category": "FLOODING",
                "title": f"Flooding Alert {i+1}",
                "description": "Water accumulation on road",
                "severity": "HIGH",
                "latitude": base_lat + (i * 0.00005),  # ~5.5 meters apart
                "longitude": base_lon
            },
            headers=auth_headers
        )
        assert resp.status_code == 201
        curr_issue = resp.json()["issue_id"]
        if issue_id is None:
            issue_id = curr_issue
        else:
            assert curr_issue == issue_id

    issue_resp = client.get(f"/api/v1/issues/{issue_id}", headers=auth_headers)
    assert issue_resp.status_code == 200
    assert issue_resp.json()["report_count"] == 4


def test_list_issues_endpoint(client, auth_headers):
    """
    Tests GET /api/v1/issues with pagination and category filtering.
    """
    # Seed a report to ensure an issue exists in this test session
    client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "Issue list test report",
            "description": "Test description",
            "severity": "LOW",
            "latitude": 10.0,
            "longitude": 10.0
        },
        headers=auth_headers
    )

    resp = client.get("/api/v1/issues?page=1&page_size=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "metadata" in data
    assert len(data["items"]) >= 1


def test_issue_reports_endpoint(client, auth_headers):
    """
    Tests GET /api/v1/issues/{id}/reports returns list of reports contributing to the issue.
    """
    # Create report
    resp = client.post(
        "/api/v1/reports",
        json={
            "category": "BLOCKED_ROAD",
            "title": "Tree fallen across lane",
            "description": "Large branch blocking right lane",
            "severity": "HIGH",
            "latitude": 13.0456,
            "longitude": 80.2100
        },
        headers=auth_headers
    )
    assert resp.status_code == 201
    report = resp.json()
    issue_id = report["issue_id"]

    # Get issue reports
    reports_resp = client.get(f"/api/v1/issues/{issue_id}/reports", headers=auth_headers)
    assert reports_resp.status_code == 200
    reports = reports_resp.json()
    assert isinstance(reports, list)
    assert len(reports) >= 1
    assert any(r["id"] == report["id"] for r in reports)


def test_report_duplicate_candidates_endpoint(client, auth_headers):
    """
    Tests GET /api/v1/reports/{id}/duplicate-candidates returns candidate matches and scores.
    """
    # Create report 1
    resp1 = client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "First Pothole Alert",
            "description": "Large pothole in road",
            "severity": "HIGH",
            "latitude": 12.9800,
            "longitude": 77.6000
        },
        headers=auth_headers
    )
    assert resp1.status_code == 201
    report1 = resp1.json()

    # Query duplicate candidates
    cand_resp = client.get(f"/api/v1/reports/{report1['id']}/duplicate-candidates", headers=auth_headers)
    assert cand_resp.status_code == 200
    cand_data = cand_resp.json()
    assert cand_data["report_id"] == report1["id"]
    assert "threshold" in cand_data
    assert "candidates" in cand_data
    assert isinstance(cand_data["candidates"], list)
    assert len(cand_data["candidates"]) >= 1
    first_cand = cand_data["candidates"][0]
    assert "duplicate_score" in first_cand
    assert "is_match" in first_cand
    assert "distance_meters" in first_cand


