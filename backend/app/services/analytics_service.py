import math
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_

from app.models.issue import Issue, PriorityLevel
from app.models.report import RoadReport, ReportCategory, ReportSeverity, ReportStatus
from app.models.history import IssueStatusHistory
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    CategoryDistributionItem,
    CategoryAnalyticsResponse,
    SeverityDistributionItem,
    SeverityAnalyticsResponse,
    StatusDistributionItem,
    StatusAnalyticsResponse,
    ResolutionAnalyticsResponse,
    GeographicDensityItem,
    GeographicAnalyticsResponse,
    TrendPoint,
    TrendsAnalyticsResponse,
    HeatmapPoint,
    HeatmapAnalyticsResponse,
)


def get_summary_metrics(db: Session) -> AnalyticsSummaryResponse:
    """
    Computes high-level KPI dashboard metrics using fast SQL database aggregations.
    """
    total_reports = db.query(func.count(RoadReport.id)).scalar() or 0
    total_issues = db.query(func.count(Issue.id)).scalar() or 0

    # Active issues: not fixed, closed, or rejected
    active_issues = (
        db.query(func.count(Issue.id))
        .filter(
            Issue.status.in_(
                [
                    ReportStatus.REPORTED,
                    ReportStatus.VERIFIED,
                    ReportStatus.ASSIGNED,
                    ReportStatus.IN_PROGRESS,
                ]
            )
        )
        .scalar()
        or 0
    )

    # Critical issues (priority CRITICAL or severity CRITICAL)
    critical_issues = (
        db.query(func.count(Issue.id))
        .filter(
            or_(
                Issue.priority_level == PriorityLevel.CRITICAL,
                Issue.severity == ReportSeverity.CRITICAL,
            )
        )
        .scalar()
        or 0
    )

    # High priority issues
    high_priority_issues = (
        db.query(func.count(Issue.id))
        .filter(Issue.priority_level == PriorityLevel.HIGH)
        .scalar()
        or 0
    )

    # Awaiting verification
    awaiting_verification = (
        db.query(func.count(Issue.id))
        .filter(Issue.status == ReportStatus.REPORTED)
        .scalar()
        or 0
    )

    # In progress / Assigned
    in_progress_issues = (
        db.query(func.count(Issue.id))
        .filter(
            Issue.status.in_([ReportStatus.IN_PROGRESS, ReportStatus.ASSIGNED])
        )
        .scalar()
        or 0
    )

    # Fixed issues
    fixed_issues = (
        db.query(func.count(Issue.id))
        .filter(Issue.status == ReportStatus.FIXED)
        .scalar()
        or 0
    )

    # Closed issues
    closed_issues = (
        db.query(func.count(Issue.id))
        .filter(Issue.status == ReportStatus.CLOSED)
        .scalar()
        or 0
    )

    # Resolution times
    resolution_data = get_resolution_metrics(db)

    return AnalyticsSummaryResponse(
        total_reports=total_reports,
        total_issues=total_issues,
        active_issues=active_issues,
        critical_issues=critical_issues,
        high_priority_issues=high_priority_issues,
        awaiting_verification=awaiting_verification,
        in_progress_issues=in_progress_issues,
        fixed_issues=fixed_issues,
        closed_issues=closed_issues,
        avg_resolution_time_hours=resolution_data.avg_hours_reported_to_fixed,
        avg_close_time_hours=resolution_data.avg_hours_reported_to_closed,
    )


def get_category_metrics(db: Session) -> CategoryAnalyticsResponse:
    """
    Computes distribution of issues across all problem categories.
    """
    results = (
        db.query(Issue.category, func.count(Issue.id))
        .group_by(Issue.category)
        .all()
    )

    counts_by_cat = {cat.value if hasattr(cat, "value") else str(cat): count for cat, count in results}
    total = sum(counts_by_cat.values())

    categories_list = []
    for cat in ReportCategory:
        cnt = counts_by_cat.get(cat.value, 0)
        pct = round((cnt / total * 100), 2) if total > 0 else 0.0
        categories_list.append(
            CategoryDistributionItem(
                category=cat.value, count=cnt, percentage=pct
            )
        )

    # Sort descending by count
    categories_list.sort(key=lambda x: x.count, reverse=True)

    return CategoryAnalyticsResponse(total=total, categories=categories_list)


