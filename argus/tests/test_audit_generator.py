from pathlib import Path
from types import SimpleNamespace

import pytest

from argus.config import settings
from argus.core.agents.audit_generator import AuditGeneratorAgent
from argus.core.agents.audit_generator import AUDIT_TEMPLATE
from argus.core.agents.audit_generator import citation_excerpt, alert_feature
from argus.core.registry import service as registry_service
from argus.core.registry.models import RiskTier


class DummySession:
    pass


@pytest.mark.parametrize("text, limit, expected", [
    (None, 100, ""),
    ("short excerpt", 100, "short excerpt"),
    ("alpha beta gamma", 8, "alpha..."),
    ("alpha beta gamma", 10, "alpha beta..."),
    ("unbrokenlongword", 5, "..."),
])
def test_citation_excerpt_ends_at_word_boundary(text, limit, expected):
    assert citation_excerpt(text, limit) == expected


def test_legacy_alert_does_not_invent_protected_groups():
    assert alert_feature(SimpleNamespace(payload={"metric": "demographic_parity"})) == "Not supplied"
    assert alert_feature(SimpleNamespace(payload={"affected_feature": "V1"})) == "V1"


def test_weasyprint_is_installed_package_not_project_shim():
    import weasyprint
    project = Path(__file__).resolve().parents[1]
    assert "shim" not in weasyprint.__version__.lower()
    assert not Path(weasyprint.__file__).resolve().is_relative_to(project)
    assert "Source HTML Hash (SHA-256, before hash insertion)" in AUDIT_TEMPLATE
    assert "citation.canonical_citation or citation.article" in AUDIT_TEMPLATE


@pytest.mark.asyncio
async def test_generate_handles_missing_timestamps_and_writes_pdf(tmp_path, monkeypatch):
    import hashlib
    import weasyprint
    from pypdf import PdfReader

    rendered = []
    original_html = weasyprint.HTML

    def capture_html(*args, **kwargs):
        rendered.append(kwargs["string"])
        return original_html(*args, **kwargs)

    monkeypatch.setattr(weasyprint, "HTML", capture_html)
    saved_hashes = []

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
                    "status": "assessed", "risk_tier": "HIGH_RISK",
                    "llm_provider": "gemini", "llm_model": "recorded-model",
                    "confidence": .91, "needs_review": True,
                    "needs_review_reasons": ["dropped_citation"],
                    "reasoning": "The model identifies individual credit decisions.",
                    "citations": [{"article": "1", "title": "Title", "excerpt": None}],
                    "obligations": ["document"],
                },
                "RBI": {"status": "not_assessed_no_corpus", "risk_tier": None},
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
                    payload={"metric": "demographic_parity", "value": .2, "threshold": .1,
                             "protected_attribute": "age", "compared_groups": ["under_30", "30_plus"]},
                    regulatory_references=["EU AI Act Article 10(2); unverified: RBI corpus not indexed (Model Risk Section 4.3)"],
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
        saved_hashes.append(kwargs["content_hash"])
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
    assert saved_hashes == [hashlib.sha256(pdf_files[0].read_bytes()).hexdigest()]
    html = rendered[0]
    for expected in ["llm_provider:</strong> gemini", "recorded-model", "0.91",
                     "needs_review:</strong> True", "dropped_citation",
                     "The model identifies individual credit decisions.",
                     "The tier was produced by an LLM and is advisory pending human review.",
                     "age: under_30 vs 30_plus", "0.2000 / 0.1000",
                     "RBI: not assessed (no corpus indexed)",
                     "source HTML hash below is not the PDF's hash",
                     "PDF's SHA-256 is recorded in the audit record", "not_assessed_no_corpus"]:
        assert expected in html
    assert "Section 4.3" not in html
    assert html.count("The tier was produced by an LLM") == 1
    reader = PdfReader(pdf_files[0])
    assert len(reader.pages) <= 6
    text = " ".join(" ".join(page.extract_text() or "" for page in reader.pages).split())
    assert "Model reasoning:" in text
    assert "Regulatory reference" in text
    assert "age: under_30 vs 30_plus" in text
