import json
import math
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.report import ReportSeverity, ReportStatus
from app.models.issue import Issue, PriorityLevel, LocationZone, TrafficDensity
from app.models.priority_history import PriorityHistory
from app.services.weather.models import WeatherData, WeatherCondition


# ============================================================================
# PHASE 14: NORMALIZED 9-FACTOR WEIGHT BUDGET (TOTAL MAX = 100.0)
# ============================================================================
# 1. Severity:                Max 25.0 pts
# 2. Independent Reports:     Max 15.0 pts
# 3. Road Health Degradation: Max 15.0 pts
# 4. Traffic Importance:      Max 10.0 pts
# 5. Location Importance:     Max 10.0 pts
# 6. Time Unresolved (Age):   Max 10.0 pts
# 7. Predicted ML Risk:       Max 10.0 pts
# 8. Weather Conditions:      Max  5.0 pts
# 9. Citizen Confirmations:   Max  5.0 pts
# ----------------------------------------------------------------------------
# TOTAL MAXIMUM = 100.0 Points
# ============================================================================

SEVERITY_WEIGHTS_V2: Dict[ReportSeverity, float] = {
    ReportSeverity.CRITICAL: 25.0,
    ReportSeverity.HIGH: 18.0,
    ReportSeverity.MEDIUM: 10.0,
    ReportSeverity.LOW: 4.0,
}

TRAFFIC_DENSITY_WEIGHTS_V2: Dict[TrafficDensity, float] = {
    TrafficDensity.HEAVY: 10.0,
    TrafficDensity.MEDIUM: 7.0,
    TrafficDensity.LOW: 3.0,
}

LOCATION_ZONE_WEIGHTS_V2: Dict[LocationZone, float] = {
    LocationZone.HOSPITAL: 10.0,
    LocationZone.SCHOOL: 9.0,
    LocationZone.MAIN_ROAD: 7.0,
    LocationZone.JUNCTION: 7.0,
    LocationZone.RESIDENTIAL: 4.0,
    LocationZone.OTHER: 2.0,
}

# 4-Tier Categorical Thresholds
PRIORITY_THRESHOLDS_V2 = {
    PriorityLevel.CRITICAL: 75.0,
    PriorityLevel.HIGH: 50.0,
    PriorityLevel.MEDIUM: 25.0,
    PriorityLevel.LOW: 0.0,
}


class TrafficDensityService:
    """
    Traffic density evaluation service.
    Provides heuristic and configurable traffic density lookups.
    """

    @classmethod
    def get_traffic_density(cls, latitude: float, longitude: float, address: Optional[str] = None) -> TrafficDensity:
        if address:
            addr_lower = address.lower()
            if any(term in addr_lower for term in ["highway", "expressway", "arterial", "ring road", "main road", "junction"]):
                return TrafficDensity.HEAVY
            if any(term in addr_lower for term in ["avenue", "boulevard", "street", "cross"]):
                return TrafficDensity.MEDIUM
        return TrafficDensity.MEDIUM


def calculate_report_count_score(report_count: int) -> float:
    """
    Computes saturating bonus for multiple independent citizen reports (Max 15.0 pts).
    1 report  -> 5.0 pts
    2 reports -> 9.0 pts
    3 reports -> 12.0 pts
    4 reports -> 14.0 pts
    5+ reports -> 15.0 pts
    """
    if report_count <= 0:
        return 0.0
    if report_count == 1:
        return 5.0
    score = min(15.0, 5.0 + math.log(report_count, 2) * 4.3)
    return round(score, 1)


def calculate_road_health_penalty_score(road_health_score: Optional[float]) -> float:
    """
    Computes priority urgency based on surrounding corridor degradation (Max 15.0 pts).
    Road Health = 100 -> 0.0 pts (Pristine corridor)
    Road Health = 50  -> 7.5 pts
    Road Health = 0   -> 15.0 pts (Severely degraded corridor)
    """
    if road_health_score is None:
        return 5.0  # Moderate default baseline when unassigned
    clamped_health = max(0.0, min(100.0, road_health_score))
    penalty = (100.0 - clamped_health) / 100.0 * 15.0
    return round(penalty, 1)