def get_severity_metrics(db: Session) -> SeverityAnalyticsResponse:
    """
    Computes distribution of issues by severity level.
    """
    results = (
        db.query(Issue.severity, func.count(Issue.id))
        .group_by(Issue.severity)
        .all()
    )

    counts_by_sev = {sev.value if hasattr(sev, "value") else str(sev): count for sev, count in results}
    total = sum(counts_by_sev.values())

    severities_list = []
    # Desired order: CRITICAL, HIGH, MEDIUM, LOW
    severity_order = [
        ReportSeverity.CRITICAL,
        ReportSeverity.HIGH,
        ReportSeverity.MEDIUM,
        ReportSeverity.LOW,
    ]
    for sev in severity_order:
        cnt = counts_by_sev.get(sev.value, 0)
        pct = round((cnt / total * 100), 2) if total > 0 else 0.0
        severities_list.append(
            SeverityDistributionItem(
                severity=sev.value, count=cnt, percentage=pct
            )
        )

    return SeverityAnalyticsResponse(total=total, severities=severities_list)


def get_status_metrics(db: Session) -> StatusAnalyticsResponse:
    """
    Computes distribution of issues by lifecycle status.
    """
    results = (
        db.query(Issue.status, func.count(Issue.id))
        .group_by(Issue.status)
        .all()
    )

    counts_by_status = {st.value if hasattr(st, "value") else str(st): count for st, count in results}
    total = sum(counts_by_status.values())

    status_order = [
        ReportStatus.REPORTED,
        ReportStatus.VERIFIED,
        ReportStatus.ASSIGNED,
        ReportStatus.IN_PROGRESS,
        ReportStatus.FIXED,
        ReportStatus.CLOSED,
        ReportStatus.REJECTED,
    ]

    statuses_list = []
    for st in status_order:
        cnt = counts_by_status.get(st.value, 0)
        pct = round((cnt / total * 100), 2) if total > 0 else 0.0
        statuses_list.append(
            StatusDistributionItem(status=st.value, count=cnt, percentage=pct)
        )

    return StatusAnalyticsResponse(total=total, statuses=statuses_list)


