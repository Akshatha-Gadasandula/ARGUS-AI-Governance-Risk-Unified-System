import asyncio
from pathlib import Path
from types import SimpleNamespace

from argus.core.agents.audit_generator import AuditGeneratorAgent
from argus.config import settings
from argus.core.registry import service as registry_service
from argus.core.registry.models import RiskTier


class DummySession:
    pass


async def fake_get_system_for_audit(session, system_id):
    system = SimpleNamespace(
        id='sys-123',
        system_id=system_id,
        name='Credit Scoring Demo',
        version='1.0',
        purpose='Demo purpose',
        owner_team='team',
        owner_email='owner@example.com',
        data_sources=['transactions'],
        affected_demographics=['age'],
        jurisdictions=['EU', 'IN'],
        risk_tier=RiskTier.HIGH_RISK,
        monitoring_enabled=True,
        risk_classification_reasoning='Demo reasoning',
        regulatory_citations={'EU AI Act': {'citations': [{'article': '1', 'title': 'Title', 'excerpt': 'Excerpt'}], 'obligations': ['document']}},
        registered_at=None,
        owner='team',
        model_type='classifier',
        output_type='score',
    )
    return {
        'system': system,
        'fairness_snapshots': [SimpleNamespace(evaluated_at=None, sample_size=500, demographic_parity_diff=0.08, equalized_odds_diff=0.06, psi_score=0.2)],
        'alerts': [SimpleNamespace(created_at=None, severity='WARNING', alert_type='FAIRNESS_VIOLATION', title='Fairness drift', resolved=False)],
        'remediation_tasks': [SimpleNamespace(title='Check fairness', assigned_to='team', due_date=None, status=SimpleNamespace(value='OPEN'))],
    }


async def main():
    registry_service.RegistryService.get_system_for_audit = staticmethod(fake_get_system_for_audit)

    async def fake_save_audit_record(*args, **kwargs):
        return SimpleNamespace(id='rec-1')

    registry_service.RegistryService.save_audit_record = staticmethod(fake_save_audit_record)
    agent = AuditGeneratorAgent(settings)
    try:
        record = await agent.generate(DummySession(), 'credit-scoring-demo', 'demo')
        print('RECORD', record)
        print('PDFS', list(Path(settings.audit_output_dir).glob('*.pdf')))
    except Exception:
        import traceback
        traceback.print_exc()


asyncio.run(main())
