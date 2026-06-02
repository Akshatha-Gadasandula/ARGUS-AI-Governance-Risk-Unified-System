"""
Document Classification Model - Demo AI system for compliance and regulatory document tagging.
Trains a logistic regression classifier using synthetic financial text data.
"""
import argparse
import json
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_synthetic_documents(n_samples=3000):
    """Create synthetic compliance document corpus for binary classification."""
    np.random.seed(42)
    fraud_templates = [
        "Transaction appears suspicious with multiple rapid transfers from high-risk countries.",
        "Unusual login pattern and account takeover indicators detected in payment flow.",
        "Real-time fraud scoring model flagged this request due to anomalous transaction velocity.",
        "Potential money laundering behavior identified in customer payout history.",
        "Chargeback probability is elevated based on merchant and transaction profile.",
    ]
    non_fraud_templates = [
        "Loan application documentation meets underwriting criteria with customer income disclosed.",
        "KYC compliance checklist and identity verification across multi-branch records.",
        "Regulatory disclosure report for credit portfolio risk and capital adequacy.",
        "Customer service workflow for dispute resolution and billing inquiry tracking.",
        "Operational risk assessment for branch process automation and vendor review.",
    ]
    data = []

    for _ in range(n_samples):
        if np.random.random() < 0.28:
            text = np.random.choice(fraud_templates)
            label = 1
        else:
            text = np.random.choice(non_fraud_templates)
            label = 0

        length_variation = np.random.randint(1, 4)
        extra_context = " ".join(np.random.choice(
            [
                "customer behavior",
                "transaction history",
                "account monitoring",
                "regulatory review",
                "financial controls",
                "AML procedures",
                "risk management",
                "audit trail",
            ],
            size=length_variation,
        ))
        data.append({"text": f"{text} {extra_context}", "label": label})

    return pd.DataFrame(data)


def inject_drift(df, drift_strength=0.4):
    """Inject keyword drift into text data for production simulation."""
    df = df.copy()
    drifted_texts = []
    for text in df["text"]:
        if np.random.random() < drift_strength:
            drifted_texts.append(text.replace("transaction", "payment").replace("fraud", "anomaly"))
        else:
            drifted_texts.append(text)
    df["text"] = drifted_texts
    return df


def train_model(df):
    """Train a text classification pipeline."""
    X = df["text"].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=2000, ngram_range=(1, 2))),
            ("scaler", StandardScaler(with_mean=False)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ]
    )
    pipeline.fit(X_train, y_train)

    train_score = pipeline.score(X_train, y_train)
    test_score = pipeline.score(X_test, y_test)

    logger.info(f"Model trained: train_acc={train_score:.4f}, test_acc={test_score:.4f}")
    return pipeline, X_test, y_test, X_train


def save_outputs(model, X_test, y_test, df_reference, output_dir):
    """Persist model artifacts and evaluation artifacts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "model.pkl", "wb") as f:
        pickle.dump(model, f)

    with open(output_dir / "test_batch.csv", "w", encoding="utf-8") as f:
        pd.DataFrame({"text": X_test, "label": y_test}).to_csv(f, index=False)

    df_reference.to_csv(output_dir / "reference_distribution.csv", index=False)

    metadata = {
        "model_type": "logistic_regression",
        "feature_type": "tfidf_text",
        "n_samples": len(df_reference),
        "test_samples": len(X_test),
        "test_accuracy": float(model.score(X_test, y_test)),
        "fraud_rate": float(df_reference["label"].mean()),
    }

    with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved artifacts to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train document classification model")
    parser.add_argument("--output", default=".", help="Output directory for artifacts")
    parser.add_argument("--drift", action="store_true", help="Generate a drifted batch")
    args = parser.parse_args()

    logger.info("Generating synthetic document classification corpus...")
    df = create_synthetic_documents(3000)

    logger.info("Training document classifier...")
    model, X_test, y_test, df_reference = train_model(df)
    save_outputs(model, X_test, y_test, df_reference, args.output)

    if args.drift:
        logger.info("Generating drifted batch...")
        drift_df = inject_drift(pd.DataFrame({"text": X_test, "label": y_test}))
        drift_df.to_csv(Path(args.output) / "drifted_batch.csv", index=False)
        logger.info("Saved drifted batch")


if __name__ == "__main__":
    main()
