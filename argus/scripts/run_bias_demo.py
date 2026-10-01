import argparse
import pickle
from pathlib import Path

import httpx
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Run the credit scoring bias demo")
    parser.add_argument("--system-id", required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--artifacts",
        default="demo_models/credit_scoring/artifacts",
    )
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    with open(artifacts / "model.pkl", "rb") as model_file:
        model = pickle.load(model_file)
    with open(artifacts / "scaler.pkl", "rb") as scaler_file:
        scaler = pickle.load(scaler_file)

    test_batch = pd.read_csv(artifacts / "test_batch.csv")
    reference = pd.read_csv(artifacts / "reference_distribution.csv")
    feature_columns = [column for column in test_batch.columns if column not in {
        "y_true", "y_pred", "y_proba", "age_group"
    }]

    predictions = model.predict(scaler.transform(test_batch[feature_columns]))
    probabilities = model.predict_proba(scaler.transform(test_batch[feature_columns]))[:, 1]
    age_groups = test_batch["age"].apply(lambda age: "under_30" if age < 30 else "30_plus")
    approval_rates = pd.Series(predictions).groupby(age_groups.to_numpy()).mean()

    reference_data = reference[feature_columns].to_dict(orient="records")
    current_data = test_batch[feature_columns].to_dict(orient="records")
    payload = {
        "system_id": args.system_id,
        "y_true": test_batch["y_true"].astype(int).tolist(),
        "y_pred": predictions.astype(int).tolist(),
        "y_proba": probabilities.astype(float).tolist(),
        "sensitive_feature_name": "age_group",
        "sensitive_feature_values": age_groups.tolist(),
        "reference_data": reference_data,
        "current_data": current_data,
    }

    response = httpx.post(
        f"{args.api_url}/api/v1/monitoring/evaluate",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    snapshot = result["snapshot"]

    for group in ["under_30", "30_plus"]:
        print(f"Approval rate {group}: {approval_rates.get(group, 0.0):.6f}")
    print(f"Demographic parity difference: {snapshot['demographic_parity_diff']:.6f}")
    print(f"Equalized odds difference: {snapshot['equalized_odds_diff']:.6f}")
    print(f"Alerts created: {result['alerts_created']}")
    print("Violations:", [violation["metric"] for violation in result["violations"]])


if __name__ == "__main__":
    main()