def get_resolution_metrics(db: Session) -> ResolutionAnalyticsResponse:
    """
    Computes average resolution times (Reported -> Fixed and Reported -> Closed)
    using Pandas data analysis over audit histories and issue records.
    """
    # Fetch status history entries for FIXED and CLOSED
    history_records = (
        db.query(
            IssueStatusHistory.issue_id,
            IssueStatusHistory.new_status,
            IssueStatusHistory.created_at.label("status_time"),
            Issue.category,
            Issue.severity,
            Issue.created_at.label("issue_created_at"),
        )
        .join(Issue, Issue.id == IssueStatusHistory.issue_id)
        .filter(
            IssueStatusHistory.new_status.in_(
                [ReportStatus.FIXED, ReportStatus.CLOSED]
            )
        )
        .all()
    )

    # Fallback to direct Issue table if history is sparse
    if not history_records:
        fixed_issues = (
            db.query(Issue)
            .filter(
                Issue.status.in_([ReportStatus.FIXED, ReportStatus.CLOSED])
            )
            .all()
        )
        if not fixed_issues:
            return ResolutionAnalyticsResponse(total_fixed=0, total_closed=0)

        data = []
        for iss in fixed_issues:
            data.append(
                {
                    "issue_id": str(iss.id),
                    "new_status": iss.status.value,
                    "status_time": iss.updated_at,
                    "category": iss.category.value,
                    "severity": iss.severity.value,
                    "issue_created_at": iss.created_at,
                }
            )
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(
            [
                {
                    "issue_id": str(r.issue_id),
                    "new_status": r.new_status.value if hasattr(r.new_status, "value") else str(r.new_status),
                    "status_time": r.status_time,
                    "category": r.category.value if hasattr(r.category, "value") else str(r.category),
                    "severity": r.severity.value if hasattr(r.severity, "value") else str(r.severity),
                    "issue_created_at": r.issue_created_at,
                }
                for r in history_records
            ]
        )

    if df.empty:
        return ResolutionAnalyticsResponse(total_fixed=0, total_closed=0)

    # Ensure timezone aware / UTC datetimes
    df["status_time"] = pd.to_datetime(df["status_time"], utc=True)
    df["issue_created_at"] = pd.to_datetime(df["issue_created_at"], utc=True)
    df["duration_hours"] = (
        (df["status_time"] - df["issue_created_at"]).dt.total_seconds() / 3600.0
    ).clip(lower=0.0)

    fixed_df = df[df["new_status"] == ReportStatus.FIXED.value]
    closed_df = df[df["new_status"] == ReportStatus.CLOSED.value]

    avg_fixed_hours = (
        round(float(fixed_df["duration_hours"].mean()), 2)
        if not fixed_df.empty
        else None
    )
    avg_fixed_days = (
        round(avg_fixed_hours / 24.0, 2)
        if avg_fixed_hours is not None
        else None
    )

    avg_closed_hours = (
        round(float(closed_df["duration_hours"].mean()), 2)
        if not closed_df.empty
        else None
    )
    avg_closed_days = (
        round(avg_closed_hours / 24.0, 2)
        if avg_closed_hours is not None
        else None
    )

    # Breakdown by category for fixed issues
    by_cat = {}
    if not fixed_df.empty:
        cat_grouped = fixed_df.groupby("category")["duration_hours"].mean()
        for cat, val in cat_grouped.items():
            by_cat[str(cat)] = round(float(val), 2)

    # Breakdown by severity for fixed issues
    by_sev = {}
    if not fixed_df.empty:
        sev_grouped = fixed_df.groupby("severity")["duration_hours"].mean()
        for sev, val in sev_grouped.items():
            by_sev[str(sev)] = round(float(val), 2)

    return ResolutionAnalyticsResponse(
        total_fixed=len(fixed_df),
        total_closed=len(closed_df),
        avg_hours_reported_to_fixed=avg_fixed_hours,
        avg_days_reported_to_fixed=avg_fixed_days,
        avg_hours_reported_to_closed=avg_closed_hours,
        avg_days_reported_to_closed=avg_closed_days,
        by_category=by_cat,
        by_severity=by_sev,
    )


def get_geographic_density(
    db: Session, grid_size: float = 0.01
) -> GeographicAnalyticsResponse:
    """
    Calculates spatial density and hotspots by binning coordinates into geographic clusters.
    Grid size ~ 0.01 deg is approx 1.1 km.
    """
    issues = (
        db.query(
            Issue.latitude,
            Issue.longitude,
            Issue.severity,
            Issue.address,
            Issue.priority_level,
        )
        .filter(Issue.status != ReportStatus.REJECTED)
        .all()
    )

    if not issues:
        return GeographicAnalyticsResponse(total_clusters=0, clusters=[])

    data = [
        {
            "lat_bin": round(iss.latitude / grid_size) * grid_size,
            "lng_bin": round(iss.longitude / grid_size) * grid_size,
            "is_critical": 1
            if (
                iss.severity == ReportSeverity.CRITICAL
                or iss.priority_level == PriorityLevel.CRITICAL
            )
            else 0,
            "address": iss.address or "Urban Area",
        }
        for iss in issues
    ]

    df = pd.DataFrame(data)
    grouped = (
        df.groupby(["lat_bin", "lng_bin"])
        .agg(
            issue_count=("is_critical", "count"),
            critical_count=("is_critical", "sum"),
            sample_address=("address", "first"),
        )
        .reset_index()
    )

    clusters: List[GeographicDensityItem] = []
    for _, row in grouped.iterrows():
        count = int(row["issue_count"])
        crit = int(row["critical_count"])
        if count >= 5 or crit >= 2:
            density = "HIGH"
        elif count >= 2 or crit >= 1:
            density = "MEDIUM"
        else:
            density = "LOW"

        clusters.append(
            GeographicDensityItem(
                latitude=round(float(row["lat_bin"]), 4),
                longitude=round(float(row["lng_bin"]), 4),
                issue_count=count,
                critical_count=crit,
                density_level=density,
                sample_address=str(row["sample_address"])
                if row["sample_address"]
                else None,
            )
        )

    clusters.sort(key=lambda x: (x.critical_count, x.issue_count), reverse=True)
    return GeographicAnalyticsResponse(
        total_clusters=len(clusters), clusters=clusters
    )


