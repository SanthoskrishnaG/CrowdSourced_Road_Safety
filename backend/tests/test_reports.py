import pytest
from app.models.user import UserRole
from app.models.report import ReportCategory, ReportSeverity, ReportStatus


@pytest.fixture
def auth_headers(client):
    """
    Helper fixture to register and log in a standard citizen user.
    """
    email = "citizen_report@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Reporter Citizen",
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
def admin_headers(client):
    """
    Helper fixture to register and log in an admin user.
    """
    email = "admin_report@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "System Admin",
            "password": "securepassword123",
            "role": "ADMIN"
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


def test_create_report_success(client, auth_headers):
    """
    Tests successfully creating a report as an authenticated citizen.
    """
    response = client.post(
        "/api/v1/reports",
        json={
            "category": "POTHOLE",
            "title": "Large Pothole Main St",
            "description": "Pothole in the middle lane causing tire hazards.",
            "severity": "HIGH",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "123 Main St"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Large Pothole Main St"
    assert data["status"] == "REPORTED"
    assert "id" in data


def test_create_report_invalid_coordinates(client, auth_headers):
    """
    Tests creating a report fails if coordinates are out of bounds.
    """
    # Latitude out of bounds
    response = client.post(
        "/api/v1/reports",
        json={
            "category": "GARBAGE",
            "title": "Illegal Dumping",
            "description": "Large garbage dump",
            "severity": "MEDIUM",
            "latitude": 95.0,  # Invalid
            "longitude": 45.0,
        },
        headers=auth_headers
    )
    assert response.status_code == 422
    
    # Longitude out of bounds
    response = client.post(
        "/api/v1/reports",
        json={
            "category": "GARBAGE",
            "title": "Illegal Dumping",
            "description": "Large garbage dump",
            "severity": "MEDIUM",
            "latitude": 45.0,
            "longitude": 200.0,  # Invalid
        },
        headers=auth_headers
    )
    assert response.status_code == 422


def test_create_report_invalid_enums(client, auth_headers):
    """
    Tests validation errors when invalid enum values are provided.
    """
    # Invalid category
    response = client.post(
        "/api/v1/reports",
        json={
            "category": "NOT_AN_ENUM_VALUE",
            "title": "Broken light",
            "description": "Broken streetlight",
            "severity": "LOW",
            "latitude": 10.0,
            "longitude": 10.0,
        },
        headers=auth_headers
    )
    assert response.status_code == 422
    
    # Invalid severity
    response = client.post(
        "/api/v1/reports",
        json={
            "category": "BROKEN_STREETLIGHT",
            "title": "Broken light",
            "description": "Broken streetlight",
            "severity": "CRITICAL_HAZARD",  # Invalid
            "latitude": 10.0,
            "longitude": 10.0,
        },
        headers=auth_headers
    )
    assert response.status_code == 422


def test_retrieve_report_by_id(client, auth_headers):
    """
    Tests querying details of a specific report.
    """
    create_resp = client.post(
        "/api/v1/reports",
        json={
            "category": "FLOODING",
            "title": "Flooded street",
            "description": "Water overflowing",
            "severity": "CRITICAL",
            "latitude": 34.0,
            "longitude": -118.0
        },
        headers=auth_headers
    )
    report_id = create_resp.json()["id"]
    
    get_resp = client.get(f"/api/v1/reports/{report_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Flooded street"


def test_citizen_view_own_reports(client, auth_headers):
    """
    Tests citizen is able to retrieve their list of own reports.
    """
    # Post report
    client.post(
        "/api/v1/reports",
        json={
            "category": "ROAD_DAMAGE",
            "title": "Cracks",
            "description": "Minor road cracks",
            "severity": "LOW",
            "latitude": 1.0,
            "longitude": 1.0
        },
        headers=auth_headers
    )
    
    response = client.get("/api/v1/reports/my", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_unauthorized_modification(client, auth_headers):
    """
    Tests that a citizen cannot update another citizen's report.
    """
    # Citizen A creates a report
    create_resp = client.post(
        "/api/v1/reports",
        json={
            "category": "OBSTRUCTION",
            "title": "Blocked Lane",
            "description": "Branch in street",
            "severity": "MEDIUM",
            "latitude": 5.0,
            "longitude": 5.0
        },
        headers=auth_headers
    )
    report_id = create_resp.json()["id"]
    
    # Register Citizen B
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "citizenB@example.com",
            "full_name": "Citizen B",
            "password": "securepassword123"
        }
    )
    login_b = client.post(
        "/api/v1/auth/login",
        json={
            "email": "citizenB@example.com",
            "password": "securepassword123"
        }
    )
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # Try modifying A's report as B
    response = client.patch(
        f"/api/v1/reports/{report_id}",
        json={"title": "Hacked Title"},
        headers=headers_b
    )
    assert response.status_code == 403


def test_pagination_and_filtering(client, auth_headers, admin_headers):
    """
    Tests pagination layout metadata and filter queries.
    """
    # Create several reports with different statuses
    for i in range(5):
        client.post(
            "/api/v1/reports",
            json={
                "category": "GARBAGE",
                "title": f"Garbage Report {i}",
                "description": "Littering",
                "severity": "LOW",
                "latitude": 0.0,
                "longitude": 0.0
            },
            headers=auth_headers
        )
        
    # Get total list
    list_resp = client.get("/api/v1/reports?page=1&page_size=2", headers=auth_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "items" in data
    assert "metadata" in data
    assert len(data["items"]) == 2
    assert data["metadata"]["page"] == 1
    assert data["metadata"]["page_size"] == 2
    assert data["metadata"]["total"] >= 5
    
    # Test filters
    filtered_resp = client.get("/api/v1/reports?category=GARBAGE", headers=auth_headers)
    assert filtered_resp.status_code == 200
    for r in filtered_resp.json()["items"]:
        assert r["category"] == "GARBAGE"
