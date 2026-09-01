import pytest
from uuid import uuid4


@pytest.fixture
def auth_tokens(client):
    # Citizen
    c_email = "dup_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": c_email, "full_name": "Duplicate Citizen", "password": "password123", "role": "CITIZEN"}
    )
    c_token = client.post("/api/v1/auth/login", json={"email": c_email, "password": "password123"}).json()["access_token"]

    # Authority
    a_email = "dup_auth@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": a_email, "full_name": "Duplicate Officer", "password": "password123", "role": "AUTHORITY"}
    )
    a_token = client.post("/api/v1/auth/login", json={"email": a_email, "password": "password123"}).json()["access_token"]

    return {
        "citizen": {"Authorization": f"Bearer {c_token}"},
        "authority": {"Authorization": f"Bearer {a_token}"}
    }


def test_duplicate_candidates_with_explainability(client, auth_tokens):
    """
    Phase 9: Tests GET /api/v1/reports/{id}/duplicate-candidates.
    Verifies 6-Factor explainable component scores normalized to 0-100.
    """
    # 1. Create original report
    r1 = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Large pothole near college gate",
            "description": "Deep asphalt crater outside main university entrance",
            "severity": "MEDIUM",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "College Main Road, Bangalore"
        }
    ).json()

    # 2. Create second nearby report with paraphrased text
    r2 = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Deep pothole outside university entrance",
            "description": "Massive cavity on the road near campus portal",
            "severity": "HIGH",
            "latitude": 12.9718,
            "longitude": 77.5948,
            "address": "College Road, Bangalore"
        }
    ).json()

    report2_id = r2["id"]

    # 3. Query duplicate candidates
    resp = client.get(
        f"/api/v1/reports/{report2_id}/duplicate-candidates",
        headers=auth_tokens["authority"]
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["report_id"] == report2_id
    assert data["total_candidates"] >= 1

    candidate = data["candidates"][0]
    assert "explainability" in candidate
    exp = candidate["explainability"]

    # Verify all 6 component metrics are on 0-100 scale
    assert 0.0 <= exp["location"] <= 100.0
    assert 0.0 <= exp["category"] <= 100.0
    assert 0.0 <= exp["image"] <= 100.0
    assert 0.0 <= exp["description"] <= 100.0
    assert 0.0 <= exp["time"] <= 100.0
    assert 0.0 <= exp["road_segment"] <= 100.0
    assert 0.0 <= exp["overall"] <= 100.0
    assert exp["classification"] in ["NOT_DUPLICATE", "POTENTIAL_DUPLICATE", "LIKELY_DUPLICATE"]


def test_authority_merge_report_workflow(client, auth_tokens):
    """
    Phase 9: Tests POST /api/v1/reports/{id}/merge.
    Verifies human review approving duplicate merge into target issue.
    """
    # 1. Create Report 1 and Report 2 at distinct locations initially
    r1 = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Pothole Site A",
            "description": "Road damage",
            "severity": "LOW",
            "latitude": 12.9000,
            "longitude": 77.5000
        }
    ).json()

    r2 = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "POTHOLE",
            "title": "Pothole Site B",
            "description": "Same hazard reported by citizen B",
            "severity": "HIGH",
            "latitude": 12.9005,
            "longitude": 77.5005
        }
    ).json()

    target_issue_id = r1["issue_id"]
    report2_id = r2["id"]

    # 2. Citizen tries to merge -> 403 Forbidden
    forbidden_resp = client.post(
        f"/api/v1/reports/{report2_id}/merge",
        headers=auth_tokens["citizen"],
        json={"target_issue_id": target_issue_id, "merge_reason": "Citizen attempt"}
    )
    assert forbidden_resp.status_code == 403

    # 3. Authority merges report 2 into report 1's issue
    merge_resp = client.post(
        f"/api/v1/reports/{report2_id}/merge",
        headers=auth_tokens["authority"],
        json={
            "target_issue_id": target_issue_id,
            "merge_reason": "Confirmed duplicate hazard at road junction"
        }
    )
    assert merge_resp.status_code == 200
    merge_data = merge_resp.json()

    assert merge_data["target_issue_id"] == target_issue_id
    assert merge_data["updated_report_count"] >= 2
    assert merge_data["updated_priority_score"] > 0.0


def test_authority_reject_duplicate_workflow(client, auth_tokens):
    """
    Phase 9: Tests POST /api/v1/reports/{id}/reject-duplicate.
    Verifies human review rejecting duplicate merge and ensuring distinct canonical issue.
    """
    # 1. Create Report
    r1 = client.post(
        "/api/v1/reports",
        headers=auth_tokens["citizen"],
        json={
            "category": "ROAD_DAMAGE",
            "title": "Distinct Road Fissure",
            "description": "Located on opposite lane",
            "severity": "MEDIUM",
            "latitude": 12.9500,
            "longitude": 77.5500
        }
    ).json()
    report_id = r1["id"]

    # 2. Citizen tries to reject -> 403 Forbidden
    forbidden_resp = client.post(
        f"/api/v1/reports/{report_id}/reject-duplicate",
        headers=auth_tokens["citizen"],
        json={"rejection_reason": "Not duplicate"}
    )
    assert forbidden_resp.status_code == 403

    # 3. Authority rejects duplicate recommendation
    reject_resp = client.post(
        f"/api/v1/reports/{report_id}/reject-duplicate",
        headers=auth_tokens["authority"],
        json={"rejection_reason": "Inspected on site, opposite traffic lane is distinct"}
    )
    assert reject_resp.status_code == 200
    reject_data = reject_resp.json()
    assert reject_data["is_distinct"] is True
    assert reject_data["report_id"] == report_id
