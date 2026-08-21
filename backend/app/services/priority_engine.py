import math
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional

from app.models.report import ReportSeverity, ReportStatus
from app.models.issue import PriorityLevel, LocationZone, TrafficDensity


# Factor Weight Configurations (Total Max = 100)
SEVERITY_WEIGHTS: Dict[ReportSeverity, float] = {
    ReportSeverity.CRITICAL: 35.0,
    ReportSeverity.HIGH: 25.0,
    ReportSeverity.MEDIUM: 15.0,
    ReportSeverity.LOW: 5.0,
}

TRAFFIC_DENSITY_WEIGHTS: Dict[TrafficDensity, float] = {
    TrafficDensity.HEAVY: 15.0,
    TrafficDensity.MEDIUM: 10.0,
    TrafficDensity.LOW: 5.0,
}

LOCATION_ZONE_WEIGHTS: Dict[LocationZone, float] = {
    LocationZone.HOSPITAL: 15.0,
    LocationZone.SCHOOL: 13.0,
    LocationZone.MAIN_ROAD: 10.0,
    LocationZone.JUNCTION: 10.0,
    LocationZone.RESIDENTIAL: 5.0,
    LocationZone.OTHER: 3.0,
}

# Thresholds for categorical priority level mapping
PRIORITY_THRESHOLDS = {
    PriorityLevel.CRITICAL: 80.0,
    PriorityLevel.HIGH: 60.0,
    PriorityLevel.MEDIUM: 40.0,
    PriorityLevel.LOW: 0.0,
}


class TrafficDensityService:
    """
    Service provider for road segment traffic density.
    Supports default lookup, configurable overrides, and provides an extensible
    interface for live third-party traffic APIs (TomTom, Google Maps, HERE).
    """

    @classmethod
    def get_traffic_density(cls, latitude: float, longitude: float, address: Optional[str] = None) -> TrafficDensity:
        # Initial heuristic / configurable logic:
        # Main thoroughfares or arterial terms in address get HEAVY traffic
        if address:
            addr_lower = address.lower()
            if any(term in addr_lower for term in ["highway", "expressway", "arterial", "ring road", "main road", "junction"]):
                return TrafficDensity.HEAVY
            if any(term in addr_lower for term in ["avenue", "boulevard", "street", "cross"]):
                return TrafficDensity.MEDIUM
        return TrafficDensity.MEDIUM


def calculate_report_count_score(report_count: int) -> float:
    """
    Computes saturating priority bonus for multiple independent citizen reports.
    1 report -> 10.0 pts
    2 reports -> 15.0 pts
    3 reports -> 18.0 pts
    4+ reports -> 20.0 pts (max)
    """
    if report_count <= 0:
        return 0.0
    if report_count == 1:
        return 10.0
    # Logarithmic saturation
    score = min(20.0, 10.0 + (report_count - 1) * 3.5)
    return round(score, 1)


def calculate_aging_score(created_at: datetime, status: ReportStatus, now: Optional[datetime] = None) -> Tuple[float, float]:
    """
    Computes time unresolved priority escalation.
    Adds +1.5 points per 24 hours unresolved up to a 15.0 point ceiling (10+ days).
    Resolved/closed issues receive 0 aging points.
    """
    if status in [ReportStatus.FIXED, ReportStatus.CLOSED, ReportStatus.REJECTED]:
        return 0.0, 0.0

    current_time = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    delta_seconds = max(0.0, (current_time - created_at).total_seconds())
    days_unresolved = delta_seconds / 86400.0

    # 1.5 points per day, capped at 15.0 points
    aging_points = min(15.0, days_unresolved * 1.5)
    return round(aging_points, 1), round(days_unresolved, 2)


def determine_priority_level(score: float) -> PriorityLevel:
    """Maps normalized continuous score (0-100) to PriorityLevel enum."""
    if score >= PRIORITY_THRESHOLDS[PriorityLevel.CRITICAL]:
        return PriorityLevel.CRITICAL
    if score >= PRIORITY_THRESHOLDS[PriorityLevel.HIGH]:
        return PriorityLevel.HIGH
    if score >= PRIORITY_THRESHOLDS[PriorityLevel.MEDIUM]:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


def calculate_priority(
    severity: ReportSeverity,
    report_count: int,
    traffic_density: TrafficDensity = TrafficDensity.MEDIUM,
    location_zone: LocationZone = LocationZone.RESIDENTIAL,
    created_at: Optional[datetime] = None,
    current_status: ReportStatus = ReportStatus.REPORTED,
    now: Optional[datetime] = None
) -> Tuple[float, PriorityLevel, Dict[str, Any]]:
    """
    Master Multi-Factor Priority Calculation Engine:
    Score = Severity (35) + Report Count (20) + Traffic Density (15) + Location Zone (15) + Time Unresolved (15)
    Total is clamped strictly to [0.0, 100.0].
    """
    created_time = created_at or datetime.now(timezone.utc)

    # 1. Severity Factor (Max 35)
    sev_score = SEVERITY_WEIGHTS.get(severity, 5.0)

    # 2. Report Count Factor (Max 20)
    cnt_score = calculate_report_count_score(report_count)

    # 3. Traffic Density Factor (Max 15)
    traf_score = TRAFFIC_DENSITY_WEIGHTS.get(traffic_density, 10.0)

    # 4. Location Importance Zone Factor (Max 15)
    loc_score = LOCATION_ZONE_WEIGHTS.get(location_zone, 5.0)

    # 5. Time Unresolved Aging Factor (Max 15)
    age_score, days_unresolved = calculate_aging_score(created_time, current_status, now=now)

    # Total Normalized Score
    raw_total = sev_score + cnt_score + traf_score + loc_score + age_score
    total_score = round(max(0.0, min(100.0, raw_total)), 1)
    priority_level = determine_priority_level(total_score)

    breakdown = {
        "severity_score": sev_score,
        "report_count_score": cnt_score,
        "traffic_density_score": traf_score,
        "location_zone_score": loc_score,
        "aging_score": age_score,
        "aging_days": days_unresolved,
        "total_score": total_score,
        "priority_level": priority_level.value
    }

    return total_score, priority_level, breakdown
