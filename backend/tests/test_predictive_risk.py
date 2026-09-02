import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.models.road_segment import RoadSegment, RoadType, RoadImportance
from ml.prediction.model import RoadRiskModel, load_road_risk_model


@pytest.fixture
def auth_tokens(client):
    # Citizen
    c_email = f"citizen_risk_{uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": c_email, "full_name": "Risk Citizen", "password": "password123", "role": "CITIZEN"}
    )
    c_token = client.post("/api/v1/auth/login", json={"email": c_email, "password": "password123"}).json()["access_token"]

    # Authority
    a_email = f"auth_risk_{uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": a_email, "full_name": "Risk Authority", "password": "password123", "role": "AUTHORITY"}
    )
    a_token = client.post("/api/v1/auth/login", json={"email": a_email, "password": "password123"}).json()["access_token"]

    return {
        "citizen": {"Authorization": f"Bearer {c_token}"},
        "authority": {"Authorization": f"Bearer {a_token}"}
    }


def test_road_risk_model_inference():
    """
    Tests direct ML model prediction output, risk level classification,
    worsening probability, and contributing factor generation.
    """
    model = load_road_risk_model()

    # Case A: Pristine Corridor Features
    pristine_features = {
        "historical_reports_count": 0,
        "reports_last_30d": 0,
        "reports_last_7d": 0,
        "historical_issues_count": 0,
        "active_issues_count": 0,
        "critical_issues_count": 0,
        "high_issues_count": 0,
        "critical_severity_ratio": 0.0,
        "road_health_score": 100.0,
        "avg_resolution_hours": 24.0,
        "road_type": "RESIDENTIAL",
        "importance": "LOW",
        "length_km": 1.0,
        "speed_limit_kmh": 30,
        "issue_density_per_km": 0.0,
        "report_density_per_km": 0.0,
        "incident_frequency_weekly": 0.0,
    }

    res_pristine = model.predict(pristine_features)
    assert 0.0 <= res_pristine["risk_score"] <= 30.0
    assert res_pristine["risk_level"] in ["LOW", "MEDIUM"]
    assert 0.0 <= res_pristine["worsening_probability"] <= 0.40
    assert len(res_pristine["contributing_factors"]) >= 1
    assert "disclaimer" in res_pristine

    # Case B: Heavily Damaged High-Traffic Arterial Features
    severe_features = {
        "historical_reports_count": 85,
        "reports_last_30d": 24,
        "reports_last_7d": 9,
        "historical_issues_count": 32,
        "active_issues_count": 8,
        "critical_issues_count": 4,
        "high_issues_count": 3,
        "critical_severity_ratio": 0.65,
        "road_health_score": 22.0,
        "avg_resolution_hours": 140.0,
        "road_type": "ARTERIAL",
        "importance": "CRITICAL",
        "length_km": 1.5,
        "speed_limit_kmh": 60,
        "issue_density_per_km": 5.33,
        "report_density_per_km": 56.6,
        "incident_frequency_weekly": 5.6,
    }

    res_severe = model.predict(severe_features)
    assert res_severe["risk_score"] >= 65.0
    assert res_severe["risk_level"] in ["HIGH", "CRITICAL"]
    assert res_severe["worsening_probability"] >= 0.70
    assert len(res_severe["contributing_factors"]) >= 1

    # Verify explainability factors have impact percentages
    for factor in res_severe["contributing_factors"]:
        assert "factor_name" in factor
        assert "impact_percentage" in factor
        assert "description" in factor
        assert factor["impact_percentage"] > 0.0


def test_get_road_segment_risk_api(client, auth_tokens):
    """
    Tests GET /api/v1/roads/{id}/risk endpoint.
    """
    # 1. Create a road corridor
    create_resp = client.post(
        "/api/v1/roads",
        headers=auth_tokens["authority"],
        json={
            "name": "Predictive Risk Test Corridor",
            "start_latitude": 12.9600,
            "start_longitude": 77.6600,
            "end_latitude": 12.9650,
            "end_longitude": 77.6650,
            "road_type": "HIGHWAY",
            "importance": "CRITICAL",
            "speed_limit_kmh": 80
        }
    )
    assert create_resp.status_code == 201
    road_id = create_resp.json()["id"]

    # 2. Query predictive risk endpoint
    risk_resp = client.get(f"/api/v1/roads/{road_id}/risk")
    assert risk_resp.status_code == 200
    r_data = risk_resp.json()
    assert r_data["road_id"] == road_id
    assert "risk_score" in r_data
    assert "risk_level" in r_data
    assert "worsening_probability" in r_data
    assert "contributing_factors" in r_data
    assert "model_version" in r_data
    assert "disclaimer" in r_data
    assert "Application-generated predictive estimate" in r_data["disclaimer"]


def test_get_all_predictions_road_risk_api(client, auth_tokens):
    """
    Tests GET /api/v1/predictions/road-risk endpoint.
    """
    # 0. Create road segment
    client.post(
        "/api/v1/roads",
        headers=auth_tokens["authority"],
        json={
            "name": "Batch Prediction Highway",
            "start_latitude": 12.9800,
            "start_longitude": 77.6800,
            "end_latitude": 12.9900,
            "end_longitude": 77.6900,
            "road_type": "HIGHWAY",
            "importance": "CRITICAL",
            "speed_limit_kmh": 100
        }
    )

    # 1. Citizen forbidden
    cit_resp = client.get("/api/v1/predictions/road-risk", headers=auth_tokens["citizen"])
    assert cit_resp.status_code == 403

    # 2. Authority allowed
    auth_resp = client.get("/api/v1/predictions/road-risk", headers=auth_tokens["authority"])
    assert auth_resp.status_code == 200
    p_data = auth_resp.json()

    assert "summary" in p_data
    assert "predictions" in p_data
    assert "model_version" in p_data
    assert "disclaimer" in p_data
    assert p_data["summary"]["total_evaluated_segments"] >= 1

    # 3. Filter by road_type
    filtered_resp = client.get(
        "/api/v1/predictions/road-risk?road_type=HIGHWAY",
        headers=auth_tokens["authority"]
    )
    assert filtered_resp.status_code == 200
    f_data = filtered_resp.json()
    assert len(f_data["predictions"]) >= 1
    for pred in f_data["predictions"]:
        assert pred["road_type"] == "HIGHWAY"



def test_nonexistent_road_risk_returns_404(client):
    """
    Tests that querying risk for a non-existent UUID returns 404.
    """
    random_id = uuid4()
    resp = client.get(f"/api/v1/roads/{random_id}/risk")
    assert resp.status_code == 404
