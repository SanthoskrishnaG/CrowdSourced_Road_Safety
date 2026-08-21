import pytest
from ml.preprocessing.transform import (
    validate_image_bytes,
    InvalidImageError,
)
from ml.inference.predictor import RoadHazardPredictor


def test_empty_bytes_raises_error():
    with pytest.raises(InvalidImageError, match="empty"):
        validate_image_bytes(b"")


def test_corrupt_bytes_raises_error():
    corrupt_data = b"NOT_A_VALID_IMAGE_HEADER_CONTENT_12345"
    with pytest.raises(InvalidImageError, match="Corrupt"):
        validate_image_bytes(corrupt_data)


def test_oversized_payload_raises_error():
    oversized = b"0" * (16 * 1024 * 1024) # 16 MB
    with pytest.raises(InvalidImageError, match="exceeds maximum allowable size"):
        validate_image_bytes(oversized)


def test_predictor_handles_invalid_input_type():
    predictor = RoadHazardPredictor()
    with pytest.raises(InvalidImageError):
        predictor.predict(12345)  # Invalid non-image type
