import math
import os
import re
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.utils.geo import haversine_distance
from app.models.report import RoadReport, ReportCategory, ReportSeverity, ReportStatus
from app.models.issue import Issue
from app.models.user import User
from app.schemas.duplicate import (
    DuplicateTier,
    ExplainableComponentScores,
    DuplicateCandidateItem,
)
from app.services.nlp_service import calculate_text_similarity, tokenize_text
from app.services.priority_engine import calculate_priority, TrafficDensityService
from app.services.workflow_service import get_recommended_department

# Related category taxonomy map (bidirectional lookup)
RELATED_CATEGORIES = {
    (ReportCategory.POTHOLE, ReportCategory.ROAD_DAMAGE): 0.6,
    (ReportCategory.ROAD_DAMAGE, ReportCategory.POTHOLE): 0.6,
    (ReportCategory.BLOCKED_ROAD, ReportCategory.OBSTRUCTION): 0.6,
    (ReportCategory.OBSTRUCTION, ReportCategory.BLOCKED_ROAD): 0.6,
    (ReportCategory.BLOCKED_ROAD, ReportCategory.FLOODING): 0.5,
    (ReportCategory.FLOODING, ReportCategory.BLOCKED_ROAD): 0.5,
    (ReportCategory.DAMAGED_SIGN, ReportCategory.ROAD_DAMAGE): 0.4,
    (ReportCategory.ROAD_DAMAGE, ReportCategory.DAMAGED_SIGN): 0.4,
}

SEVERITY_ORDER = {
    ReportSeverity.LOW: 1,
    ReportSeverity.MEDIUM: 2,
    ReportSeverity.HIGH: 3,
    ReportSeverity.CRITICAL: 4
}


def calculate_dhash(image_path: str) -> Optional[int]:
    """
    Computes a 64-bit difference hash (dHash) for an image.
    Resizes image to 9x8 grayscale and computes horizontal gradient.
    """
    if not os.path.exists(image_path):
        return None
    try:
        with Image.open(image_path) as img:
            img = img.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(img.tobytes())
            diff = []
            for row in range(8):
                for col in range(8):
                    pixel_left = pixels[row * 9 + col]
                    pixel_right = pixels[row * 9 + col + 1]
                    diff.append(pixel_left > pixel_right)
            
            hash_val = 0
            for bit in diff:
                hash_val = (hash_val << 1) | int(bit)
            return hash_val
    except Exception:
        return None


def calculate_image_similarity(hash1: Optional[int], hash2: Optional[int]) -> Optional[float]:
    """
    Calculates normalized perceptual similarity from two 64-bit dHashes using Hamming distance.
    Returns value between 0.0 (completely dissimilar) and 1.0 (identical).
    """
    if hash1 is None or hash2 is None:
        return None
    hamming_dist = bin(hash1 ^ hash2).count('1')
    similarity = max(0.0, 1.0 - (hamming_dist / 64.0))
    return round(similarity, 4)


def calculate_location_score(distance_meters: float, threshold_meters: float) -> float:
    """
    Calculates continuous location similarity score (0.0 to 1.0) based on Haversine distance.
    Distance <= 15m gets 1.0, linearly decays to 0.0 at threshold_meters.
    """
    if distance_meters <= 15.0:
        return 1.0
    if distance_meters >= threshold_meters:
        return 0.0
    return round(1.0 - ((distance_meters - 15.0) / (threshold_meters - 15.0)), 4)


def calculate_category_score(cat1: ReportCategory, cat2: ReportCategory) -> float:
    """
    Calculates category similarity (0.0 to 1.0) based on exact and taxonomy relationships.
    """
    if cat1 == cat2:
        return 1.0
    return RELATED_CATEGORIES.get((cat1, cat2), 0.0)


def calculate_time_score(dt1: datetime, dt2: datetime) -> float:
    """
    Calculates time similarity decay (0.0 to 1.0) based on difference in report timestamps.
    """
    delta_hours = abs((dt1 - dt2).total_seconds()) / 3600.0
    if delta_hours <= 24.0:
        return 1.0
    if delta_hours <= 168.0:  # 7 days
        return 0.8
    if delta_hours <= 720.0:  # 30 days
        return 0.4
    return 0.1


