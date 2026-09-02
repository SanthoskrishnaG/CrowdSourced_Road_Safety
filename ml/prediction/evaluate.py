import argparse
import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, classification_report, confusion_matrix

from ml.prediction.dataset import generate_synthetic_road_risk_dataset
from ml.prediction.model import RoadRiskModel


def evaluate_road_risk_model(
    model_path: str = "ml/models/weights/road_risk_model_v1.joblib",
    n_samples: int = 500,
    random_state: int = 123,
):
    """
    Evaluates serialized predictive road risk model against independent validation set.
    """
    print("=" * 70)
    print("PHASE 12: PREDICTIVE ROAD RISK EVALUATION BENCHMARK")
    print("=" * 70)

    if not os.path.exists(model_path):
        print(f"Error: Model file {model_path} not found. Please run training first.")
        return

    print(f"Loading model from: {model_path}")
    model = RoadRiskModel.load(model_path)
    print(f"Model Version: {model.metadata.get('version')}")
    print(f"Algorithm:     {model.metadata.get('algorithm')}")

    print(f"Generating independent benchmark validation set ({n_samples} samples)...")
    X_val, y_val = generate_synthetic_road_risk_dataset(n_samples=n_samples, random_state=random_state)

    preds = []
    pred_levels = []
    true_levels = []

    for idx, row in X_val.iterrows():
        res = model.predict(row.to_dict())
        preds.append(res["risk_score"])
        pred_levels.append(res["risk_level"])
        true_levels.append(RoadRiskModel.classify_risk_level(float(y_val.iloc[idx])))

    preds = np.array(preds)
    y_val_arr = y_val.to_numpy()

    mse = mean_squared_error(y_val_arr, preds)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_val_arr, preds)
    r2 = r2_score(y_val_arr, preds)

    print("-" * 70)
    print("REGRESSION METRICS:")
    print(f"  R2 Score:                  {r2:.4f}")
    print(f"  Root Mean Squared Error:   {rmse:.3f} points")
    print(f"  Mean Absolute Error:       {mae:.3f} points")
    print("-" * 70)

    print("RISK LEVEL CLASSIFICATION PERFORMANCE:")
    target_names = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    report = classification_report(true_levels, pred_levels, labels=target_names, zero_division=0)
    print(report)

    cm = confusion_matrix(true_levels, pred_levels, labels=target_names)
    print("Confusion Matrix (Rows=True, Cols=Predicted):")
    print(pd.DataFrame(cm, index=target_names, columns=target_names))
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Road Risk Model")
    parser.add_argument(
        "--model_path",
        type=str,
        default="ml/models/weights/road_risk_model_v1.joblib",
        help="Path to serialized model weights",
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=500,
        help="Evaluation benchmark sample count",
    )
    args = parser.parse_args()

    evaluate_road_risk_model(model_path=args.model_path, n_samples=args.n_samples)
