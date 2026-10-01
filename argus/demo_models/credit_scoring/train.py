"""
Credit Scoring Model - Demo AI system with optional bias injection.
Use --inject-bias to flip a fraction of under-30 good labels to default labels,
simulating historically biased training data at the same underlying risk.
"""
import argparse
import json
import logging
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_synthetic_data(n_samples=5000):
    """Create synthetic credit scoring dataset."""
    np.random.seed(42)
    
    data = {
        'RevolvingUtilizationOfUnsecuredLines': np.random.uniform(0, 1, n_samples),
        'age': np.random.randint(18, 80, n_samples),
        'NumberOfTime30_59DaysPastDueNotWorse': np.random.poisson(2, n_samples),
        'DebtRatio': np.random.uniform(0, 5, n_samples),
        'MonthlyIncome': np.random.gamma(2, 2000, n_samples),
        'NumberOfOpenCreditLinesAndLoans': np.random.poisson(4, n_samples),
        'NumberOfTimes90DaysLate': np.random.poisson(1, n_samples),
        'NumberRealEstateLoansOrLines': np.random.poisson(1, n_samples),
        'NumberOfTime60_89DaysPastDueNotWorse': np.random.poisson(1, n_samples),
        'NumberOfDependents': np.random.poisson(1, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Create target: probability based on features
    prob = (
        0.5 - 0.3 * df['RevolvingUtilizationOfUnsecuredLines'] -
        0.1 * (df['NumberOfTime30_59DaysPastDueNotWorse'] > 0).astype(int) -
        0.2 * (df['DebtRatio'] > 2) +
        0.1 * np.clip(df['MonthlyIncome'] / 5000, 0, 1)
    )
    prob = np.clip(prob, 0, 1)
    df['label'] = (np.random.random(n_samples) < prob).astype(int)
    
    return df


def inject_bias(df, factor=0.35):
    """Flip a fraction of under-30 good labels to default labels."""
    age_groups = pd.cut(
        df['age'],
        bins=[0, 29, 45, 60, 120],
        labels=['under_30', '30_45', '45_60', 'over_60'],
    )
    young_good = (age_groups == 'under_30') & (df['label'] == 1)
    indices_to_flip = np.random.choice(
        df[young_good].index,
        size=int(len(df[young_good]) * factor),
        replace=False,
    )
    biased = df.copy()
    biased.loc[indices_to_flip, 'label'] = 0
    return biased


def train_model(df, fair=False):
    """Train XGBoost model."""
    features = [c for c in df.columns if c != 'label']
    X = df[features]
    y = df['label']
    
    # Split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    model = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        scale_pos_weight=scale_pos_weight,
        verbosity=0,
    )
    model.fit(X_train_scaled, y_train, verbose=False)
    
    # Evaluate
    train_acc = model.score(X_train_scaled, y_train)
    test_acc = model.score(X_test_scaled, y_test)
    
    logger.info(f"Model accuracy - Train: {train_acc:.4f}, Test: {test_acc:.4f}")
    logger.info(f"Class weight: {scale_pos_weight:.4f}")
    
    return model, scaler, X_test, y_test


def save_outputs(model, scaler, X_test, y_test, df_train, output_dir, fair=False):
    """Save model, scaler, test batch, and metadata."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model and scaler
    with open(output_dir / "model.pkl", "wb") as f:
        pickle.dump(model, f)
    
    with open(output_dir / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    
    # Generate test batch with age groups
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    age_groups = pd.cut(X_test['age'], bins=[0, 29, 45, 60, 120], labels=['under_30', '30_45', '45_60', 'over_60'])
    
    test_batch = X_test.copy()
    test_batch['y_true'] = y_test.values
    test_batch['y_pred'] = y_pred
    test_batch['y_proba'] = y_proba
    test_batch['age_group'] = age_groups
    test_batch = test_batch.reset_index(drop=True)
    
    test_batch.to_csv(output_dir / "test_batch.csv", index=False)
    
    # Save reference distribution
    df_train.to_csv(output_dir / "reference_distribution.csv", index=False)
    
    # Save metadata
    metadata = {
        "model_type": "xgboost",
        "features": X_test.columns.tolist(),
        "n_features": len(X_test.columns),
        "fair": fair,
        "test_size": len(X_test),
        "test_accuracy": float(model.score(X_test_scaled, y_test)),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Outputs saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train credit scoring model")
    parser.add_argument("--fair", action="store_true", help="Train fair model without bias")
    parser.add_argument(
        "--inject-bias",
        action="store_true",
        help="Flip under-30 good labels to default labels in training data",
    )
    parser.add_argument(
        "--bias-flip-fraction",
        type=float,
        default=0.35,
        help="Fraction of under-30 good labels to flip when bias is injected",
    )
    parser.add_argument("--drift", action="store_true", help="Generate drifted batch")
    parser.add_argument("--output", default=".", help="Output directory")
    
    args = parser.parse_args()
    
    logger.info("Generating synthetic credit data...")
    df = create_synthetic_data(5000)
    
    if args.inject_bias and not args.fair:
        logger.info("Injecting historical under-30 label bias...")
        df = inject_bias(df, factor=args.bias_flip_fraction)
    
    logger.info(f"Training model ({len(df)} samples)...")
    model, scaler, X_test, y_test = train_model(df)
    
    logger.info("Saving outputs...")
    save_outputs(model, scaler, X_test, y_test, df, args.output, fair=args.fair)
    
    if args.drift:
        # Generate drifted batch
        logger.info("Generating drifted test batch...")
        X_test_drifted = X_test.copy()
        X_test_drifted['RevolvingUtilizationOfUnsecuredLines'] *= np.random.uniform(1.3, 1.6, len(X_test))
        X_test_drifted['DebtRatio'] *= np.random.uniform(1.2, 1.5, len(X_test))
        X_test_drifted['NumberOfTime30_59DaysPastDueNotWorse'] += np.random.poisson(0.5, len(X_test))
        
        X_test_scaled_drifted = scaler.transform(X_test_drifted)
        y_pred_drifted = model.predict(X_test_scaled_drifted)
        y_proba_drifted = model.predict_proba(X_test_scaled_drifted)[:, 1]
        
        age_groups = pd.cut(X_test_drifted['age'], bins=[0, 29, 45, 60, 120], labels=['under_30', '30_45', '45_60', 'over_60'])
        
        drifted_batch = X_test_drifted.copy()
        drifted_batch['y_pred'] = y_pred_drifted
        drifted_batch['y_proba'] = y_proba_drifted
        drifted_batch['age_group'] = age_groups
        drifted_batch = drifted_batch.reset_index(drop=True)
        
        Path(args.output).mkdir(parents=True, exist_ok=True)
        drifted_batch.to_csv(Path(args.output) / "drifted_batch.csv", index=False)
        logger.info("Drifted batch saved")


if __name__ == "__main__":
    main()
