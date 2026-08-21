from datetime import datetime, timezone, timedelta
from typing import Optional
from app.models.issue import Issue, PriorityLevel
from app.models.report import ReportStatus
from app.schemas.intelligence import SLATrackingInfo

# Municipal Resolution SLA Deadlines
SLA_HOURS_MATRIX = {
    PriorityLevel.CRITICAL: 24,    # 24 Hours
    PriorityLevel.HIGH: 48,        # 48 Hours
    PriorityLevel.MEDIUM: 120,     # 5 Days
    PriorityLevel.LOW: 336         # 14 Days
}


def calculate_sla_info(issue: Issue) -> SLATrackingInfo:
    """
    Calculates target resolution SLA, remaining hours, breach status,
    and automatic escalation triggers for an issue.
    """
    # If issue is REOPENED, set an urgent 24h SLA target
    if issue.status == ReportStatus.REOPENED:
        target_hours = 24
    else:
        target_hours = SLA_HOURS_MATRIX.get(issue.priority_level, 72)

    created_time = issue.created_at or datetime.now(timezone.utc)
    if created_time.tzinfo is None:
        created_time = created_time.replace(tzinfo=timezone.utc)
    deadline_at = created_time + timedelta(hours=target_hours)
    now = datetime.now(timezone.utc)

    remaining_hours = (deadline_at - now).total_seconds() / 3600.0

    if issue.status in [ReportStatus.FIXED, ReportStatus.CLOSED]:
        sla_status = "RESOLVED"
        is_escalated = False
        escalation_reason = None
    elif remaining_hours <= 0.0:
        sla_status = "BREACHED"
        is_escalated = True
        escalation_reason = f"SLA Target of {target_hours}h exceeded by {abs(remaining_hours):.1f}h."
    elif remaining_hours <= (target_hours * 0.25):
        sla_status = "APPROACHING_BREACH"
        is_escalated = issue.priority_level == PriorityLevel.CRITICAL
        escalation_reason = "Less than 25% of SLA resolution window remaining." if is_escalated else None
    else:
        sla_status = "ON_TRACK"
        is_escalated = False
        escalation_reason = None

    # Force escalation if reopened
    if issue.status == ReportStatus.REOPENED:
        is_escalated = True
        escalation_reason = "Citizen disputed repair quality. Issue reopened for urgent re-inspection."

    return SLATrackingInfo(
        priority_level=issue.priority_level.value,
        sla_target_hours=target_hours,
        deadline_at=deadline_at,
        remaining_hours=round(remaining_hours, 1),
        sla_status=sla_status,
        is_escalated=is_escalated,
        escalation_reason=escalation_reason
    )
