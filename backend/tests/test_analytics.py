import pytest
from datetime import datetime, timezone, timedelta
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.models.assignment import AuthorityDepartment
from app.models.issue import Issue, PriorityLevel
from app.models.history import IssueStatusHistory


@pytest.fixture
def citizen_token(client):
    email = "analytic_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Analytics Citizen", "password": "password123", "role": "CITIZEN"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def authority_token(client):
    email = "analytic_authority@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Road Authority Officer", "password": "password123", "role": "AUTHORITY"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin_token(client):
    email = "analytic_admin@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "System Administrator", "password": "password123", "role": "ADMIN"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def populate_test_dataset(client, citizen_token, authority_token):
    """
    Creates a varied dataset of reports/issues for testing analytics.
    """
    items = [
        {"cat": "POTHOLE", "sev": "CRITICAL", "lat": 12.9716, "lng": 77.5946, "addr": "MG Road", "title": "Large crater pothole"},
        {"cat": "BROKEN_STREETLIGHT", "sev": "LOW", "lat": 12.9720, "lng": 77.5950, "addr": "Brigade Road", "title": "Dark street lamp"},
        {"cat": "FLOODING", "sev": "HIGH", "lat": 12.9352, "lng": 77.6245, "addr": "Koramangala 80ft Road", "title": "Severe waterlogging"},
        {"cat": "ROAD_DAMAGE", "sev": "MEDIUM", "lat": 12.9360, "lng": 77.6250, "addr": "Koramangala 4th Block", "title": "Asphalt peeling"},
        {"cat": "GARBAGE", "sev": "MEDIUM", "lat": 13.0358, "lng": 77.5970, "addr": "Hebbal Flyover", "title": "Debris pile blocking lane"},
    ]

    issue_ids = []
    for item in items:
        res = client.post(
            "/api/v1/reports",
            headers=citizen_token,
            json={
                "category": item["cat"],
                "title": item["title"],
                "description": f"Detailed description for {item['title']}",
                "severity": item["sev"],
                "latitude": item["lat"],
                "longitude": item["lng"],
                "address": item["addr"]
            }
        )
        assert res.status_code == 201
        issue_ids.append(res.json()["issue_id"])

    # Progress one issue to VERIFIED -> ASSIGNED -> IN_PROGRESS -> FIXED
    if issue_ids:
        client.post(
            f"/api/v1/issues/{issue_ids[0]}/verify",
            headers=authority_token,
            json={"department": "ROAD_DEPARTMENT", "notes": "Verified critical pothole"}
        )
        client.post(
            f"/api/v1/issues/{issue_ids[0]}/assign",
            headers=authority_token,
            json={"department": "ROAD_DEPARTMENT", "notes": "Assigned to road repair team"}
        )
        client.post(
            f"/api/v1/issues/{issue_ids[0]}/status",
            headers=authority_token,
            json={"status": "IN_PROGRESS", "comment": "Asphalt team dispatched"}
        )
        client.post(
            f"/api/v1/issues/{issue_ids[0]}/status",
            headers=authority_token,
            json={"status": "FIXED", "comment": "Patch completed successfully"}
        )

    # Progress second issue to CLOSED (VERIFIED -> ASSIGNED -> IN_PROGRESS -> FIXED -> CLOSED)
    if len(issue_ids) > 1:
        client.post(
            f"/api/v1/issues/{issue_ids[1]}/verify",
            headers=authority_token,
            json={"department": "ELECTRICAL_DEPARTMENT"}
        )
        client.post(
            f"/api/v1/issues/{issue_ids[1]}/assign",
            headers=authority_token,
            json={"department": "ELECTRICAL_DEPARTMENT", "notes": "Assigned to electric crew"}
        )
        client.post(
            f"/api/v1/issues/{issue_ids[1]}/status",
            headers=authority_token,
            json={"status": "IN_PROGRESS"}
        )
        client.post(
            f"/api/v1/issues/{issue_ids[1]}/status",
            headers=authority_token,
            json={"status": "FIXED"}
        )
        client.post(
            f"/api/v1/issues/{issue_ids[1]}/status",
            headers=authority_token,
            json={"status": "CLOSED", "comment": "Confirmed repaired and closed"}
        )

    return issue_ids


def test_analytics_permission_controls(client, citizen_token, authority_token, admin_token):
    # Unauthenticated should fail with 403 (HTTPBearer without credentials) or 401
    res_unauth = client.get("/api/v1/analytics/summary")
    assert res_unauth.status_code in [401, 403]

    # Citizen role should be forbidden 403
    res_citizen = client.get("/api/v1/analytics/summary", headers=citizen_token)
    assert res_citizen.status_code == 403

    # Authority should succeed 200
    res_auth = client.get("/api/v1/analytics/summary", headers=authority_token)
    assert res_auth.status_code == 200

    # Admin should succeed 200
    res_admin = client.get("/api/v1/analytics/summary", headers=admin_token)
    assert res_admin.status_code == 200


