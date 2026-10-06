import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from argus.core.schemas import AlertResponse, EvaluationRequest


@pytest.mark.parametrize("reference", [
    "unverified: RBI corpus not indexed (Model Risk Guidelines Section 5.1)",
    "EU AI Act Article 10(2); unverified: RBI corpus not indexed (Model Risk Section 4.3)",
])
def test_alert_response_sanitizes_legacy_references_without_mutating_storage(reference):
    stored = SimpleNamespace(
        id=uuid4(), system_id=uuid4(), alert_type="INPUT_DRIFT", severity="CRITICAL",
        title="PSI violation", description="Threshold exceeded", payload={"metric": "psi"},
        regulatory_references=[reference], resolved=False, resolved_at=None,
        created_at=datetime.utcnow(),
    )
    response = AlertResponse.model_validate(stored)
    expected = "RBI: not assessed (no corpus indexed)"
    if reference.startswith("EU"):
        expected = "EU AI Act Article 10(2); " + expected
    assert response.regulatory_references == [expected]
    assert stored.regulatory_references == [reference]
    assert stored.payload == {"metric": "psi"}


def test_evaluate_persists_attribute_and_compared_groups_only_for_fairness(monkeypatch):
    from argus.api.routers import monitoring
    from argus.core.agents.drift_monitor import DriftFairnessMonitor

    monitor = DriftFairnessMonitor()
    monkeypatch.setattr(monitor, "_demographic_parity", lambda *a: .3)
    monkeypatch.setattr(monitor, "_equalized_odds", lambda *a: .3)
    monkeypatch.setattr(monitor, "_compute_psi", lambda *a: {"V1": .3})
    monkeypatch.setattr(monitoring, "drift_monitor", monitor)
    system_uuid = uuid4()
    service = monitoring.RegistryService
    monkeypatch.setattr(service, "get_system_uuid", AsyncMock(return_value=system_uuid))
    monkeypatch.setattr(service, "save_fairness_snapshot", AsyncMock(return_value=SimpleNamespace(
        id=uuid4(), system_id=system_uuid, demographic_parity_diff=.3,
        equalized_odds_diff=.3, psi_score=.3, drifted_features=["V1"],
        sample_size=4, evaluated_at=datetime.utcnow(),
    )))
    create_alert = AsyncMock()
    monkeypatch.setattr(service, "create_alert", create_alert)
    request = EvaluationRequest(
        system_id="test-system", y_true=[0, 1, 0, 1], y_pred=[0, 1, 0, 1],
        y_proba=[.1, .9, .2, .8], sensitive_feature_name="age",
        sensitive_feature_values=["under_30", "30_plus", "under_30", "30_plus"],
        reference_data=[{"V1": 0}], current_data=[{"V1": 1}],
    )
    response = asyncio.run(monitoring.evaluate_system(request, session=object(), current_user={}))
    assert response.alerts_created == 3
    for call in create_alert.await_args_list:
        alert = call.args[2]
        payload = alert["payload"]
        if alert["alert_type"] == "FAIRNESS_VIOLATION":
            assert payload["protected_attribute"] == "age"
            assert payload["compared_groups"] == ["under_30", "30_plus"]
            assert payload["affected_feature"] == "age"
        else:
            assert payload["affected_feature"] == "V1"
            assert "protected_attribute" not in payload
            assert "compared_groups" not in payload
        assert all("Section" not in ref for ref in alert["regulatory_references"])
