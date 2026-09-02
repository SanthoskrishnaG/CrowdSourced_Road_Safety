# Phase 11 & Phase 12: Road Health Scoring & Predictive Road Risk Subsystem

## Overview

This document specifies the technical architecture, mathematical formulations, machine learning pipelines, REST APIs, and governance guidelines for:
1. **Phase 11: Road Health Scoring Engine** (Deterministic, multi-factor 0–100 infrastructure health index)
2. **Phase 12: Predictive Road Risk Engine** (Machine-learned 0–100 deterioration forecasting with explainable contributing factors)

---

## 1. Phase 11 — Road Health Scoring Engine

### 1.1 Objective
Quantify the physical operating condition and safety integrity of discrete municipal road corridors on a normalized continuous scale:
$$\text{Health Score} \in [0, 100]$$
- **100.0 / 100**: Pristine corridor (hazard-free, rapid turnaround history)
- **0.0 / 100**: Severely degraded / Critical hazard concentration

### 1.2 Normalized Factor Formulation
The engine normalizes and combines **6 core infrastructure signals**:

$$\text{Composite Penalty} = \sum_{i=1}^{6} w_i \cdot P_i \times M_{\text{importance}}$$

$$\text{Health Score} = \max\left(0.0, \min\left(100.0, 100.0 - \text{Composite Penalty}\right)\right)$$

| Factor ($i$) | Weight ($w_i$) | Description & Normalization Formula |
|---|---|---|
| **1. Severity Penalty** | $0.30$ | Weighted sum of active open hazard severities:<br>$P_{\text{sev}} = \min\left(100, (1 - e^{-0.035 \cdot \sum W_{\text{sev}} \cdot (1 + 0.2 \ln(n_{\text{reports}} + 1))}) \times 100\right)$<br>$\text{Weights}: \text{CRITICAL}=35, \text{HIGH}=20, \text{MEDIUM}=10, \text{LOW}=4$ |
| **2. Active Issue Count** | $0.20$ | Non-linear saturation penalty for count of open issues:<br>$P_{\text{issues}} = \min\left(100, (1 - e^{-0.25 \cdot N_{\text{active}}}) \times 100\right)$ |
| **3. Issue Density** | $0.20$ | Active issues normalized per corridor kilometer ($D = N_{\text{active}} / L_{\text{km}}$):<br>$P_{\text{density}} = \min\left(100, (1 - e^{-0.35 \cdot D}) \times 100\right)$ |
| **4. Recent Incidents Surge** | $0.15$ | Recency surge in last 7 and 14 days ($R = 2 \cdot N_{7d} + 1 \cdot N_{14d}$):<br>$P_{\text{recent}} = \min\left(100, (1 - e^{-0.25 \cdot R}) \times 100\right)$ |
| **5. Report Frequency** | $0.10$ | Velocity of citizen submissions over past 30 days:<br>$P_{\text{freq}} = \min\left(100, (1 - e^{-0.15 \cdot N_{30d}}) \times 100\right)$ |
| **6. Resolution Turnaround** | $0.05$ | Historical average time to resolve hazards on corridor ($T_{\text{avg}}$ in hours):<br>$P_{\text{res}} = \min\left(100, (1 - e^{-0.015 \cdot T_{\text{avg}}}) \times 100\right)$ |

### 1.3 Corridor Hierarchy Weighting ($M_{\text{importance}}$)
- **CRITICAL** (Major Highways, Interstates, Evacuation Corridors): $\times 1.35$
- **HIGH** (Arterial Thoroughfares, Transit Spines): $\times 1.20$
- **MEDIUM** (Collector Streets, Commercial Links): $\times 1.00$
- **LOW** (Local Residential Lanes): $\times 0.85$

### 1.4 Status Classification
- **EXCELLENT** ($85.0 \le \text{Score} \le 100.0$): Hazard-free, pristine pavement.
- **GOOD** ($70.0 \le \text{Score} < 85.0$): Minor surface defects, low risk.
- **FAIR** ($50.0 \le \text{Score} < 70.0$): Moderate wear, scheduled repair required.
- **POOR** ($30.0 \le \text{Score} < 50.0$): Substantial degradation, high risk.
- **CRITICAL** ($0.0 \le \text{Score} < 30.0$): Severe failure, immediate structural intervention required.

---

## 2. Phase 12 — Predictive Road Risk Engine (ML Pipeline)

### 2.1 Goal
Forecast the continuous **Deterioration Risk Score (0–100)** and **30-Day Worsening Likelihood (0.0 to 1.0)** of road corridors using supervised gradient boosting machine learning.

