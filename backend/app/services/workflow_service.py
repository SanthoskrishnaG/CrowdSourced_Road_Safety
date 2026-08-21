from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.report import ReportCategory, ReportSeverity, ReportStatus, RoadReport
from app.models.issue import Issue, PriorityLevel, LocationZone, TrafficDensity
from app.models.assignment import AuthorityDepartment, IssueAssignment
from app.models.history import IssueStatusHistory
from app.models.user import User, UserRole
from app.services.priority_engine import calculate_priority


# Automated Department Routing Map
CATEGORY_DEPARTMENT_ROUTING: Dict[ReportCategory, AuthorityDepartment] = {
    ReportCategory.POTHOLE: AuthorityDepartment.ROAD_DEPARTMENT,
    ReportCategory.ROAD_DAMAGE: AuthorityDepartment.ROAD_DEPARTMENT,
    ReportCategory.BROKEN_STREETLIGHT: AuthorityDepartment.ELECTRICAL_DEPARTMENT,
    ReportCategory.GARBAGE: AuthorityDepartment.SANITATION_DEPARTMENT,
    ReportCategory.DAMAGED_SIGN: AuthorityDepartment.TRAFFIC_DEPARTMENT,
    ReportCategory.BLOCKED_ROAD: AuthorityDepartment.TRAFFIC_DEPARTMENT,
    ReportCategory.OBSTRUCTION: AuthorityDepartment.TRAFFIC_DEPARTMENT,
    ReportCategory.FLOODING: AuthorityDepartment.DRAINAGE_DEPARTMENT,
    ReportCategory.OTHER: AuthorityDepartment.GENERAL_WORKS,
}

# State Machine Transition Rules
VALID_TRANSITIONS: Dict[ReportStatus, List[ReportStatus]] = {
    ReportStatus.REPORTED: [ReportStatus.VERIFIED, ReportStatus.REJECTED],
    ReportStatus.VERIFIED: [ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS, ReportStatus.REJECTED],
    ReportStatus.ASSIGNED: [ReportStatus.IN_PROGRESS, ReportStatus.VERIFIED, ReportStatus.REJECTED],
    ReportStatus.IN_PROGRESS: [ReportStatus.FIXED, ReportStatus.ASSIGNED, ReportStatus.REJECTED],
    ReportStatus.FIXED: [ReportStatus.CLOSED, ReportStatus.IN_PROGRESS],
    ReportStatus.CLOSED: [ReportStatus.VERIFIED],  # Admin reopen
    ReportStatus.REJECTED: [ReportStatus.REPORTED],  # Admin reopen
}


def get_recommended_department(category: ReportCategory) -> AuthorityDepartment:
    """Returns the default municipal department mapped to the hazard category."""
    return CATEGORY_DEPARTMENT_ROUTING.get(category, AuthorityDepartment.GENERAL_WORKS)


def validate_status_transition(current_status: ReportStatus, new_status: ReportStatus, user_role: UserRole):
    """
    Ensures state machine transitions strictly follow allowed paths.
    """
    if current_status == new_status:
        return

    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: Cannot change from '{current_status.value}' to '{new_status.value}'."
        )

    # Reopening closed or rejected issues requires ADMIN role
    if current_status in [ReportStatus.CLOSED, ReportStatus.REJECTED] and user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reopen CLOSED or REJECTED issues."
        )


def log_status_history(
    db: Session,
    issue: Issue,
    previous_status: Optional[ReportStatus],
    new_status: ReportStatus,
    changed_by_user: User,
    comment: Optional[str] = None
) -> IssueStatusHistory:
    """
    Records an immutable audit entry in the issue_status_history table.
    """
    history_entry = IssueStatusHistory(
        issue_id=issue.id,
        previous_status=previous_status,
        new_status=new_status,
        changed_by_user_id=changed_by_user.id,
        comment=comment,
        created_at=datetime.now(timezone.utc)
    )
    db.add(history_entry)
    return history_entry


def update_issue_priority(issue: Issue):
    """
    Recalculates and sets priority score and priority level on an issue.
    """
    score, level, _ = calculate_priority(
        severity=issue.severity,
        report_count=issue.report_count,
        traffic_density=issue.traffic_density,
        location_zone=issue.location_zone,
        created_at=issue.created_at,
        current_status=issue.status
    )
    issue.priority_score = score
    issue.priority_level = level


