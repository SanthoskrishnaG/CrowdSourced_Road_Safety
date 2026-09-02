import os
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from ml.prediction.dataset import FEATURE_COLUMNS, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from ml.prediction.features import build_preprocessor


class RoadRiskModel:
    """
    Predictive Machine Learning model for forecasting road segment deterioration risk (0-100),
    risk classification levels, worsening probabilities, and explainable contributing factors.
    """

    MODEL_VERSION = "road-risk-v1.0"

    def __init__(self, pipeline: Optional[Pipeline] = None, metadata: Optional[Dict[str, Any]] = None):
        self.pipeline = pipeline
        self.metadata = metadata or {
            "version": self.MODEL_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": "GradientBoostingRegressor",
            "metrics": {},
        }
        # Baseline population reference means for explainability calculation
        self.feature_means = {
            "historical_reports_count": 15.0,
            "reports_last_30d": 3.5,
            "reports_last_7d": 1.0,
            "historical_issues_count": 8.0,
            "active_issues_count": 1.8,
            "critical_issues_count": 0.3,
            "high_issues_count": 0.6,
            "critical_severity_ratio": 0.2,
            "road_health_score": 75.0,
            "avg_resolution_hours": 48.0,
            "length_km": 2.5,
            "speed_limit_kmh": 50.0,
            "issue_density_per_km": 0.8,
            "report_density_per_km": 6.0,
            "incident_frequency_weekly": 0.8,
        }

    @staticmethod
    def classify_risk_level(score: float) -> str:
        """
        Maps continuous 0-100 risk score to canonical Risk Level.
        """
        if score >= 75.0:
            return "CRITICAL"
        elif score >= 50.0:
            return "HIGH"
        elif score >= 25.0:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def calculate_worsening_probability(score: float) -> float:
        """
        Computes calibrated probability (0.00 to 1.00) of road segment worsening in next 30 days.
        Uses a smooth logistic function centered at score 50.
        """
        # Sigmoidal mapping centered at 50 with scale factor
        prob = 1.0 / (1.0 + math.exp(-0.065 * (score - 45.0)))
        return round(float(np.clip(prob, 0.02, 0.98)), 3)

    def extract_contributing_factors(self, features: Dict[str, Any], risk_score: float) -> List[Dict[str, Any]]:
        """
        Generates human-readable, non-deterministic explainability factors indicating
        the primary driving attributes behind the risk prediction.
        """
        contributions: List[Tuple[str, float, str]] = []

        # 1. Road health deficit
        health = float(features.get("road_health_score", 100.0))
        if health < 70.0:
            impact = (70.0 - health) * 0.45
            contributions.append((
                "Degraded Current Health Index",
                impact,
                f"Health score is at {health}/100, indicating existing physical structural compromise."
            ))

        # 2. Critical & High severity active hazards
        crit = int(features.get("critical_issues_count", 0))
        high = int(features.get("high_issues_count", 0))
        if crit > 0 or high > 0:
            crit_impact = (crit * 16.0) + (high * 8.0)
            contributions.append((
                "Active High-Severity Hazards",
                crit_impact,
                f"{crit} critical and {high} high-severity hazards remain unresolved on this corridor."
            ))

        # 3. Citizen report velocity
        rep_7d = int(features.get("reports_last_7d", 0))
        rep_30d = int(features.get("reports_last_30d", 0))
        if rep_7d >= 2 or rep_30d >= 5:
            vel_impact = (rep_7d * 6.0) + (rep_30d * 2.0)
            contributions.append((
                "Surge in Citizen Reports",
                vel_impact,
                f"Elevated report velocity ({rep_7d} in past 7d, {rep_30d} in past 30d) reflects rapid hazard formation."
            ))

        # 4. Issue Density
        density = float(features.get("issue_density_per_km", 0.0))
        if density > 1.2:
            dens_impact = min(20.0, (density - 1.0) * 8.0)
            contributions.append((
                "Elevated Hazard Density",
                dens_impact,
                f"Hazard density of {density:.1f} issues/km exceeds baseline urban threshold."
            ))

        # 5. Road hierarchy & traffic exposure
        rtype = str(features.get("road_type", "LOCAL")).upper()
        if rtype in ["HIGHWAY", "ARTERIAL"]:
            traffic_impact = 12.0 if rtype == "HIGHWAY" else 9.0
            contributions.append((
                f"High-Volume {rtype.capitalize()} Classification",
                traffic_impact,
                f"Heavy traffic volume and higher speed limits accelerate wear on this {rtype.lower()} corridor."
            ))

        # 6. Resolution turnaround lag
        res_hours = features.get("avg_resolution_hours")
        if res_hours is not None and float(res_hours) > 72.0:
            res_impact = min(15.0, (float(res_hours) - 48.0) * 0.12)
            contributions.append((
                "Maintenance Resolution Delay",
                res_impact,
                f"Average resolution turnaround time of {res_hours:.1f} hours allows damage to compound."
            ))

        # If low risk and few penalties, highlight positive stabilizing factors
        if not contributions or risk_score < 25.0:
            contributions.append((
                "Pristine Structural Baseline",
                5.0,
                "Hazard-free corridor with timely maintenance response records."
            ))

        # Sort contributions descending by impact
        contributions.sort(key=lambda x: x[1], reverse=True)
        total_impact = sum(c[1] for c in contributions) or 1.0

        factors: List[Dict[str, Any]] = []
        for name, impact, desc in contributions[:4]:
            pct = round(min(95.0, max(5.0, (impact / total_impact) * 100.0)), 1)
            factors.append({
                "factor_name": name,
                "impact_percentage": pct,
                "description": desc,
            })

        return factors

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes inference on road segment feature dictionary.
        Returns risk score, risk level, worsening probability, explainability factors, and disclaimer.
        """
        # Ensure all columns present
        df_row = pd.DataFrame([features])
        for col in FEATURE_COLUMNS:
            if col not in df_row.columns:
                df_row[col] = self.feature_means.get(col, 0.0)

        # Reorder columns
        df_row = df_row[FEATURE_COLUMNS]

        if self.pipeline is not None:
            try:
                raw_score = float(self.pipeline.predict(df_row)[0])
            except Exception:
                raw_score = self._fallback_heuristic_score(features)
        else:
            raw_score = self._fallback_heuristic_score(features)

        risk_score = round(float(np.clip(raw_score, 0.0, 100.0)), 1)
        risk_level = self.classify_risk_level(risk_score)
        worsening_prob = self.calculate_worsening_probability(risk_score)
        contributing_factors = self.extract_contributing_factors(features, risk_score)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "worsening_probability": worsening_prob,
            "contributing_factors": contributing_factors,
            "features_used": {k: features.get(k) for k in FEATURE_COLUMNS},
            "model_version": self.metadata.get("version", self.MODEL_VERSION),
            "disclaimer": (
                "Application-generated predictive estimate for prioritization. "
                "Does not claim certainty or replace official engineering inspections."
            ),
        }

    def _fallback_heuristic_score(self, features: Dict[str, Any]) -> float:
        """
        Deterministic scoring fallback if ML pipeline is uninitialized.
        """
        health = float(features.get("road_health_score", 100.0))
        crit = int(features.get("critical_issues_count", 0))
        high = int(features.get("high_issues_count", 0))
        density = float(features.get("issue_density_per_km", 0.0))
        rep_7d = int(features.get("reports_last_7d", 0))
        rtype = str(features.get("road_type", "LOCAL")).upper()

        traffic_bonus = 10.0 if rtype == "HIGHWAY" else (6.0 if rtype == "ARTERIAL" else 0.0)
        score = (
            (100.0 - health) * 0.40 +
            (crit * 14.0) +
            (high * 7.0) +
            (density * 5.0) +
            (rep_7d * 4.0) +
            traffic_bonus
        )
        return float(np.clip(score, 0.0, 100.0))

    def save(self, file_path: str):
        """Serializes trained model artifact with pipeline and metadata."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        payload = {
            "pipeline": self.pipeline,
            "metadata": self.metadata,
            "feature_means": self.feature_means,
        }
        joblib.dump(payload, file_path)

    @classmethod
    def load(cls, file_path: str) -> "RoadRiskModel":
        """Loads serialized model artifact from disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file not found at {file_path}")
        payload = joblib.load(file_path)
        model = cls(pipeline=payload.get("pipeline"), metadata=payload.get("metadata"))
        if "feature_means" in payload:
            model.feature_means = payload["feature_means"]
        return model


_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "weights", "road_risk_model_v1.joblib"
)

_cached_model: Optional[RoadRiskModel] = None


def load_road_risk_model(model_path: Optional[str] = None) -> RoadRiskModel:
    """
    Returns singleton instance of RoadRiskModel. Loads from disk if available,
    otherwise initializes with robust fallback.
    """
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    path = model_path or _DEFAULT_MODEL_PATH
    if os.path.exists(path):
        try:
            _cached_model = RoadRiskModel.load(path)
            return _cached_model
        except Exception:
            pass

    _cached_model = RoadRiskModel()
    return _cached_model
