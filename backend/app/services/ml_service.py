import json
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.report import RoadReport, ReportCategory, ReportSeverity
from app.models.image import ReportImage
from app.models.classification import ImageClassification
from app.models.user import User
from app.schemas.classification import (
    ImageQualityMetrics,
    AIAnalysisImageItem,
    ReportAIAnalysisResponse,
)
from ml.inference.service import get_inference_service
from ml.preprocessing.transform import InvalidImageError


def map_category_string_to_enum(cat_str: str) -> ReportCategory:
    """Maps prediction string to ReportCategory Enum safely."""
    try:
        return ReportCategory(cat_str.upper())
    except (ValueError, KeyError):
        return ReportCategory.OTHER


def map_severity_string_to_enum(sev_str: str) -> ReportSeverity:
    """Maps prediction string to ReportSeverity Enum safely."""
    try:
        return ReportSeverity(sev_str.upper())
    except (ValueError, KeyError):
        return ReportSeverity.MEDIUM


def classify_standalone_bytes(image_bytes: bytes) -> Dict[str, Any]:
    """
    Executes real-time ML image classification, severity estimation, and quality diagnostics
    on raw uploaded bytes. Used for preview / instant validation.
    """
    service = get_inference_service()
    unified_res = service.analyze_image_unified(image_bytes)

    category_enum = map_category_string_to_enum(unified_res.category)
    severity_enum = map_severity_string_to_enum(unified_res.severity)

    quality_metrics = ImageQualityMetrics(
        quality_score=unified_res.quality.quality_score,
        is_acceptable=unified_res.quality.is_acceptable,
        blur_score=unified_res.quality.blur_score,
        brightness_score=unified_res.quality.brightness_score,
        contrast_score=unified_res.quality.contrast_score,
        resolution_score=unified_res.quality.resolution_score,
        is_corrupt=unified_res.quality.is_corrupt,
        detected_issues=unified_res.quality.detected_issues,
        recommendation=unified_res.quality.recommendation
    )

    return {
        "predicted_category": category_enum,
        "confidence": unified_res.confidence,
        "probabilities": unified_res.probabilities,
        "model_version": unified_res.model_version,
        "severity": severity_enum,
        "severity_confidence": unified_res.severity_confidence,
        "severity_probabilities": unified_res.severity_probabilities,
        "quality": quality_metrics
    }


def classify_and_store_report_image(
    db: Session,
    image: ReportImage,
    image_bytes: bytes,
    user_suggested_category: Optional[ReportCategory] = None,
    user_suggested_severity: Optional[ReportSeverity] = None
) -> ImageClassification:
    """
    Runs unified AI pipeline (Category + Severity + Quality) on an uploaded image,
    and persists the complete ImageClassification record.
    """
    service = get_inference_service()
    unified_res = service.analyze_image_unified(image_bytes)
    category_enum = map_category_string_to_enum(unified_res.category)
    severity_enum = map_severity_string_to_enum(unified_res.severity)

    existing_classification = (
        db.query(ImageClassification)
        .filter(ImageClassification.image_id == image.id)
        .first()
    )

    if existing_classification:
        existing_classification.predicted_category = category_enum
        existing_classification.confidence = unified_res.confidence
        existing_classification.model_version = unified_res.model_version
        existing_classification.probabilities_json = json.dumps(unified_res.probabilities)

        existing_classification.predicted_severity = severity_enum
        existing_classification.severity_confidence = unified_res.severity_confidence
        existing_classification.severity_model_version = unified_res.severity_model_version
        existing_classification.severity_probabilities_json = json.dumps(unified_res.severity_probabilities)

        existing_classification.quality_score = unified_res.quality.quality_score
        existing_classification.quality_blur_score = unified_res.quality.blur_score
        existing_classification.quality_brightness_score = unified_res.quality.brightness_score
        existing_classification.quality_contrast_score = unified_res.quality.contrast_score
        existing_classification.quality_resolution_score = unified_res.quality.resolution_score
        existing_classification.quality_issues_json = json.dumps(unified_res.quality.detected_issues)
        existing_classification.quality_recommendation = unified_res.quality.recommendation

        if user_suggested_category:
            existing_classification.user_suggested_category = user_suggested_category
        if user_suggested_severity:
            existing_classification.user_suggested_severity = user_suggested_severity

        db.commit()
        db.refresh(existing_classification)
        return existing_classification

    new_classification = ImageClassification(
        image_id=image.id,
        predicted_category=category_enum,
        confidence=unified_res.confidence,
        model_version=unified_res.model_version,
        probabilities_json=json.dumps(unified_res.probabilities),
        predicted_severity=severity_enum,
        severity_confidence=unified_res.severity_confidence,
        severity_model_version=unified_res.severity_model_version,
        severity_probabilities_json=json.dumps(unified_res.severity_probabilities),
        quality_score=unified_res.quality.quality_score,
        quality_blur_score=unified_res.quality.blur_score,
        quality_brightness_score=unified_res.quality.brightness_score,
        quality_contrast_score=unified_res.quality.contrast_score,
        quality_resolution_score=unified_res.quality.resolution_score,
        quality_issues_json=json.dumps(unified_res.quality.detected_issues),
        quality_recommendation=unified_res.quality.recommendation,
        user_suggested_category=user_suggested_category,
        user_suggested_severity=user_suggested_severity,
        is_corrected=False,
        is_severity_corrected=False
    )
    db.add(new_classification)
    db.commit()
    db.refresh(new_classification)
    return new_classification


