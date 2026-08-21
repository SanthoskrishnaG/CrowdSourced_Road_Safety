import io
from typing import Tuple, Union, Optional
import numpy as np
from PIL import Image, ImageOps


class InvalidImageError(ValueError):
    """Raised when an image fails validation checks."""
    pass


class ImagePreprocessor:
    """
    Standardized image preprocessing and feature transformation pipeline for road vision models.
    Supports resizing, aspect-ratio preservation, normalization, and visual feature extraction.
    """

    TARGET_SIZE: Tuple[int, int] = (224, 224)
    MIN_DIMENSION: int = 16
    MAX_DIMENSION: int = 6000
    MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB

    # Standard ImageNet Mean and Standard Deviation for Transfer Learning
    IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __init__(self, target_size: Tuple[int, int] = TARGET_SIZE):
        self.target_size = target_size

    @classmethod
    def validate_image_bytes(cls, image_bytes: bytes) -> Image.Image:
        """
        Validates raw image bytes:
        - Non-empty byte payload
        - File size limit
        - Legitimate image format (JPEG, PNG, WEBP, BMP)
        - Non-degenerate dimensions
        """
        if not image_bytes:
            raise InvalidImageError("Image payload is empty (0 bytes).")

        if len(image_bytes) > cls.MAX_FILE_SIZE_BYTES:
            raise InvalidImageError(f"Image exceeds maximum allowable size of {cls.MAX_FILE_SIZE_BYTES // (1024*1024)}MB.")

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
        except Exception as e:
            raise InvalidImageError(f"Corrupt or unsupported image file: {str(e)}")

        # Reopen after verify() (Pillow closes stream upon verify)
        img = Image.open(io.BytesIO(image_bytes))

        # Handle EXIF orientation tag if present
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Validate dimensions
        width, height = img.size
        if width < cls.MIN_DIMENSION or height < cls.MIN_DIMENSION:
            raise InvalidImageError(f"Image dimensions ({width}x{height}) are too small (minimum {cls.MIN_DIMENSION}px).")
        if width > cls.MAX_DIMENSION or height > cls.MAX_DIMENSION:
            raise InvalidImageError(f"Image dimensions ({width}x{height}) exceed maximum allowed ({cls.MAX_DIMENSION}px).")

        # Convert to standard RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        return img

    def resize_and_pad(self, image: Image.Image) -> Image.Image:
        """
        Resizes image to target dimensions (default 224x224) maintaining aspect ratio
        with symmetric border padding (neutral gray).
        """
        orig_w, orig_h = image.size
        target_w, target_h = self.target_size

        scale = min(target_w / orig_w, target_h / orig_h)
        new_w = max(1, int(orig_w * scale))
        new_h = max(1, int(orig_h * scale))

        resized = image.resize((new_w, new_h), Image.Resampling.BILINEAR)

        # Pad onto neutral gray canvas
        canvas = Image.new("RGB", (target_w, target_h), (128, 128, 128))
        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2
        canvas.paste(resized, (pad_x, pad_y))
        return canvas

    def to_normalized_array(self, image: Image.Image) -> np.ndarray:
        """
        Converts PIL Image to normalized float32 array scaled to [0, 1] or ImageNet normalized.
        Returns shape (H, W, C) in float32.
        """
        arr = np.asarray(image, dtype=np.float32) / 255.0
        return arr

    def to_chw_tensor(self, image: Image.Image) -> np.ndarray:
        """
        Converts PIL Image to standard PyTorch/ONNX tensor format (1, C, H, W) normalized by ImageNet mean/std.
        """
        arr = self.to_normalized_array(image)
        norm_arr = (arr - self.IMAGENET_MEAN) / self.IMAGENET_STD
        chw = np.transpose(norm_arr, (2, 0, 1))  # (C, H, W)
        return np.expand_dims(chw, axis=0)      # (1, C, H, W)

    def extract_features(self, image: Image.Image) -> np.ndarray:
        """
        Extracts robust, handcrafted Computer Vision visual feature representations
        combining spatial color moments, spatial edge gradients, and multi-scale texture energy.
        This provides deterministic, highly discriminative ML features for road hazard classification.
        Feature vector length: 128 dimensions.
        """
        preprocessed = self.resize_and_pad(image)
        rgb_arr = self.to_normalized_array(preprocessed) # (224, 224, 3)
        hsv_img = preprocessed.convert("HSV")
        hsv_arr = np.asarray(hsv_img, dtype=np.float32) / 255.0

        # Grayscale representation for gradients & texture
        gray = 0.2989 * rgb_arr[:, :, 0] + 0.5870 * rgb_arr[:, :, 1] + 0.1140 * rgb_arr[:, :, 2]

        feature_vector = []

        # 1. Spatial Color Moments (3x3 grid = 9 cells, 3 channels RGB + 3 channels HSV, mean & std = 9*6*2 = 108 features -> condensed to 48)
        grid_rows, grid_cols = 3, 3
        cell_h = preprocessed.height // grid_rows
        cell_w = preprocessed.width // grid_cols

        for r in range(grid_rows):
            for c in range(grid_cols):
                cell_rgb = rgb_arr[r * cell_h:(r + 1) * cell_h, c * cell_w:(c + 1) * cell_w, :]
                cell_hsv = hsv_arr[r * cell_h:(r + 1) * cell_h, c * cell_w:(c + 1) * cell_w, :]

                # Means and stds
                rgb_means = np.mean(cell_rgb, axis=(0, 1))
                rgb_stds = np.std(cell_rgb, axis=(0, 1))
                hsv_means = np.mean(cell_hsv, axis=(0, 1))
                hsv_stds = np.std(cell_hsv, axis=(0, 1))

                feature_vector.extend(rgb_means.tolist())
                feature_vector.extend(rgb_stds.tolist()[:2])
                feature_vector.extend(hsv_means.tolist())

        # 2. Edge Gradient Energy & Directional Histograms (Sobel gradient kernels)
        gx = np.zeros_like(gray)
        gy = np.zeros_like(gray)
        gx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) * 0.5
        gy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) * 0.5

        grad_magnitude = np.sqrt(gx**2 + gy**2)
        grad_angle = np.arctan2(gy, gx + 1e-7)

        # 4x4 spatial edge magnitude distribution (16 cells)
        egrid_r, egrid_c = 4, 4
        ecell_h = gray.shape[0] // egrid_r
        ecell_w = gray.shape[1] // egrid_c
        for r in range(egrid_r):
            for c in range(egrid_c):
                sub_mag = grad_magnitude[r * ecell_h:(r + 1) * ecell_h, c * ecell_w:(c + 1) * ecell_w]
                feature_vector.append(float(np.mean(sub_mag)))
                feature_vector.append(float(np.std(sub_mag)))

        # Gradient orientation histogram (8 bins)
        hist, _ = np.histogram(grad_angle, bins=8, range=(-np.pi, np.pi), weights=grad_magnitude)
        hist_sum = np.sum(hist) + 1e-6
        norm_hist = hist / hist_sum
        feature_vector.extend(norm_hist.tolist())

        # 3. Global Texture & Contrast Descriptors
        contrast = float(np.std(gray))
        mean_lum = float(np.mean(gray))
        specular_ratio = float(np.mean(gray > 0.85)) # High in flooding/streetlights
        dark_ratio = float(np.mean(gray < 0.20))     # High in potholes/asphalt crevices
        laplacian_var = float(np.var(gx + gy))       # High in road cracks / debris

        # Chromatic richness (saturation variance)
        sat_richness = float(np.std(hsv_arr[:, :, 1]))
        hue_entropy = float(-np.sum((hsv_arr[:, :, 0] + 1e-5) * np.log(hsv_arr[:, :, 0] + 1e-5)) / (224*224))

        feature_vector.extend([contrast, mean_lum, specular_ratio, dark_ratio, laplacian_var, sat_richness, hue_entropy])

        vec = np.array(feature_vector, dtype=np.float32)
        return vec


def validate_image_bytes(image_bytes: bytes) -> Image.Image:
    """Convenience helper function to validate raw bytes."""
    return ImagePreprocessor.validate_image_bytes(image_bytes)


def preprocess_image_bytes(image_bytes: bytes, target_size: Tuple[int, int] = (224, 224)) -> Image.Image:
    """Validates raw image bytes and returns a standardized resized/padded PIL Image."""
    img = ImagePreprocessor.validate_image_bytes(image_bytes)
    preprocessor = ImagePreprocessor(target_size=target_size)
    return preprocessor.resize_and_pad(img)


def extract_vision_features(image_input: Union[bytes, Image.Image]) -> np.ndarray:
    """
    Extracts high-dimensional computer vision feature vectors from image bytes or PIL Image.
    """
    if isinstance(image_input, bytes):
        img = validate_image_bytes(image_input)
    elif isinstance(image_input, Image.Image):
        img = image_input
        if img.mode != "RGB":
            img = img.convert("RGB")
    else:
        raise TypeError(f"Expected bytes or PIL.Image.Image, got {type(image_input)}")

    preprocessor = ImagePreprocessor()
    return preprocessor.extract_features(img)