def calculate_road_segment_score(addr1: Optional[str], addr2: Optional[str]) -> float:
    """
    Computes road corridor / street name token matching score in [0.0, 1.0].
    """
    if not addr1 or not addr2:
        return 0.5  # Neutral default when address metadata is unavailable

    tokens1 = set(tokenize_text(addr1))
    tokens2 = set(tokenize_text(addr2))
    if not tokens1 or not tokens2:
        return 0.5

    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return round(intersection / union, 4) if union > 0 else 0.0


def classify_duplicate_tier(score_100: float) -> DuplicateTier:
    """
    Classifies duplicate score into canonical tiers:
    0–39: NOT_DUPLICATE
    40–69: POTENTIAL_DUPLICATE
    70–100: LIKELY_DUPLICATE
    """
    if score_100 >= 70.0:
        return DuplicateTier.LIKELY_DUPLICATE
    elif score_100 >= 40.0:
        return DuplicateTier.POTENTIAL_DUPLICATE
    else:
        return DuplicateTier.NOT_DUPLICATE


def calculate_duplicate_score(
    report: RoadReport,
    candidate_issue: Issue,
    report_image_hash: Optional[int] = None,
    issue_image_hash: Optional[int] = None
) -> Tuple[float, Dict[str, Any], ExplainableComponentScores]:
    """
    Calculates 6-Factor composite duplicate score between a report and candidate issue.
    Components:
    1. Location score (0-100)
    2. Category score (0-100)
    3. Image score (0-100)
    4. NLP Description score (0-100)
    5. Time score (0-100)
    6. Road segment score (0-100)
    """
    # 1. Geographic Distance
    dist_meters = haversine_distance(
        report.latitude, report.longitude,
        candidate_issue.latitude, candidate_issue.longitude
    )
    loc_score = calculate_location_score(dist_meters, settings.DUPLICATE_DISTANCE_THRESHOLD_METERS)

    # 2. Category Similarity
    cat_score = calculate_category_score(report.category, candidate_issue.category)

    # 3. Time Proximity
    time_score = calculate_time_score(report.created_at, candidate_issue.created_at)

    # 4. Image Similarity
    img_sim = calculate_image_similarity(report_image_hash, issue_image_hash)
    effective_img_sim = img_sim if img_sim is not None else 0.50

    # 5. NLP Semantic Description Similarity
    desc1 = report.description or report.title or ""
    desc2 = candidate_issue.description or candidate_issue.title or ""
    text_score = calculate_text_similarity(desc1, desc2)

    # 6. Road Segment Similarity
    road_score = calculate_road_segment_score(report.address, candidate_issue.address)

    # Convert component metrics to 0-100 scale
    loc_100 = round(loc_score * 100.0, 1)
    cat_100 = round(cat_score * 100.0, 1)
    time_100 = round(time_score * 100.0, 1)
    img_100 = round(effective_img_sim * 100.0, 1)
    text_100 = round(text_score * 100.0, 1)
    road_100 = round(road_score * 100.0, 1)

    # Weighted Composite Normalization (Location: 30%, Category: 20%, Description: 20%, Image: 15%, Time: 10%, Road Segment: 5%)
    overall_100 = (
        (loc_100 * 0.30) +
        (cat_100 * 0.20) +
        (text_100 * 0.20) +
        (img_100 * 0.15) +
        (time_100 * 0.10) +
        (road_100 * 0.05)
    )
    overall_100 = round(overall_100, 1)
    tier = classify_duplicate_tier(overall_100)

    explainability = ExplainableComponentScores(
        location=loc_100,
        category=cat_100,
        image=img_100,
        description=text_100,
        time=time_100,
        road_segment=road_100,
        overall=overall_100,
        classification=tier
    )

    composite_normalized = round(overall_100 / 100.0, 4)
    breakdown = {
        "distance_meters": dist_meters,
        "location_score": loc_score,
        "category_score": cat_score,
        "time_score": time_score,
        "image_score": img_sim,
        "text_similarity_score": text_score,
        "road_segment_score": road_score,
        "composite_score": composite_normalized,
        "composite_score_100": overall_100,
        "classification": tier.value,
        "explainability": explainability.model_dump()
    }

    return composite_normalized, breakdown, explainability


