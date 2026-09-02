import math
import random
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "historical_reports_count",
    "reports_last_30d",
    "reports_last_7d",
    "historical_issues_count",
    "active_issues_count",
    "critical_issues_count",
    "high_issues_count",
    "critical_severity_ratio",
    "road_health_score",
    "avg_resolution_hours",
    "road_type",
    "importance",
    "length_km",
    "speed_limit_kmh",
    "issue_density_per_km",
    "report_density_per_km",
    "incident_frequency_weekly",
]

CATEGORICAL_FEATURES = ["road_type", "importance"]
NUMERICAL_FEATURES = [f for f in FEATURE_COLUMNS if f not in CATEGORICAL_FEATURES]


def generate_synthetic_road_risk_dataset(n_samples: int = 1500, random_state: int = 42) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Generates a realistic municipal road corridor dataset representing various road types,
    traffic volumes, maintenance profiles, hazard densities, and deterioration risk scores (0-100).
    """
    rng = np.random.default_rng(random_state)

    road_types = ["HIGHWAY", "ARTERIAL", "COLLECTOR", "LOCAL", "RESIDENTIAL"]
    importances = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    data: List[Dict[str, Any]] = []
    targets: List[float] = []

    for _ in range(n_samples):
        rtype = rng.choice(road_types, p=[0.15, 0.35, 0.25, 0.15, 0.10])
        imp = rng.choice(importances, p=[0.20, 0.30, 0.35, 0.15])

        # Length in km
        if rtype == "HIGHWAY":
            length_km = rng.uniform(2.0, 15.0)
            speed_limit = rng.choice([80, 90, 100, 110, 120])
            traffic_mult = 1.6
        elif rtype == "ARTERIAL":
            length_km = rng.uniform(1.0, 6.0)
            speed_limit = rng.choice([50, 60, 70, 80])
            traffic_mult = 1.4
        elif rtype == "COLLECTOR":
            length_km = rng.uniform(0.5, 3.0)
            speed_limit = rng.choice([40, 50, 60])
            traffic_mult = 1.1
        elif rtype == "LOCAL":
            length_km = rng.uniform(0.3, 2.0)
            speed_limit = rng.choice([30, 40, 50])
            traffic_mult = 0.9
        else: # RESIDENTIAL
            length_km = rng.uniform(0.2, 1.5)
            speed_limit = rng.choice([20, 30, 40])
            traffic_mult = 0.7

        # Historical reports & issues
        hist_reports = int(rng.exponential(scale=12.0 * traffic_mult))
        reports_30d = min(hist_reports, int(rng.poisson(lam=3.0 * traffic_mult)))
        reports_7d = min(reports_30d, int(rng.poisson(lam=0.9 * traffic_mult)))

        hist_issues = max(0, int(hist_reports * rng.uniform(0.4, 0.85)))
        active_issues = min(hist_issues, int(rng.poisson(lam=1.5 * traffic_mult)))

        # Severity breakdown
        if active_issues > 0:
            crit_issues = int(rng.binomial(n=active_issues, p=0.18))
            high_issues = int(rng.binomial(n=(active_issues - crit_issues), p=0.35))
        else:
            crit_issues = 0
            high_issues = 0

        total_tracked = max(1, active_issues)
        crit_ratio = (crit_issues * 1.0 + high_issues * 0.5) / total_tracked

        # Resolution turnaround in hours
        avg_res_hours = float(rng.gamma(shape=3.0, scale=18.0)) # ~54 hours mean

        # Densities
        issue_density = active_issues / length_km
        report_density = hist_reports / length_km
        incident_freq_weekly = reports_30d / 4.28

        # Simulated road health (correlated negatively with active issues & severity)
        raw_health_penalty = (
            (active_issues * 6.5) +
            (crit_issues * 18.0) +
            (high_issues * 8.0) +
            (issue_density * 4.0) +
            (reports_7d * 3.5)
        )
        health_score = max(5.0, min(100.0, 100.0 - raw_health_penalty + rng.normal(0, 3.0)))

        # Target Risk Score formulation (ground truth simulated from physical degradation model)
        # Ground truth risk considers:
        # - low health (weight 0.35)
        # - high active issue & critical severity density (weight 0.25)
        # - high velocity of recent citizen reports (weight 0.20)
        # - heavy road type / traffic load (weight 0.12)
        # - prolonged historical resolution delay (weight 0.08)
        health_risk_component = (100.0 - health_score) * 0.35
        severity_density_comp = min(30.0, (crit_issues * 8.0 + high_issues * 4.0 + issue_density * 3.0)) * 0.85
        velocity_comp = min(25.0, (reports_7d * 4.0 + reports_30d * 1.5)) * 0.80
        traffic_comp = 15.0 * (traffic_mult - 0.7) / 0.9
        resolution_comp = min(15.0, (avg_res_hours / 120.0) * 15.0)

        importance_boost = {"CRITICAL": 1.25, "HIGH": 1.10, "MEDIUM": 1.0, "LOW": 0.90}[imp]

        target_risk = (
            health_risk_component +
            severity_density_comp +
            velocity_comp +
            traffic_comp +
            resolution_comp
        ) * importance_boost + rng.normal(0, 2.5)

        target_risk = float(np.clip(target_risk, 0.0, 100.0))

        row = {
            "historical_reports_count": hist_reports,
            "reports_last_30d": reports_30d,
            "reports_last_7d": reports_7d,
            "historical_issues_count": hist_issues,
            "active_issues_count": active_issues,
            "critical_issues_count": crit_issues,
            "high_issues_count": high_issues,
            "critical_severity_ratio": round(crit_ratio, 3),
            "road_health_score": round(health_score, 1),
            "avg_resolution_hours": round(avg_res_hours, 1),
            "road_type": rtype,
            "importance": imp,
            "length_km": round(length_km, 2),
            "speed_limit_kmh": speed_limit,
            "issue_density_per_km": round(issue_density, 2),
            "report_density_per_km": round(report_density, 2),
            "incident_frequency_weekly": round(incident_freq_weekly, 2),
        }

        data.append(row)
        targets.append(round(target_risk, 1))

    df = pd.DataFrame(data)
    y = pd.Series(targets, name="risk_score")
    return df, y
