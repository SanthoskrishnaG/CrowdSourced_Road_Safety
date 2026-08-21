import io
import pytest
from uuid import uuid4
from PIL import Image

from app.models.issue import Issue, PriorityLevel, LocationZone, TrafficDensity
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.utils.image import assess_image_quality
from app.services.nlp_service import calculate_text_similarity, extract_hazard_urgency
from app.services.road_health_service import calculate_road_health_score, predict_accident_risk
from app.services.sla_service import calculate_sla_info


@pytest.fixture
def auth_headers(client):
    email = "intel_officer@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Intelligence Lead", "password": "Password123!", "role": "AUTHORITY"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_image_quality_assessment():
    """
    Tests computer vision image quality metrics: blur, brightness, and contrast.
    """
    # 1. Generate clean test image
    img = Image.new("RGB", (200, 200), color=(128, 128, 128))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    quality = assess_image_quality(img_byte_arr.getvalue())

    assert "blur_score" in quality
    assert "brightness" in quality
    assert "contrast" in quality
    assert "quality_label" in quality
    assert quality["is_acceptable_quality"] is not None

    # 2. Pitch black image -> POOR_DARK
    dark_img = Image.new("RGB", (200, 200), color=(5, 5, 5))
    dark_bytes = io.BytesIO()
    dark_img.save(dark_bytes, format='JPEG')
    dark_quality = assess_image_quality(dark_bytes.getvalue())
    assert dark_quality["quality_label"] == "POOR_DARK"
    assert dark_quality["is_acceptable_quality"] is False


def test_nlp_semantic_text_similarity():
    """
    Tests NLP semantic text similarity and urgency keyword extraction.
    """
    t1 = "Massive deep pothole on MG Road near the metro station."
    t2 = "Large deep pothole on MG road in front of metro station."
    t3 = "Broken streetlight on residential side alley."

    sim_high = calculate_text_similarity(t1, t2)
    sim_low = calculate_text_similarity(t1, t3)

    assert sim_high > 0.60
    assert sim_low < 0.25

    # Urgency extraction
    urgency_text = "Dangerous collapsed sinkhole caused car crash near school hospital."
    urgency = extract_hazard_urgency(urgency_text)
    assert urgency["urgency_multiplier"] > 1.20
    assert urgency["has_critical_language"] is True
    assert "accident" in urgency["flagged_keywords"] or "crash" in urgency["flagged_keywords"] or "sinkhole" in urgency["flagged_keywords"]


def test_road_health_score_and_risk_model(db_session):
    """
    Tests Road Health Index (0-100) and Predictive Accident Risk Model.
    """
    lat, lng = 12.9716, 77.5946

    # Create dummy critical issue
    issue = Issue(
        id=uuid4(),
        category=ReportCategory.POTHOLE,
        title="Severe Pothole Cluster",
        latitude=lat,
        longitude=lng,
        severity=ReportSeverity.CRITICAL,
        status=ReportStatus.VERIFIED,
        priority_score=88.0,
        priority_level=PriorityLevel.CRITICAL,
        traffic_density=TrafficDensity.HEAVY,
        location_zone=LocationZone.SCHOOL,
        report_count=4
    )
    db_session.add(issue)
    db_session.commit()

    # Calculate Road Health
    health = calculate_road_health_score(lat, lng, db_session, radius_meters=500.0)
    assert 0.0 <= health.health_score <= 100.0
    assert health.active_hazards_count >= 1

    # Predict Accident Risk
    risk = predict_accident_risk(issue, health.health_score, has_critical_language=True)
    assert 0.0 <= risk.risk_probability <= 1.0
    assert risk.risk_level in ["HIGH", "SEVERE"]
    assert risk.pedestrian_risk_flag is True
    assert len(risk.primary_risk_factors) >= 3


def test_sla_tracking_and_escalation():
    """
    Tests resolution SLA deadline calculations and automated escalation flags.
    """
    issue_crit = Issue(
        id=uuid4(),
        category=ReportCategory.POTHOLE,
        title="Critical Hazard",
        latitude=12.97,
        longitude=77.59,
        severity=ReportSeverity.CRITICAL,
        status=ReportStatus.IN_PROGRESS,
        priority_score=90.0,
        priority_level=PriorityLevel.CRITICAL
    )

    sla_crit = calculate_sla_info(issue_crit)
    assert sla_crit.sla_target_hours == 24
    assert sla_crit.sla_status in ["ON_TRACK", "APPROACHING_BREACH", "BREACHED"]

    # Reopened issue must be escalated
    issue_reopened = Issue(
        id=uuid4(),
        category=ReportCategory.ROAD_DAMAGE,
        title="Disputed Pothole",
        latitude=12.97,
        longitude=77.59,
        severity=ReportSeverity.HIGH,
        status=ReportStatus.REOPENED,
        priority_score=75.0,
        priority_level=PriorityLevel.HIGH
    )
    sla_reopened = calculate_sla_info(issue_reopened)
    assert sla_reopened.is_escalated is True
    assert sla_reopened.sla_target_hours == 24


def test_citizen_reverification_workflow_lifecycle(client, auth_headers):
    """
    Tests the complete citizen re-verification pipeline:
    REPORTED -> VERIFIED -> IN_PROGRESS -> FIXED -> CITIZEN DISPUTED (REOPENED) -> FIXED -> CITIZEN CONFIRMED (CLOSED).
    """
    # 1. Create Report
    rep_res = client.post(
        "/api/v1/reports",
        headers=auth_headers,
        json={
            "category": "POTHOLE",
            "title": "Hazard on 100ft Road",
            "description": "Deep crater near market.",
            "severity": "HIGH",
            "latitude": 12.9780,
            "longitude": 77.6020,
            "phone_number": "+1234567890"
        }
    )
    issue_id = rep_res.json()["issue_id"]

    # 2. Authority Verifies and Sets to IN_PROGRESS then FIXED
    client.post(f"/api/v1/issues/{issue_id}/verify", headers=auth_headers, json={"department": "ROAD_DEPARTMENT"})
    client.post(f"/api/v1/issues/{issue_id}/status", headers=auth_headers, json={"status": "IN_PROGRESS"})
    client.post(f"/api/v1/issues/{issue_id}/status", headers=auth_headers, json={"status": "FIXED"})

    # 3. Citizen Disputes Repair -> REOPENED
    reopen_res = client.post(
        f"/api/v1/issues/{issue_id}/citizen-verify",
        headers=auth_headers,
        json={"verified": False, "feedback": "Asphalt patch washed away, pothole is open again.", "rating": 1}
    )
    assert reopen_res.status_code == 200
    issue_data = reopen_res.json()
    assert issue_data["status"] == "REOPENED"
    assert issue_data["sla"]["is_escalated"] is True
    assert issue_data["priority_score"] >= 70.0

    # 4. Repair Crew Fixes again
    client.post(f"/api/v1/issues/{issue_id}/status", headers=auth_headers, json={"status": "IN_PROGRESS"})
    client.post(f"/api/v1/issues/{issue_id}/status", headers=auth_headers, json={"status": "FIXED"})

    # 5. Citizen Confirms Resolution -> CLOSED
    close_res = client.post(
        f"/api/v1/issues/{issue_id}/citizen-verify",
        headers=auth_headers,
        json={"verified": True, "feedback": "Clean solid patch now. Good work!", "rating": 5}
    )
    assert close_res.status_code == 200
    final_data = close_res.json()
    assert final_data["status"] == "CLOSED"
    assert final_data["sla"]["sla_status"] == "RESOLVED"
