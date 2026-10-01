import httpx
import random
import time

BASE = "http://127.0.0.1:8000"

# Register 3 systems
systems = [
    {
        "name": "Credit Scoring Model v2",
        "purpose": "Predicts probability of loan default using 24-month applicant transaction history and credit bureau data to approve or reject retail loan applications. Outputs a binary decision affecting whether a customer receives credit.",
        "owner_team": "retail-credit-engineering",
        "data_sources": ["transaction_history", "credit_bureau", "income_data"],
        "affected_demographics": ["age", "income_band", "geography"],
        "jurisdictions": ["EU", "IN"]
    },
    {
        "name": "Fraud Detection Engine",
        "purpose": "Real-time classification of financial transactions as fraudulent or legitimate using behavioral patterns and device fingerprinting. Flags suspicious transactions and can automatically block customer payments.",
        "owner_team": "financial-crime-ai",
        "data_sources": ["transaction_stream", "device_data", "merchant_data"],
        "affected_demographics": ["geography", "transaction_type"],
        "jurisdictions": ["EU", "IN"]
    },
    {
        "name": "Customer Support Chatbot",
        "purpose": "Conversational AI assistant that answers customer queries about account balances and general banking services. Does not make any financial decisions.",
        "owner_team": "digital-channels",
        "data_sources": ["faq_knowledge_base"],
        "affected_demographics": [],
        "jurisdictions": ["EU"]
    }
]

ids = []

for s in systems:
    r = httpx.post(
        f"{BASE}/api/v1/registry/systems",
        json=s,
        timeout=30
    )

    data = r.json()

    sid = data.get("system_id", "unknown")
    risk = data.get("risk_tier", "unknown")

    ids.append(sid)

    print(f"Registered: {s['name']} -> {sid} [{risk}]")

    time.sleep(1)

credit_id = ids[0]

random.seed(42)

n = 600

age_groups = (
    ["under_30"] * 150
    + ["30_45"] * 150
    + ["45_60"] * 150
    + ["over_60"] * 150
)

y_true = []
y_pred = []
y_proba = []

for ag in age_groups:
    t = random.choice([0, 1])

    y_true.append(t)

    threshold = 0.45 if ag == "under_30" else 0.22

    p = 0 if random.random() < threshold else 1

    y_pred.append(p)

    y_proba.append(
        min(
            1.0,
            max(
                0.0,
                p * 0.8 + random.gauss(0.1, 0.05)
            )
        )
    )

ref = [
    {
        "RevolvingUtil": random.gauss(0.5, 0.15),
        "DebtRatio": random.gauss(0.3, 0.1),
        "MonthlyIncome": random.gauss(5000, 1000)
    }
    for _ in range(300)
]

curr = [
    {
        "RevolvingUtil": random.gauss(0.72, 0.15),
        "DebtRatio": random.gauss(0.48, 0.1),
        "MonthlyIncome": random.gauss(4200, 1000)
    }
    for _ in range(300)
]

eval_payload = {
    "system_id": credit_id,
    "y_true": y_true,
    "y_pred": y_pred,
    "y_proba": y_proba,
    "sensitive_feature_name": "age_group",
    "sensitive_feature_values": age_groups,
    "reference_data": ref,
    "current_data": curr
}

r = httpx.post(
    f"{BASE}/api/v1/monitoring/evaluate",
    json=eval_payload,
    timeout=60
)

result = r.json()

print(
    f"Fairness eval: {result.get('alerts_created', 0)} alerts created"
)

print(
    "Violations:",
    [v.get("metric") for v in result.get("violations", [])]
)

print("System IDs:", ids)

print(
    "Done. Use credit system_id for audit:",
    credit_id
)