def calculate_aging_score(
    created_at: datetime,
    status: ReportStatus,
    now: Optional[datetime] = None
) -> Tuple[float, float]:
    """
    Computes time unresolved aging penalty (Max 10.0 pts).
    Adds +1.0 pt per 24 hours unresolved up to 10.0 pts ceiling (10+ days).
    Resolved/closed issues receive 0 aging points.
    """
    if status in [ReportStatus.FIXED, ReportStatus.CLOSED, ReportStatus.REJECTED]:
        return 0.0, 0.0

    current_time = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    delta_seconds = max(0.0, (current_time - created_at).total_seconds())
    days_unresolved = delta_seconds / 86400.0

    aging_points = min(10.0, days_unresolved * 1.0)
    return round(aging_points, 1), round(days_unresolved, 2)


def calculate_predicted_risk_score(predicted_risk: Optional[float]) -> float:
    """
    Computes machine learning predicted deterioration/accident risk points (Max 10.0 pts).
    Risk 0   -> 0.0 pts
    Risk 50  -> 5.0 pts
    Risk 100 -> 10.0 pts
    """
    if predicted_risk is None:
        return 3.0  # Baseline expectation
    clamped_risk = max(0.0, min(100.0, predicted_risk))
    return round((clamped_risk / 100.0) * 10.0, 1)


def calculate_weather_score(weather: Optional[WeatherData]) -> Tuple[float, str]:
    """
    Computes active weather hazard multiplier points (Max 5.0 pts).
    Severe Alert / Torrential Rain -> 5.0 pts
    Rain / Wet Pavement           -> 3.5 pts
    Cloudy / Humid                -> 1.5 pts
    Clear Dry                     -> 0.0 pts
    """
    if not weather:
        return 1.0, "Standard dry atmospheric baseline"

    if weather.is_severe or weather.rainfall_mm_per_hour >= 15.0:
        return 5.0, f"Severe weather alert: {weather.severe_weather_alert or 'Intense Rain'} ({weather.rainfall_mm_per_hour} mm/h)"
    elif weather.condition in [WeatherCondition.HEAVY_RAIN, WeatherCondition.THUNDERSTORM] or weather.rainfall_mm_per_hour >= 5.0:
        return 4.0, f"Heavy precipitation ({weather.rainfall_mm_per_hour} mm/h) accelerating erosion"
    elif weather.condition == WeatherCondition.RAIN or weather.rainfall_mm_per_hour > 0.0:
        return 2.5, f"Wet road surface ({weather.rainfall_mm_per_hour} mm/h)"
    elif weather.condition in [WeatherCondition.FOG, WeatherCondition.CLOUDY]:
        return 1.0, f"Overcast visibility ({weather.condition.value})"
    return 0.0, "Clear dry pavement"


def calculate_citizen_confirmations_score(confirmations_count: int) -> float:
    """
    Computes community reverification / confirmation bonus (Max 5.0 pts).
    +1.0 pt per citizen confirmation up to 5 confirmations.
    """
    count = max(0, confirmations_count)
    return float(min(5.0, count * 1.0))


def determine_priority_level(score: float) -> PriorityLevel:
    """Maps normalized continuous score (0-100) to PriorityLevel enum."""
    if score >= PRIORITY_THRESHOLDS_V2[PriorityLevel.CRITICAL]:
        return PriorityLevel.CRITICAL
    if score >= PRIORITY_THRESHOLDS_V2[PriorityLevel.HIGH]:
        return PriorityLevel.HIGH
    if score >= PRIORITY_THRESHOLDS_V2[PriorityLevel.MEDIUM]:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


