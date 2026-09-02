import pytest
from datetime import datetime, timezone, timedelta
from app.models.report import ReportCategory, ReportSeverity, ReportStatus, RoadReport
from app.models.issue import Issue, PriorityLevel, LocationZone, TrafficDensity
from app.models.priority_history import PriorityHistory
from app.services.weather.models import WeatherData, WeatherCondition
from app.services.priority_engine import (
    calculate_priority,
    determine_priority_level,
    calculate_report_count_score,
    calculate_road_health_penalty_score,
    calculate_aging_score,
    calculate_predicted_risk_score,
    calculate_weather_score,
    calculate_citizen_confirmations_score,
    PriorityRecalculationService
)


def test_independent_factors_scoring():
    # 1. Severity
    score_crit, _, _ = calculate_priority(severity=ReportSeverity.CRITICAL, report_count=1)
    score_low, _, _ = calculate_priority(severity=ReportSeverity.LOW, report_count=1)
    assert score_crit > score_low

    # 2. Report Count
    assert calculate_report_count_score(1) == 5.0
    assert calculate_report_count_score(2) == 9.3 or calculate_report_count_score(2) >= 9.0
    assert calculate_report_count_score(10) == 15.0

    # 3. Road Health Degradation
    assert calculate_road_health_penalty_score(100.0) == 0.0
    assert calculate_road_health_penalty_score(50.0) == 7.5
    assert calculate_road_health_penalty_score(0.0) == 15.0

    # 4. Aging
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=5)
    age_pts, days = calculate_aging_score(old_date, ReportStatus.REPORTED, now=now)
    assert days >= 4.9
    assert age_pts == 5.0

    # 5. ML Predicted Risk
    assert calculate_predicted_risk_score(0.0) == 0.0
    assert calculate_predicted_risk_score(50.0) == 5.0
    assert calculate_predicted_risk_score(100.0) == 10.0

    # 6. Weather
    severe_weather = WeatherData(
        latitude=12.0, longitude=77.0,
        temperature_celsius=24.0, humidity_percent=90.0,
        rainfall_mm_per_hour=20.0, condition=WeatherCondition.THUNDERSTORM,
        is_severe=True, is_mock=True, provider_name="mock"
    )
    w_pts, _ = calculate_weather_score(severe_weather)
    assert w_pts == 5.0

    # 7. Citizen Confirmations
    assert calculate_citizen_confirmations_score(0) == 0.0
    assert calculate_citizen_confirmations_score(3) == 3.0
    assert calculate_citizen_confirmations_score(10) == 5.0


def test_combined_priority_bounds_and_explainability():
    # Max conditions
    max_weather = WeatherData(
        latitude=12.0, longitude=77.0,
        temperature_celsius=24.0, humidity_percent=90.0,
        rainfall_mm_per_hour=30.0, condition=WeatherCondition.THUNDERSTORM,
        is_severe=True, is_mock=True, provider_name="mock"
    )
    score, level, breakdown = calculate_priority(
        severity=ReportSeverity.CRITICAL,
        report_count=10,
        traffic_density=TrafficDensity.HEAVY,
        location_zone=LocationZone.HOSPITAL,
        created_at=datetime.now(timezone.utc) - timedelta(days=20),
        current_status=ReportStatus.REPORTED,
        road_health_score=0.0,
        predicted_risk_score=100.0,
        weather_data=max_weather,
        confirmations_count=5
    )

    assert score == 100.0
    assert level == PriorityLevel.CRITICAL
    assert len(breakdown["factors"]) == 9
    assert len(breakdown["top_contributing_drivers"]) > 0


def test_priority_recalculation_service_audit_history(db_session):
    issue = Issue(
        title="Pothole in School Zone",
        category=ReportCategory.POTHOLE,
        severity=ReportSeverity.HIGH,
        status=ReportStatus.REPORTED,
        latitude=12.9716,
        longitude=77.5946,
        priority_score=40.0,
        priority_level=PriorityLevel.MEDIUM,
        report_count=1
    )
    db_session.add(issue)
    db_session.commit()
    db_session.refresh(issue)

    # Recalculate
    new_score, new_level, breakdown, history_entry = PriorityRecalculationService.recalculate_and_log_priority(
        db=db_session,
        issue=issue,
        trigger_event="TEST_RECALCULATION",
        road_health_score=35.0,
        predicted_risk_score=75.0
    )

    assert issue.priority_score == new_score
    assert history_entry.issue_id == issue.id
    assert history_entry.trigger_event == "TEST_RECALCULATION"
    assert history_entry.previous_score == 40.0
    assert history_entry.new_score == new_score


def test_priority_recalculation_and_history_apis(client, authority_token):
    # 1. Create a report which creates an issue
    rep_res = client.post(
        "/api/v1/reports",
        headers=authority_token,
        json={
            "title": "Major Sinkhole",
            "category": "POTHOLE",
            "severity": "CRITICAL",
            "latitude": 12.9750,
            "longitude": 77.5990,
            "description": "Urgent sinkhole forming on arterial road"
        }
    )
    assert rep_res.status_code == 201
    issue_id = rep_res.json()["issue_id"]

    # 2. Trigger priority recalculation
    recalc_res = client.post(f"/api/v1/issues/{issue_id}/recalculate-priority", headers=authority_token)
    assert recalc_res.status_code == 200
    recalc_data = recalc_res.json()
    assert recalc_data["priority_score"] > 0.0
    assert "priority_breakdown" in recalc_data
    assert "factors" in recalc_data["priority_breakdown"]

    # 3. Fetch priority history audit
    hist_res = client.get(f"/api/v1/issues/{issue_id}/priority-history", headers=authority_token)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data) >= 1
    assert hist_data[0]["trigger_event"] == "MANUAL_RECALCULATION"
    assert "factor_breakdown" in hist_data[0]
