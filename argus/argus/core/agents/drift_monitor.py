"""
Drift & Fairness Monitor Agent - detects demographic bias and data drift using fairlearn and PSI.
Continuously monitors AI systems for fairness violations and distribution shifts.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from fairlearn.metrics import demographic_parity_difference, equalized_odds_difference

logger = logging.getLogger(__name__)


@dataclass
class Violation:
    """Represents a fairness or drift violation."""
    violation_type: str  # "FAIRNESS" or "DRIFT"
    metric: str  # "demographic_parity", "equalized_odds", "psi", "ks_test"
    value: float
    threshold: float
    severity: str  # "WARNING" or "CRITICAL"
    description: str
    regulatory_reference: str
    affected_feature: Optional[str] = None


@dataclass
class FairnessReport:
    """Complete fairness and drift evaluation report."""
    system_id: str
    sample_size: int
    demographic_parity_diff: float
    equalized_odds_diff: float
    calibration_diff: float
    psi_per_feature: dict[str, float]
    psi_overall: float
    drifted_features: list[str]
    violations: list[Violation]
    evaluated_at: datetime


class DriftFairnessMonitor:
    """
    Monitors AI systems for fairness violations and data drift.
    Implements demographic parity, equalized odds, calibration, and PSI metrics.
    """

    def __init__(self, settings=None):
        """
        Initialize monitor with threshold settings.
        
        Args:
            settings: Settings object with fairness thresholds
        """
        self.settings = settings
        if settings:
            self.demographic_parity_warning = settings.demographic_parity_warning
            self.demographic_parity_critical = settings.demographic_parity_critical
            self.equalized_odds_warning = settings.equalized_odds_warning
            self.equalized_odds_critical = settings.equalized_odds_critical
            self.psi_warning = settings.psi_warning
            self.psi_critical = settings.psi_critical
        else:
            # Default thresholds
            self.demographic_parity_warning = 0.05
            self.demographic_parity_critical = 0.10
            self.equalized_odds_warning = 0.05
            self.equalized_odds_critical = 0.10
            self.psi_warning = 0.20
            self.psi_critical = 0.25

    def evaluate(
        self,
        system_id: str,
        y_true: list[int],
        y_pred: list[int],
        y_proba: list[float],
        sensitive_feature_name: str,
        sensitive_feature_values: list[str],
        reference_data: list[dict],
        current_data: list[dict],
    ) -> FairnessReport:
        """
        Complete fairness and drift evaluation.
        
        Args:
            system_id: System being evaluated
            y_true: Ground truth labels (0/1)
            y_pred: Binary predictions (0/1)
            y_proba: Predicted probabilities
            sensitive_feature_name: Name of sensitive feature
            sensitive_feature_values: Values of sensitive feature per sample
            reference_data: Reference/training distribution
            current_data: Current production batch
            
        Returns:
            FairnessReport with all metrics and violations
        """
        logger.info(f"Starting fairness and drift evaluation for {system_id}")

        # Convert to numpy/pandas for processing
        y_true_array = np.array(y_true)
        y_pred_array = np.array(y_pred)
        y_proba_array = np.array(y_proba)
        sensitive_series = pd.Series(sensitive_feature_values)

        # Convert data to DataFrames
        ref_df = pd.DataFrame(reference_data)
        current_df = pd.DataFrame(current_data)

        violations = []

        # Metric 1: Demographic Parity
        dp_diff = self._demographic_parity(y_true_array, y_pred_array, sensitive_series)
        dp_violation = self._check_threshold(
            "demographic_parity",
            dp_diff,
            self.demographic_parity_warning,
            self.demographic_parity_critical,
            "EU AI Act Article 10(2); RBI Model Risk Section 4.3",
        )
        if dp_violation:
            violations.append(dp_violation)

        # Metric 2: Equalized Odds
        eq_odds_diff = self._equalized_odds(y_true_array, y_pred_array, sensitive_series)
        eq_odds_violation = self._check_threshold(
            "equalized_odds",
            eq_odds_diff,
            self.equalized_odds_warning,
            self.equalized_odds_critical,
            "EU AI Act Article 10(2)",
        )
        if eq_odds_violation:
            violations.append(eq_odds_violation)

        # Metric 3: Calibration Difference
        cal_diff = self._calibration_diff(y_true_array, y_proba_array, sensitive_series)

        # Metric 4: Population Stability Index (PSI)
        psi_per_feature = self._compute_psi(ref_df, current_df)
        drifted_features = []

        for feature, psi_value in psi_per_feature.items():
            psi_violation = self._check_threshold(
                "psi",
                psi_value,
                self.psi_warning,
                self.psi_critical,
                "RBI Model Risk Guidelines Section 5.1",
                feature=feature,
            )
            if psi_violation:
                violations.append(psi_violation)
                drifted_features.append(feature)

        psi_overall = np.mean(list(psi_per_feature.values())) if psi_per_feature else 0.0

        report = FairnessReport(
            system_id=system_id,
            sample_size=len(y_true),
            demographic_parity_diff=dp_diff,
            equalized_odds_diff=eq_odds_diff,
            calibration_diff=cal_diff,
            psi_per_feature=psi_per_feature,
            psi_overall=psi_overall,
            drifted_features=drifted_features,
            violations=violations,
            evaluated_at=datetime.utcnow(),
        )

        logger.info(
            f"Evaluation complete: {len(violations)} violations, "
            f"DP={dp_diff:.4f}, EO={eq_odds_diff:.4f}, PSI={psi_overall:.4f}"
        )

        return report

    def _demographic_parity(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sensitive_feature: pd.Series,
    ) -> float:
        """
        Calculate demographic parity difference.
        Measures if predictions are independent of sensitive attribute.
        
        Args:
            y_true: Ground truth labels
            y_pred: Binary predictions
            sensitive_feature: Sensitive feature values
            
        Returns:
            Demographic parity difference (0-1)
        """
        try:
            dp = demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive_feature)
            return float(abs(dp))
        except Exception as e:
            logger.warning(f"Error calculating demographic parity: {e}")
            return 0.0

    def _equalized_odds(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sensitive_feature: pd.Series,
    ) -> float:
        """
        Calculate equalized odds difference.
        Measures if error rates are equal across sensitive groups.
        
        Args:
            y_true: Ground truth labels
            y_pred: Binary predictions
            sensitive_feature: Sensitive feature values
            
        Returns:
            Equalized odds difference (0-1)
        """
        try:
            eo = equalized_odds_difference(y_true, y_pred, sensitive_features=sensitive_feature)
            return float(abs(eo))
        except Exception as e:
            logger.warning(f"Error calculating equalized odds: {e}")
            return 0.0

    def _calibration_diff(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        sensitive_feature: pd.Series,
    ) -> float:
        """
        Calculate calibration difference across groups.
        Measures if predicted probabilities match actual positive rates by group.
        
        Args:
            y_true: Ground truth labels
            y_proba: Predicted probabilities
            sensitive_feature: Sensitive feature values
            
        Returns:
            Max calibration difference across groups
        """
        try:
            df = pd.DataFrame({
                "y_true": y_true,
                "y_proba": y_proba,
                "group": sensitive_feature,
            })

            calibration_diffs = []
            for group in df["group"].unique():
                group_data = df[df["group"] == group]
                if len(group_data) > 0:
                    mean_proba = group_data["y_proba"].mean()
                    mean_true = group_data["y_true"].mean()
                    cal_diff = abs(mean_proba - mean_true)
                    calibration_diffs.append(cal_diff)

            return max(calibration_diffs) if calibration_diffs else 0.0

        except Exception as e:
            logger.warning(f"Error calculating calibration difference: {e}")
            return 0.0

    def _compute_psi(
        self,
        reference: pd.DataFrame,
        current: pd.DataFrame,
    ) -> dict[str, float]:
        """
        Calculate Population Stability Index (PSI) for each numeric feature.
        Detects distribution shifts between reference and current data.
        
        Args:
            reference: Reference/training data
            current: Current production data
            
        Returns:
            Dictionary mapping feature names to PSI values
        """
        psi_scores = {}

        try:
            # Get numeric columns present in both DataFrames
            numeric_cols = reference.select_dtypes(include=[np.number]).columns
            numeric_cols = [c for c in numeric_cols if c in current.columns]

            for col in numeric_cols:
                try:
                    ref_col = reference[col].dropna()
                    curr_col = current[col].dropna()

                    if len(ref_col) == 0 or len(curr_col) == 0:
                        continue

                    # Create bins from reference data
                    bins = np.percentile(ref_col, np.linspace(0, 100, 11))
                    bins = np.unique(bins)  # Remove duplicates

                    # Histogram counts
                    ref_counts, _ = np.histogram(ref_col, bins=bins)
                    curr_counts, _ = np.histogram(curr_col, bins=bins)

                    # Convert to proportions with Laplace smoothing
                    ref_pct = (ref_counts + 1e-6) / ref_counts.sum()
                    curr_pct = (curr_counts + 1e-6) / curr_counts.sum()

                    # Calculate PSI
                    psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
                    psi_scores[col] = float(psi)

                except Exception as e:
                    logger.warning(f"Error calculating PSI for {col}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error computing PSI: {e}")

        return psi_scores

    def _check_threshold(
        self,
        metric: str,
        value: float,
        warning_threshold: float,
        critical_threshold: float,
        regulatory_reference: str,
        feature: Optional[str] = None,
    ) -> Optional[Violation]:
        """
        Check if metric exceeds thresholds and create violation if needed.
        
        Args:
            metric: Metric name
            value: Measured value
            warning_threshold: Warning level
            critical_threshold: Critical level
            regulatory_reference: Regulatory citation
            feature: Affected feature name if applicable
            
        Returns:
            Violation if value >= warning_threshold, None otherwise
        """
        if value < warning_threshold:
            return None

        if value >= critical_threshold:
            severity = "CRITICAL"
            description = f"{metric} value of {value:.4f} exceeds critical threshold of {critical_threshold}"
        else:
            severity = "WARNING"
            description = f"{metric} value of {value:.4f} exceeds warning threshold of {warning_threshold}"

        violation_type = "FAIRNESS" if metric in ["demographic_parity", "equalized_odds"] else "DRIFT"

        return Violation(
            violation_type=violation_type,
            metric=metric,
            value=value,
            threshold=critical_threshold if severity == "CRITICAL" else warning_threshold,
            severity=severity,
            description=description,
            regulatory_reference=regulatory_reference,
            affected_feature=feature,
        )
