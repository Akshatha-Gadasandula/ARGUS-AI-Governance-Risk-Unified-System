import asyncio
from pathlib import Path
from argus.db.database import create_db_and_tables, AsyncSessionLocal
from argus.core.registry.models import AISystem, GovernanceAlert, FairnessSnapshot, RemediationTask, AlertSeverity, AlertType, RemediationStatus, RiskTier
from argus.core.agents.audit_generator import AuditGeneratorAgent
from argus.config import settings

async def main():
    await create_db_and_tables()
    async with AsyncSessionLocal() as session:
        system = AISystem(
            system_id='credit-scoring-demo',
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
            regulatory_citations={'EU AI Act': {'citations': [], 'obligations': ['document']}}
        )
        session.add(system)
        await session.flush()
        await session.refresh(system)
        session.add(FairnessSnapshot(system_id=system.id, demographic_parity_diff=0.08, equalized_odds_diff=0.06, psi_score=0.2, sample_size=500, metrics_detail={}, drifted_features=['income']))
        session.add(GovernanceAlert(system_id=system.id, alert_type=AlertType.FAIRNESS_VIOLATION, severity=AlertSeverity.WARNING, title='Fairness drift', description='test', payload={}, regulatory_references=[]))
        session.add(RemediationTask(system_id=system.id, title='Check fairness', description='test', status=RemediationStatus.OPEN, assigned_to='team', due_date=None))
        await session.commit()
        agent = AuditGeneratorAgent(settings)
        record = await agent.generate(session, 'credit-scoring-demo', 'demo')
        print('RECORD', record)
        print('OUTPUT DIR', settings.audit_output_dir)
        print('FILES', list(Path(settings.audit_output_dir).glob('*.pdf')))

asyncio.run(main())