def test_analytics_summary_kpis(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    res = client.get("/api/v1/analytics/summary", headers=authority_token)
    assert res.status_code == 200
    data = res.json()

    assert data["total_reports"] >= 5
    assert data["total_issues"] >= 5
    assert data["fixed_issues"] >= 1
    assert data["closed_issues"] >= 1
    assert "active_issues" in data
    assert "critical_issues" in data
    assert "high_priority_issues" in data
    assert "awaiting_verification" in data
    assert "in_progress_issues" in data


def test_analytics_category_breakdown(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    res = client.get("/api/v1/analytics/categories", headers=authority_token)
    assert res.status_code == 200
    data = res.json()

    assert data["total"] >= 5
    assert len(data["categories"]) > 0
    categories = {c["category"]: c["count"] for c in data["categories"]}
    assert categories.get("POTHOLE", 0) >= 1
    assert categories.get("FLOODING", 0) >= 1


def test_analytics_severity_breakdown(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    res = client.get("/api/v1/analytics/severity", headers=authority_token)
    assert res.status_code == 200
    data = res.json()

    assert data["total"] >= 5
    severities = {s["severity"]: s["count"] for s in data["severities"]}
    assert severities.get("CRITICAL", 0) >= 1
    assert severities.get("HIGH", 0) >= 1


def test_analytics_status_breakdown(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    res = client.get("/api/v1/analytics/status", headers=authority_token)
    assert res.status_code == 200
    data = res.json()

    assert data["total"] >= 5
    statuses = {s["status"]: s["count"] for s in data["statuses"]}
    assert statuses.get("FIXED", 0) >= 1
    assert statuses.get("CLOSED", 0) >= 1


def test_analytics_resolution_durations(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    res = client.get("/api/v1/analytics/resolution", headers=authority_token)
    assert res.status_code == 200
    data = res.json()

    assert data["total_fixed"] >= 1
    assert data["total_closed"] >= 1
    assert data["avg_hours_reported_to_fixed"] is not None
    assert data["avg_days_reported_to_fixed"] is not None
    assert "by_category" in data
    assert "by_severity" in data


def test_analytics_geographic_density(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    res = client.get("/api/v1/analytics/geographic?grid_size=0.05", headers=authority_token)
    assert res.status_code == 200
    data = res.json()

    assert data["total_clusters"] > 0
    assert len(data["clusters"]) > 0
    first_cluster = data["clusters"][0]
    assert "latitude" in first_cluster
    assert "longitude" in first_cluster
    assert "density_level" in first_cluster
    assert first_cluster["density_level"] in ["HIGH", "MEDIUM", "LOW"]


def test_analytics_trend_data(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    for interval in ["day", "week", "month"]:
        res = client.get(f"/api/v1/analytics/trends?interval={interval}", headers=authority_token)
        assert res.status_code == 200
        data = res.json()
        assert data["interval"] == interval
        assert len(data["data"]) > 0
        point = data["data"][0]
        assert "period" in point
        assert "count" in point
        assert "critical_count" in point
        assert "resolved_count" in point


def test_analytics_heatmap_coordinates(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    res = client.get("/api/v1/analytics/heatmap", headers=authority_token)
    assert res.status_code == 200
    data = res.json()

    assert data["total_points"] >= 5
    assert len(data["points"]) >= 5
    first_point = data["points"][0]
    assert "latitude" in first_point
    assert "longitude" in first_point
    assert 0.0 <= first_point["intensity"] <= 1.0
    assert "category" in first_point
    assert "severity" in first_point


def test_issue_search_and_filter(client, citizen_token, authority_token):
    populate_test_dataset(client, citizen_token, authority_token)

    # Search keyword
    res = client.get("/api/v1/issues?search=crater", headers=authority_token)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    assert "crater" in items[0]["title"].lower()

    # Search address
    res = client.get("/api/v1/issues?search=Koramangala", headers=authority_token)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 2
    for itm in items:
        assert "koramangala" in itm["address"].lower()

    # Multi-factor filter
    res = client.get("/api/v1/issues?category=POTHOLE&severity=CRITICAL", headers=authority_token)
    assert res.status_code == 200
    items = res.json()["items"]
    for itm in items:
        assert itm["category"] == "POTHOLE"
        assert itm["severity"] == "CRITICAL"