def calculate_priority(
    severity: ReportSeverity,
    report_count: int,
    traffic_density: TrafficDensity = TrafficDensity.MEDIUM,
    location_zone: LocationZone = LocationZone.RESIDENTIAL,
    created_at: Optional[datetime] = None,
    current_status: ReportStatus = ReportStatus.REPORTED,
    now: Optional[datetime] = None,
    road_health_score: Optional[float] = None,
    predicted_risk_score: Optional[float] = None,
    weather_data: Optional[WeatherData] = None,
    confirmations_count: int = 0
) -> Tuple[float, PriorityLevel, Dict[str, Any]]:
    """
    Master Multi-Factor Priority Calculation Engine:
    Score = Severity (25) + Report Count (15) + Road Health (15) + Traffic (10)
          + Location Zone (10) + Aging (10) + ML Risk (10) + Weather (5) + Confirmations (5)
    Total is clamped strictly to [0.0, 100.0].
    """
    created_time = created_at or datetime.now(timezone.utc)

    # 1. Severity (Max 25)
    sev_score = SEVERITY_WEIGHTS_V2.get(severity, 4.0)

    # 2. Report Count (Max 15)
    cnt_score = calculate_report_count_score(report_count)

    # 3. Road Health Degradation (Max 15)
    health_score_pts = calculate_road_health_penalty_score(road_health_score)

    # 4. Traffic Density (Max 10)
    traf_score = TRAFFIC_DENSITY_WEIGHTS_V2.get(traffic_density, 7.0)

    # 5. Location Importance Zone (Max 10)
    loc_score = LOCATION_ZONE_WEIGHTS_V2.get(location_zone, 4.0)

    # 6. Time Unresolved Aging (Max 10)
    age_score, days_unresolved = calculate_aging_score(created_time, current_status, now=now)

    # 7. Predicted ML Risk (Max 10)
    ml_risk_pts = calculate_predicted_risk_score(predicted_risk_score)

    # 8. Weather Condition (Max 5)
    weather_pts, weather_desc = calculate_weather_score(weather_data)

    # 9. Citizen Confirmations (Max 5)
    conf_score = calculate_citizen_confirmations_score(confirmations_count)

    # Total Normalized Score
    raw_total = (
        sev_score + cnt_score + health_score_pts + traf_score +
        loc_score + age_score + ml_risk_pts + weather_pts + conf_score
    )
    total_score = round(max(0.0, min(100.0, raw_total)), 1)
    priority_level = determine_priority_level(total_score)

    # Build Granular Explainability Factor Breakdown
    factors = [
        {
            "factor_name": "Severity",
            "earned_points": sev_score,
            "max_points": 25.0,
            "percentage": round((sev_score / 25.0) * 100, 1),
            "description": f"Hazard severity rated as {severity.value}"
        },
        {
            "factor_name": "Independent Reports",
            "earned_points": cnt_score,
            "max_points": 15.0,
            "percentage": round((cnt_score / 15.0) * 100, 1),
            "description": f"{report_count} independent citizen submission(s)"
        },
        {
            "factor_name": "Road Health Degradation",
            "earned_points": health_score_pts,
            "max_points": 15.0,
            "percentage": round((health_score_pts / 15.0) * 100, 1),
            "description": f"Corridor health {road_health_score if road_health_score is not None else 'Unmonitored'}/100"
        },
        {
            "factor_name": "Traffic Importance",
            "earned_points": traf_score,
            "max_points": 10.0,
            "percentage": round((traf_score / 10.0) * 100, 1),
            "description": f"{traffic_density.value} traffic throughput"
        },
        {
            "factor_name": "Location Zone",
            "earned_points": loc_score,
            "max_points": 10.0,
            "percentage": round((loc_score / 10.0) * 100, 1),
            "description": f"Zone classified as {location_zone.value}"
        },
        {
            "factor_name": "Time Unresolved (Aging)",
            "earned_points": age_score,
            "max_points": 10.0,
            "percentage": round((age_score / 10.0) * 100, 1),
            "description": f"{days_unresolved} day(s) awaiting resolution"
        },
        {
            "factor_name": "Predicted ML Risk",
            "earned_points": ml_risk_pts,
            "max_points": 10.0,
            "percentage": round((ml_risk_pts / 10.0) * 100, 1),
            "description": f"ML risk index: {predicted_risk_score if predicted_risk_score is not None else 'Default'}/100"
        },
        {
            "factor_name": "Weather Conditions",
            "earned_points": weather_pts,
            "max_points": 5.0,
            "percentage": round((weather_pts / 5.0) * 100, 1),
            "description": weather_desc
        },
        {
            "factor_name": "Citizen Confirmations",
            "earned_points": conf_score,
            "max_points": 5.0,
            "percentage": round((conf_score / 5.0) * 100, 1),
            "description": f"{confirmations_count} community confirmation(s)"
        }
    ]

    # Top Drivers (factors with highest percentage contribution)
    sorted_factors = sorted(factors, key=lambda f: f["percentage"], reverse=True)
    top_drivers = [
        f"{f['factor_name']}: {f['earned_points']}/{f['max_points']} ({f['percentage']}%)"
        for f in sorted_factors[:3] if f["earned_points"] > 0
    ]

    breakdown = {
        "severity_score": sev_score,
        "severity_max": 25.0,
        "report_count_score": cnt_score,
        "report_count_max": 15.0,
        "road_health_score": health_score_pts,
        "road_health_max": 15.0,
        "traffic_density_score": traf_score,
        "traffic_density_max": 10.0,
        "location_zone_score": loc_score,
        "location_zone_max": 10.0,
        "aging_score": age_score,
        "aging_max": 10.0,
        "aging_days": days_unresolved,
        "predicted_risk_score": ml_risk_pts,
        "predicted_risk_max": 10.0,
        "weather_condition_score": weather_pts,
        "weather_condition_max": 5.0,
        "citizen_confirmations_score": conf_score,
        "citizen_confirmations_max": 5.0,
        "total_score": total_score,
        "priority_level": priority_level.value,
        "factors": factors,
        "top_contributing_drivers": top_drivers
    }

    return total_score, priority_level, breakdown