def find_duplicate_issue(
    db: Session,
    report: RoadReport
) -> Tuple[Optional[Issue], float, Optional[dict]]:
    """
    Searches for an existing active canonical Issue matching the report.
    Returns (Best Matching Issue, Score, Score Breakdown) or (None, 0.0, None).
    """
    lat_delta = (settings.DUPLICATE_DISTANCE_THRESHOLD_METERS / 111000.0) * 1.5
    lon_delta = lat_delta / math.cos(math.radians(report.latitude)) if abs(report.latitude) < 89.0 else lat_delta

    candidate_issues = (
        db.query(Issue)
        .filter(
            Issue.status.notin_([ReportStatus.FIXED, ReportStatus.CLOSED, ReportStatus.REJECTED]),
            Issue.latitude.between(report.latitude - lat_delta, report.latitude + lat_delta),
            Issue.longitude.between(report.longitude - lon_delta, report.longitude + lon_delta)
        )
        .all()
    )

    if not candidate_issues:
        return None, 0.0, None

    report_img_hash = None
    if report.images:
        first_img_path = os.path.join(settings.UPLOAD_DIRECTORY, report.images[0].file_path.replace("uploads/", ""))
        report_img_hash = calculate_dhash(first_img_path)

    best_issue = None
    max_score = 0.0
    best_breakdown = None

    for issue in candidate_issues:
        issue_img_hash = None
        if issue.reports and issue.reports[0].images:
            issue_img_path = os.path.join(settings.UPLOAD_DIRECTORY, issue.reports[0].images[0].file_path.replace("uploads/", ""))
            issue_img_hash = calculate_dhash(issue_img_path)

        score, breakdown, _ = calculate_duplicate_score(report, issue, report_img_hash, issue_img_hash)
        if score > max_score:
            max_score = score
            best_issue = issue
            best_breakdown = breakdown

    if max_score >= settings.DUPLICATE_SCORE_THRESHOLD:
        return best_issue, max_score, best_breakdown

    return None, max_score, best_breakdown


def process_report_issue(db: Session, report: RoadReport) -> Issue:
    """
    Executes automatic duplicate detection upon report creation:
    1. Evaluates candidate issues nearby.
    2. Links report to existing Issue if duplicate score >= threshold (Likely duplicate).
    3. Otherwise, creates a new canonical Issue and links report to it.
    """
    matched_issue, score, _ = find_duplicate_issue(db, report)

    if matched_issue:
        report.issue_id = matched_issue.id
        matched_issue.report_count += 1
        matched_issue.updated_at = datetime.now(timezone.utc)

        if SEVERITY_ORDER.get(report.severity, 0) > SEVERITY_ORDER.get(matched_issue.severity, 0):
            matched_issue.severity = report.severity

        p_score, p_level, _ = calculate_priority(
            severity=matched_issue.severity,
            report_count=matched_issue.report_count,
            traffic_density=matched_issue.traffic_density,
            location_zone=matched_issue.location_zone,
            created_at=matched_issue.created_at,
            current_status=matched_issue.status
        )
        matched_issue.priority_score = p_score
        matched_issue.priority_level = p_level

        db.commit()
        db.refresh(matched_issue)
        return matched_issue
    else:
        traffic_density = TrafficDensityService.get_traffic_density(
            report.latitude, report.longitude, report.address
        )
        rec_department = get_recommended_department(report.category)

        p_score, p_level, _ = calculate_priority(
            severity=report.severity,
            report_count=1,
            traffic_density=traffic_density,
            created_at=datetime.now(timezone.utc),
            current_status=ReportStatus.REPORTED
        )

        new_issue = Issue(
            category=report.category,
            title=report.title,
            description=report.description,
            latitude=report.latitude,
            longitude=report.longitude,
            address=report.address,
            severity=report.severity,
            status=ReportStatus.REPORTED,
            report_count=1,
            priority_score=p_score,
            priority_level=p_level,
            traffic_density=traffic_density,
            assigned_department=rec_department
        )
        db.add(new_issue)
        db.commit()
        db.refresh(new_issue)

        report.issue_id = new_issue.id
        db.commit()
        return new_issue