def get_trend_analytics(
    db: Session, interval: str = "day", days_back: int = 30
) -> TrendsAnalyticsResponse:
    """
    Computes time-series trend of issue creation and resolution over day, week, or month.
    """
    valid_intervals = ["day", "week", "month"]
    if interval not in valid_intervals:
        interval = "day"

    issues = (
        db.query(Issue.created_at, Issue.severity, Issue.status)
        .order_by(Issue.created_at.asc())
        .all()
    )

    if not issues:
        return TrendsAnalyticsResponse(interval=interval, data=[])

    data = [
        {
            "created_at": iss.created_at,
            "is_critical": 1 if iss.severity == ReportSeverity.CRITICAL else 0,
            "is_resolved": 1
            if iss.status in [ReportStatus.FIXED, ReportStatus.CLOSED]
            else 0,
        }
        for iss in issues
    ]

    df = pd.DataFrame(data)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df.set_index("created_at", inplace=True)

    rule_map = {"day": "D", "week": "W", "month": "ME"}
    rule = rule_map[interval]

    resampled = df.resample(rule).agg(
        count=("is_critical", "count"),
        critical_count=("is_critical", "sum"),
        resolved_count=("is_resolved", "sum"),
    )

    points: List[TrendPoint] = []
    for dt, row in resampled.iterrows():
        if interval == "day":
            period_str = dt.strftime("%Y-%m-%d")
        elif interval == "week":
            period_str = f"Wk of {dt.strftime('%b %d')}"
        else:
            period_str = dt.strftime("%Y-%m")

        points.append(
            TrendPoint(
                period=period_str,
                count=int(row["count"]),
                critical_count=int(row["critical_count"]),
                resolved_count=int(row["resolved_count"]),
            )
        )

    return TrendsAnalyticsResponse(interval=interval, data=points)


def get_heatmap_points(
    db: Session,
    category: Optional[ReportCategory] = None,
    severity: Optional[ReportSeverity] = None,
    status: Optional[ReportStatus] = None,
) -> HeatmapAnalyticsResponse:
    """
    Generates Leaflet-compatible weighted heatmap coordinates based on severity,
    report frequency, and hazard priority.
    """
    query = db.query(Issue).filter(Issue.status != ReportStatus.REJECTED)

    if category:
        query = query.filter(Issue.category == category)
    if severity:
        query = query.filter(Issue.severity == severity)
    if status:
        query = query.filter(Issue.status == status)

    issues = query.all()

    points: List[HeatmapPoint] = []
    severity_weight = {
        ReportSeverity.CRITICAL: 1.0,
        ReportSeverity.HIGH: 0.75,
        ReportSeverity.MEDIUM: 0.5,
        ReportSeverity.LOW: 0.25,
    }

    for iss in issues:
        base_weight = severity_weight.get(iss.severity, 0.4)
        # Factor in report count: each extra duplicate report adds +0.08 intensity (capped at 1.0)
        report_boost = min((iss.report_count - 1) * 0.08, 0.4)
        intensity = min(round(base_weight + report_boost, 2), 1.0)

        points.append(
            HeatmapPoint(
                latitude=iss.latitude,
                longitude=iss.longitude,
                intensity=intensity,
                category=iss.category.value,
                severity=iss.severity.value,
                status=iss.status.value,
                title=iss.title,
            )
        )

    return HeatmapAnalyticsResponse(total_points=len(points), points=points)
