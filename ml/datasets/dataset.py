import os
import json
from typing import Dict, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw

from ml.preprocessing.transform import ImagePreprocessor, extract_vision_features

DEFAULT_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "class_mapping.json")


def load_class_mapping(mapping_path: str = DEFAULT_MAPPING_PATH) -> Dict:
    """Loads target category class mapping dictionary from JSON."""
    if not os.path.exists(mapping_path):
        # Default fallback mapping
        return {
            "classes": [
                "POTHOLE",
                "ROAD_DAMAGE",
                "GARBAGE",
                "BROKEN_STREETLIGHT",
                "OBSTRUCTION",
                "FLOODING",
                "DAMAGED_SIGN",
                "OTHER"
            ],
            "class_to_idx": {
                "POTHOLE": 0,
                "ROAD_DAMAGE": 1,
                "GARBAGE": 2,
                "BROKEN_STREETLIGHT": 3,
                "OBSTRUCTION": 4,
                "FLOODING": 5,
                "DAMAGED_SIGN": 6,
                "OTHER": 7
            },
            "idx_to_class": {
                "0": "POTHOLE",
                "1": "ROAD_DAMAGE",
                "2": "GARBAGE",
                "3": "BROKEN_STREETLIGHT",
                "4": "OBSTRUCTION",
                "5": "FLOODING",
                "6": "DAMAGED_SIGN",
                "7": "OTHER"
            }
        }
    with open(mapping_path, "r", encoding="utf-8") as f:
        return json.load(f)


class RoadHazardDataset:
    """
    Dataset loader for Road Hazard Image Classification.
    Supports directory-based dataset loading (`dataset_dir/{train,val,test}/{category}/*.jpg`),
    feature matrix extraction, and synthetic sample generation for testing/benchmarks.
    """

    def __init__(self, root_dir: Optional[str] = None, split: str = "train", mapping_path: str = DEFAULT_MAPPING_PATH):
        self.root_dir = root_dir
        self.split = split
        self.mapping = load_class_mapping(mapping_path)
        self.classes: List[str] = self.mapping["classes"]
        self.class_to_idx: Dict[str, int] = self.mapping["class_to_idx"]
        self.samples: List[Tuple[str, int]] = []

        if root_dir and os.path.exists(os.path.join(root_dir, split)):
            self._scan_directory(os.path.join(root_dir, split))

    def _scan_directory(self, split_dir: str):
        """Scans folder structure for images."""
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        for cls_name in self.classes:
            cls_dir = os.path.join(split_dir, cls_name)
            if not os.path.isdir(cls_dir):
                continue
            cls_idx = self.class_to_idx[cls_name]
            for fname in os.listdir(cls_dir):
                ext = os.path.splitext(fname)[1].lower()
                if ext in valid_exts:
                    full_path = os.path.join(cls_dir, fname)
                    self.samples.append((full_path, cls_idx))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[Image.Image, int, str]:
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        return img, label, self.classes[label]

    def extract_features_and_labels(self) -> Tuple[np.ndarray, np.ndarray]:
        """Extracts (N, D) feature matrix and (N,) label array for all scanned images."""
        X, y = [], []
        for path, label in self.samples:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                features = extract_vision_features(data)
                X.append(features)
                y.append(label)
            except Exception as e:
                print(f"Skipping corrupt sample {path}: {e}")
        return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


def generate_synthetic_hazard_image(category: str, width: int = 300, height: int = 300) -> Image.Image:
    """
    Generates a realistic synthetic road hazard sample for automated testing,
    feature calibration, and validation pipelines.
    """
    img = Image.new("RGB", (width, height), (100, 100, 105)) # Asphalt gray base
    draw = ImageDraw.Draw(img)

    # Road surface texture noise
    rng = np.random.RandomState(hash(category) % (2**32 - 1))
    
    if category == "POTHOLE":
        # Draw dark crater with rough inner depth
        draw.ellipse([width*0.25, height*0.3, width*0.75, height*0.7], fill=(30, 25, 25), outline=(15, 15, 15), width=4)
        draw.ellipse([width*0.35, height*0.4, width*0.65, height*0.6], fill=(15, 10, 10))
    elif category == "ROAD_DAMAGE":
        # Draw cracking fissures across pavement
        draw.line([width*0.1, height*0.2, width*0.5, height*0.5, width*0.9, height*0.8], fill=(20, 20, 20), width=5)
        draw.line([width*0.5, height*0.5, width*0.7, height*0.2], fill=(25, 25, 25), width=3)
        draw.line([width*0.3, height*0.35, width*0.2, height*0.7], fill=(25, 25, 25), width=3)
    elif category == "GARBAGE":
        # Draw multicolored debris/trash heap
        draw.rectangle([width*0.2, height*0.5, width*0.45, height*0.8], fill=(220, 40, 40)) # red plastic
        draw.rectangle([width*0.4, height*0.55, width*0.65, height*0.85], fill=(40, 180, 220)) # blue bag
        draw.polygon([(width*0.6, height*0.6), (width*0.8, height*0.5), (width*0.75, height*0.8)], fill=(240, 220, 50)) # cardboard
    elif category == "BROKEN_STREETLIGHT":
        # Sky/background with vertical pole and luminaire
        draw.rectangle([0, 0, width, int(height*0.6)], fill=(135, 180, 220)) # Sky
        draw.rectangle([int(width*0.45), int(height*0.2), int(width*0.55), height], fill=(60, 60, 65)) # Pole
        draw.ellipse([int(width*0.35), int(height*0.1), int(width*0.65), int(height*0.3)], fill=(255, 255, 200), outline=(50, 50, 50), width=3) # Light
    elif category == "OBSTRUCTION":
        # Fallen log / blockage across road
        draw.line([width*0.05, height*0.6, width*0.95, height*0.65], fill=(100, 60, 30), width=24) # Big log
        draw.line([width*0.3, height*0.62, width*0.4, height*0.4], fill=(70, 45, 20), width=8) # Branch
    elif category == "FLOODING":
        # Water layer with reflection / blue-gray tone
        draw.rectangle([0, int(height*0.35), width, height], fill=(60, 100, 140)) # Water
        draw.line([width*0.1, height*0.5, width*0.9, height*0.5], fill=(180, 210, 240), width=3) # Ripple
        draw.line([width*0.2, height*0.65, width*0.8, height*0.65], fill=(180, 210, 240), width=3)
    elif category == "DAMAGED_SIGN":
        # Tilted or vandalized traffic sign
        draw.polygon([(width*0.3, height*0.2), (width*0.7, height*0.15), (width*0.8, height*0.55), (width*0.4, height*0.6)], fill=(220, 30, 30)) # Red octagonal tilted
        draw.text((int(width*0.45), int(height*0.3)), "STOP", fill=(255, 255, 255))
        draw.line([width*0.55, height*0.55, width*0.6, height*0.9], fill=(150, 150, 150), width=6) # Pole
    else: # OTHER
        draw.rectangle([width*0.3, height*0.3, width*0.7, height*0.7], fill=(160, 140, 120), outline=(80, 70, 60), width=3)

    return img
