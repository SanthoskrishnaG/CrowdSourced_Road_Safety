import io
import pytest
from PIL import Image

from ml.inference.predictor import RoadHazardPredictor
from ml.datasets.dataset import generate_synthetic_hazard_image


def test_confidence_bounds():
    predictor = RoadHazardPredictor()
    for cat in ["POTHOLE", "BROKEN_STREETLIGHT", "FLOODING", "GARBAGE"]:
        img = generate_synthetic_hazard_image(cat)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        res = predictor.predict(buf.getvalue())
        assert 0.0 <= res.confidence <= 1.0
        assert isinstance(res.confidence, float)


def test_confidence_calibration():
    predictor = RoadHazardPredictor()
    # Distinct pattern should yield high confidence (> 0.50)
    pothole_img = generate_synthetic_hazard_image("POTHOLE")
    buf = io.BytesIO()
    pothole_img.save(buf, format="JPEG")
    res = predictor.predict(buf.getvalue())
    assert res.confidence > 0.50
    assert res.category == "POTHOLE"
