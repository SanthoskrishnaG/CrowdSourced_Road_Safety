import io
import pytest
from PIL import Image
from ml.datasets.dataset import generate_synthetic_hazard_image


@pytest.fixture
def citizen_headers(client):
    email = "cls_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Classification Citizen",
            "password": "securepassword123",
            "role": "CITIZEN"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepassword123"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authority_headers(client):
    email = "cls_authority@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Classification Officer",
            "password": "securepassword123",
            "role": "AUTHORITY"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepassword123"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_image_bytes(category="POTHOLE") -> bytes:
    img = generate_synthetic_hazard_image(category)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_standalone_classification_endpoint(client, citizen_headers):
    img_bytes = create_image_bytes("POTHOLE")
    files = {"file": ("pothole.jpg", img_bytes, "image/jpeg")}
    
    resp = client.post("/api/v1/reports/classify-image", headers=citizen_headers, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_category"] == "POTHOLE"
    assert data["confidence"] > 0.0
    assert "road-vision" in data["model_version"]
    assert "probabilities" in data
    assert len(data["probabilities"]) == 8


def test_report_image_upload_automatic_classification(client, citizen_headers):
    # 1. Create a report
    rep_resp = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "category": "POTHOLE",
            "title": "Severe pothole on main road",
            "description": "Deep asphalt crater",
            "severity": "CRITICAL",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
    )
    assert rep_resp.status_code == 201
    report_id = rep_resp.json()["id"]

    # 2. Upload photo
    img_bytes = create_image_bytes("POTHOLE")
    files = [("files", ("hazard.jpg", img_bytes, "image/jpeg"))]
    upload_resp = client.post(
        f"/api/v1/reports/{report_id}/images",
        headers=citizen_headers,
        files=files
    )
    assert upload_resp.status_code == 201
    uploaded_images = upload_resp.json()
    assert len(uploaded_images) == 1

    img_data = uploaded_images[0]
    image_id = img_data["id"]
    classification = img_data["classification"]
    assert classification is not None
    assert classification["predicted_category"] == "POTHOLE"
    assert classification["confidence"] > 0.0
    assert classification["is_corrected"] is False

    # 3. Query classification endpoint directly
    cls_resp = client.get(
        f"/api/v1/reports/{report_id}/images/{image_id}/classification",
        headers=citizen_headers
    )
    assert cls_resp.status_code == 200
    cls_data = cls_resp.json()
    assert cls_data["predicted_category"] == "POTHOLE"


def test_authority_override_and_verification(client, citizen_headers, authority_headers):
    # 1. Create report and upload image
    rep_resp = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "category": "ROAD_DAMAGE",
            "title": "Cracked pavement",
            "description": "Needs inspection",
            "severity": "MEDIUM",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
    )
    report_id = rep_resp.json()["id"]

    img_bytes = create_image_bytes("ROAD_DAMAGE")
    upload_resp = client.post(
        f"/api/v1/reports/{report_id}/images",
        headers=citizen_headers,
        files=[("files", ("crack.jpg", img_bytes, "image/jpeg"))]
    )
    image_id = upload_resp.json()[0]["id"]

    # 2. Non-authority attempting to verify/override -> 403
    forbidden_resp = client.post(
        f"/api/v1/reports/{report_id}/images/{image_id}/verify",
        headers=citizen_headers,
        json={"verified_category": "ROAD_DAMAGE", "notes": "Citizen trying to verify"}
    )
    assert forbidden_resp.status_code == 403

    # 3. Authority verifies category
    verify_resp = client.post(
        f"/api/v1/reports/{report_id}/images/{image_id}/verify",
        headers=authority_headers,
        json={"verified_category": "ROAD_DAMAGE", "notes": "Confirmed by field officer"}
    )
    assert verify_resp.status_code == 200
    verified_data = verify_resp.json()
    assert verified_data["authority_verified_category"] == "ROAD_DAMAGE"
    assert verified_data["correction_notes"] == "Confirmed by field officer"
    assert verified_data["corrected_at"] is not None
