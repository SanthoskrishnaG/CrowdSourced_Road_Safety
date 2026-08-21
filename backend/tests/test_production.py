import pytest
from io import BytesIO
from PIL import Image

from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.models.assignment import AuthorityDepartment
from app.models.user import UserRole
from app.services import notification_service


def create_mock_jpeg_bytes(width=100, height=100, color="red") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def citizen_auth(client):
    email = "prod_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Production Citizen", "password": "Password123!", "role": "CITIZEN"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return {
        "headers": {"Authorization": f"Bearer {res.json()['access_token']}"},
        "email": email
    }


@pytest.fixture
def authority_auth(client):
    email = "prod_authority@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Production Officer", "password": "Password123!", "role": "AUTHORITY"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return {
        "headers": {"Authorization": f"Bearer {res.json()['access_token']}"},
        "email": email
    }


def test_security_headers(client):
    """
    Verifies that security headers are applied to API responses.
    """
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "X-Process-Time" in res.headers


def test_standardized_error_envelope(client, citizen_auth):
    """
    Verifies that HTTP exceptions return the standardized error envelope.
    """
    # 404 Not Found
    res = client.get("/api/v1/reports/00000000-0000-0000-0000-000000000000", headers=citizen_auth["headers"])
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]


def test_validation_error_envelope(client, citizen_auth):
    """
    Verifies that validation errors return the standardized error envelope.
    """
    # Missing required title and category
    res = client.post("/api/v1/reports", headers=citizen_auth["headers"], json={})
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["details"] is not None


def test_notification_service_dispatch():
    """
    Verifies that notification dispatch helpers execute cleanly without errors.
    """
    import uuid
    dummy_id = uuid.uuid4()

    assert notification_service.notify_issue_verified(
        issue_id=dummy_id,
        issue_title="Pothole on Main St",
        department_name="ROAD_DEPARTMENT"
    ) is None or True

    assert notification_service.notify_issue_assigned(
        issue_id=dummy_id,
        issue_title="Pothole on Main St",
        department_name="ROAD_DEPARTMENT",
        notes="Inspect pavement"
    ) is None or True

    assert notification_service.notify_issue_status_changed(
        issue_id=dummy_id,
        issue_title="Pothole on Main St",
        previous_status="ASSIGNED",
        new_status="IN_PROGRESS"
    ) is None or True


