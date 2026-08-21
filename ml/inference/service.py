"""
High-Level ML Inference Service.
Provides singleton instance management, warm startup caching, and safe error handling.
"""

from typing import Union, Optional
from PIL import Image

from ml.inference.predictor import RoadHazardPredictor, PredictionResult
from ml.models.classifier import DEFAULT_WEIGHTS_PATH


class MLInferenceService:
    """Singleton service wrapping RoadHazardPredictor."""

    _instance: Optional["MLInferenceService"] = None

    def __init__(self, weights_path: str = DEFAULT_WEIGHTS_PATH):
        self.predictor = RoadHazardPredictor(weights_path=weights_path)

    @classmethod
    def get_instance(cls, weights_path: str = DEFAULT_WEIGHTS_PATH) -> "MLInferenceService":
        if cls._instance is None:
            cls._instance = cls(weights_path=weights_path)
        return cls._instance

    def classify_image(self, image_input: Union[bytes, str, Image.Image]) -> PredictionResult:
        """Runs inference and returns structured prediction."""
        return self.predictor.predict(image_input)


def get_inference_service() -> MLInferenceService:
    """Helper to access the ML Inference Service instance."""
    return MLInferenceService.get_instance()
