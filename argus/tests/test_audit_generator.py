from pathlib import Path
from types import SimpleNamespace

import pytest

from argus.config import settings
from argus.core.agents.audit_generator import AuditGeneratorAgent
from argus.core.registry import service as registry_service
from argus.core.registry.models import RiskTier


class DummySession:
    pass


@pytest.mark.asyncio
async def test_generate_handles_missing_timestamps_and_writes_pdf(tmp_path, monkeypatch):
    async def fake_get_system_for_audit(session, system_id):
        system = SimpleNamespace(
            id="sys-123",
            system_id=system_id,
            name="Credit Scoring Demo",
            version="1.0",
            purpose="Demo purpose",
            owner_team="team",
            owner_email=None,
            data_sources=["transactions"],
            affected_demographics=["age"],
            jurisdictions=["EU", "IN"],
            risk_tier=RiskTier.HIGH_RISK,
            monitoring_enabled=True,
            risk_classification_reasoning="Demo reasoning",
            regulatory_citations={
                "EU AI Act": {
                    "citations": [{"article": "1", "title": "Title", "excerpt": None}],
                    "obligations": ["document"],
                }
            },
            registered_at=None,
        )
        return {
            "system": system,
            "fairness_snapshots": [
                SimpleNamespace(
                    evaluated_at=None,
                    sample_size=500,
                    demographic_parity_diff=0.08,
                    equalized_odds_diff=0.06,
                    psi_score=0.2,
                )
            ],
            "alerts": [
                SimpleNamespace(
                    created_at=None,
                    severity="WARNING",
                    alert_type="FAIRNESS_VIOLATION",
                    title="Fairness drift",
                    resolved=False,
                )
            ],
            "remediation_tasks": [
                SimpleNamespace(
                    title="Check fairness",
                    assigned_to=None,
                    due_date=None,
                    status=SimpleNamespace(value="OPEN"),
                )
            ],
        }

    async def fake_save_audit_record(*args, **kwargs):
        return SimpleNamespace(id="rec-1")

    monkeypatch.setattr(
        registry_service.RegistryService,
        "get_system_for_audit",
        staticmethod(fake_get_system_for_audit),
    )
    monkeypatch.setattr(
        registry_service.RegistryService,
        "save_audit_record",
        staticmethod(fake_save_audit_record),
    )

    agent = AuditGeneratorAgent(settings)
    agent.output_dir = tmp_path

    record = await agent.generate(DummySession(), "credit-scoring-demo", "demo")

    assert record is not None
    pdf_files = list(tmp_path.glob("*.pdf"))
    assert len(pdf_files) == 1
    assert pdf_files[0].stat().st_size > 0
