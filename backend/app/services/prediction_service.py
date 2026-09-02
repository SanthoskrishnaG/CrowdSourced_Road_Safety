from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.road_segment import RoadSegment, RoadType, RoadImportance
from app.models.issue import Issue
from app.models.report import RoadReport, ReportSeverity, ReportStatus
from app.services.road_health_service import calculate_detailed_road_health
from app.schemas.road_risk import (
    RoadRiskFactor,
    RoadRiskResponse,
    RoadRiskPredictionItem,
    RoadRiskPredictionSummary,
    RoadRiskPredictionListResponse,
)
from ml.prediction.model import load_road_risk_model, RoadRiskModel


def extract_segment_features(
    segment: RoadSegment,
    issues: List[Issue],
    reports: List[RoadReport]
) -> TupleDict:
    """
    Constructs feature dictionary from live corridor state for ML inference.
    """
    now_utc = datetime.now(timezone.utc)
    cutoff_7d = now_utc - timedelta(days=7)
    cutoff_30d = now_utc - timedelta(days=30)

    # Health score
    health_score, _, _, _, metrics = calculate_detailed_road_health(segment, issues, reports)

    hist_reports = len(reports)
    reports_30d = sum(
        1 for r in reports
        if (r.created_at.replace(tzinfo=timezone.utc) if r.created_at.tzinfo is None else r.created_at) >= cutoff_30d
    )
    reports_7d = sum(
        1 for r in reports
        if (r.created_at.replace(tzinfo=timezone.utc) if r.created_at.tzinfo is None else r.created_at) >= cutoff_7d
    )

    hist_issues = len(issues)
    active_issues = metrics.active_issues_count
    crit_issues = metrics.critical_issues_count
    high_issues = metrics.high_issues_count

    crit_ratio = (
        (crit_issues * 1.0 + high_issues * 0.5) / max(1, active_issues)
        if active_issues > 0 else 0.0
    )

    length_km = max(0.1, (segment.length_meters or 1000.0) / 1000.0)
    issue_density = active_issues / length_km
    report_density = hist_reports / length_km
    incident_freq_weekly = reports_30d / 4.28

    avg_res_hours = metrics.avg_resolution_hours or 48.0

    features = {
        "historical_reports_count": hist_reports,
        "reports_last_30d": reports_30d,
        "reports_last_7d": reports_7d,
        "historical_issues_count": hist_issues,
        "active_issues_count": active_issues,
        "critical_issues_count": crit_issues,
        "high_issues_count": high_issues,
        "critical_severity_ratio": round(crit_ratio, 3),
        "road_health_score": round(health_score, 1),
        "avg_resolution_hours": round(avg_res_hours, 1),
        "road_type": segment.road_type.value if hasattr(segment.road_type, "value") else str(segment.road_type),
        "importance": segment.importance.value if hasattr(segment.importance, "value") else str(segment.importance),
        "length_km": round(length_km, 2),
        "speed_limit_kmh": segment.speed_limit_kmh or 50,
        "issue_density_per_km": round(issue_density, 2),
        "report_density_per_km": round(report_density, 2),
        "incident_frequency_weekly": round(incident_freq_weekly, 2),
    }

    return features, health_score, active_issues


TupleDict = Any


def get_road_risk_prediction(db: Session, segment: RoadSegment) -> RoadRiskResponse:
    """
    Computes individual road risk prediction, explainability factors, and model metadata.
    """
    issues = db.query(Issue).filter(Issue.road_segment_id == segment.id).all()
    reports = db.query(RoadReport).filter(RoadReport.road_segment_id == segment.id).all()

    features, health_score, active_issues_count = extract_segment_features(segment, issues, reports)

    model = load_road_risk_model()
    pred_res = model.predict(features)

    factors = [
        RoadRiskFactor(
            factor_name=f["factor_name"],
            impact_percentage=f["impact_percentage"],
            description=f["description"],
        )
        for f in pred_res.get("contributing_factors", [])
    ]

    return RoadRiskResponse(
        road_id=segment.id,
        name=segment.name,
        road_type=segment.road_type,
        importance=segment.importance,
        risk_score=pred_res["risk_score"],
        risk_level=pred_res["risk_level"],
        worsening_probability=pred_res["worsening_probability"],
        current_health_score=health_score,
        active_issues_count=active_issues_count,
        contributing_factors=factors,
        features_used=pred_res.get("features_used"),
        model_version=pred_res.get("model_version", RoadRiskModel.MODEL_VERSION),
        disclaimer=pred_res.get(
            "disclaimer",
            "Application-generated predictive estimate for prioritization. Does not claim certainty or replace official engineering inspections."
        )
    )


