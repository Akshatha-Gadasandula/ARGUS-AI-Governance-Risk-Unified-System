import httpx
import json
import time

# Step 1: Register Credit Scoring System
system_1 = {
    "name": "Credit Scoring Model v2",
    "purpose": "Predicts probability of loan default using 24-month applicant transaction history and credit bureau data to approve or reject retail loan applications. Outputs a binary decision affecting whether a customer receives credit.",
    "owner_team": "retail-credit-engineering",
    "owner_email": "credit-team@bank.com",
    "data_sources": ["transaction_history", "credit_bureau", "income_data"],
    "affected_demographics": ["age", "income_band", "geography"],
    "jurisdictions": ["EU", "IN"]
}

client = httpx.Client(timeout=30)
response = client.post("http://127.0.0.1:8000/api/v1/registry/systems", json=system_1)
print("STEP 1 - Register Credit Scoring System")
print(f"Status: {response.status_code}")
result_1 = response.json()
print(json.dumps(result_1, indent=2))
system_1_id = result_1.get("system_id")
print(f"\n>>> CREDIT_SCORING_SYSTEM_ID = {system_1_id}\n")

# Step 2a: Register Fraud Detection System
system_2 = {
    "name": "Fraud Detection Engine",
    "purpose": "Real-time classification of financial transactions as fraudulent or legitimate using behavioral patterns and device fingerprinting. Flags suspicious transactions and can automatically block payments.",
    "owner_team": "financial-crime-ai",
    "owner_email": "fraud-team@bank.com",
    "data_sources": ["transaction_stream", "device_data", "merchant_data"],
    "affected_demographics": ["geography", "transaction_type"],
    "jurisdictions": ["EU", "IN"]
}

response = client.post("http://127.0.0.1:8000/api/v1/registry/systems", json=system_2)
print("STEP 2a - Register Fraud Detection System")
print(f"Status: {response.status_code}")
result_2 = response.json()
print(json.dumps(result_2, indent=2))
system_2_id = result_2.get("system_id")
print(f"\n>>> FRAUD_DETECTION_SYSTEM_ID = {system_2_id}\n")

# Step 2b: Register Customer Service Chatbot
system_3 = {
    "name": "Customer Support Chatbot",
    "purpose": "Conversational AI assistant that answers customer queries about account balances, recent transactions, and general banking services. Does not make any financial decisions.",
    "owner_team": "digital-channels",
    "owner_email": "support-team@bank.com",
    "data_sources": ["faq_knowledge_base", "product_documentation"],
    "affected_demographics": [],
    "jurisdictions": ["EU"]
}

response = client.post("http://127.0.0.1:8000/api/v1/registry/systems", json=system_3)
print("STEP 2b - Register Customer Support Chatbot")
print(f"Status: {response.status_code}")
result_3 = response.json()
print(json.dumps(result_3, indent=2))
system_3_id = result_3.get("system_id")
print(f"\n>>> CHATBOT_SYSTEM_ID = {system_3_id}\n")

# Step 3: Verify all three systems are registered
print("\n" + "="*80)
print("STEP 3 - Verify All Systems Registered with Risk Tiers")
print("="*80)
response = client.get("http://127.0.0.1:8000/api/v1/registry/systems")
print(f"Status: {response.status_code}")
all_systems = response.json()
print(json.dumps(all_systems, indent=2))

# Save IDs for use in fairness evaluation
with open("system_ids.json", "w") as f:
    json.dump({
        "credit_scoring": system_1_id,
        "fraud_detection": system_2_id,
        "chatbot": system_3_id
    }, f, indent=2)

print("\n✓ System IDs saved to system_ids.json")
client.close()
