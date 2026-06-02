"""
Fraud Detection Model - Demo AI system for transaction monitoring.
Trains a Random Forest model to detect fraudulent transactions.
"""
import argparse
import json
import logging
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_synthetic_fraud_data(n_samples=10000):
    """Create synthetic credit card fraud dataset."""
    np.random.seed(42)
    
    data = {
        'V1': np.random.normal(0, 1.5, n_samples),
        'V2': np.random.normal(0, 1.5, n_samples),
        'V3': np.random.normal(0, 1.5, n_samples),
        'V4': np.random.normal(0, 1.5, n_samples),
        'V5': np.random.normal(0, 1.5, n_samples),
        'V6': np.random.normal(0, 1.5, n_samples),
        'V7': np.random.normal(0, 1.5, n_samples),
        'V8': np.random.normal(0, 1.5, n_samples),
        'V9': np.random.normal(0, 1.5, n_samples),
        'V10': np.random.normal(0, 1.5, n_samples),
        'V11': np.random.normal(0, 1.5, n_samples),
        'V12': np.random.normal(0, 1.5, n_samples),
        'V13': np.random.normal(0, 1.5, n_samples),
        'V14': np.random.normal(0, 1.5, n_samples),
        'V15': np.random.normal(0, 1.5, n_samples),
        'V16': np.random.normal(0, 1.5, n_samples),
        'V17': np.random.normal(0, 1.5, n_samples),
        'V18': np.random.normal(0, 1.5, n_samples),
        'V19': np.random.normal(0, 1.5, n_samples),
        'V20': np.random.normal(0, 1.5, n_samples),
        'Amount': np.random.exponential(50, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Create target: 3% fraud rate
    fraud_mask = np.random.random(n_samples) < 0.03
    df['Class'] = fraud_mask.astype(int)
    
    # Make fraud distinguishable via anomalous V1, V14 values
    fraud_indices = df[fraud_mask].index
    df.loc[fraud_indices, 'V1'] += np.random.uniform(3, 5, len(fraud_indices))
    df.loc[fraud_indices, 'V14'] -= np.random.uniform(2, 4, len(fraud_indices))
    df.loc[fraud_indices, 'Amount'] *= np.random.uniform(1.5, 3, len(fraud_indices))
    
    return df


def train_model(df):
    """Train Random Forest model."""
    features = [c for c in df.columns if c != 'Class']
    X = df[features]
    y = df['Class']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        random_state=42,
        class_weight={0: 1, 1: scale_pos_weight},
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    train_acc = model.score(X_train_scaled, y_train)
    test_acc = model.score(X_test_scaled, y_test)
    
    logger.info(f"Model accuracy - Train: {train_acc:.4f}, Test: {test_acc:.4f}")
    logger.info(f"Fraud rate: {y_train.sum() / len(y_train):.4f}")
    
    return model, scaler, X_test, y_test


def save_outputs(model, scaler, X_test, y_test, df_train, output_dir):
    """Save model, scaler, test batch, and metadata."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model and scaler
    with open(output_dir / "model.pkl", "wb") as f:
        pickle.dump(model, f)
    
    with open(output_dir / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    
    # Generate test batch
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    test_batch = X_test.copy()
    test_batch['y_true'] = y_test.values
    test_batch['y_pred'] = y_pred
    test_batch['y_proba'] = y_proba
    test_batch = test_batch.reset_index(drop=True)
    
    test_batch.to_csv(output_dir / "test_batch.csv", index=False)
    
    # Save reference distribution
    df_train.to_csv(output_dir / "reference_distribution.csv", index=False)
    
    # Save feature importances
    feature_importance = pd.DataFrame({
        'feature': X_test.columns,
        'importance': model.feature_importances_,
    }).sort_values('importance', ascending=False)
    
    feature_importance.to_csv(output_dir / "feature_importance.csv", index=False)
    
    # Save metadata
    metadata = {
        "model_type": "random_forest",
        "features": X_test.columns.tolist(),
        "n_features": len(X_test.columns),
        "test_size": len(X_test),
        "test_accuracy": float(model.score(X_test_scaled, y_test)),
        "top_features": feature_importance['feature'].head(5).tolist(),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Outputs saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train fraud detection model")
    parser.add_argument("--drift", action="store_true", help="Generate drifted batch")
    parser.add_argument("--output", default=".", help="Output directory")
    
    args = parser.parse_args()
    
    logger.info("Generating synthetic fraud data...")
    df = create_synthetic_fraud_data(10000)
    
    logger.info(f"Training model ({len(df)} samples, {df['Class'].sum()} frauds)...")
    model, scaler, X_test, y_test = train_model(df)
    
    logger.info("Saving outputs...")
    save_outputs(model, scaler, X_test, y_test, df, args.output)
    
    if args.drift:
        # Generate drifted batch (shift top features)
        logger.info("Generating drifted test batch...")
        X_test_drifted = X_test.copy()
        
        # Drift key predictive features
        X_test_drifted['V1'] *= np.random.uniform(1.3, 1.6, len(X_test))
        X_test_drifted['V3'] *= np.random.uniform(1.2, 1.5, len(X_test))
        X_test_drifted['V14'] *= np.random.uniform(1.3, 1.6, len(X_test))
        
        X_test_scaled_drifted = scaler.transform(X_test_drifted)
        y_pred_drifted = model.predict(X_test_scaled_drifted)
        y_proba_drifted = model.predict_proba(X_test_scaled_drifted)[:, 1]
        
        drifted_batch = X_test_drifted.copy()
        drifted_batch['y_pred'] = y_pred_drifted
        drifted_batch['y_proba'] = y_proba_drifted
        drifted_batch = drifted_batch.reset_index(drop=True)
        
        Path(args.output).mkdir(parents=True, exist_ok=True)
        drifted_batch.to_csv(Path(args.output) / "drifted_batch.csv", index=False)
        logger.info("Drifted batch saved")


if __name__ == "__main__":
    main()
