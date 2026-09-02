import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.models.road_segment import RoadSegment, RoadType, RoadImportance
from app.models.issue import Issue, PriorityLevel
from app.models.report import RoadReport, ReportCategory, ReportSeverity, ReportStatus
from app.services.road_health_service import (
    calculate_detailed_road_health,
    compute_health_status_and_risk,
)


@pytest.fixture
def auth_tokens(client):
    # Citizen
    c_email = f"citizen_health_{uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": c_email, "full_name": "Health Citizen", "password": "password123", "role": "CITIZEN"}
    )
    c_token = client.post("/api/v1/auth/login", json={"email": c_email, "password": "password123"}).json()["access_token"]

    # Authority
    a_email = f"auth_health_{uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": a_email, "full_name": "Health Authority", "password": "password123", "role": "AUTHORITY"}
    )
    a_token = client.post("/api/v1/auth/login", json={"email": a_email, "password": "password123"}).json()["access_token"]

    return {
        "citizen": {"Authorization": f"Bearer {c_token}"},
        "authority": {"Authorization": f"Bearer {a_token}"}
    }


def test_health_scoring_pristine_segment():
    """
    Tests that a road segment with 0 active issues and 0 reports receives a pristine 100 score.
    """
    seg = RoadSegment(
        id=uuid4(),
        name="Pristine Boulevard",
        start_latitude=12.90,
        start_longitude=77.50,
        end_latitude=12.91,
        end_longitude=77.51,
        road_type=RoadType.ARTERIAL,
        importance=RoadImportance.MEDIUM,
        length_meters=1200.0,
    )
    score, status, risk, breakdown, metrics = calculate_detailed_road_health(seg, [], [])
    assert score == 100.0
    assert status == "EXCELLENT"
    assert risk == "LOW"
    assert metrics.active_issues_count == 0
    assert breakdown.active_issue_penalty == 0.0
    assert breakdown.severity_penalty == 0.0


def test_health_scoring_critical_degradation():
    """
    Tests that multiple critical active issues and high report volume degrade health to CRITICAL.
    """
    seg = RoadSegment(
        id=uuid4(),
        name="Heavily Damaged Highway",
        start_latitude=12.90,
        start_longitude=77.50,
        end_latitude=12.91,
        end_longitude=77.51,
        road_type=RoadType.HIGHWAY,
        importance=RoadImportance.CRITICAL,
        length_meters=800.0,
    )

    now = datetime.now(timezone.utc)
    issues = [
        Issue(
            id=uuid4(),
            title=f"Critical Crater {i}",
            category=ReportCategory.POTHOLE,
            severity=ReportSeverity.CRITICAL,
            status=ReportStatus.IN_PROGRESS,
            report_count=5,
            latitude=12.905,
            longitude=77.505,
            created_at=now - timedelta(days=2),
            updated_at=now,
        )
        for i in range(5)
    ]

    reports = [
        RoadReport(
            id=uuid4(),
            title=f"Citizen Report {i}",
            category=ReportCategory.POTHOLE,
            severity=ReportSeverity.CRITICAL,
            status=ReportStatus.REPORTED,
            latitude=12.905,
            longitude=77.505,
            created_at=now - timedelta(days=1),
        )
        for i in range(15)
    ]

    score, status, risk, breakdown, metrics = calculate_detailed_road_health(seg, issues, reports)
    assert score < 30.0
    assert status == "CRITICAL"
    assert risk == "SEVERE"
    assert metrics.active_issues_count == 5
    assert metrics.critical_issues_count == 5
    assert breakdown.severity_penalty > 50.0
    assert breakdown.recent_incidents_penalty > 50.0


def test_get_road_segment_health_api(client, auth_tokens):
    """
    Tests GET /api/v1/roads/{id}/health endpoint.
    """
    # 1. Create road segment
    create_resp = client.post(
        "/api/v1/roads",
        headers=auth_tokens["authority"],
        json={
            "name": "Health Test Corridor",
            "start_latitude": 12.9500,
            "start_longitude": 77.6500,
            "end_latitude": 12.9550,
            "end_longitude": 77.6550,
            "road_type": "ARTERIAL",
            "importance": "HIGH",
        }
    )
    assert create_resp.status_code == 201
    road_id = create_resp.json()["id"]

    # 2. Query health endpoint initially (should be 100)
    health_resp = client.get(f"/api/v1/roads/{road_id}/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()
    assert h_data["road_id"] == road_id
    assert h_data["health_score"] == 100.0
    assert h_data["health_status"] == "EXCELLENT"
    assert "factors" in h_data
    assert "metrics" in h_data
    assert "disclaimer" in h_data
    assert "not an official government road rating" in h_data["disclaimer"]

    # 3. Submit report to create an issue
    rep_resp = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Severe Crater on Test Corridor",
            "description": "Large hole causing tire damage",
            "severity": "HIGH",
            "latitude": 12.9525,
            "longitude": 77.6525,
            "address": "Health Test Corridor Midpoint"
        }
    )
    assert rep_resp.status_code == 201

    # 4. Query health again - health score should be reduced
    updated_health_resp = client.get(f"/api/v1/roads/{road_id}/health")
    assert updated_health_resp.status_code == 200
    updated_data = updated_health_resp.json()
    assert updated_data["health_score"] < 100.0
    assert updated_data["active_issues_count"] >= 1
    assert updated_data["factors"]["active_issue_penalty"] > 0.0


def test_get_city_wide_road_health_analytics_api(client, auth_tokens):
    """
    Tests GET /api/v1/analytics/road-health endpoint.
    """
    # 0. Create a road segment to guarantee presence in db
    client.post(
        "/api/v1/roads",
        headers=auth_tokens["authority"],
        json={
            "name": "City Analytics Test Segment",
            "start_latitude": 12.9100,
            "start_longitude": 77.6100,
            "end_latitude": 12.9150,
            "end_longitude": 77.6150,
            "road_type": "ARTERIAL",
            "importance": "MEDIUM",
        }
    )

    # 1. Citizen forbidden
    cit_resp = client.get("/api/v1/analytics/road-health", headers=auth_tokens["citizen"])
    assert cit_resp.status_code == 403

    # 2. Authority success
    auth_resp = client.get("/api/v1/analytics/road-health", headers=auth_tokens["authority"])
    assert auth_resp.status_code == 200
    data = auth_resp.json()

    assert "summary" in data
    assert "worst_roads" in data
    assert "best_roads" in data
    assert "health_distribution" in data
    assert "health_trends" in data
    assert "disclaimer" in data

    assert data["summary"]["total_monitored_segments"] >= 1
    assert len(data["health_distribution"]) == 5
    assert len(data["health_trends"]) >= 1



def test_nonexistent_road_health_returns_404(client):
    """
    Tests that querying health for a non-existent UUID returns 404.
    """
    random_id = uuid4()
    resp = client.get(f"/api/v1/roads/{random_id}/health")
    assert resp.status_code == 404
