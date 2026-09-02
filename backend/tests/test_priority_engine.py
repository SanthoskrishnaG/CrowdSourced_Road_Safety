from datetime import datetime, timezone, timedelta
import pytest

from app.models.report import ReportSeverity, ReportStatus
from app.models.issue import PriorityLevel, LocationZone, TrafficDensity
from app.services.priority_engine import (
    calculate_priority,
    calculate_report_count_score,
    calculate_aging_score,
    determine_priority_level,
    TrafficDensityService,
)


def test_priority_score_bounds_and_clamping():
    # Maximum theoretical points: Severity(25) + Count(15) + Traffic(10) + Location(10) + Aging(10) + Health(15) + Risk(10) + Weather(5) = 100.0
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=20)

    score, level, breakdown = calculate_priority(
        severity=ReportSeverity.CRITICAL,
        report_count=10,
        traffic_density=TrafficDensity.HEAVY,
        location_zone=LocationZone.HOSPITAL,
        created_at=old_time,
        current_status=ReportStatus.REPORTED,
        now=now,
        road_health_score=0.0,
        predicted_risk_score=100.0,
        confirmations_count=5
    )
    assert 0.0 <= score <= 100.0
    assert score == 100.0
    assert level == PriorityLevel.CRITICAL
    assert breakdown["severity_score"] == 25.0
    assert breakdown["report_count_score"] == 15.0
    assert breakdown["traffic_density_score"] == 10.0
    assert breakdown["location_zone_score"] == 10.0
    assert breakdown["aging_score"] == 10.0


def test_priority_score_low_severity_single_report():
    now = datetime.now(timezone.utc)
    score, level, breakdown = calculate_priority(
        severity=ReportSeverity.LOW,
        report_count=1,
        traffic_density=TrafficDensity.LOW,
        location_zone=LocationZone.RESIDENTIAL,
        created_at=now,
        current_status=ReportStatus.REPORTED,
        now=now,
        road_health_score=100.0,
        predicted_risk_score=0.0
    )
    # Severity(4) + Count(5) + Health(0) + Traffic(3) + Location(4) + Aging(0) + Risk(0) + Weather(1) = 17.0
    assert score <= 20.0
    assert level == PriorityLevel.LOW
    assert breakdown["aging_score"] == 0.0


def test_aging_progression_and_resolution_freeze():
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(days=4)

    # When active: 4 days * 1.0 = 4.0 points
    aging_pts, days = calculate_aging_score(created_at, ReportStatus.IN_PROGRESS, now=now)
    assert aging_pts == 4.0
    assert days == 4.0

    # When fixed/closed: aging points must be 0
    aging_fixed, _ = calculate_aging_score(created_at, ReportStatus.FIXED, now=now)
    assert aging_fixed == 0.0

    aging_closed, _ = calculate_aging_score(created_at, ReportStatus.CLOSED, now=now)
    assert aging_closed == 0.0


def test_report_count_logarithmic_saturation():
    assert calculate_report_count_score(1) == 5.0
    assert calculate_report_count_score(2) >= 9.0
    assert calculate_report_count_score(4) >= 13.0
    assert calculate_report_count_score(100) == 15.0  # Capped at 15


def test_priority_level_thresholds():
    assert determine_priority_level(85.0) == PriorityLevel.CRITICAL
    assert determine_priority_level(75.0) == PriorityLevel.CRITICAL
    assert determine_priority_level(70.0) == PriorityLevel.HIGH
    assert determine_priority_level(50.0) == PriorityLevel.HIGH
    assert determine_priority_level(45.0) == PriorityLevel.MEDIUM
    assert determine_priority_level(25.0) == PriorityLevel.MEDIUM
    assert determine_priority_level(24.9) == PriorityLevel.LOW


def test_traffic_density_heuristic_provider():
    assert TrafficDensityService.get_traffic_density(12.9, 77.5, "Outer Ring Road Highway Junction") == TrafficDensity.HEAVY
    assert TrafficDensityService.get_traffic_density(12.9, 77.5, "12th Cross Road Avenue") == TrafficDensity.MEDIUM
    assert TrafficDensityService.get_traffic_density(12.9, 77.5, None) == TrafficDensity.MEDIUM

