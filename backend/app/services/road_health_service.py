import math
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.issue import Issue, PriorityLevel, TrafficDensity, LocationZone
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.schemas.intelligence import RoadHealthResponse, AccidentRiskPrediction
from app.utils.geo import haversine_distance


def calculate_road_health_score(
    latitude: float,
    longitude: float,
    db: Session,
    radius_meters: float = 1000.0
) -> RoadHealthResponse:
    """
    Computes a localized 0-100 Road Health Score for a geographic corridor
    based on hazard density, severity penalties, and recurring issues.
    """
    lat_delta = (radius_meters / 111000.0)
    lon_delta = lat_delta / math.cos(math.radians(latitude)) if abs(latitude) < 89.0 else lat_delta

    nearby_issues = (
        db.query(Issue)
        .filter(
            Issue.status.notin_([ReportStatus.CLOSED, ReportStatus.REJECTED]),
            Issue.latitude.between(latitude - lat_delta, latitude + lat_delta),
            Issue.longitude.between(longitude - lon_delta, longitude + lon_delta)
        )
        .all()
    )

    base_score = 100.0
    active_count = 0
    pothole_count = 0

    for issue in nearby_issues:
        dist = haversine_distance(latitude, longitude, issue.latitude, issue.longitude)
        if dist <= radius_meters:
            active_count += 1
            if issue.category == ReportCategory.POTHOLE:
                pothole_count += 1

            # Severity-weighted health degradation
            if issue.severity == ReportSeverity.CRITICAL:
                base_score -= 14.0
            elif issue.severity == ReportSeverity.HIGH:
                base_score -= 9.0
            elif issue.severity == ReportSeverity.MEDIUM:
                base_score -= 4.0
            else:
                base_score -= 1.5

    # Clamping
    health_score = max(15.0, min(100.0, base_score))

    # Determine status
    if health_score >= 85.0:
        status = "EXCELLENT"
    elif health_score >= 70.0:
        status = "GOOD"
    elif health_score >= 50.0:
        status = "FAIR"
    elif health_score >= 30.0:
        status = "POOR"
    else:
        status = "CRITICAL"

    area_km2 = math.pi * ((radius_meters / 1000.0) ** 2)
    density = round(active_count / area_km2, 2)

    return RoadHealthResponse(
        latitude=latitude,
        longitude=longitude,
        segment_name="Urban Transit Corridor",
        health_score=round(health_score, 1),
        health_status=status,
        hazard_density_per_km2=density,
        active_hazards_count=active_count,
        recurring_pothole_cluster=pothole_count >= 2
    )


def predict_accident_risk(
    issue: Issue,
    road_health_score: float = 75.0,
    has_critical_language: bool = False
) -> AccidentRiskPrediction:
    """
    Predictive Model evaluating the likelihood of vehicular crashes or severe
    traffic gridlock caused by the infrastructure hazard.
    """
    factors = []
    base_risk = 0.10

    # 1. Hazard Type Risk Weight
    cat_risk_map = {
        ReportCategory.POTHOLE: 0.25,
        ReportCategory.FLOODING: 0.30,
        ReportCategory.ROAD_DAMAGE: 0.20,
        ReportCategory.BLOCKED_ROAD: 0.35,
        ReportCategory.BROKEN_STREETLIGHT: 0.18,
        ReportCategory.DAMAGED_SIGN: 0.12,
        ReportCategory.GARBAGE: 0.08,
        ReportCategory.OTHER: 0.05
    }
    cat_risk = cat_risk_map.get(issue.category, 0.15)
    base_risk += cat_risk
    factors.append(f"Hazard Category: {issue.category.value} (+{int(cat_risk * 100)}% risk)")

    # 2. Severity Factor
    if issue.severity == ReportSeverity.CRITICAL:
        base_risk += 0.25
        factors.append("Critical Structural Severity (+25% risk)")
    elif issue.severity == ReportSeverity.HIGH:
        base_risk += 0.15
        factors.append("High Hazard Severity (+15% risk)")

    # 3. Traffic Density Multiplier
    if issue.traffic_density == TrafficDensity.HEAVY:
        base_risk += 0.20
        factors.append("Heavy Traffic Flow Area (+20% risk)")
    elif issue.traffic_density == TrafficDensity.MEDIUM:
        base_risk += 0.10

    # 4. Sensitive Zone Check
    is_pedestrian_risk = False
    if issue.location_zone in [LocationZone.SCHOOL, LocationZone.HOSPITAL]:
        base_risk += 0.15
        is_pedestrian_risk = True
        factors.append(f"Sensitive Pedestrian Zone: {issue.location_zone.value} (+15% risk)")
    elif issue.location_zone == LocationZone.JUNCTION:
        base_risk += 0.12
        factors.append("Traffic Junction Bottleneck (+12% risk)")

    # 5. Road Health Index Deficit
    if road_health_score < 40.0:
        base_risk += 0.15
        factors.append("Degraded Road Health Corridor (+15% risk)")
    elif road_health_score < 60.0:
        base_risk += 0.08

    # 6. NLP Critical Language
    if has_critical_language:
        base_risk += 0.10
        factors.append("Citizen NLP Urgency Markers Detected (+10% risk)")

    # Clamping probability to [0.05, 0.98]
    risk_prob = max(0.05, min(0.98, base_risk))

    # Risk level classification
    if risk_prob >= 0.75:
        risk_lvl = "SEVERE"
    elif risk_prob >= 0.50:
        risk_lvl = "HIGH"
    elif risk_prob >= 0.30:
        risk_lvl = "MODERATE"
    else:
        risk_lvl = "LOW"

    delay_minutes = round(risk_prob * 35.0, 1)

    return AccidentRiskPrediction(
        risk_probability=round(risk_prob, 3),
        risk_level=risk_lvl,
        primary_risk_factors=factors,
        estimated_traffic_delay_min=delay_minutes,
        pedestrian_risk_flag=is_pedestrian_risk
    )
