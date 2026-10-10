import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from argus.api.routers import qa
from argus.core.registry.models import Base, AISystem, GovernanceAlert, RiskTier, AlertSeverity, AlertType
from argus.core.schemas import QARequest

async def seeded_session():
    sync_engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(sync_engine)
    sync_session=Session(sync_engine,expire_on_commit=False)
    class Adapter:
        def add(self,row): sync_session.add(row)
        async def execute(self,statement): return sync_session.execute(statement)
        async def flush(self): sync_session.flush()
        async def commit(self): sync_session.commit()
        async def close(self): sync_session.close()
    class Engine:
        async def dispose(self): sync_engine.dispose()
    engine,session=Engine(),Adapter()
    systems=[]
    for sid,name,tier,team in [('credit','Credit Scoring Model',RiskTier.HIGH_RISK,'Credit Team'),('fraud','Fraud Detection Engine',RiskTier.MINIMAL_RISK,'Fraud Team'),('spam','Email Spam Filter',RiskTier.MINIMAL_RISK,'Mail Team')]:
        s=AISystem(id=uuid4(),system_id=sid,name=name,version='1',purpose='A meaningful registered purpose',owner_team=team,
            risk_tier=tier,jurisdictions=['EU'],risk_classification_reasoning='Stored summary',
            regulatory_citations={'EU_AI_ACT':{'status':'assessed','risk_tier':tier.value,'llm_provider':'gemini',
                'llm_model':'original-model','reasoning':'Stored regulatory rationale','citations':[],
                'needs_review':True,'needs_review_reasons':['original_review']}})
        session.add(s);systems.append(s)
    await session.flush()
    for s,severity,resolved in [(systems[0],AlertSeverity.CRITICAL,False),(systems[0],AlertSeverity.CRITICAL,True),(systems[1],AlertSeverity.WARNING,False)]:
        session.add(GovernanceAlert(id=uuid4(),system_id=s.id,severity=severity,alert_type=AlertType.INPUT_DRIFT,title='Test alert',description='Measured violation',resolved=resolved,payload={}))
    await session.commit()
    return engine,session

@pytest.mark.parametrize('question,expected,ids',[
    ('Which systems are high risk?','HIGH_RISK',{'credit'}),
    ('Which systems are minimal risk?','MINIMAL_RISK',{'fraud','spam'}),
    ('How many AI systems are registered?','3 active',{'credit','fraud','spam'}),
    ('Who owns the fraud detection system?','Fraud Team',{'fraud'}),
    ('What is the tier of the email spam filter?','MINIMAL_RISK',{'spam'}),
    ('Which systems have unresolved critical alerts?','Credit Scoring Model',{'credit'}),
    ('How many open alerts does the credit scoring system have?','1 open',{'credit'}),
    ('Which jurisdictions apply to the email spam filter?','EU',{'spam'}),
])
def test_sql_paths_use_matching_rows_without_llm(monkeypatch,question,expected,ids):
    monkeypatch.setattr(qa,'get_llm',lambda _:pytest.fail('Deterministic path must not even select a provider'))
    async def run():
        engine,session=await seeded_session()
        try:
            result=await qa.answer_question(QARequest(question=question),session,{})
            assert expected in result.answer
            assert {row['system_id'] for row in result.row_sources}==ids
            assert result.llm_provider=='none' and not result.needs_review
            assert all(not row.get('resolved',False) for row in result.row_sources)
        finally:
            await session.close();await engine.dispose()
    asyncio.run(run())


def test_decline_before_database_or_llm(monkeypatch):
    monkeypatch.setattr(qa,'get_llm',lambda _:pytest.fail('No LLM for out-of-scope'))
    result=asyncio.run(qa.answer_question(QARequest(question='What is the capital of France?'),None,{}))
    assert result.answer==qa.DECLINE and result.status=='declined' and result.sources==[]


def test_empty_or_wrong_article_retrieval_does_not_call_llm(monkeypatch):
    monkeypatch.setattr(qa,'get_llm',lambda _:pytest.fail('No LLM for empty retrieval'))
    monkeypatch.setattr(qa,'RegulatoryRetriever',lambda _:SimpleNamespace(retrieve=lambda *a,**kw:[],engine=SimpleNamespace(dispose=lambda:None)))
    result=asyncio.run(qa.answer_question(QARequest(question='What does Article 14 require?'),None,{}))
    assert result.answer==qa.NOT_FOUND and result.status=='not_found'
    assert result.needs_review_reasons==['no_retrieved_chunks']


def test_article_number_filters_the_search_before_top_five(monkeypatch):
    calls=[]
    def retrieve(*args,**kwargs):
        calls.append(kwargs)
        return []
    monkeypatch.setattr(qa,'RegulatoryRetriever',lambda _:SimpleNamespace(retrieve=retrieve,engine=SimpleNamespace(dispose=lambda:None)))
    monkeypatch.setattr(qa,'get_llm',lambda _:pytest.fail('No generation for empty result'))
    asyncio.run(qa.answer_question(QARequest(question='What does Article 37 require?'),None,{}))
    assert calls==[{'k':5,'filter':{'section_type':'article','article_number':37}}]


def test_why_uses_stored_context_and_identifies_original_provider(monkeypatch):
    generate=AsyncMock(return_value={'answer':'Stored regulatory rationale','citations':[],
        'llm_provider':'anthropic','llm_model':'answer-model','needs_review':False,'needs_review_reasons':[]})
    monkeypatch.setattr(qa,'get_llm',lambda _:SimpleNamespace(generate_json=generate))
    async def run():
        engine,session=await seeded_session()
        try:
            result=await qa.answer_question(QARequest(question='What is the tier of the email spam filter, and why?'),session,{})
            assert 'gemini / original-model' in result.answer
            assert result.llm_provider=='anthropic' and result.llm_model=='answer-model'
            assert result.needs_review and 'original_review' in result.needs_review_reasons
            assert 'Stored regulatory rationale' in generate.call_args.args[0]
            assert 'citations' in generate.call_args.args[0]
            assert result.stored_classification['frameworks']['EU_AI_ACT']['llm_provider']=='gemini'
            generate.assert_awaited_once()
            assert generate.call_args.kwargs['max_attempts']==1
        finally:
            await session.close();await engine.dispose()
    asyncio.run(run())
