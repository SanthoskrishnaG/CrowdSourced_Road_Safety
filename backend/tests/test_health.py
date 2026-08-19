def test_health_endpoint(client):
    """
    Tests the health check endpoint returns 200 and healthy status.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint(client):
    """
    Tests the root endpoint returns welcome message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]