class PriorityRecalculationService:
    """
    Manages priority recalculation, explainability logging, and priority history auditing.
    """

    @classmethod
    def recalculate_and_log_priority(
        cls,
        db: Session,
        issue: Issue,
        trigger_event: str = "MANUAL_RECALCULATION",
        weather_data: Optional[WeatherData] = None,
        road_health_score: Optional[float] = None,
        predicted_risk_score: Optional[float] = None
    ) -> Tuple[float, PriorityLevel, Dict[str, Any], PriorityHistory]:
        """
        Recalculates issue priority, updates the issue record, and creates an audit snapshot in PriorityHistory.
        """
        prev_score = issue.priority_score
        prev_level = issue.priority_level

        # Calculate new score
        new_score, new_level, breakdown = calculate_priority(
            severity=issue.severity,
            report_count=issue.report_count,
            traffic_density=issue.traffic_density,
            location_zone=issue.location_zone,
            created_at=issue.created_at,
            current_status=issue.status,
            road_health_score=road_health_score,
            predicted_risk_score=predicted_risk_score,
            weather_data=weather_data,
            confirmations_count=getattr(issue, "confirmations_count", 0)
        )

        # Update Issue
        issue.priority_score = new_score
        issue.priority_level = new_level

        # Record History Snapshot
        history_entry = PriorityHistory(
            issue_id=issue.id,
            previous_score=prev_score,
            new_score=new_score,
            previous_level=prev_level,
            new_level=new_level,
            trigger_event=trigger_event,
            factor_breakdown=json.dumps(breakdown)
        )
        db.add(history_entry)
        db.commit()
        db.refresh(issue)
        db.refresh(history_entry)

        return new_score, new_level, breakdown, history_entry
