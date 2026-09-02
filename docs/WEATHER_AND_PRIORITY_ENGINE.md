# Weather Intelligence & Advanced Priority Engine Documentation

This document describes the architectural specifications, mathematical formulations, provider abstractions, and explainability frameworks for **Phase 13 (Weather Correlation & Intelligence)** and **Phase 14 (Advanced Priority Engine)**.

---

## 1. Phase 13: Weather Intelligence & Correlation Architecture

### 1.1 Provider Abstraction Layer

The platform abstracts weather telemetry behind `BaseWeatherProvider` in [`backend/app/services/weather/base.py`](file:///c:/Users/Santhoskrishna/Documents/Crowdsourced%20Road%20Safety/backend/app/services/weather/base.py):

* `MockWeatherProvider`: Deterministic, localized meteorological simulation based on lat/lon coordinates and time-of-year sin/cos curves. Returns `is_mock=True` to maintain clear data provenance.
* `OpenWeatherMapProvider`: Production integration utilizing OpenWeatherMap OneCall 3.0 API. Gracefully falls back to mock telemetry if the API key is unconfigured.
* `WeatherAPIProvider`: Production integration utilizing WeatherAPI.com endpoints with automatic fallback.

### 1.2 Meteorological Telemetry Points

Each weather telemetry reading captures:
* **Temperature** (°C)
* **Relative Humidity** (%)
* **Precipitation / Rainfall Rate** (mm/h and 24h cumulative mm)
* **Atmospheric Condition**: `CLEAR`, `CLOUDY`, `RAIN`, `HEAVY_RAIN`, `THUNDERSTORM`, `FOG`, `SNOW`, `HIGH_WIND`
* **Severe Weather Flag**: `is_severe: bool` denoting active convective warnings or intense precipitation.

### 1.3 Statistical Hazard Correlation Engine

Implemented in [`backend/app/services/weather_correlation_service.py`](file:///c:/Users/Santhoskrishna/Documents/Crowdsourced%20Road%20Safety/backend/app/services/weather_correlation_service.py):

1. **Pearson Linear Correlation ($r$)**:
   $$r = \frac{\sum (X_i - \bar{X})(Y_i - \bar{Y})}{\sqrt{\sum (X_i - \bar{X})^2 \sum (Y_i - \bar{Y})^2}}$$
2. **Spearman Rank Correlation ($\rho$)**:
   $$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$$
3. **Rainfall Impact Multiplier**:
   $$\text{Multiplier} = \frac{\text{Mean Daily Hazard Incidents (Rainy Days)}}{\text{Mean Daily Hazard Incidents (Dry Days)}}$$
4. **Lagged Saturation Model**:
   * *Flooding*: Instantaneous (0-day lag) correlation with precipitation.
   * *Potholes*: 1–2 day delayed correlation reflecting asphalt hydrostatic pressure expansion and pore saturation.

---

## 2. Phase 14: Advanced 9-Factor Priority Engine

Implemented in [`backend/app/services/priority_engine.py`](file:///c:/Users/Santhoskrishna/Documents/Crowdsourced%20Road%20Safety/backend/app/services/priority_engine.py).

### 2.1 Mathematical Formulation & Factor Weights

Total Priority Score $S \in [0, 100]$:

| # | Factor | Max Pts | Formula / Discrete Mapping | Rationale |
|---|---|---|---|---|
| 1 | **Severity** | 25 | `CRITICAL`: 25, `HIGH`: 18, `MEDIUM`: 10, `LOW`: 4 | Inherent physical hazard size & danger |
| 2 | **Independent Citizen Reports** | 15 | $5.0 + 3.5 \cdot \ln(\text{count})$ (capped at 15.0) | Multi-citizen consensus with diminishing return |
| 3 | **Road Health Degradation** | 15 | $\frac{100 - \text{Health Score}}{100} \times 15.0$ | Segments in critical condition receive higher urgency |
| 4 | **Traffic Density** | 10 | `HEAVY`: 10.0, `MEDIUM`: 7.0, `LOW`: 3.0 | Arterial impact and vehicle volume exposure |
| 5 | **Location Zone** | 10 | `HOSPITAL`: 10, `SCHOOL`: 9, `MAIN_ROAD`: 7, `RESIDENTIAL`: 4 | Proximity to vulnerable pedestrian corridors |
| 6 | **Time Unresolved (Aging)** | 10 | $\min(10.0, 1.0 \times \text{days unresolved})$ | Enforces municipal SLA compliance |
| 7 | **ML Predicted Accident Risk** | 10 | $\frac{\text{Predicted Risk Score}}{100} \times 10.0$ | Machine-learning accident likelihood weighting |
| 8 | **Weather Conditions** | 5 | `Severe/Heavy Rain`: 5.0, `Moderate Rain`: 2.5, `Clear`: 0.0 | Environmental worsening acceleration |
| 9 | **Citizen Confirmations** | 5 | $\min(5.0, 1.0 \times \text{confirmations})$ | Community validation on ground |

### 2.2 4-Tier Categorical Thresholds

* **CRITICAL**: $75.0 \le S \le 100.0$ (Immediate emergency dispatch within 4–12 hours)
* **HIGH**: $50.0 \le S < 75.0$ (Actionable within 24–48 hours)
* **MEDIUM**: $25.0 \le S < 50.0$ (Scheduled within standard maintenance queue)
* **LOW**: $0.0 \le S < 25.0$ (Routine periodic repair)

### 2.3 Explainability & Audit Trail

* Every issue response includes `priority_breakdown` containing exact earned points, maximum points, percentage weight, and `top_contributing_drivers`.
* Changes in priority (due to status change, road health change, or manual recalculation) are preserved in the `PriorityHistory` table and queryable via `GET /api/v1/issues/{id}/priority-history`.
