import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import joblib
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from ml.datasets.dataset import load_class_mapping

DEFAULT_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "weights")
DEFAULT_WEIGHTS_PATH = os.path.join(DEFAULT_WEIGHTS_DIR, "road_classifier_v1.joblib")
DEFAULT_SEVERITY_WEIGHTS_PATH = os.path.join(DEFAULT_WEIGHTS_DIR, "severity_estimator_v1.joblib")

SEVERITY_CLASSES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_TO_IDX = {cls_name: i for i, cls_name in enumerate(SEVERITY_CLASSES)}
IDX_TO_SEVERITY = {i: cls_name for i, cls_name in enumerate(SEVERITY_CLASSES)}


class BaseRoadClassifier(ABC):
    """Abstract base class for all road hazard computer vision classifiers."""

    @abstractmethod
    def predict(self, feature_vector: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
        """
        Takes a feature vector or tensor.
        Returns:
            (predicted_class_name, confidence_score, dict_of_all_class_probabilities)
        """
        pass

    @abstractmethod
    def save(self, file_path: str):
        pass

    @abstractmethod
    def load(self, file_path: str):
        pass


class FeatureEnsembleClassifier(BaseRoadClassifier):
    """
    Trained high-performance road hazard classifier combining multi-layer perceptron neural network
    with standardized feature scaling and softmax probability calibration.
    Model Version: 'road-vision-v1.0'
    """

    MODEL_VERSION = "road-vision-v1.0"

    def __init__(self, mapping_path: Optional[str] = None):
        self.mapping = load_class_mapping(mapping_path) if mapping_path else load_class_mapping()
        self.classes: List[str] = self.mapping["classes"]
        self.class_to_idx: Dict[str, int] = self.mapping["class_to_idx"]
        self.idx_to_class: Dict[str, str] = {str(k): v for k, v in self.mapping["idx_to_class"].items()}
        
        # Scikit-learn Pipeline with Feature Scaler and Multi-Layer Perceptron
        self.pipeline: Optional[Pipeline] = None
        self.is_trained: bool = False

    def build_default_pipeline(self) -> Pipeline:
        """Constructs the neural classifier pipeline architecture."""
        scaler = StandardScaler()
        mlp = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            batch_size=32,
            learning_rate_init=1e-3,
            max_iter=300,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.15
        )
        return Pipeline([
            ("scaler", scaler),
            ("mlp", mlp)
        ])

    def fit(self, X: np.ndarray, y: np.ndarray):
        """Fits the classifier on feature matrix X and label array y."""
        if self.pipeline is None:
            self.pipeline = self.build_default_pipeline()
        self.pipeline.fit(X, y)
        self.is_trained = True

    def predict_probabilities(self, feature_vector: np.ndarray) -> np.ndarray:
        """
        Computes calibrated class probability distribution across all 8 target categories.
        """
        if not self.is_trained or self.pipeline is None:
            raise RuntimeError("Model is not trained or loaded. Call .fit() or .load() first.")

        if feature_vector.ndim == 1:
            feature_vector = np.expand_dims(feature_vector, axis=0)

        probs = self.pipeline.predict_proba(feature_vector)[0]
        return probs

    def predict(self, feature_vector: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
        """
        Generates classification prediction for a given feature vector.
        Returns:
            - predicted_class: str (e.g. "POTHOLE")
            - confidence: float (0.0 to 1.0)
            - probabilities: Dict[str, float]
        """
        probs = self.predict_probabilities(feature_vector)
        predicted_idx = int(np.argmax(probs))
        predicted_class = self.idx_to_class.get(str(predicted_idx), self.classes[predicted_idx])
        confidence = float(probs[predicted_idx])

        prob_dict = {
            self.idx_to_class.get(str(i), self.classes[i]): float(round(probs[i], 4))
            for i in range(len(self.classes))
        }

        return predicted_class, confidence, prob_dict

    def save(self, file_path: str = DEFAULT_WEIGHTS_PATH):
        """Serializes trained model artifact and class mapping to disk."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        payload = {
            "model_version": self.MODEL_VERSION,
            "mapping": self.mapping,
            "pipeline": self.pipeline,
            "is_trained": self.is_trained
        }
        joblib.dump(payload, file_path, compress=3)

    def load(self, file_path: str = DEFAULT_WEIGHTS_PATH):
        """Loads serialized model artifact from disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model weight file not found at {file_path}")
        payload = joblib.load(file_path)
        self.mapping = payload.get("mapping", self.mapping)
        self.classes = self.mapping["classes"]
        self.class_to_idx = self.mapping["class_to_idx"]
        self.idx_to_class = {str(k): v for k, v in self.mapping["idx_to_class"].items()}
        self.pipeline = payload["pipeline"]
        self.is_trained = payload.get("is_trained", True)


class RoadSeverityEstimator:
    """
    Trained Computer Vision Machine Learning Severity Estimator.
    Predicts hazard physical impact tier: LOW, MEDIUM, HIGH, CRITICAL.
    Model Version: 'road-severity-v1.0'
    """

    MODEL_VERSION = "road-severity-v1.0"

    def __init__(self):
        self.classes: List[str] = SEVERITY_CLASSES
        self.class_to_idx: Dict[str, int] = SEVERITY_TO_IDX
        self.idx_to_class: Dict[int, str] = IDX_TO_SEVERITY
        self.pipeline: Optional[Pipeline] = None
        self.is_trained: bool = False

    def build_default_pipeline(self) -> Pipeline:
        """Constructs the severity estimation pipeline architecture."""
        scaler = StandardScaler()
        mlp = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            alpha=1e-3,
            batch_size=32,
            learning_rate_init=1e-3,
            max_iter=300,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.15
        )
        return Pipeline([
            ("scaler", scaler),
            ("mlp", mlp)
        ])

    def fit(self, X: np.ndarray, y: np.ndarray):
        """Fits the severity estimator on feature matrix X and severity labels y."""
        if self.pipeline is None:
            self.pipeline = self.build_default_pipeline()
        self.pipeline.fit(X, y)
        self.is_trained = True

    def predict_probabilities(self, feature_vector: np.ndarray) -> np.ndarray:
        if not self.is_trained or self.pipeline is None:
            raise RuntimeError("Severity model is not trained or loaded. Call .fit() or .load() first.")

        if feature_vector.ndim == 1:
            feature_vector = np.expand_dims(feature_vector, axis=0)

        return self.pipeline.predict_proba(feature_vector)[0]

    def predict(self, feature_vector: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
        """
        Estimates hazard severity from extracted visual features.
        Returns:
            (predicted_severity, confidence_score, dict_of_severity_probabilities)
        """
        probs = self.predict_probabilities(feature_vector)
        predicted_idx = int(np.argmax(probs))
        predicted_severity = self.idx_to_class.get(predicted_idx, self.classes[predicted_idx])
        confidence = float(probs[predicted_idx])

        prob_dict = {
            self.classes[i]: float(round(probs[i], 4))
            for i in range(len(self.classes))
        }

        return predicted_severity, confidence, prob_dict

    def save(self, file_path: str = DEFAULT_SEVERITY_WEIGHTS_PATH):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        payload = {
            "model_version": self.MODEL_VERSION,
            "classes": self.classes,
            "pipeline": self.pipeline,
            "is_trained": self.is_trained
        }
        joblib.dump(payload, file_path, compress=3)

    def load(self, file_path: str = DEFAULT_SEVERITY_WEIGHTS_PATH):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Severity weight file not found at {file_path}")
        payload = joblib.load(file_path)
        self.classes = payload.get("classes", self.classes)
        self.pipeline = payload["pipeline"]
        self.is_trained = payload.get("is_trained", True)


def load_road_classifier(weights_path: str = DEFAULT_WEIGHTS_PATH) -> FeatureEnsembleClassifier:
    """Factory helper to instantiate and load the trained road classifier."""
    classifier = FeatureEnsembleClassifier()
    if os.path.exists(weights_path):
        classifier.load(weights_path)
    else:
        from ml.training.train import train_baseline_model
        classifier = train_baseline_model(save_path=weights_path)
    return classifier


def load_severity_estimator(weights_path: str = DEFAULT_SEVERITY_WEIGHTS_PATH) -> RoadSeverityEstimator:
    """Factory helper to instantiate and load the trained road severity estimator."""
    estimator = RoadSeverityEstimator()
    if os.path.exists(weights_path):
        estimator.load(weights_path)
    else:
        from ml.training.train import train_baseline_severity_model
        estimator = train_baseline_severity_model(save_path=weights_path)
    return estimator