def verify_issue(
    db: Session,
    issue: Issue,
    current_user: User,
    department: Optional[AuthorityDepartment] = None,
    notes: Optional[str] = None
) -> Issue:
    """
    Transitions issue from REPORTED -> VERIFIED.
    """
    validate_status_transition(issue.status, ReportStatus.VERIFIED, current_user.role)

    prev_status = issue.status
    issue.status = ReportStatus.VERIFIED
    if department:
        issue.assigned_department = department
    elif not issue.assigned_department:
        issue.assigned_department = get_recommended_department(issue.category)

    issue.updated_at = datetime.now(timezone.utc)
    update_issue_priority(issue)

    log_status_history(
        db=db,
        issue=issue,
        previous_status=prev_status,
        new_status=ReportStatus.VERIFIED,
        changed_by_user=current_user,
        comment=notes or "Issue verified by municipal authority."
    )

    # Sync contributing reports to VERIFIED
    for rep in issue.reports:
        if rep.status == ReportStatus.REPORTED:
            rep.status = ReportStatus.VERIFIED

    db.commit()
    db.refresh(issue)
    return issue


def assign_issue(
    db: Session,
    issue: Issue,
    department: AuthorityDepartment,
    current_user: User,
    assigned_to_user_id: Optional[UUID] = None,
    notes: Optional[str] = None
) -> IssueAssignment:
    """
    Assigns or reassigns an issue to a municipal department and responsible officer.
    Sets issue status to ASSIGNED if currently VERIFIED.
    """
    # Deactivate any existing active assignments for this issue
    for existing_assignment in issue.assignments:
        if existing_assignment.is_active:
            existing_assignment.is_active = False

    new_assignment = IssueAssignment(
        issue_id=issue.id,
        department=department,
        assigned_to_user_id=assigned_to_user_id,
        assigned_by_user_id=current_user.id,
        assigned_at=datetime.now(timezone.utc),
        notes=notes,
        is_active=True
    )
    db.add(new_assignment)

    issue.assigned_department = department

    prev_status = issue.status
    if issue.status in [ReportStatus.REPORTED, ReportStatus.VERIFIED]:
        issue.status = ReportStatus.ASSIGNED
        log_status_history(
            db=db,
            issue=issue,
            previous_status=prev_status,
            new_status=ReportStatus.ASSIGNED,
            changed_by_user=current_user,
            comment=f"Assigned to {department.value}. {notes or ''}".strip()
        )
    else:
        # Just record the assignment update note in history
        log_status_history(
            db=db,
            issue=issue,
            previous_status=issue.status,
            new_status=issue.status,
            changed_by_user=current_user,
            comment=f"Reassigned to {department.value}. {notes or ''}".strip()
        )

    issue.updated_at = datetime.now(timezone.utc)
    update_issue_priority(issue)

    # Sync contributing reports to ASSIGNED if needed
    for rep in issue.reports:
        if rep.status in [ReportStatus.REPORTED, ReportStatus.VERIFIED]:
            rep.status = ReportStatus.ASSIGNED

    db.commit()
    db.refresh(issue)
    db.refresh(new_assignment)
    return new_assignment


def transition_issue_status(
    db: Session,
    issue: Issue,
    new_status: ReportStatus,
    current_user: User,
    comment: Optional[str] = None
) -> Issue:
    """
    Executes a validated state transition on an issue and logs history.
    """
    validate_status_transition(issue.status, new_status, current_user.role)

    prev_status = issue.status
    issue.status = new_status
    issue.updated_at = datetime.now(timezone.utc)
    update_issue_priority(issue)

    log_status_history(
        db=db,
        issue=issue,
        previous_status=prev_status,
        new_status=new_status,
        changed_by_user=current_user,
        comment=comment or f"Status changed from {prev_status.value} to {new_status.value}."
    )

    # Cascade status update to all linked reports
    for rep in issue.reports:
        rep.status = new_status

    db.commit()
    db.refresh(issue)
    return issue


def add_issue_comment(
    db: Session,
    issue: Issue,
    current_user: User,
    comment: str
) -> IssueStatusHistory:
    """
    Adds an authority/admin audit note or comment to the issue without changing status.
    """
    history_entry = log_status_history(
        db=db,
        issue=issue,
        previous_status=issue.status,
        new_status=issue.status,
        changed_by_user=current_user,
        comment=comment
    )
    issue.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(history_entry)
    return history_entry
