"""
Inference Predictor Engine for Road Hazard Classification.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Union, Optional
from PIL import Image

from ml.preprocessing.transform import (
    validate_image_bytes,
    extract_vision_features,
    InvalidImageError,
)
from ml.models.classifier import (
    load_road_classifier,
    BaseRoadClassifier,
    DEFAULT_WEIGHTS_PATH,
)


@dataclass
class PredictionResult:
    category: str
    confidence: float
    probabilities: Dict[str, float]
    model_version: str

    def to_dict(self) -> Dict:
        return asdict(self)


class RoadHazardPredictor:
    """
    Thread-safe ML inference engine for road hazard classification.
    Processes raw images through the computer vision pipeline and returns predictions with confidence.
    """

    def __init__(self, weights_path: str = DEFAULT_WEIGHTS_PATH):
        self.weights_path = weights_path
        self.classifier: BaseRoadClassifier = load_road_classifier(weights_path)
        self.model_version: str = getattr(self.classifier, "MODEL_VERSION", "road-vision-v1.0")

    def predict(self, image_input: Union[bytes, str, Image.Image]) -> PredictionResult:
        """
        Runs inference on an image:
        1. Validates input
        2. Preprocesses image (aspect ratio resize, RGB check)
        3. Extracts visual feature representation
        4. Evaluates classifier with softmax probability distribution
        5. Returns PredictionResult(category, confidence, probabilities, model_version)
        """
        if isinstance(image_input, str):
            # File path
            with open(image_input, "rb") as f:
                raw_bytes = f.read()
            img = validate_image_bytes(raw_bytes)
        elif isinstance(image_input, bytes):
            img = validate_image_bytes(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
            if img.mode != "RGB":
                img = img.convert("RGB")
        else:
            raise InvalidImageError(f"Unsupported image input type: {type(image_input)}")

        # Extract features
        features = extract_vision_features(img)

        # Run inference
        predicted_category, confidence, probabilities = self.classifier.predict(features)

        # Ensure confidence is within [0.0, 1.0]
        confidence = max(0.0, min(1.0, float(confidence)))

        return PredictionResult(
            category=predicted_category,
            confidence=round(confidence, 4),
            probabilities=probabilities,
            model_version=self.model_version
        )
