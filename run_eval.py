import httpx
import json
import random

SYSTEM_ID = "credit_scoring_model-7dcc97"

random.seed(42)
n = 600
age_groups = ["under_30"]*150 + ["30_45"]*150 + ["45_60"]*150 + ["over_60"]*150

# Biased: under_30 gets approved only 55% of time, others ~78%
y_true, y_pred, y_proba, groups = [], [], [], []
for ag in age_groups:
    label = random.choice([0, 1])
    y_true.append(label)
    threshold = 0.45 if ag == "under_30" else 0.22
    pred = 0 if random.random() < threshold else 1
    y_pred.append(pred)
    y_proba.append(random.random())
    groups.append(ag)

# Reference data (balanced distribution, good performance)
reference_data = [
    {
        "age_group": "under_30",
        "RevolvingUtil": random.gauss(30, 10),
        "DebtRatio": random.gauss(0.20, 0.07),
        "Income": random.gauss(45000, 15000)
    }
    for _ in range(150)
] + [
    {
        "age_group": "30_45",
        "RevolvingUtil": random.gauss(32, 10),
        "DebtRatio": random.gauss(0.22, 0.07),
        "Income": random.gauss(55000, 18000)
    }
    for _ in range(150)
] + [
    {
        "age_group": "45_60",
        "RevolvingUtil": random.gauss(35, 12),
        "DebtRatio": random.gauss(0.25, 0.08),
        "Income": random.gauss(65000, 20000)
    }
    for _ in range(150)
] + [
    {
        "age_group": "over_60",
        "RevolvingUtil": random.gauss(38, 14),
        "DebtRatio": random.gauss(0.28, 0.09),
        "Income": random.gauss(55000, 22000)
    }
    for _ in range(150)
]

# Current data (with drift and bias)
current_data = [
    {
        "age_group": ag,
        "RevolvingUtil": random.gauss(38, 16),
        "DebtRatio": random.gauss(0.28, 0.09),
        "Income": random.gauss(50000, 20000)
    }
    for ag in groups
]

payload = {
    "system_id": SYSTEM_ID,
    "y_true": y_true,
    "y_pred": y_pred,
    "y_proba": y_proba,
    "sensitive_feature_name": "age_group",
    "sensitive_feature_values": groups,
    "reference_data": reference_data,
    "current_data": current_data,
}

client = httpx.Client(timeout=30)
response = client.post("http://127.0.0.1:8000/api/v1/monitoring/evaluate", json=payload)
print("STEP 4 - Run Fairness Evaluation with Deliberate Bias")
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
client.close()
