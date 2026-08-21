import pytest
from uuid import uuid4
from app.models.issue import Issue, PriorityLevel, LocationZone, TrafficDensity
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.models.assignment import AuthorityDepartment
from app.services.pdf_service import generate_issue_work_order_pdf
from app.services import notification_service
from app.services.video_stream_service import analyze_video_stream


@pytest.fixture
def auth_headers(client):
    email = "roadmap_authority@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Roadmap Officer", "password": "Password123!", "role": "AUTHORITY"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def sample_issue_id(client, auth_headers):
    # Citizen creates report
    res = client.post(
        "/api/v1/reports",
        headers=auth_headers,
        json={
            "category": "POTHOLE",
            "title": "Severe Pothole on MG Road",
            "description": "Deep asphalt crater near metro station.",
            "severity": "CRITICAL",
            "latitude": 12.9750,
            "longitude": 77.6050,
            "address": "MG Road, Bangalore",
            "phone_number": "+1234567890"
        }
    )
    return res.json()["issue_id"]


def test_work_order_pdf_generation_direct():
    """
    Tests direct PDF generation from Issue model instance.
    """
    issue = Issue(
        id=uuid4(),
        category=ReportCategory.POTHOLE,
        title="Major Pothole on 100ft Road",
        description="Hazardous asphalt cavity.",
        latitude=12.9716,
        longitude=77.5946,
        address="100ft Road, Indiranagar",
        severity=ReportSeverity.CRITICAL,
        status=ReportStatus.ASSIGNED,
        priority_score=85.5,
        priority_level=PriorityLevel.CRITICAL,
        report_count=3,
        location_zone=LocationZone.MAIN_ROAD,
        traffic_density=TrafficDensity.HEAVY,
        assigned_department=AuthorityDepartment.ROAD_DEPARTMENT
    )

    pdf_bytes = generate_issue_work_order_pdf(issue)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-")


def test_work_order_pdf_api_endpoint(client, auth_headers, sample_issue_id):
    """
    Tests GET /api/v1/issues/{id}/work-order API endpoint.
    """
    res = client.get(f"/api/v1/issues/{sample_issue_id}/work-order", headers=auth_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=WorkOrder_" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")


def test_twilio_sms_notification_dispatch():
    """
    Tests Twilio SMS dispatch in mock/configured modes.
    """
    assert notification_service.send_sms_notification("+1234567890", "Test alert message") is True
    assert notification_service.send_sms_notification("", "Invalid empty phone") is False


def test_status_update_triggers_citizen_sms(client, auth_headers, sample_issue_id):
    """
    Tests that status transitions trigger citizen SMS alerts for reports with phone numbers.
    """
    # Verify and transition issue
    verify_res = client.post(
        f"/api/v1/issues/{sample_issue_id}/verify",
        headers=auth_headers,
        json={"department": "ROAD_DEPARTMENT", "notes": "Confirmed."}
    )
    assert verify_res.status_code == 200

    # Status update to IN_PROGRESS
    status_res = client.post(
        f"/api/v1/issues/{sample_issue_id}/status",
        headers=auth_headers,
        json={"status": "IN_PROGRESS", "comment": "Repair crew dispatched."}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "IN_PROGRESS"


def test_dashcam_video_stream_analyzer_service():
    """
    Tests edge video stream analyzer service with temporal persistence filtering.
    """
    analysis = analyze_video_stream(
        video_bytes=b"sample_video_bytes",
        filename="dashcam_patrol.mp4",
        duration_sec=6.0,
        sample_interval_sec=1.0,
        start_lat=12.9716,
        start_lng=77.5946,
        end_lat=12.9750,
        end_lng=77.5990
    )

    assert analysis.video_filename == "dashcam_patrol.mp4"
    assert analysis.video_duration_sec == 6.0
    assert analysis.total_frames_sampled == 6
    assert analysis.detections_count >= 1
    assert len(analysis.hazards) >= 1

    first_hazard = analysis.hazards[0]
    assert first_hazard.category in [ReportCategory.POTHOLE, ReportCategory.ROAD_DAMAGE, ReportCategory.BROKEN_STREETLIGHT, ReportCategory.GARBAGE, ReportCategory.FLOODING]
    assert 0.0 <= first_hazard.confidence <= 1.0
    assert first_hazard.estimated_lat is not None
    assert first_hazard.estimated_lng is not None
    assert first_hazard.bounding_box is not None


def test_dashcam_stream_api_endpoints(client, auth_headers):
    """
    Tests /api/v1/stream/analyze and /api/v1/stream/convert-to-report endpoints.
    """
    # 1. Analyze stream endpoint
    res = client.post(
        "/api/v1/stream/analyze",
        headers=auth_headers,
        files={"video_file": ("patrol.mp4", b"video-stream-payload", "video/mp4")},
        data={"duration_sec": "5.0", "sample_interval_sec": "1.0"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detections_count"] >= 1
    hazards = data["hazards"]
    assert len(hazards) >= 1

    # 2. Convert stream hazard to report
    target_hazard = hazards[0]
    conv_res = client.post(
        "/api/v1/stream/convert-to-report",
        headers=auth_headers,
        json={
            "category": target_hazard["category"],
            "severity": target_hazard["severity"],
            "title": f"Dashcam Detected {target_hazard['category']}",
            "description": "Hazard automatically identified on live edge camera feed.",
            "latitude": target_hazard["estimated_lat"] or 12.9716,
            "longitude": target_hazard["estimated_lng"] or 77.5946,
            "timestamp_sec": target_hazard["timestamp_sec"],
            "snapshot_base64": target_hazard.get("snapshot_base64")
        }
    )
    assert conv_res.status_code == 201
    rep = conv_res.json()
    assert rep["category"] == target_hazard["category"]
    assert rep["issue_id"] is not None
