import pytest
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.api.dependencies import RoleChecker


def test_registration_success(client):
    """
    Tests successful registration of a citizen user.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "citizen@example.com",
            "full_name": "Citizen User",
            "password": "securepassword123",
            "role": "CITIZEN"
        }
    )
    assert response.status_code == 210 or response.status_code == 201
    data = response.json()
    assert data["email"] == "citizen@example.com"
    assert data["full_name"] == "Citizen User"
    assert "password_hash" not in data


def test_registration_duplicate_email(client):
    """
    Tests that registering with an already registered email returns 400.
    """
    # Register first user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "full_name": "User One",
            "password": "password123"
        }
    )
    # Register second user with same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "full_name": "User Two",
            "password": "password1234"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_registration_invalid_password(client):
    """
    Tests that a short password fails validation via Pydantic.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalidpass@example.com",
            "full_name": "User Short Pass",
            "password": "123"  # too short
        }
    )
    assert response.status_code == 422


def test_login_success(client):
    """
    Tests user login returns a valid JWT access token.
    """
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "full_name": "Login User",
            "password": "mypassword123"
        }
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "mypassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """
    Tests login with incorrect credentials.
    """
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


def test_protected_endpoint_without_token(client):
    """
    Tests that a protected endpoint without header fails with 401.
    """
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_protected_endpoint_with_token(client):
    """
    Tests access to a protected endpoint using a valid JWT token.
    """
    email = "me_endpoint@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Me User",
            "password": "mypassword123"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "mypassword123"
        }
    )
    token = login_resp.json()["access_token"]
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_role_authorization_dependency():
    """
    Unit tests the role-based auth dependency logic.
    """
    admin_checker = RoleChecker([UserRole.ADMIN])
    
    admin_user = User(email="admin@example.com", role=UserRole.ADMIN, is_active=True)
    citizen_user = User(email="citizen@example.com", role=UserRole.CITIZEN, is_active=True)
    
    # Authorized access should return the user
    assert admin_checker(admin_user) == admin_user
    
    # Unauthorized access should raise 403 FORBIDDEN
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(citizen_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_logout(client):
    """
    Tests logout endpoint with a valid JWT token.
    """
    email = "logout_test@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Logout User",
            "password": "securepassword123"
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
    
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "Successfully logged out" in response.json()["detail"]

