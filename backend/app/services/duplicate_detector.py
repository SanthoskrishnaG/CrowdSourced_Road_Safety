import math
import os
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.utils.geo import haversine_distance
from app.models.report import RoadReport, ReportCategory, ReportSeverity, ReportStatus
from app.models.issue import Issue

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
            # Convert to grayscale and resize to 9x8
            img = img.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(img.tobytes())
            # Compute difference between adjacent pixels in each row
            diff = []
            for row in range(8):
                for col in range(8):
                    pixel_left = pixels[row * 9 + col]
                    pixel_right = pixels[row * 9 + col + 1]
                    diff.append(pixel_left > pixel_right)
            
            # Convert boolean array to 64-bit integer
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
    # Hamming distance via XOR and popcount
    hamming_dist = bin(hash1 ^ hash2).count('1')
    similarity = max(0.0, 1.0 - (hamming_dist / 64.0))
    return round(similarity, 4)


def calculate_location_score(distance_meters: float, threshold_meters: float) -> float:
    """
    Calculates continuous location similarity score based on Haversine distance.
    Distance <= 15m gets 1.0, linearly decays to 0.0 at threshold_meters.
    """
    if distance_meters <= 15.0:
        return 1.0
    if distance_meters >= threshold_meters:
        return 0.0
    return round(1.0 - ((distance_meters - 15.0) / (threshold_meters - 15.0)), 4)


def calculate_category_score(cat1: ReportCategory, cat2: ReportCategory) -> float:
    """
    Calculates category similarity based on exact and taxonomy relationships.
    """
    if cat1 == cat2:
        return 1.0
    return RELATED_CATEGORIES.get((cat1, cat2), 0.0)


def calculate_time_score(dt1: datetime, dt2: datetime) -> float:
    """
    Calculates time similarity decay based on difference in report timestamps.
    """
    delta_hours = abs((dt1 - dt2).total_seconds()) / 3600.0
    if delta_hours <= 24.0:
        return 1.0
    if delta_hours <= 168.0:  # 7 days
        return 0.8
    if delta_hours <= 720.0:  # 30 days
        return 0.4
    return 0.1


def calculate_duplicate_score(
    report: RoadReport,
    candidate_issue: Issue,
    report_image_hash: Optional[int] = None,
    issue_image_hash: Optional[int] = None
) -> Tuple[float, dict]:
    """
    Calculates multi-factor composite duplicate score between a new report and an existing issue.
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
    img_score = calculate_image_similarity(report_image_hash, issue_image_hash)

    # 5. NLP Semantic Description Similarity
    from app.services.nlp_service import calculate_text_similarity
    text_score = calculate_text_similarity(report.description or "", candidate_issue.description or candidate_issue.title or "")

    # Dynamic Weight Allocation
    w_loc = settings.WEIGHT_LOCATION
    w_cat = settings.WEIGHT_CATEGORY
    w_time = settings.WEIGHT_TIME
    w_img = settings.WEIGHT_IMAGE if img_score is not None else 0.0
    w_text = 0.10 if text_score > 0.0 else 0.0

    total_weight = w_loc + w_cat + w_time + w_img + w_text
    composite_score = (
        (loc_score * w_loc)
        + (cat_score * w_cat)
        + (time_score * w_time)
        + ((img_score or 0.0) * w_img)
        + (text_score * w_text)
    ) / total_weight

    score_breakdown = {
        "distance_meters": dist_meters,
        "location_score": loc_score,
        "category_score": cat_score,
        "time_score": time_score,
        "image_score": img_score,
        "text_similarity_score": text_score,
        "composite_score": round(composite_score, 4)
    }

    return round(composite_score, 4), score_breakdown


def find_duplicate_issue(
    db: Session,
    report: RoadReport
) -> Tuple[Optional[Issue], float, Optional[dict]]:
    """
    Searches for an existing active canonical Issue matching the report.
    Returns (Best Matching Issue, Score, Score Breakdown) or (None, 0.0, None).
    """
    # Search radius: approximate +/- 0.001 degrees lat/lon (~110 meters)
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

    # Get primary image hash of new report if available
    report_img_hash = None
    if report.images:
        first_img_path = os.path.join(settings.UPLOAD_DIRECTORY, report.images[0].file_path.replace("uploads/", ""))
        report_img_hash = calculate_dhash(first_img_path)

    best_issue = None
    max_score = 0.0
    best_breakdown = None

    for issue in candidate_issues:
        # Check first image of first report in issue
        issue_img_hash = None
        if issue.reports and issue.reports[0].images:
            issue_img_path = os.path.join(settings.UPLOAD_DIRECTORY, issue.reports[0].images[0].file_path.replace("uploads/", ""))
            issue_img_hash = calculate_dhash(issue_img_path)

        score, breakdown = calculate_duplicate_score(report, issue, report_img_hash, issue_img_hash)
        if score > max_score:
            max_score = score
            best_issue = issue
            best_breakdown = breakdown

    if max_score >= settings.DUPLICATE_SCORE_THRESHOLD:
        return best_issue, max_score, best_breakdown

    return None, max_score, best_breakdown


from app.services.priority_engine import calculate_priority, TrafficDensityService
from app.services.workflow_service import get_recommended_department


def process_report_issue(db: Session, report: RoadReport) -> Issue:
    """
    Executes the duplicate detection workflow upon report creation:
    1. Evaluates candidate issues nearby.
    2. Links report to existing Issue if duplicate score >= threshold.
    3. Otherwise, creates a new canonical Issue and links report to it.
    """
    matched_issue, score, _ = find_duplicate_issue(db, report)

    if matched_issue:
        # Attach to existing issue
        report.issue_id = matched_issue.id
        matched_issue.report_count += 1
        matched_issue.updated_at = datetime.now(timezone.utc)
        
        # Upgrade severity if incoming report reports higher severity
        if SEVERITY_ORDER.get(report.severity, 0) > SEVERITY_ORDER.get(matched_issue.severity, 0):
            matched_issue.severity = report.severity

        # Recalculate priority score and priority level with updated report count & severity
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
        # Determine initial traffic density and default department
        traffic_density = TrafficDensityService.get_traffic_density(
            report.latitude, report.longitude, report.address
        )
        rec_department = get_recommended_department(report.category)

        # Calculate initial priority score and level
        p_score, p_level, _ = calculate_priority(
            severity=report.severity,
            report_count=1,
            traffic_density=traffic_density,
            created_at=datetime.now(timezone.utc),
            current_status=ReportStatus.REPORTED
        )

        # Create a new canonical issue
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