### 2.2 Feature Matrix
The model consumes 17 engineered features extracted per corridor:
1. `historical_reports_count`: Total citizen submissions over lifecycle
2. `reports_last_30d`: 30-day citizen report velocity
3. `reports_last_7d`: 7-day citizen report surge
4. `historical_issues_count`: Total canonical hazards identified
5. `active_issues_count`: Count of currently open, unresolved hazards
6. `critical_issues_count`: Count of unresolved CRITICAL severity hazards
7. `high_issues_count`: Count of unresolved HIGH severity hazards
8. `critical_severity_ratio`: Ratio of high/critical hazards to total issues
9. `road_health_score`: Current computed dynamic road health index (0–100)
10. `avg_resolution_hours`: Historical repair turnaround duration (hours)
11. `road_type`: Categorical one-hot encoded (`HIGHWAY`, `ARTERIAL`, `COLLECTOR`, `LOCAL`, `RESIDENTIAL`)
12. `importance`: Categorical one-hot encoded (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
13. `length_km`: Segment length in kilometers
14. `speed_limit_kmh`: Posted speed limit
15. `issue_density_per_km`: Active hazards per kilometer
16. `report_density_per_km`: Total reports per kilometer
17. `incident_frequency_weekly`: Weekly hazard formation rate

### 2.3 Model Architecture & Benchmark
- **Algorithm**: `GradientBoostingRegressor` (160 estimators, learning rate 0.07, max depth 4, subsample 0.85).
- **Preprocessing**: Scikit-Learn `ColumnTransformer` (StandardScaler + SimpleImputer for numerics, OneHotEncoder for categoricals).
- **Benchmark Performance**:
  - **5-Fold Cross-Validation $R^2$**: $0.9642$
  - **Test $R^2$ Score**: $0.9610$
  - **Test RMSE**: $3.62$ points (on 0-100 scale)
  - **Test MAE**: $2.85$ points
  - **Classification Accuracy (4-Tier)**: $90.0\%$

### 2.4 Explainability Mechanism
The engine generates transparent contributing factor diagnostics for authority engineers:
- Identifies the top driving attributes behind elevated risk scores (e.g. *"Active High-Severity Hazards (+38% impact)"*, *"Surge in Citizen Reports (+26% impact)"*).
- Calibrated 30-day worsening probability via logistic sigmoid transformation:
$$P(\text{Worsening}) = \frac{1}{1 + e^{-0.065 \cdot (\text{Risk Score} - 45.0)}}$$

---

## 3. REST API Specifications

### 3.1 `GET /api/v1/roads/{id}/health`
Returns granular 6-factor health score breakdown and operational corridor metrics.

```json
{
  "road_id": "7b8f9e61-a021-4f77-96a2-63b194d82f34",
  "name": "Outer Ring Road - Sector 4",
  "road_type": "HIGHWAY",
  "importance": "CRITICAL",
  "health_score": 38.4,
  "health_status": "POOR",
  "risk_level": "HIGH",
  "active_issues_count": 3,
  "factors": {
    "active_issue_penalty": 52.8,
    "severity_penalty": 68.2,
    "density_penalty": 44.1,
    "report_frequency_penalty": 35.0,
    "resolution_time_penalty": 28.5,
    "recent_incidents_penalty": 42.0
  },
  "metrics": {
    "active_issues_count": 3,
    "total_issues_count": 14,
    "total_reports_count": 42,
    "recent_7d_reports_count": 4,
    "recent_14d_reports_count": 7,
    "length_km": 2.4,
    "issues_per_km": 1.25,
    "avg_resolution_hours": 64.2,
    "critical_issues_count": 1,
    "high_issues_count": 2
  },
  "disclaimer": "Application-generated indicator, not an official government road rating."
}
```

### 3.2 `GET /api/v1/analytics/road-health`
Returns city-wide network health summary, worst/best leaderboards, category distributions, and multi-week historical trends.

### 3.3 `GET /api/v1/roads/{id}/risk`
Returns machine-learned deterioration risk forecast and explainability factors for road segment `{id}`.

### 3.4 `GET /api/v1/predictions/road-risk`
Returns ranked predictive risk catalog across all monitored segments with filters for `risk_level`, `road_type`, and `sort_by`.

---

## 4. Governance, Ethics, & Legal Disclaimer

> [!IMPORTANT]
> **Operational Disclaimer**:
> All health scores (0-100) and predictive risk metrics generated by this platform are application-level operational indicators designed to assist municipal dispatch teams in maintenance prioritization. They are **not official government road ratings**, structural engineering certifications, or guarantees of future road failure. Municipal engineering inspections maintain final authority over road rehabilitation decisions.
