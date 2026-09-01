import math
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.road_segment import RoadSegment, RoadType, RoadImportance
from app.models.issue import Issue
from app.models.report import RoadReport, ReportSeverity, ReportStatus
from app.schemas.road_segment import (
    RoadSegmentResponse,
    RoadSegmentDetailResponse,
    RoadSegmentCreate,
)
from app.utils.geo import (
    haversine_distance,
    point_to_segment_distance,
    find_nearest_road_segment,
)

SEVERITY_WEIGHTS = {
    ReportSeverity.LOW: 5.0,
    ReportSeverity.MEDIUM: 12.0,
    ReportSeverity.HIGH: 22.0,
    ReportSeverity.CRITICAL: 35.0,
}

IMPORTANCE_MULTIPLIERS = {
    RoadImportance.CRITICAL: 1.5,
    RoadImportance.HIGH: 1.25,
    RoadImportance.MEDIUM: 1.0,
    RoadImportance.LOW: 0.8,
}


def calculate_segment_health(
    segment: RoadSegment,
    issues: List[Issue]
) -> Tuple[float, str, str]:
    """
    Computes real-time dynamic road segment health index (0 to 100) and risk level
    based on active open hazards, aggregate severity penalties, and corridor importance.
    - 100.0: Pristine / Hazard-free
    - Health status: EXCELLENT (85-100), GOOD (70-84), FAIR (50-69), POOR (30-49), CRITICAL (0-29)
    - Risk levels: LOW, MODERATE, HIGH, SEVERE
    """
    active_issues = [
        iss for iss in issues
        if iss.status not in [ReportStatus.FIXED, ReportStatus.CLOSED, ReportStatus.REJECTED]
    ]

    if not active_issues:
        return 100.0, "EXCELLENT", "LOW"

    importance_mult = IMPORTANCE_MULTIPLIERS.get(segment.importance, 1.0)
    total_penalty = 0.0

    for iss in active_issues:
        sev_weight = SEVERITY_WEIGHTS.get(iss.severity, 10.0)
        # Factor in recurrence / multiple reports on same issue
        report_boost = 1.0 + (math.log(iss.report_count + 1) * 0.3)
        total_penalty += (sev_weight * report_boost)

    total_penalty *= importance_mult

    # Length normalization if segment is long (diminishes penalty per kilometer)
    length_km = (segment.length_meters or 1000.0) / 1000.0
    if length_km > 1.0:
        total_penalty = total_penalty / (1.0 + math.log(length_km))

    health_score = max(0.0, min(100.0, round(100.0 - total_penalty, 1)))

    if health_score >= 85.0:
        status = "EXCELLENT"
        risk = "LOW"
    elif health_score >= 70.0:
        status = "GOOD"
        risk = "MODERATE"
    elif health_score >= 50.0:
        status = "FAIR"
        risk = "HIGH"
    elif health_score >= 30.0:
        status = "POOR"
        risk = "HIGH"
    else:
        status = "CRITICAL"
        risk = "SEVERE"

    return health_score, status, risk


def build_segment_response(db: Session, segment: RoadSegment) -> RoadSegmentResponse:
    """Constructs enriched RoadSegmentResponse with computed health and active issue count."""
    active_issues = [
        iss for iss in segment.issues
        if iss.status not in [ReportStatus.FIXED, ReportStatus.CLOSED, ReportStatus.REJECTED]
    ]
    health_score, status, risk = calculate_segment_health(segment, segment.issues)

    return RoadSegmentResponse(
        id=segment.id,
        name=segment.name,
        start_latitude=segment.start_latitude,
        start_longitude=segment.start_longitude,
        end_latitude=segment.end_latitude,
        end_longitude=segment.end_longitude,
        road_type=segment.road_type,
        importance=segment.importance,
        speed_limit_kmh=segment.speed_limit_kmh,
        length_meters=segment.length_meters,
        active_issues_count=len(active_issues),
        health_score=health_score,
        health_status=status,
        risk_level=risk,
        created_at=segment.created_at,
        updated_at=segment.updated_at
    )


def build_segment_detail_response(db: Session, segment: RoadSegment) -> RoadSegmentDetailResponse:
    """Constructs full RoadSegmentDetailResponse with associated issues and recent reports."""
    base_res = build_segment_response(db, segment)
    
    # Active/Recent issues
    issues_list = (
        db.query(Issue)
        .filter(Issue.road_segment_id == segment.id)
        .order_by(desc(Issue.priority_score))
        .all()
    )

    # Recent reports
    reports_list = (
        db.query(RoadReport)
        .filter(RoadReport.road_segment_id == segment.id)
        .order_by(desc(RoadReport.created_at))
        .limit(20)
        .all()
    )

    return RoadSegmentDetailResponse(
        **base_res.model_dump(),
        issues=issues_list,
        recent_reports=reports_list
    )


def create_road_segment(db: Session, segment_in: RoadSegmentCreate) -> RoadSegment:
    """Creates a new municipal road segment, computing length in meters automatically."""
    length = haversine_distance(
        segment_in.start_latitude, segment_in.start_longitude,
        segment_in.end_latitude, segment_in.end_longitude
    )

    segment = RoadSegment(
        name=segment_in.name,
        start_latitude=segment_in.start_latitude,
        start_longitude=segment_in.start_longitude,
        end_latitude=segment_in.end_latitude,
        end_longitude=segment_in.end_longitude,
        road_type=segment_in.road_type,
        importance=segment_in.importance,
        speed_limit_kmh=segment_in.speed_limit_kmh,
        length_meters=length
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


def associate_point_with_segment(
    db: Session,
    latitude: float,
    longitude: float,
    max_distance_meters: float = 1000.0
) -> Optional[RoadSegment]:
    """Finds and returns the nearest road segment within threshold."""
    return find_nearest_road_segment(db, latitude, longitude, max_distance_meters=max_distance_meters)
