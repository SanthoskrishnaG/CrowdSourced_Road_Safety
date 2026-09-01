import io
import pytest
from PIL import Image
from ml.datasets.dataset import generate_synthetic_hazard_image


@pytest.fixture
def auth_tokens(client):
    # Citizen
    c_email = "ai_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": c_email, "full_name": "AI Citizen", "password": "password123", "role": "CITIZEN"}
    )
    c_token = client.post("/api/v1/auth/login", json={"email": c_email, "password": "password123"}).json()["access_token"]

    # Authority
    a_email = "ai_auth@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": a_email, "full_name": "AI Officer", "password": "password123", "role": "AUTHORITY"}
    )
    a_token = client.post("/api/v1/auth/login", json={"email": a_email, "password": "password123"}).json()["access_token"]

    return {
        "citizen": {"Authorization": f"Bearer {c_token}"},
        "authority": {"Authorization": f"Bearer {a_token}"}
    }


def create_image_bytes(category="POTHOLE") -> bytes:
    img = generate_synthetic_hazard_image(category, width=300, height=300)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_get_ai_analysis_endpoint(client, auth_tokens):
    """
    Phase 8: Tests GET /api/v1/reports/{id}/ai-analysis
    Verifies citizen values, AI category & severity estimations with confidences,
    image quality diagnostics, and override tracking.
    """
    # 1. Create Report
    rep_resp = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Large pothole on highway",
            "description": "Deep depression in asphalt near crossroad",
            "severity": "HIGH",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
    )
    assert rep_resp.status_code == 201
    report_id = rep_resp.json()["id"]

    # 2. Upload image
    img_bytes = create_image_bytes("POTHOLE")
    files = [("files", ("hazard.jpg", img_bytes, "image/jpeg"))]
    upload_resp = client.post(
        f"/api/v1/reports/{report_id}/images",
        headers=auth_tokens["citizen"],
        files=files
    )
    assert upload_resp.status_code == 201

    # 3. Call GET /api/v1/reports/{id}/ai-analysis
    ai_resp = client.get(
        f"/api/v1/reports/{report_id}/ai-analysis",
        headers=auth_tokens["citizen"]
    )
    assert ai_resp.status_code == 200
    ai_data = ai_resp.json()

    assert ai_data["report_id"] == report_id
    assert ai_data["citizen_category"] == "POTHOLE"
    assert ai_data["citizen_severity"] == "HIGH"
    assert ai_data["ai_category"] == "POTHOLE"
    assert ai_data["ai_severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert 0.0 <= ai_data["primary_category_confidence"] <= 1.0
    assert 0.0 <= ai_data["primary_severity_confidence"] <= 1.0
    assert 0.0 <= ai_data["average_quality_score"] <= 100.0
    assert ai_data["images_analyzed"] == 1
    assert len(ai_data["images"]) == 1

    img_detail = ai_data["images"][0]
    assert img_detail["quality_diagnostics"]["quality_score"] >= 0.0
    assert "blur_score" in img_detail["quality_diagnostics"]


def test_ai_analysis_human_override_workflow(client, auth_tokens):
    """
    Phase 8: Tests authority overriding AI predictions and verifying audit tracking in AI analysis.
    """
    # 1. Create Report and Upload Image
    rep_resp = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Road depression",
            "description": "Needs review",
            "severity": "LOW",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
    )
    report_id = rep_resp.json()["id"]

    img_bytes = create_image_bytes("ROAD_DAMAGE")
    up_resp = client.post(
        f"/api/v1/reports/{report_id}/images",
        headers=auth_tokens["citizen"],
        files=[("files", ("damage.jpg", img_bytes, "image/jpeg"))]
    )
    image_id = up_resp.json()[0]["id"]

    # 2. Authority overrides Category and Severity
    override_resp = client.post(
        f"/api/v1/reports/{report_id}/images/{image_id}/verify",
        headers=auth_tokens["authority"],
        json={
            "verified_category": "ROAD_DAMAGE",
            "verified_severity": "CRITICAL",
            "notes": "Field inspection confirmed severe alligator cracking"
        }
    )
    assert override_resp.status_code == 200

    # 3. Retrieve AI analysis and verify override is tracked
    analysis_resp = client.get(
        f"/api/v1/reports/{report_id}/ai-analysis",
        headers=auth_tokens["authority"]
    )
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()

    assert analysis_data["has_overrides"] is True
    assert analysis_data["authority_verified_category"] == "ROAD_DAMAGE"
    assert analysis_data["authority_verified_severity"] == "CRITICAL"
    assert analysis_data["effective_category"] == "ROAD_DAMAGE"
    assert analysis_data["effective_severity"] == "CRITICAL"
