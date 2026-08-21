import pytest
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.models.assignment import AuthorityDepartment


@pytest.fixture
def citizen_token(client):
    email = "wf_citizen@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "WF Citizen", "password": "password123", "role": "CITIZEN"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def authority_token(client):
    email = "wf_officer@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Road Inspector", "password": "password123", "role": "AUTHORITY"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin_token(client):
    email = "wf_admin@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "City Admin", "password": "password123", "role": "ADMIN"}
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def create_sample_issue(client, citizen_token) -> str:
    rep_res = client.post(
        "/api/v1/reports",
        headers=citizen_token,
        json={
            "category": "POTHOLE",
            "title": "Hazardous road pothole",
            "description": "Needs municipal repair",
            "severity": "HIGH",
            "latitude": 12.9352,
            "longitude": 77.6245,
            "address": "Outer Ring Road Junction"
        }
    )
    report = rep_res.json()
    return report["issue_id"]


def test_complete_valid_workflow_lifecycle(client, citizen_token, authority_token):
    issue_id = create_sample_issue(client, citizen_token)
    assert issue_id is not None

    # 1. Initial State: REPORTED
    res = client.get(f"/api/v1/issues/{issue_id}", headers=citizen_token)
    assert res.status_code == 200
    issue = res.json()
    assert issue["status"] == "REPORTED"
    assert issue["assigned_department"] == "ROAD_DEPARTMENT"
    assert issue["priority_score"] > 0.0

    # 2. Transition: REPORTED -> VERIFIED
    ver_res = client.post(
        f"/api/v1/issues/{issue_id}/verify",
        headers=authority_token,
        json={"department": "ROAD_DEPARTMENT", "notes": "Verified by field team."}
    )
    assert ver_res.status_code == 200
    assert ver_res.json()["status"] == "VERIFIED"

    # 3. Transition: VERIFIED -> ASSIGNED
    assign_res = client.post(
        f"/api/v1/issues/{issue_id}/assign",
        headers=authority_token,
        json={"department": "ROAD_DEPARTMENT", "notes": "Assigned to PWD maintenance crew 4."}
    )
    assert assign_res.status_code == 201
    assert assign_res.json()["department"] == "ROAD_DEPARTMENT"
    assert assign_res.json()["is_active"] is True

    # Check issue status is now ASSIGNED
    issue_check = client.get(f"/api/v1/issues/{issue_id}", headers=authority_token).json()
    assert issue_check["status"] == "ASSIGNED"

    # 4. Transition: ASSIGNED -> IN_PROGRESS
    prog_res = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=authority_token,
        json={"status": "IN_PROGRESS", "comment": "Asphalt patch work commenced."}
    )
    assert prog_res.status_code == 200
    assert prog_res.json()["status"] == "IN_PROGRESS"

    # 5. Transition: IN_PROGRESS -> FIXED
    fixed_res = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=authority_token,
        json={"status": "FIXED", "comment": "Pothole filled and sealed."}
    )
    assert fixed_res.status_code == 200
    assert fixed_res.json()["status"] == "FIXED"

    # 6. Transition: FIXED -> CLOSED
    closed_res = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=authority_token,
        json={"status": "CLOSED", "comment": "Quality assurance passed. Ticket closed."}
    )
    assert closed_res.status_code == 200
    assert closed_res.json()["status"] == "CLOSED"

    # 7. Verify complete audit trail
    hist_res = client.get(f"/api/v1/issues/{issue_id}/history", headers=authority_token)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 5
    statuses_recorded = [h["new_status"] for h in history]
    assert "VERIFIED" in statuses_recorded
    assert "ASSIGNED" in statuses_recorded
    assert "IN_PROGRESS" in statuses_recorded
    assert "FIXED" in statuses_recorded
    assert "CLOSED" in statuses_recorded


def test_invalid_status_transitions_rejected(client, citizen_token, authority_token):
    issue_id = create_sample_issue(client, citizen_token)

    # Cannot jump from REPORTED directly to FIXED
    bad_res = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=authority_token,
        json={"status": "FIXED", "comment": "Attempting illegal jump"}
    )
    assert bad_res.status_code == 400
    assert "Invalid status transition" in bad_res.json()["detail"]

    # Cannot jump from REPORTED directly to CLOSED
    bad_res2 = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=authority_token,
        json={"status": "CLOSED", "comment": "Attempting illegal jump to closed"}
    )
    assert bad_res2.status_code == 400


def test_citizen_unauthorized_workflow_operations(client, citizen_token):
    issue_id = create_sample_issue(client, citizen_token)

    # Citizen cannot verify
    res_ver = client.post(
        f"/api/v1/issues/{issue_id}/verify",
        headers=citizen_token,
        json={"notes": "Citizen trying to verify"}
    )
    assert res_ver.status_code == 403

    # Citizen cannot assign
    res_assign = client.post(
        f"/api/v1/issues/{issue_id}/assign",
        headers=citizen_token,
        json={"department": "ROAD_DEPARTMENT"}
    )
    assert res_assign.status_code == 403

    # Citizen cannot change status
    res_status = client.post(
        f"/api/v1/issues/{issue_id}/status",
        headers=citizen_token,
        json={"status": "IN_PROGRESS"}
    )
    assert res_status.status_code == 403


def test_authority_internal_comments(client, citizen_token, authority_token):
    issue_id = create_sample_issue(client, citizen_token)

    comment_res = client.post(
        f"/api/v1/issues/{issue_id}/comments",
        headers=authority_token,
        json={"comment": "Material procurement underway for road section."}
    )
    assert comment_res.status_code == 201
    entry = comment_res.json()
    assert entry["comment"] == "Material procurement underway for road section."

    # Verify history contains comment
    hist_res = client.get(f"/api/v1/issues/{issue_id}/history", headers=authority_token)
    assert any("Material procurement" in (h["comment"] or "") for h in hist_res.json())


def test_priority_recalculation_endpoint(client, citizen_token, authority_token):
    issue_id = create_sample_issue(client, citizen_token)

    recalc_res = client.post(f"/api/v1/issues/{issue_id}/recalculate-priority", headers=authority_token)
    assert recalc_res.status_code == 200
    data = recalc_res.json()
    assert "priority_score" in data
    assert "priority_breakdown" in data
    assert data["priority_breakdown"]["total_score"] == data["priority_score"]
