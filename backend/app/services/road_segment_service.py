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
    issues: List[Issue],
    reports: Optional[List[RoadReport]] = None
) -> Tuple[float, str, str]:
    """
    Computes real-time dynamic road segment health index (0 to 100) and risk level
    based on the normalized 6-factor Road Health Engine.
    - 100.0: Pristine / Hazard-free
    - Health status: EXCELLENT (85-100), GOOD (70-84), FAIR (50-69), POOR (30-49), CRITICAL (0-29)
    - Risk levels: LOW, MODERATE, HIGH, SEVERE
    """
    from app.services.road_health_service import calculate_detailed_road_health
    score, status, risk, _, _ = calculate_detailed_road_health(
        segment,
        issues,
        reports or (segment.reports if hasattr(segment, "reports") and segment.reports else [])
    )
    return score, status, risk


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
