import os
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

from ml.prediction.dataset import generate_synthetic_road_risk_dataset, FEATURE_COLUMNS
from ml.prediction.features import build_preprocessor
from ml.prediction.model import RoadRiskModel


def train_road_risk_model(
    save_path: str = "ml/models/weights/road_risk_model_v1.joblib",
    n_samples: int = 2000,
    model_type: str = "gradient_boosting",
    random_state: int = 42,
) -> RoadRiskModel:
    """
    Trains and serializes the predictive road risk regression model with feature preprocessor.
    """
    print("=" * 70)
    print("PHASE 12: PREDICTIVE ROAD RISK MODEL TRAINING PIPELINE")
    print("=" * 70)

    print(f"Generating synthetic municipal road dataset ({n_samples} samples)...")
    X, y = generate_synthetic_road_risk_dataset(n_samples=n_samples, random_state=random_state)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state
    )

    print(f"Dataset split: {len(X_train)} training samples, {len(X_test)} validation samples.")

    preprocessor = build_preprocessor()

    if model_type == "random_forest":
        regressor = RandomForestRegressor(
            n_estimators=150,
            max_depth=9,
            min_samples_split=4,
            random_state=random_state,
            n_jobs=-1,
        )
        algo_name = "RandomForestRegressor"
    else:
        regressor = GradientBoostingRegressor(
            n_estimators=160,
            learning_rate=0.07,
            max_depth=4,
            subsample=0.85,
            random_state=random_state,
        )
        algo_name = "GradientBoostingRegressor"

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", regressor),
        ]
    )

    print(f"Running 5-Fold Cross Validation with {algo_name}...")
    kf = KFold(n_splits=5, shuffle=True, random_state=random_state)
    cv_r2 = cross_val_score(pipeline, X_train, y_train, cv=kf, scoring="r2")
    cv_neg_mse = cross_val_score(
        pipeline, X_train, y_train, cv=kf, scoring="neg_mean_squared_error"
    )
    cv_rmse = np.sqrt(-cv_neg_mse)

    print(f"  5-Fold CV R2 Score: {cv_r2.mean():.4f} (+/- {cv_r2.std():.4f})")
    print(f"  5-Fold CV RMSE:     {cv_rmse.mean():.4f} (+/- {cv_rmse.std():.4f})")

    print(f"Fitting final pipeline on {len(X_train)} samples...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    test_mse = mean_squared_error(y_test, y_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_pred)
    test_r2 = r2_score(y_test, y_pred)

    print("-" * 70)
    print("TEST BENCHMARK EVALUATION:")
    print(f"  R2 Score: {test_r2:.4f}")
    print(f"  RMSE:     {test_rmse:.3f} points")
    print(f"  MAE:      {test_mae:.3f} points")
    print("-" * 70)

    # Compute feature means for explainability baseline
    feature_means = {}
    for col in FEATURE_COLUMNS:
        if col in X.columns and pd.api.types.is_numeric_dtype(X[col]):
            feature_means[col] = float(X[col].mean())

    metadata = {
        "version": RoadRiskModel.MODEL_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": algo_name,
        "n_samples": n_samples,
        "metrics": {
            "cv_r2_mean": float(cv_r2.mean()),
            "cv_rmse_mean": float(cv_rmse.mean()),
            "test_r2": float(test_r2),
            "test_rmse": float(test_rmse),
            "test_mae": float(test_mae),
        },
    }

    model = RoadRiskModel(pipeline=pipeline, metadata=metadata)
    model.feature_means = feature_means

    print(f"Saving trained model weights to: {save_path}")
    model.save(save_path)
    print("[SUCCESS] Predictive Road Risk Model successfully saved!")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Road Risk Predictive Model")
    parser.add_argument(
        "--save_path",
        type=str,
        default="ml/models/weights/road_risk_model_v1.joblib",
        help="Target output artifact path",
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=2000,
        help="Number of synthetic samples to generate",
    )
    parser.add_argument(
        "--model_type",
        type=str,
        choices=["gradient_boosting", "random_forest"],
        default="gradient_boosting",
        help="Model algorithm choice",
    )
    args = parser.parse_args()

    train_road_risk_model(
        save_path=args.save_path,
        n_samples=args.n_samples,
        model_type=args.model_type,
    )
