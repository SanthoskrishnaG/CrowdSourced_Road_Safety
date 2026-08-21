import io
import pytest
from PIL import Image

from ml.inference.predictor import RoadHazardPredictor, PredictionResult
from ml.datasets.dataset import generate_synthetic_hazard_image, load_class_mapping


def test_predictor_initialization():
    predictor = RoadHazardPredictor()
    assert predictor.classifier is not None
    assert predictor.model_version == "road-vision-v1.0"


def test_inference_pothole_prediction():
    predictor = RoadHazardPredictor()
    pothole_img = generate_synthetic_hazard_image("POTHOLE")
    
    buf = io.BytesIO()
    pothole_img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    result = predictor.predict(raw_bytes)
    assert isinstance(result, PredictionResult)
    assert result.category == "POTHOLE"
    assert 0.0 <= result.confidence <= 1.0
    assert result.model_version == "road-vision-v1.0"
    assert "POTHOLE" in result.probabilities


def test_inference_all_target_classes():
    predictor = RoadHazardPredictor()
    mapping = load_class_mapping()
    classes = mapping["classes"]

    for cls in classes:
        sample_img = generate_synthetic_hazard_image(cls)
        buf = io.BytesIO()
        sample_img.save(buf, format="PNG")
        res = predictor.predict(buf.getvalue())

        assert res.category in classes
        assert 0.0 <= res.confidence <= 1.0
        assert len(res.probabilities) == 8
        prob_sum = sum(res.probabilities.values())
        assert 0.99 <= prob_sum <= 1.01
