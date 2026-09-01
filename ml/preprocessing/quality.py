"""
Image Quality Assessment Module.
Evaluates photographic evidence for road infrastructure reports:
- Blur / sharpness (Laplacian variance)
- Resolution (dimensions & megapixels)
- Brightness / exposure (mean luminance & clipping)
- Contrast (dynamic range & RMS contrast)
- File integrity / corruption detection
- Normalized Quality Score (0 to 100)
- Actionable recommendations for citizens
"""

import io
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageOps


@dataclass
class ImageQualityResult:
    quality_score: float  # 0 to 100
    is_acceptable: bool   # True if quality_score >= 40
    blur_score: float     # 0 to 100 (100 = perfectly sharp)
    brightness_score: float # 0 to 100 (100 = ideal exposure)
    contrast_score: float   # 0 to 100 (100 = high dynamic range)
    resolution_score: float # 0 to 100 (100 = high resolution)
    is_corrupt: bool
    detected_issues: List[str]
    recommendation: Optional[str]

    def to_dict(self) -> Dict:
        return asdict(self)


class ImageQualityAnalyzer:
    """
    Diagnostic computer vision tool to quantify image quality before/during ML inference.
    """

    MIN_RESOLUTION = (200, 200)
    RECOMMENDED_RESOLUTION = (800, 600)
    MIN_LAPLACIAN_VAR = 25.0
    IDEAL_LAPLACIAN_VAR = 150.0

    @classmethod
    def check_file_integrity(cls, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validates whether raw byte payload constitutes an uncorrupted image.
        Returns: (is_corrupt, error_reason)
        """
        if not image_bytes or len(image_bytes) < 16:
            return True, "Empty or truncated image file header."

        try:
            stream = io.BytesIO(image_bytes)
            img = Image.open(stream)
            img.verify()
        except Exception as e:
            return True, f"Image stream corruption: {str(e)}"

        try:
            # Reopen to load pixel data and test decode
            stream = io.BytesIO(image_bytes)
            img = Image.open(stream)
            img.load()
        except Exception as e:
            return True, f"Image decoding failed: {str(e)}"

        return False, None

    @classmethod
    def analyze(cls, image_input: Union[bytes, Image.Image]) -> ImageQualityResult:
        """
        Runs comprehensive image quality diagnosis on bytes or PIL Image.
        """
        detected_issues: List[str] = []
        is_corrupt = False

        if isinstance(image_input, bytes):
            corrupt, reason = cls.check_file_integrity(image_input)
            if corrupt:
                return ImageQualityResult(
                    quality_score=0.0,
                    is_acceptable=False,
                    blur_score=0.0,
                    brightness_score=0.0,
                    contrast_score=0.0,
                    resolution_score=0.0,
                    is_corrupt=True,
                    detected_issues=["CORRUPTED_FILE: " + (reason or "Invalid image")],
                    recommendation="The uploaded file is corrupted or incomplete. Please upload a valid image file."
                )
            img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            raise TypeError(f"Expected bytes or PIL.Image.Image, got {type(image_input)}")

        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        pixels = w * h

        # 1. Resolution Score (0 - 100)
        min_pixels = cls.MIN_RESOLUTION[0] * cls.MIN_RESOLUTION[1]
        rec_pixels = cls.RECOMMENDED_RESOLUTION[0] * cls.RECOMMENDED_RESOLUTION[1]

        if pixels < min_pixels:
            res_score = max(0.0, (pixels / min_pixels) * 40.0)
            detected_issues.append("LOW_RESOLUTION: Image is smaller than minimum required 200x200 pixels.")
        elif pixels >= rec_pixels:
            res_score = 100.0
        else:
            res_score = 40.0 + ((pixels - min_pixels) / (rec_pixels - min_pixels)) * 60.0

        # Convert to numpy grayscale array
        rgb_arr = np.asarray(img, dtype=np.float32)
        gray = 0.2989 * rgb_arr[:, :, 0] + 0.5870 * rgb_arr[:, :, 1] + 0.1140 * rgb_arr[:, :, 2]

        # 2. Blur / Sharpness Score via discrete Laplacian 2D convolution
        laplacian = np.zeros_like(gray)
        laplacian[1:-1, 1:-1] = (
            gray[:-2, 1:-1] + gray[2:, 1:-1] +
            gray[1:-1, :-2] + gray[1:-1, 2:] -
            4.0 * gray[1:-1, 1:-1]
        )
        laplacian_var = float(np.var(laplacian))

        if laplacian_var < cls.MIN_LAPLACIAN_VAR:
            blur_score = max(0.0, (laplacian_var / cls.MIN_LAPLACIAN_VAR) * 40.0)
            detected_issues.append("BLURRY: High degree of motion or optical blur detected.")
        elif laplacian_var >= cls.IDEAL_LAPLACIAN_VAR:
            blur_score = 100.0
        else:
            blur_score = 40.0 + ((laplacian_var - cls.MIN_LAPLACIAN_VAR) / (cls.IDEAL_LAPLACIAN_VAR - cls.MIN_LAPLACIAN_VAR)) * 60.0

        # 3. Brightness / Exposure Score (0 - 100)
        mean_brightness = float(np.mean(gray))
        if mean_brightness < 40.0:
            bright_score = max(0.0, (mean_brightness / 40.0) * 45.0)
            detected_issues.append("UNDEREXPOSED: Image is very dark or captured at night with insufficient lighting.")
        elif mean_brightness > 220.0:
            bright_score = max(0.0, ((255.0 - mean_brightness) / 35.0) * 45.0)
            detected_issues.append("OVEREXPOSED: Severe glare or washout detected.")
        elif 80.0 <= mean_brightness <= 175.0:
            bright_score = 100.0
        elif mean_brightness < 80.0:
            bright_score = 45.0 + ((mean_brightness - 40.0) / 40.0) * 55.0
        else:
            bright_score = 45.0 + ((220.0 - mean_brightness) / 45.0) * 55.0

        # 4. Contrast Score (0 - 100)
        std_contrast = float(np.std(gray))
        if std_contrast < 20.0:
            contrast_score = max(0.0, (std_contrast / 20.0) * 45.0)
            detected_issues.append("LOW_CONTRAST: Low dynamic range, hazard features may be washed out.")
        elif std_contrast >= 60.0:
            contrast_score = 100.0
        else:
            contrast_score = 45.0 + ((std_contrast - 20.0) / 40.0) * 55.0

        # Composite Quality Score (0 to 100)
        composite = (
            blur_score * 0.35 +
            bright_score * 0.25 +
            contrast_score * 0.20 +
            res_score * 0.20
        )
        quality_score = float(round(composite, 1))

        # Generate clear actionable recommendation
        recommendation: Optional[str] = None
        if detected_issues:
            recommendation = (
                "Photo quality warning: " + "; ".join(detected_issues) +
                ". Recommend taking a clearer, steady photo in well-lit conditions."
            )

        return ImageQualityResult(
            quality_score=quality_score,
            is_acceptable=quality_score >= 40.0,
            blur_score=float(round(blur_score, 1)),
            brightness_score=float(round(bright_score, 1)),
            contrast_score=float(round(contrast_score, 1)),
            resolution_score=float(round(res_score, 1)),
            is_corrupt=is_corrupt,
            detected_issues=detected_issues,
            recommendation=recommendation
        )
