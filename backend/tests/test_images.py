import io
import pytest
from PIL import Image


@pytest.fixture
def citizen_auth_headers(client):
    email = "img_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Image Citizen",
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


@pytest.fixture
def other_citizen_auth_headers(client):
    email = "other_img_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Other Citizen",
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


@pytest.fixture
def sample_report_id(client, citizen_auth_headers):
    resp = client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "Pothole for image test",
            "description": "Needs photo evidence",
            "severity": "HIGH",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "location_accuracy": 5.0
        },
        headers=citizen_auth_headers
    )
    return resp.json()["id"]


def create_mock_image_bytes(format="JPEG", size=(200, 200), color="blue") -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_upload_valid_image(client, citizen_auth_headers, sample_report_id):
    """
    Tests uploading a valid JPEG image evidence to a report.
    """
    img_bytes = create_mock_image_bytes("JPEG", (400, 300))
    response = client.post(
        f"/api/v1/reports/{sample_report_id}/images",
        files=[("files", ("pothole.jpg", img_bytes, "image/jpeg"))],
        headers=citizen_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["width"] == 400
    assert data[0]["height"] == 300
    assert "thumbnail_path" in data[0]
    assert data[0]["thumbnail_path"] is not None


def test_upload_multiple_images(client, citizen_auth_headers, sample_report_id):
    """
    Tests uploading multiple images in a single request.
    """
    img1 = create_mock_image_bytes("JPEG", (100, 100), "red")
    img2 = create_mock_image_bytes("PNG", (150, 150), "green")

    response = client.post(
        f"/api/v1/reports/{sample_report_id}/images",
        files=[
            ("files", ("photo1.jpg", img1, "image/jpeg")),
            ("files", ("photo2.png", img2, "image/png"))
        ],
        headers=citizen_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2


def test_upload_invalid_file_type(client, citizen_auth_headers, sample_report_id):
    """
    Tests uploading non-image file (e.g. text/plain) is rejected.
    """
    bad_bytes = b"This is just a text file, not an image."
    response = client.post(
        f"/api/v1/reports/{sample_report_id}/images",
        files=[("files", ("fake_image.jpg", bad_bytes, "image/jpeg"))],
        headers=citizen_auth_headers
    )
    assert response.status_code == 400
    assert "Invalid or corrupted image file" in response.json()["detail"]


def test_upload_oversized_file(client, citizen_auth_headers, sample_report_id):
    """
    Tests uploading a file exceeding 5MB is rejected.
    """
    oversized_bytes = b"X" * (6 * 1024 * 1024)  # 6MB
    response = client.post(
        f"/api/v1/reports/{sample_report_id}/images",
        files=[("files", ("huge.jpg", oversized_bytes, "image/jpeg"))],
        headers=citizen_auth_headers
    )
    assert response.status_code == 413


def test_get_report_images(client, citizen_auth_headers, sample_report_id):
    """
    Tests retrieving images attached to a report.
    """
    img = create_mock_image_bytes("JPEG")
    client.post(
        f"/api/v1/reports/{sample_report_id}/images",
        files=[("files", ("test.jpg", img, "image/jpeg"))],
        headers=citizen_auth_headers
    )

    response = client.get(
        f"/api/v1/reports/{sample_report_id}/images",
        headers=citizen_auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_unauthorized_image_deletion(
    client,
    citizen_auth_headers,
    other_citizen_auth_headers,
    sample_report_id
):
    """
    Tests that another citizen cannot delete an image they do not own.
    """
    # Upload image as owner
    img = create_mock_image_bytes("JPEG")
    upload_resp = client.post(
        f"/api/v1/reports/{sample_report_id}/images",
        files=[("files", ("test.jpg", img, "image/jpeg"))],
        headers=citizen_auth_headers
    )
    image_id = upload_resp.json()[0]["id"]

    # Try deleting as another citizen
    del_resp = client.delete(
        f"/api/v1/reports/{sample_report_id}/images/{image_id}",
        headers=other_citizen_auth_headers
    )
    assert del_resp.status_code == 403


def test_authorized_image_deletion(client, citizen_auth_headers, sample_report_id):
    """
    Tests that the owner citizen can successfully delete their uploaded image.
    """
    img = create_mock_image_bytes("JPEG")
    upload_resp = client.post(
        f"/api/v1/reports/{sample_report_id}/images",
        files=[("files", ("test.jpg", img, "image/jpeg"))],
        headers=citizen_auth_headers
    )
    image_id = upload_resp.json()[0]["id"]

    del_resp = client.delete(
        f"/api/v1/reports/{sample_report_id}/images/{image_id}",
        headers=citizen_auth_headers
    )
    assert del_resp.status_code == 204
