import io
import pytest
import numpy as np
from PIL import Image

from ml.preprocessing.transform import (
    ImagePreprocessor,
    validate_image_bytes,
    preprocess_image_bytes,
    extract_vision_features,
    InvalidImageError,
)


def create_test_image(mode="RGB", size=(300, 300), color=(120, 100, 90)) -> bytes:
    buf = io.BytesIO()
    img = Image.new(mode, size, color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_image_bytes_valid_jpeg():
    raw_bytes = create_test_image()
    img = validate_image_bytes(raw_bytes)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.size == (300, 300)


def test_validate_image_bytes_png_and_rgba():
    buf = io.BytesIO()
    img = Image.new("RGBA", (200, 150), (255, 0, 0, 128))
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    validated = validate_image_bytes(raw_bytes)
    assert validated.mode == "RGB"
    assert validated.size == (200, 150)


def test_preprocess_image_aspect_ratio_padding():
    raw_bytes = create_test_image(size=(400, 200))
    preprocessed = preprocess_image_bytes(raw_bytes, target_size=(224, 224))
    assert preprocessed.size == (224, 224)


def test_tensor_conversion():
    preprocessor = ImagePreprocessor(target_size=(224, 224))
    img = Image.new("RGB", (224, 224), (100, 100, 100))
    tensor = preprocessor.to_chw_tensor(img)
    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.dtype == np.float32


def test_extract_vision_features():
    raw_bytes = create_test_image()
    features = extract_vision_features(raw_bytes)
    assert isinstance(features, np.ndarray)
    assert features.ndim == 1
    assert len(features) > 50
    assert not np.isnan(features).any()
    assert not np.isinf(features).any()
