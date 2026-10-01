import numpy as np
import pandas as pd

from argus.core.agents.drift_monitor import DriftFairnessMonitor


def test_psi_identical_distribution_is_near_zero_and_shift_is_finite():
    monitor = DriftFairnessMonitor()
    reference = pd.DataFrame({"x": np.random.default_rng(42).normal(100, 10, 1000)})

    identical = monitor._compute_psi(reference, reference.copy())["x"]
    shifted = monitor._compute_psi(reference, pd.DataFrame({"x": reference["x"] * 1.5}))["x"]

    assert np.isclose(identical, 0.0, atol=1e-10)
    assert np.isfinite(shifted)
    assert shifted > 0.2


def test_demographic_parity_difference_is_021_for_known_rates():
    monitor = DriftFairnessMonitor()
    y_true = np.ones(200, dtype=int)
    y_pred = np.array([1] * 76 + [0] * 24 + [1] * 55 + [0] * 45)
    sensitive_feature = pd.Series(["A"] * 100 + ["B"] * 100)

    difference = monitor._demographic_parity(y_true, y_pred, sensitive_feature)

    assert np.isclose(difference, 0.21)