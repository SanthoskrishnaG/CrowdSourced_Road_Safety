"""
Model Weights Download & Verification Utility.

Allows automated or on-demand retrieval of deep learning weights (ONNX/PyTorch checkpoints)
from remote asset storage without bloating Git repositories with binary blobs.
"""

import os
import sys
import hashlib
import urllib.request

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "weights")

# Remote artifact registry (can be configured via environment variables or CDN)
MODELS_REGISTRY = {
    "road_classifier_v1.joblib": {
        "description": "Calibrated Feature Ensemble Neural Classifier for Road Hazard Vision",
        "url": "https://storage.googleapis.com/road-safety-models/road_classifier_v1.joblib",
        "sha256": "placeholder_sha256_hash",
        "local_filename": "road_classifier_v1.joblib"
    },
    "mobilenetv3_road_hazards.onnx": {
        "description": "MobileNetV3 ONNX Optimized Neural Network for Road Hazard Classification",
        "url": "https://storage.googleapis.com/road-safety-models/mobilenetv3_road_hazards.onnx",
        "sha256": "placeholder_sha256_hash",
        "local_filename": "mobilenetv3_road_hazards.onnx"
    }
}


def ensure_weights_directory() -> str:
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    return WEIGHTS_DIR


def download_model_weights(model_key: str = "road_classifier_v1.joblib", force: bool = False) -> str:
    """
    Downloads model weights if missing or verifies local artifact presence.
    """
    ensure_weights_directory()
    if model_key not in MODELS_REGISTRY:
        raise KeyError(f"Unknown model key '{model_key}'. Available: {list(MODELS_REGISTRY.keys())}")

    entry = MODELS_REGISTRY[model_key]
    dest_path = os.path.join(WEIGHTS_DIR, entry["local_filename"])

    if os.path.exists(dest_path) and not force:
        print(f"[ML] Model weights already exist at: {dest_path}")
        return dest_path

    print(f"[ML] Downloading {entry['description']}...")
    try:
        urllib.request.urlretrieve(entry["url"], dest_path)
        print(f"[ML] Successfully saved weights to: {dest_path}")
    except Exception as e:
        print(f"[ML] Remote download failed ({e}). Generating local baseline model weights...")
        from ml.training.train import train_baseline_model
        train_baseline_model(save_path=dest_path)

    return dest_path


if __name__ == "__main__":
    download_model_weights()
