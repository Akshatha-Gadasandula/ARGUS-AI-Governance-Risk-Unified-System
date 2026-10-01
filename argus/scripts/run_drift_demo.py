import argparse
import pickle
from pathlib import Path
import sys

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argus.core.agents.drift_monitor import DriftFairnessMonitor


def main():
    parser = argparse.ArgumentParser(description="Run the fraud input-drift demo")
    parser.add_argument("--system-id", required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--artifacts",
        default="demo_models/fraud_detection/artifacts",
    )
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    with open(artifacts / "model.pkl", "rb") as model_file:
        model = pickle.load(model_file)
    with open(artifacts / "scaler.pkl", "rb") as scaler_file:
        scaler = pickle.load(scaler_file)

    reference = pd.read_csv(artifacts / "reference_distribution.csv")
    test_batch = pd.read_csv(artifacts / "test_batch.csv")
    drifted_batch = pd.read_csv(artifacts / "drifted_batch.csv")
    feature_columns = [column for column in test_batch.columns if column not in {
        "y_true", "y_pred", "y_proba"
    }]

    predictions = model.predict(scaler.transform(drifted_batch[feature_columns]))
    probabilities = model.predict_proba(scaler.transform(drifted_batch[feature_columns]))[:, 1]
    monitor = DriftFairnessMonitor()
    report = monitor.evaluate(
        system_id=args.system_id,
        y_true=test_batch["y_true"].astype(int).tolist(),
        y_pred=predictions.astype(int).tolist(),
        y_proba=probabilities.astype(float).tolist(),
        sensitive_feature_name="population",
        sensitive_feature_values=["all"] * len(test_batch),
        reference_data=reference[feature_columns].to_dict(orient="records"),
        current_data=drifted_batch[feature_columns].to_dict(orient="records"),
    )

    payload = {
        "system_id": args.system_id,
        "y_true": test_batch["y_true"].astype(int).tolist(),
        "y_pred": predictions.astype(int).tolist(),
        "y_proba": probabilities.astype(float).tolist(),
        "sensitive_feature_name": "population",
        "sensitive_feature_values": ["all"] * len(test_batch),
        "reference_data": reference[feature_columns].to_dict(orient="records"),
        "current_data": drifted_batch[feature_columns].to_dict(orient="records"),
    }
    response = httpx.post(
        f"{args.api_url}/api/v1/monitoring/evaluate",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()

    for feature, value in report.psi_per_feature.items():
        print(f"PSI {feature}: {value:.6f}")
    print(f"Overall PSI: {report.psi_overall:.6f}")
    print(f"Alerts created: {result['alerts_created']}")
    print("Violations:", [violation["metric"] for violation in result["violations"]])


if __name__ == "__main__":
    main()