def record_human_override(
    db: Session,
    image_id: UUID,
    current_user: User,
    verified_category: Optional[ReportCategory] = None,
    verified_severity: Optional[ReportSeverity] = None,
    notes: Optional[str] = None
) -> ImageClassification:
    """
    Applies human-in-the-loop verification/override to an image classification.
    Maintains full audit tracking of who verified/corrected the prediction and when.
    """
    classification = (
        db.query(ImageClassification)
        .filter(ImageClassification.image_id == image_id)
        .first()
    )
    if not classification:
        cat = verified_category or ReportCategory.OTHER
        sev = verified_severity or ReportSeverity.MEDIUM
        classification = ImageClassification(
            image_id=image_id,
            predicted_category=cat,
            confidence=1.0,
            model_version="human-verified",
            probabilities_json=json.dumps({cat.value: 1.0}),
            predicted_severity=sev,
            severity_confidence=1.0,
            severity_model_version="human-verified",
            authority_verified_category=verified_category,
            authority_verified_severity=verified_severity,
            is_corrected=False,
            is_severity_corrected=False,
            corrected_by_user_id=current_user.id,
            corrected_at=datetime.now(timezone.utc),
            correction_notes=notes
        )
        db.add(classification)
    else:
        if verified_category is not None:
            classification.authority_verified_category = verified_category
            classification.is_corrected = (verified_category != classification.predicted_category)

        if verified_severity is not None:
            classification.authority_verified_severity = verified_severity
            classification.is_severity_corrected = (verified_severity != classification.predicted_severity)

        classification.corrected_by_user_id = current_user.id
        classification.corrected_at = datetime.now(timezone.utc)
        if notes:
            classification.correction_notes = notes

    db.commit()
    db.refresh(classification)
    return classification


