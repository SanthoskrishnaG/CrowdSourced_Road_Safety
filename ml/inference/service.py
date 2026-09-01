"""
High-Level ML Inference Service.
Provides singleton instance management, warm startup caching, and safe error handling.
"""

from typing import Union, Optional
from PIL import Image

from ml.inference.predictor import (
    RoadHazardPredictor,
    PredictionResult,
    UnifiedPredictionResult,
)
from ml.preprocessing.quality import ImageQualityResult
from ml.models.classifier import DEFAULT_WEIGHTS_PATH, DEFAULT_SEVERITY_WEIGHTS_PATH


class MLInferenceService:
    """Singleton service wrapping RoadHazardPredictor."""

    _instance: Optional["MLInferenceService"] = None

    def __init__(
        self,
        weights_path: str = DEFAULT_WEIGHTS_PATH,
        severity_weights_path: str = DEFAULT_SEVERITY_WEIGHTS_PATH
    ):
        self.predictor = RoadHazardPredictor(
            weights_path=weights_path,
            severity_weights_path=severity_weights_path
        )

    @classmethod
    def get_instance(
        cls,
        weights_path: str = DEFAULT_WEIGHTS_PATH,
        severity_weights_path: str = DEFAULT_SEVERITY_WEIGHTS_PATH
    ) -> "MLInferenceService":
        if cls._instance is None:
            cls._instance = cls(
                weights_path=weights_path,
                severity_weights_path=severity_weights_path
            )
        return cls._instance

    def classify_image(self, image_input: Union[bytes, str, Image.Image]) -> PredictionResult:
        """Runs category classification and returns standard prediction."""
        return self.predictor.predict(image_input)

    def analyze_image_unified(self, image_input: Union[bytes, str, Image.Image]) -> UnifiedPredictionResult:
        """Runs unified AI pipeline (Quality + Category + Severity)."""
        return self.predictor.predict_unified(image_input)

    def assess_quality(self, image_input: Union[bytes, str, Image.Image]) -> ImageQualityResult:
        """Runs standalone image quality evaluation."""
        return self.predictor.analyze_quality(image_input)


def get_inference_service() -> MLInferenceService:
    """Helper to access the ML Inference Service instance."""
    return MLInferenceService.get_instance()
