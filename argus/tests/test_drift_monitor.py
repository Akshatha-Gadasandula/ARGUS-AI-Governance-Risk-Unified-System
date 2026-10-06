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


def test_psi_reference_bins_handle_uniform_scale_shift():
    monitor = DriftFairnessMonitor()
    rng = np.random.default_rng(42)
    reference_values = rng.uniform(0, 1, 5000)
    reference = pd.DataFrame({"x": reference_values})
    current = pd.DataFrame({"x": reference_values * 1.5})

    psi = monitor._compute_psi(reference, current)["x"]

    assert np.isfinite(psi)
    assert psi > 0.25


def test_alert_references_distinguish_indexed_eu_text_and_unverified_rbi(monkeypatch):
    monitor = DriftFairnessMonitor()
    monkeypatch.setattr(monitor, "_demographic_parity", lambda *a: .3)
    monkeypatch.setattr(monitor, "_equalized_odds", lambda *a: .3)
    monkeypatch.setattr(monitor, "_compute_psi", lambda *a: {"x":.3})
    report = monitor.evaluate("test", [0,1], [0,1], [.1,.9], "group", ["a","b"], [{"x":0}], [{"x":1}])
    references = [v.regulatory_reference for v in report.violations]
    assert any("EU AI Act Article 10(2)" in ref for ref in references)
    assert all("RBI: not assessed (no corpus indexed)" in ref for ref in references if "RBI" in ref)
    assert all("Section" not in ref for ref in references)