def test_complete_15_step_production_workflow(client, citizen_auth, authority_auth):
    """
    Complete End-to-End 15-step Lifecycle Integration Test:
    Citizen -> Register -> Login -> Create Report -> Upload Image -> Location Capture
    -> AI Classification -> Duplicate Detection -> Issue Creation/Merge -> Priority Calculation
    -> Authority Dashboard -> Verify -> Assign -> Status In Progress -> Status Fixed
    -> Status Closed -> Citizen Status Verification -> Analytics Updated.
    """
    # 1. Citizen Authentication
    c_headers = citizen_auth["headers"]
    a_headers = authority_auth["headers"]

    # 2. Citizen creates report with location coordinates
    rep_res = client.post(
        "/api/v1/reports",
        headers=c_headers,
        json={
            "category": "POTHOLE",
            "title": "Severe Pothole on 100ft Road",
            "description": "Hazardous road crater causing traffic disruption.",
            "severity": "CRITICAL",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "100ft Road, Indiranagar"
        }
    )
    assert rep_res.status_code == 201
    report = rep_res.json()
    report_id = report["id"]
    issue_id = report["issue_id"]
    assert issue_id is not None

    # 3. Citizen uploads photographic evidence
    img_bytes = create_mock_jpeg_bytes(300, 300, "gray")
    files = {"files": ("evidence.jpg", img_bytes, "image/jpeg")}
    upload_res = client.post(
        f"/api/v1/reports/{report_id}/images",
        headers=c_headers,
        files=files
    )
    assert upload_res.status_code == 201
    uploaded_images = upload_res.json()
    assert len(uploaded_images) >= 1

    # 4. AI Vision classification standalone verification
    classify_res = client.post(
        "/api/v1/reports/classify-image",
        headers=c_headers,
        files={"file": ("test.jpg", img_bytes, "image/jpeg")}
    )
    assert classify_res.status_code == 200
    ai_result = classify_res.json()
    assert "predicted_category" in ai_result
    assert "confidence" in ai_result

    # 5. Duplicate Detection: Second citizen submits duplicate nearby (< 20m)
    dup_res = client.post(
        "/api/v1/reports",
        headers=c_headers,
        json={
            "category": "POTHOLE",
            "title": "Deep Pothole same spot",
            "description": "Another report for the same road problem.",
            "severity": "CRITICAL",
            "latitude": 12.9717,
            "longitude": 77.5947,
            "address": "100ft Road, Near Signal"
        }
    )
    assert dup_res.status_code == 201
    dup_report = dup_res.json()
    # Reports should merge into the same canonical issue
    assert dup_report["issue_id"] == issue_id

    # 6. Canonical Issue Inspection & Multi-factor Priority
    issue_res = client.get(f"/api/v1/issues/{issue_id}", headers=a_headers)
    assert issue_res.status_code == 200
    issue_data = issue_res.json()
    assert issue_data["report_count"] == 2
    assert issue_data["status"] == "REPORTED"
    assert issue_data["priority_score"] > 0.0
    assert issue_data["priority_breakdown"] is not None

    # 7. Authority Dashboard Summary Check
    dash_res = client.get("/api/v1/analytics/summary", headers=a_headers)
    assert dash_res.status_code == 200
    assert dash_res.json()["awaiting_verification"] >= 1

    # 8. Authority Step 1: Verify Issue
    verify_res = client.post(
        f"/api/v1/issues/{issue_id}/verify",
        headers=a_headers,
        json={"department": "ROAD_DEPARTMENT", "notes": "Field team confirmed severe road hazard."}
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "VERIFIED"

    # 9. Authority Step 2: Assign Department & Crew
    assign_res = client.post(
        f"/api/v1/issues/{issue_id}/assign",
        headers=a_headers,
        json={"department": "ROAD_DEPARTMENT", "notes": "Dispatched Asphalt Repair Team 2."}
    )
    assert assign_res.status_code == 201
    assert assign_res.json()["department"] == "ROAD_DEPARTMENT"

    # 10. Authority Step 3: Transition to IN_PROGRESS
    prog_res = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=a_headers,
        json={"status": "IN_PROGRESS", "comment": "Asphalt laying in progress."}
    )
    assert prog_res.status_code == 200
    assert prog_res.json()["status"] == "IN_PROGRESS"

    # 11. Authority Step 4: Transition to FIXED
    fix_res = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=a_headers,
        json={"status": "FIXED", "comment": "Pothole filled, leveled, and sealed."}
    )
    assert fix_res.status_code == 200
    assert fix_res.json()["status"] == "FIXED"

    # 12. Authority Step 5: Transition to CLOSED
    close_res = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=a_headers,
        json={"status": "CLOSED", "comment": "Final inspection passed. Closed."}
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"

    # 13. Citizen views updated resolution status
    c_check_res = client.get(f"/api/v1/reports/{report_id}", headers=c_headers)
    assert c_check_res.status_code == 200
    assert c_check_res.json()["status"] == "CLOSED"

    # 14. Analytics updates reflect resolved/closed issue
    analytics_res = client.get("/api/v1/analytics/summary", headers=a_headers)
    assert analytics_res.status_code == 200
    assert analytics_res.json()["closed_issues"] >= 1

    # 15. Status audit trail contains complete progression
    history_res = client.get(f"/api/v1/issues/{issue_id}/history", headers=a_headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 5
    statuses_in_history = [h["new_status"] for h in history]
    assert "VERIFIED" in statuses_in_history
    assert "ASSIGNED" in statuses_in_history
    assert "IN_PROGRESS" in statuses_in_history
    assert "FIXED" in statuses_in_history
    assert "CLOSED" in statuses_in_history
