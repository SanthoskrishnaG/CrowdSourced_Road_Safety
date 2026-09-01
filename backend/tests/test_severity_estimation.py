import pytest
from PIL import Image

from ml.inference.predictor import RoadHazardPredictor, UnifiedPredictionResult
from ml.datasets.dataset import generate_synthetic_hazard_image
from ml.models.classifier import SEVERITY_CLASSES


@pytest.fixture
def predictor():
    return RoadHazardPredictor()


def test_severity_prediction_valid_output(predictor):
    """Predictor should return genuine severity tier, confidence, and probabilities."""
    img = generate_synthetic_hazard_image("POTHOLE", width=300, height=300)
    result = predictor.predict_unified(img)

    assert isinstance(result, UnifiedPredictionResult)
    assert result.category == "POTHOLE"
    assert result.severity in SEVERITY_CLASSES
    assert 0.0 <= result.severity_confidence <= 1.0
    assert len(result.severity_probabilities) == 4
    for sev_name in SEVERITY_CLASSES:
        assert sev_name in result.severity_probabilities
        assert 0.0 <= result.severity_probabilities[sev_name] <= 1.0


def test_severity_confidence_calibration(predictor):
    """Sum of severity probabilities should equal ~1.0."""
    img = generate_synthetic_hazard_image("ROAD_DAMAGE", width=250, height=250)
    result = predictor.predict_unified(img)

    prob_sum = sum(result.severity_probabilities.values())
    assert pytest.approx(prob_sum, abs=1e-2) == 1.0


def test_unified_prediction_dict_serialization(predictor):
    """Unified result converts cleanly to dictionary."""
    img = generate_synthetic_hazard_image("FLOODING", width=250, height=250)
    result = predictor.predict_unified(img)
    d = result.to_dict()

    assert "category" in d
    assert "severity" in d
    assert "quality" in d
    assert "quality_score" in d["quality"]
    assert "model_version" in d
    assert "severity_model_version" in d
