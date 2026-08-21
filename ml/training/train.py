"""
Road Hazard Model Training Pipeline.
Trains calibrated visual classifiers and transfer-learning models on road problem images.
"""

import os
import argparse
from typing import Optional, Tuple, List, Dict
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score

from ml.datasets.dataset import (
    load_class_mapping,
    RoadHazardDataset,
    generate_synthetic_hazard_image,
)
from ml.preprocessing.transform import extract_vision_features
from ml.models.classifier import (
    FeatureEnsembleClassifier,
    DEFAULT_WEIGHTS_PATH,
)


def generate_augmented_training_data(
    samples_per_class: int = 40,
    random_seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates a calibrated, multi-condition training dataset covering all 8 road hazard categories
    with variations in illumination, scale, occlusion, and road surface conditions.
    """
    mapping = load_class_mapping()
    classes = mapping["classes"]
    class_to_idx = mapping["class_to_idx"]

    rng = np.random.RandomState(random_seed)
    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    for cls_name in classes:
        cls_idx = class_to_idx[cls_name]
        for i in range(samples_per_class):
            # Vary dimensions slightly to simulate citizen camera resolutions
            w = rng.randint(200, 360)
            h = rng.randint(200, 360)
            base_img = generate_synthetic_hazard_image(cls_name, width=w, height=h)

            # Apply computer vision feature extraction
            features = extract_vision_features(base_img)

            # Add slight realistic Gaussian feature perturbation for generalization
            noise = rng.normal(0, 0.015, size=features.shape).astype(np.float32)
            aug_features = features + noise

            X_list.append(aug_features)
            y_list.append(cls_idx)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)
    return X, y


def train_baseline_model(
    save_path: str = DEFAULT_WEIGHTS_PATH,
    samples_per_class: int = 50
) -> FeatureEnsembleClassifier:
    """
    Trains and validates the baseline road hazard classifier and saves artifact to disk.
    """
    print(f"[ML Training] Generating calibrated dataset ({samples_per_class} samples/class)...")
    X, y = generate_augmented_training_data(samples_per_class=samples_per_class)

    print(f"[ML Training] Dataset feature matrix shape: {X.shape}, labels shape: {y.shape}")

    classifier = FeatureEnsembleClassifier()
    
    # 5-Fold Stratified Cross Validation to ensure no overfitting
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_scores = []
    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        fold_model = classifier.build_default_pipeline()
        fold_model.fit(X_train, y_train)
        y_pred = fold_model.predict(X_val)
        score = accuracy_score(y_val, y_pred)
        fold_scores.append(score)

    mean_cv_accuracy = float(np.mean(fold_scores))
    print(f"[ML Training] Stratified 5-Fold Cross-Validation Accuracy: {mean_cv_accuracy:.4f} (+/- {np.std(fold_scores):.4f})")

    # Fit final model on full dataset
    classifier.fit(X, y)
    print(f"[ML Training] Model fitting complete. Saving weights to {save_path}...")
    classifier.save(save_path)
    print(f"[ML Training] Artifact saved successfully. Model version: {classifier.MODEL_VERSION}")
    return classifier


def train_classifier(
    dataset_dir: Optional[str] = None,
    save_path: str = DEFAULT_WEIGHTS_PATH,
    samples_per_class: int = 50
) -> FeatureEnsembleClassifier:
    """
    Main training entry point. If dataset_dir is provided, loads images from disk;
    otherwise trains baseline model.
    """
    if dataset_dir and os.path.exists(dataset_dir):
        print(f"[ML Training] Loading custom dataset from {dataset_dir}...")
        ds = RoadHazardDataset(root_dir=dataset_dir, split="train")
        X, y = ds.extract_features_and_labels()
        if len(X) == 0:
            print("[ML Training] No valid images found in dataset directory. Falling back to synthetic baseline.")
            return train_baseline_model(save_path=save_path, samples_per_class=samples_per_class)

        classifier = FeatureEnsembleClassifier()
        classifier.fit(X, y)
        classifier.save(save_path)
        return classifier
    else:
        return train_baseline_model(save_path=save_path, samples_per_class=samples_per_class)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Road Hazard Image Classifier")
    parser.add_argument("--dataset_dir", type=str, default=None, help="Path to road dataset directory")
    parser.add_argument("--save_path", type=str, default=DEFAULT_WEIGHTS_PATH, help="Path to output model weights")
    parser.add_argument("--samples", type=int, default=50, help="Samples per class for baseline generation")
    args = parser.parse_args()

    train_classifier(dataset_dir=args.dataset_dir, save_path=args.save_path, samples_per_class=args.samples)
