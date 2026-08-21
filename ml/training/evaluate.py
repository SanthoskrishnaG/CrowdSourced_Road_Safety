"""
Model Evaluation and Benchmark Reporting Pipeline.
Computes Confusion Matrices, Classification Reports (Precision, Recall, F1), and Calibration Scores.
"""

import os
import argparse
from typing import Dict, Any, Optional
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

from ml.datasets.dataset import load_class_mapping, generate_synthetic_hazard_image
from ml.preprocessing.transform import extract_vision_features
from ml.models.classifier import load_road_classifier, DEFAULT_WEIGHTS_PATH


def evaluate_model(
    weights_path: str = DEFAULT_WEIGHTS_PATH,
    test_samples_per_class: int = 25,
    random_seed: int = 1337
) -> Dict[str, Any]:
    """
    Evaluates the road hazard classifier on an independent test split.
    """
    mapping = load_class_mapping()
    classes = mapping["classes"]
    class_to_idx = mapping["class_to_idx"]

    classifier = load_road_classifier(weights_path)

    rng = np.random.RandomState(random_seed)
    y_true = []
    y_pred = []
    confidences = []

    for cls_name in classes:
        cls_idx = class_to_idx[cls_name]
        for i in range(test_samples_per_class):
            w = rng.randint(224, 400)
            h = rng.randint(224, 400)
            img = generate_synthetic_hazard_image(cls_name, width=w, height=h)
            features = extract_vision_features(img)

            pred_class, conf, _ = classifier.predict(features)
            pred_idx = class_to_idx[pred_class]

            y_true.append(cls_idx)
            y_pred.append(pred_idx)
            confidences.append(conf)

    acc = accuracy_score(y_true, y_pred)
    report_dict = classification_report(
        y_true,
        y_pred,
        target_names=classes,
        output_dict=True,
        zero_division=0
    )
    conf_matrix = confusion_matrix(y_true, y_pred).tolist()
    mean_conf = float(np.mean(confidences))

    summary = {
        "model_version": classifier.MODEL_VERSION,
        "accuracy": float(acc),
        "mean_confidence": mean_conf,
        "classification_report": report_dict,
        "confusion_matrix": conf_matrix,
        "classes": classes
    }

    print("=" * 60)
    print(f"ROAD HAZARD ML MODEL EVALUATION: {classifier.MODEL_VERSION}")
    print("=" * 60)
    print(f"Overall Test Accuracy: {acc * 100:.2f}%")
    print(f"Mean Prediction Confidence: {mean_conf * 100:.2f}%")
    print("\nDetailed Per-Class Metrics:")
    print(classification_report(y_true, y_pred, target_names=classes, zero_division=0))
    print("=" * 60)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Road Hazard Classifier")
    parser.add_argument("--weights", type=str, default=DEFAULT_WEIGHTS_PATH, help="Path to weights file")
    parser.add_argument("--samples", type=int, default=25, help="Test samples per class")
    args = parser.parse_args()

    evaluate_model(weights_path=args.weights, test_samples_per_class=args.samples)
