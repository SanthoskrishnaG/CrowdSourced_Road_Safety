"""
Inference Predictor Engine for Road Hazard Classification, Severity Estimation, and Image Quality.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Union, Optional, List
from PIL import Image

from ml.preprocessing.transform import (
    validate_image_bytes,
    extract_vision_features,
    InvalidImageError,
)
from ml.preprocessing.quality import (
    ImageQualityAnalyzer,
    ImageQualityResult,
)
from ml.models.classifier import (
    load_road_classifier,
    load_severity_estimator,
    BaseRoadClassifier,
    RoadSeverityEstimator,
    DEFAULT_WEIGHTS_PATH,
    DEFAULT_SEVERITY_WEIGHTS_PATH,
)


@dataclass
class UnifiedPredictionResult:
    category: str
    confidence: float
    probabilities: Dict[str, float]
    severity: str
    severity_confidence: float
    severity_probabilities: Dict[str, float]
    quality: ImageQualityResult
    model_version: str
    severity_model_version: str

    def to_dict(self) -> Dict:
        res = asdict(self)
        res["quality"] = self.quality.to_dict()
        return res


# Backward compatibility alias
@dataclass
class PredictionResult:
    category: str
    confidence: float
    probabilities: Dict[str, float]
    model_version: str
    severity: Optional[str] = "MEDIUM"
    severity_confidence: Optional[float] = 0.85
    quality_score: Optional[float] = 90.0

    def to_dict(self) -> Dict:
        return asdict(self)


class RoadHazardPredictor:
    """
    Thread-safe ML inference engine for road hazard classification, severity estimation,
    and image quality diagnosis.
    """

    def __init__(
        self,
        weights_path: str = DEFAULT_WEIGHTS_PATH,
        severity_weights_path: str = DEFAULT_SEVERITY_WEIGHTS_PATH
    ):
        self.weights_path = weights_path
        self.severity_weights_path = severity_weights_path
        self.classifier: BaseRoadClassifier = load_road_classifier(weights_path)
        self.severity_estimator: RoadSeverityEstimator = load_severity_estimator(severity_weights_path)
        self.model_version: str = getattr(self.classifier, "MODEL_VERSION", "road-vision-v1.0")
        self.severity_model_version: str = getattr(self.severity_estimator, "MODEL_VERSION", "road-severity-v1.0")

    def analyze_quality(self, image_input: Union[bytes, str, Image.Image]) -> ImageQualityResult:
        """Runs image quality diagnostics."""
        if isinstance(image_input, str):
            with open(image_input, "rb") as f:
                raw_bytes = f.read()
            return ImageQualityAnalyzer.analyze(raw_bytes)
        return ImageQualityAnalyzer.analyze(image_input)

    def predict(self, image_input: Union[bytes, str, Image.Image]) -> PredictionResult:
        """
        Runs category classification on an image input.
        """
        unified = self.predict_unified(image_input)
        return PredictionResult(
            category=unified.category,
            confidence=unified.confidence,
            probabilities=unified.probabilities,
            model_version=unified.model_version,
            severity=unified.severity,
            severity_confidence=unified.severity_confidence,
            quality_score=unified.quality.quality_score
        )

    def predict_unified(self, image_input: Union[bytes, str, Image.Image]) -> UnifiedPredictionResult:
        """
        Runs end-to-end AI pipeline:
        1. Validates input and executes Image Quality Diagnostics (Blur, Lighting, Resolution, Integrity)
        2. Computes Computer Vision feature representation
        3. Predicts Hazard Category with calibrated probabilities
        4. Predicts Hazard Severity (LOW, MEDIUM, HIGH, CRITICAL) with calibrated probabilities
        5. Returns UnifiedPredictionResult
        """
        raw_bytes: Optional[bytes] = None
        if isinstance(image_input, str):
            with open(image_input, "rb") as f:
                raw_bytes = f.read()
            img = validate_image_bytes(raw_bytes)
        elif isinstance(image_input, bytes):
            raw_bytes = image_input
            img = validate_image_bytes(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
            if img.mode != "RGB":
                img = img.convert("RGB")
        else:
            raise InvalidImageError(f"Unsupported image input type: {type(image_input)}")

        # 1. Quality Analysis
        quality_res = ImageQualityAnalyzer.analyze(raw_bytes if raw_bytes else img)

        # 2. Feature Extraction
        features = extract_vision_features(img)

        # 3. Category Prediction
        predicted_category, cat_conf, cat_probs = self.classifier.predict(features)
        cat_conf = max(0.0, min(1.0, float(cat_conf)))

        # 4. Severity Prediction
        predicted_sev, sev_conf, sev_probs = self.severity_estimator.predict(features)
        sev_conf = max(0.0, min(1.0, float(sev_conf)))

        return UnifiedPredictionResult(
            category=predicted_category,
            confidence=round(cat_conf, 4),
            probabilities=cat_probs,
            severity=predicted_sev,
            severity_confidence=round(sev_conf, 4),
            severity_probabilities=sev_probs,
            quality=quality_res,
            model_version=self.model_version,
            severity_model_version=self.severity_model_version
        )
