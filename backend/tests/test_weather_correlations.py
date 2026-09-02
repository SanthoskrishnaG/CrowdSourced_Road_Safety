from app.models.report import ReportCategory, ReportSeverity, ReportStatus, RoadReport
from app.services.weather_correlation_service import (
    WeatherCorrelationService,
    _compute_pearson_r,
    _compute_spearman_r
)


def test_pearson_and_spearman_math():
    x = [10.0, 20.0, 30.0, 40.0, 50.0]
    y = [5.0, 10.0, 15.0, 20.0, 25.0]

    # Perfect linear positive correlation
    r = _compute_pearson_r(x, y)
    assert r == 1.0

    rho = _compute_spearman_r(x, y)
    assert rho == 1.0

    # Negative correlation
    y_neg = [50.0, 40.0, 30.0, 20.0, 10.0]
    assert _compute_pearson_r(x, y_neg) == -1.0


def test_weather_correlation_service_calculation(db_session):
    import uuid
    from app.models.user import User, UserRole

    user = User(
        id=uuid.uuid4(),
        email=f"weather_test_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Weather Test User",
        password_hash="hash",
        role=UserRole.CITIZEN
    )
    db_session.add(user)
    db_session.commit()

    # Insert test reports
    for cat in [ReportCategory.FLOODING, ReportCategory.POTHOLE, ReportCategory.ROAD_DAMAGE]:
        report = RoadReport(
            reporter_id=user.id,
            title=f"Test {cat.value}",
            category=cat,
            description=f"Test hazard report description for {cat.value}",
            severity=ReportSeverity.HIGH,
            status=ReportStatus.REPORTED,
            latitude=12.9716,
            longitude=77.5946
        )
        db_session.add(report)
    db_session.commit()


    res = WeatherCorrelationService.get_weather_correlations(db_session, days=14)
    assert res.time_window_days == 14
    assert len(res.trend_history) == 14
    assert len(res.category_correlations) >= 3

    categories = [c.category for c in res.category_correlations]
    assert "FLOODING" in categories
    assert "POTHOLE" in categories
    assert "ROAD_DAMAGE" in categories

    for c in res.category_correlations:
        assert -1.0 <= c.pearson_r <= 1.0
        assert -1.0 <= c.spearman_r <= 1.0
        assert c.rainfall_multiplier >= 0.0


def test_weather_correlation_analytics_api(client, authority_token, citizen_token):
    # Citizen access forbidden
    res_citizen = client.get("/api/v1/analytics/weather-correlations", headers=citizen_token)
    assert res_citizen.status_code == 403

    # Authority access allowed
    res_auth = client.get("/api/v1/analytics/weather-correlations?days=30", headers=authority_token)
    assert res_auth.status_code == 200
    data = res_auth.json()

    assert "summary" in data
    assert "category_correlations" in data
    assert "trend_history" in data
    assert "advisory_recommendations" in data
    assert len(data["trend_history"]) == 30
