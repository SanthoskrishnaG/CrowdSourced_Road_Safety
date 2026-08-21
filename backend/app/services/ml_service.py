import json
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.report import ReportCategory
from app.models.image import ReportImage
from app.models.classification import ImageClassification
from app.models.user import User
from ml.inference.service import get_inference_service
from ml.preprocessing.transform import InvalidImageError


def map_category_string_to_enum(cat_str: str) -> ReportCategory:
    """Maps prediction string to ReportCategory Enum safely."""
    try:
        return ReportCategory(cat_str.upper())
    except (ValueError, KeyError):
        return ReportCategory.OTHER


def classify_standalone_bytes(image_bytes: bytes) -> Dict[str, Any]:
    """
    Executes real-time ML image classification on raw uploaded bytes.
    Used for instant preview / classification suggestions during report creation.
    """
    service = get_inference_service()
    pred_result = service.classify_image(image_bytes)
    
    category_enum = map_category_string_to_enum(pred_result.category)
    return {
        "predicted_category": category_enum,
        "confidence": pred_result.confidence,
        "probabilities": pred_result.probabilities,
        "model_version": pred_result.model_version
    }


def classify_and_store_report_image(
    db: Session,
    image: ReportImage,
    image_bytes: bytes,
    user_suggested_category: Optional[ReportCategory] = None
) -> ImageClassification:
    """
    Runs the ML inference pipeline on an uploaded image, maps the output to a ReportCategory,
    and persists the ImageClassification record in the database linked to ReportImage.
    """
    service = get_inference_service()
    pred_result = service.classify_image(image_bytes)
    category_enum = map_category_string_to_enum(pred_result.category)

    # Check if a classification already exists for this image
    existing_classification = (
        db.query(ImageClassification)
        .filter(ImageClassification.image_id == image.id)
        .first()
    )

    if existing_classification:
        existing_classification.predicted_category = category_enum
        existing_classification.confidence = pred_result.confidence
        existing_classification.model_version = pred_result.model_version
        existing_classification.probabilities_json = json.dumps(pred_result.probabilities)
        if user_suggested_category:
            existing_classification.user_suggested_category = user_suggested_category
        db.commit()
        db.refresh(existing_classification)
        return existing_classification

    new_classification = ImageClassification(
        image_id=image.id,
        predicted_category=category_enum,
        confidence=pred_result.confidence,
        model_version=pred_result.model_version,
        probabilities_json=json.dumps(pred_result.probabilities),
        user_suggested_category=user_suggested_category,
        is_corrected=False
    )
    db.add(new_classification)
    db.commit()
    db.refresh(new_classification)
    return new_classification


def record_human_override(
    db: Session,
    image_id: UUID,
    verified_category: ReportCategory,
    current_user: User,
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
        # If no classification exists yet, create one with verified category
        classification = ImageClassification(
            image_id=image_id,
            predicted_category=verified_category,
            confidence=1.0,
            model_version="human-verified",
            probabilities_json=json.dumps({verified_category.value: 1.0}),
            authority_verified_category=verified_category,
            is_corrected=False,
            corrected_by_user_id=current_user.id,
            corrected_at=datetime.now(timezone.utc),
            correction_notes=notes
        )
        db.add(classification)
    else:
        classification.authority_verified_category = verified_category
        classification.is_corrected = (verified_category != classification.predicted_category)
        classification.corrected_by_user_id = current_user.id
        classification.corrected_at = datetime.now(timezone.utc)
        classification.correction_notes = notes

    db.commit()
    db.refresh(classification)
    return classification