def get_report_ai_analysis(db: Session, report: RoadReport) -> ReportAIAnalysisResponse:
    """
    Assembles comprehensive AI diagnostics, category & severity estimations,
    image quality scores, and human override audit trails for a report.
    """
    images_analyzed = []
    total_quality = 0.0
    primary_ai_cat: Optional[ReportCategory] = None
    primary_ai_sev: Optional[ReportSeverity] = None
    primary_cat_conf = 0.0
    primary_sev_conf = 0.0
    verified_cat: Optional[ReportCategory] = None
    verified_sev: Optional[ReportSeverity] = None
    has_overrides = False
    all_recommendations = []

    for img in report.images:
        cls = img.classification
        if not cls:
            continue

        probs = json.loads(cls.probabilities_json) if cls.probabilities_json else {}
        sev_probs = json.loads(cls.severity_probabilities_json) if cls.severity_probabilities_json else {}
        issues = json.loads(cls.quality_issues_json) if cls.quality_issues_json else []

        q_score = cls.quality_score if cls.quality_score is not None else 80.0
        total_quality += q_score

        if cls.authority_verified_category:
            verified_cat = cls.authority_verified_category
            has_overrides = True
        if cls.authority_verified_severity:
            verified_sev = cls.authority_verified_severity
            has_overrides = True
        if cls.is_corrected or cls.is_severity_corrected:
            has_overrides = True

        if cls.quality_recommendation:
            all_recommendations.append(cls.quality_recommendation)

        if primary_ai_cat is None:
            primary_ai_cat = cls.predicted_category
            primary_cat_conf = cls.confidence
            primary_ai_sev = cls.predicted_severity or ReportSeverity.MEDIUM
            primary_sev_conf = cls.severity_confidence or 0.85

        q_metrics = ImageQualityMetrics(
            quality_score=q_score,
            is_acceptable=q_score >= 40.0,
            blur_score=cls.quality_blur_score,
            brightness_score=cls.quality_brightness_score,
            contrast_score=cls.quality_contrast_score,
            resolution_score=cls.quality_resolution_score,
            is_corrupt=False,
            detected_issues=issues,
            recommendation=cls.quality_recommendation
        )

        item = AIAnalysisImageItem(
            image_id=img.id,
            file_path=img.file_path,
            thumbnail_path=img.thumbnail_path,
            ai_category=cls.predicted_category,
            category_confidence=cls.confidence,
            category_model_version=cls.model_version,
            category_probabilities=probs,
            ai_severity=cls.predicted_severity or ReportSeverity.MEDIUM,
            severity_confidence=cls.severity_confidence or 0.85,
            severity_model_version=cls.severity_model_version or "road-severity-v1.0",
            severity_probabilities=sev_probs,
            quality_score=q_score,
            quality_diagnostics=q_metrics,
            citizen_category=cls.user_suggested_category or report.category,
            authority_verified_category=cls.authority_verified_category,
            citizen_severity=cls.user_suggested_severity or report.severity,
            authority_verified_severity=cls.authority_verified_severity,
            is_category_corrected=cls.is_corrected,
            is_severity_corrected=cls.is_severity_corrected,
            corrected_by_user_id=cls.corrected_by_user_id,
            corrected_at=cls.corrected_at,
            correction_notes=cls.correction_notes
        )
        images_analyzed.append(item)

    avg_quality = (total_quality / len(images_analyzed)) if images_analyzed else 100.0
    quality_status = "GOOD" if avg_quality >= 75.0 else ("ACCEPTABLE" if avg_quality >= 45.0 else "POOR")

    eff_cat = verified_cat if verified_cat else (primary_ai_cat if primary_ai_cat else report.category)
    eff_sev = verified_sev if verified_sev else (primary_ai_sev if primary_ai_sev else report.severity)

    return ReportAIAnalysisResponse(
        report_id=report.id,
        title=report.title,
        citizen_category=report.category,
        ai_category=primary_ai_cat,
        authority_verified_category=verified_cat,
        effective_category=eff_cat,
        citizen_severity=report.severity,
        ai_severity=primary_ai_sev,
        authority_verified_severity=verified_sev,
        effective_severity=eff_sev,
        primary_category_confidence=primary_cat_conf,
        primary_severity_confidence=primary_sev_conf,
        average_quality_score=round(avg_quality, 1),
        quality_status=quality_status,
        overall_recommendation="; ".join(set(all_recommendations)) if all_recommendations else None,
        has_overrides=has_overrides,
        images_analyzed=len(images_analyzed),
        images=images_analyzed
    )