def get_duplicate_candidates_for_report(db: Session, report: RoadReport) -> List[DuplicateCandidateItem]:
    """
    Retrieves all candidate issues within search radius of a report,
    returning computed duplicate scores, explainable component metrics, and tier classification.
    """
    lat_delta = (settings.DUPLICATE_DISTANCE_THRESHOLD_METERS / 111000.0) * 2.0
    lon_delta = lat_delta / math.cos(math.radians(report.latitude)) if abs(report.latitude) < 89.0 else lat_delta

    candidate_issues = (
        db.query(Issue)
        .filter(
            Issue.latitude.between(report.latitude - lat_delta, report.latitude + lat_delta),
            Issue.longitude.between(report.longitude - lon_delta, report.longitude + lon_delta)
        )
        .all()
    )

    report_img_hash = None
    if report.images:
        first_img_path = os.path.join(settings.UPLOAD_DIRECTORY, report.images[0].file_path.replace("uploads/", ""))
        report_img_hash = calculate_dhash(first_img_path)

    results: List[DuplicateCandidateItem] = []
    for issue in candidate_issues:
        issue_img_hash = None
        if issue.reports and issue.reports[0].images:
            issue_img_path = os.path.join(settings.UPLOAD_DIRECTORY, issue.reports[0].images[0].file_path.replace("uploads/", ""))
            issue_img_hash = calculate_dhash(issue_img_path)

        score, breakdown, explainability = calculate_duplicate_score(report, issue, report_img_hash, issue_img_hash)
        dist = haversine_distance(report.latitude, report.longitude, issue.latitude, issue.longitude)

        tier = explainability.classification
        is_match = (tier == DuplicateTier.LIKELY_DUPLICATE)
        requires_review = (tier == DuplicateTier.POTENTIAL_DUPLICATE)

        item = DuplicateCandidateItem(
            issue_id=issue.id,
            issue_title=issue.title,
            issue_category=issue.category,
            issue_severity=issue.severity,
            issue_status=issue.status,
            latitude=issue.latitude,
            longitude=issue.longitude,
            distance_meters=dist,
            duplicate_score=explainability.overall,
            classification=tier,
            is_match=is_match,
            requires_authority_review=requires_review,
            explainability=explainability,
            score_breakdown=breakdown
        )
        results.append(item)

    results.sort(key=lambda x: x.duplicate_score, reverse=True)
    return results


def merge_report_into_issue(
    db: Session,
    report: RoadReport,
    target_issue: Issue,
    current_user: User,
    merge_reason: Optional[str] = None
) -> Issue:
    """
    Authority action to approve merge of a report into a target canonical Issue.
    Updates report links, aggregates counts, upgrades severity if needed, recalculates priority.
    """
    prev_issue_id = report.issue_id
    report.issue_id = target_issue.id
    target_issue.report_count += 1
    target_issue.updated_at = datetime.now(timezone.utc)

    # Upgrade severity if incoming report is higher
    if SEVERITY_ORDER.get(report.severity, 0) > SEVERITY_ORDER.get(target_issue.severity, 0):
        target_issue.severity = report.severity

    # Recalculate priority
    p_score, p_level, _ = calculate_priority(
        severity=target_issue.severity,
        report_count=target_issue.report_count,
        traffic_density=target_issue.traffic_density,
        location_zone=target_issue.location_zone,
        created_at=target_issue.created_at,
        current_status=target_issue.status
    )
    target_issue.priority_score = p_score
    target_issue.priority_level = p_level

    # If previous issue is left empty, clean up
    if prev_issue_id and prev_issue_id != target_issue.id:
        prev_issue = db.query(Issue).filter(Issue.id == prev_issue_id).first()
        if prev_issue and len(prev_issue.reports) <= 1:
            db.delete(prev_issue)

    db.commit()
    db.refresh(target_issue)
    return target_issue


def reject_report_duplicate(
    db: Session,
    report: RoadReport,
    current_user: User,
    rejection_reason: Optional[str] = None
) -> Issue:
    """
    Authority action to reject duplicate merge. Ensures the report possesses its own
    independent canonical Issue and will not be automatically collapsed.
    """
    current_issue = report.issue
    # If the report is currently sharing an issue with other reports, split it off
    if current_issue and current_issue.report_count > 1:
        current_issue.report_count -= 1
        traffic_density = TrafficDensityService.get_traffic_density(
            report.latitude, report.longitude, report.address
        )
        rec_dept = get_recommended_department(report.category)
        p_score, p_level, _ = calculate_priority(
            severity=report.severity,
            report_count=1,
            traffic_density=traffic_density,
            created_at=datetime.now(timezone.utc),
            current_status=ReportStatus.REPORTED
        )
        new_issue = Issue(
            category=report.category,
            title=report.title,
            description=report.description,
            latitude=report.latitude,
            longitude=report.longitude,
            address=report.address,
            severity=report.severity,
            status=ReportStatus.REPORTED,
            report_count=1,
            priority_score=p_score,
            priority_level=p_level,
            traffic_density=traffic_density,
            assigned_department=rec_dept
        )
        db.add(new_issue)
        db.flush()
        report.issue_id = new_issue.id
        db.commit()
        db.refresh(new_issue)
        return new_issue

    return current_issue