def get_all_road_risk_predictions(
    db: Session,
    risk_level: Optional[str] = None,
    road_type: Optional[RoadType] = None,
    sort_by: str = "risk_desc",
) -> RoadRiskPredictionListResponse:
    """
    Evaluates and ranks predictive deterioration risks across all registered road segments.
    """
    query = db.query(RoadSegment)
    if road_type:
        query = query.filter(RoadSegment.road_type == road_type)

    segments = query.all()

    if not segments:
        return RoadRiskPredictionListResponse(
            summary=RoadRiskPredictionSummary(
                total_evaluated_segments=0,
                high_or_critical_risk_count=0,
                average_risk_score=0.0,
                critical_risk_count=0,
                high_risk_count=0,
                medium_risk_count=0,
                low_risk_count=0,
            ),
            predictions=[],
            model_version=RoadRiskModel.MODEL_VERSION,
        )

    model = load_road_risk_model()
    evaluated_items: List[RoadRiskPredictionItem] = []
    level_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    total_risk = 0.0

    for seg in segments:
        issues = db.query(Issue).filter(Issue.road_segment_id == seg.id).all()
        reports = db.query(RoadReport).filter(RoadReport.road_segment_id == seg.id).all()

        features, health_score, active_issues_count = extract_segment_features(seg, issues, reports)
        pred_res = model.predict(features)

        r_score = pred_res["risk_score"]
        r_level = pred_res["risk_level"]
        w_prob = pred_res["worsening_probability"]

        level_counts[r_level] = level_counts.get(r_level, 0) + 1
        total_risk += r_score

        top_factor_desc: Optional[str] = None
        factors = pred_res.get("contributing_factors", [])
        if factors:
            top_factor_desc = f"{factors[0]['factor_name']} (+{factors[0]['impact_percentage']}%)"

        item = RoadRiskPredictionItem(
            road_id=seg.id,
            name=seg.name,
            road_type=seg.road_type,
            importance=seg.importance,
            risk_score=r_score,
            risk_level=r_level,
            worsening_probability=w_prob,
            current_health_score=health_score,
            active_issues_count=active_issues_count,
            top_contributing_factor=top_factor_desc,
        )

        # Filter by risk_level if requested
        if risk_level is None or r_level.upper() == risk_level.upper():
            evaluated_items.append(item)

    total_evaluated = len(segments)
    avg_risk = round(total_risk / total_evaluated, 1)

    # Sorting
    if sort_by == "risk_asc":
        evaluated_items.sort(key=lambda x: x.risk_score)
    elif sort_by == "health_asc":
        evaluated_items.sort(key=lambda x: x.current_health_score)
    else:  # risk_desc default
        evaluated_items.sort(key=lambda x: x.risk_score, reverse=True)

    summary = RoadRiskPredictionSummary(
        total_evaluated_segments=total_evaluated,
        high_or_critical_risk_count=level_counts.get("CRITICAL", 0) + level_counts.get("HIGH", 0),
        average_risk_score=avg_risk,
        critical_risk_count=level_counts.get("CRITICAL", 0),
        high_risk_count=level_counts.get("HIGH", 0),
        medium_risk_count=level_counts.get("MEDIUM", 0),
        low_risk_count=level_counts.get("LOW", 0),
    )

    return RoadRiskPredictionListResponse(
        summary=summary,
        predictions=evaluated_items,
        model_version=model.metadata.get("version", RoadRiskModel.MODEL_VERSION),
        disclaimer=(
            "Application-generated predictive estimate for prioritization. "
            "Does not claim certainty or replace official engineering inspections."
        ),
    )
