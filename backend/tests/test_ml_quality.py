import io
import pytest
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ml.preprocessing.quality import ImageQualityAnalyzer, ImageQualityResult


def create_test_image(width=400, height=400, color=(128, 128, 128), add_shapes=True) -> bytes:
    """Helper to generate in-memory test images."""
    img = Image.new("RGB", (width, height), color)
    if add_shapes:
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 200, 200], fill=(20, 20, 20), outline=(220, 220, 220))
        draw.ellipse([150, 150, 350, 350], fill=(240, 180, 20), outline=(0, 0, 0))
        draw.line([(0, 0), (width, height)], fill=(255, 0, 0), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_quality_analyzer_crisp_image():
    """Sharp, well-lit image should have high quality score (> 70)."""
    img_bytes = create_test_image(width=800, height=600, add_shapes=True)
    res = ImageQualityAnalyzer.analyze(img_bytes)

    assert isinstance(res, ImageQualityResult)
    assert res.quality_score >= 65.0
    assert res.is_acceptable is True
    assert res.is_corrupt is False
    assert res.blur_score > 50.0
    assert res.resolution_score >= 80.0


def test_quality_analyzer_blurry_image():
    """Severely blurred image should produce low blur score and recommendation."""
    base = Image.new("RGB", (600, 600), (120, 120, 120))
    draw = ImageDraw.Draw(base)
    draw.rectangle([100, 100, 300, 300], fill=(10, 10, 10))
    # Apply severe Gaussian blur
    blurred = base.filter(ImageFilter.GaussianBlur(radius=15.0))
    buf = io.BytesIO()
    blurred.save(buf, format="JPEG", quality=90)

    res = ImageQualityAnalyzer.analyze(buf.getvalue())
    assert res.blur_score < 45.0
    assert any("BLURRY" in issue for issue in res.detected_issues)
    assert res.recommendation is not None
    assert "clearer" in res.recommendation.lower() or "steady" in res.recommendation.lower()


def test_quality_analyzer_underexposed_image():
    """Dark image should be flagged as underexposed."""
    dark_img = Image.new("RGB", (400, 400), (15, 15, 15))
    buf = io.BytesIO()
    dark_img.save(buf, format="JPEG")

    res = ImageQualityAnalyzer.analyze(buf.getvalue())
    assert res.brightness_score < 45.0
    assert any("UNDEREXPOSED" in issue for issue in res.detected_issues)


def test_quality_analyzer_low_resolution():
    """Image below minimum resolution should be flagged."""
    small_img = Image.new("RGB", (80, 80), (100, 100, 100))
    buf = io.BytesIO()
    small_img.save(buf, format="JPEG")

    res = ImageQualityAnalyzer.analyze(buf.getvalue())
    assert res.resolution_score < 40.0
    assert any("LOW_RESOLUTION" in issue for issue in res.detected_issues)


def test_quality_analyzer_corrupt_file():
    """Corrupted byte payload should yield quality_score=0 and is_corrupt=True."""
    bad_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01NOTANIMAGE"
    res = ImageQualityAnalyzer.analyze(bad_bytes)

    assert res.quality_score == 0.0
    assert res.is_corrupt is True
    assert res.is_acceptable is False
    assert res.recommendation is not None
