import pytest
from argus.core.citations import canonicalize_citation, tier_citation_review_reasons
from argus.core.agents.risk_classifier import split_citation_roles


@pytest.mark.parametrize('raw,expected,incomplete', [
    ({'article':'Article 5(1)(f)'}, 'Article 5(1)(f)', False),
    ({'article':'Article 5','point':'1(f)'}, 'Article 5(1)(f)', False),
    ({'article':'Article 5','paragraph':'1','point':'f'}, 'Article 5(1)(f)', False),
    ({'article':'Article 5','point':'f'}, 'Article 5(f)', True),
    ({'article':'Article 5(1)'}, 'Article 5(1)', True),
    ({'article':'Annex III','annex':'III','point':'5(b)'}, 'Annex III point 5(b)', False),
    ({'article':'Annex III, point 4(a)'}, 'Annex III point 4(a)', False),
    ({'article':'Article 50','point':'1'}, 'Article 50(1)', False),
])
def test_canonical_identity_retains_raw_fields(raw, expected, incomplete):
    result = canonicalize_citation(raw)
    assert result['canonical_citation'] == expected
    assert result['citation_incomplete'] == incomplete
    assert all(result[k] == v for k,v in raw.items())


@pytest.mark.parametrize('tier,raw', [
    ('PROHIBITED', {'article':'Article 5','point':'f'}),
    ('LIMITED_RISK', {'article':'Article 6'}),
    ('HIGH_RISK', {'article':'Article 6'}),
    ('MINIMAL_RISK', {'article':'Article 50'}),
])
def test_inconsistent_tier_support_gets_reason(tier,raw):
    assert tier_citation_review_reasons(tier,[raw])[0].startswith('tier_citation_inconsistent:')


@pytest.mark.parametrize('tier,raw', [
    ('PROHIBITED', {'article':'Article 5(1)(c)'}),
    ('LIMITED_RISK', {'article':'Article 50'}),
    ('HIGH_RISK', {'article':'Annex III','point':'4(a)'}),
    ('HIGH_RISK', {'article':'Article 6(1)'}),
])
def test_consistent_tiers_have_no_consistency_reason(tier,raw):
    assert not tier_citation_review_reasons(tier,[raw])
    assert not tier_citation_review_reasons('MINIMAL_RISK',[])


def test_minimal_article_six_is_checked_exclusion():
    raw = {'article':'Article 6','citation_role':'supporting'}
    support, excluded = split_citation_roles('MINIMAL_RISK',[raw],[])
    assert not support and excluded == [raw]


@pytest.mark.asyncio
async def test_classifier_persists_consistency_and_incomplete_reasons(monkeypatch, complete_prohibition_screen):
    from types import SimpleNamespace
    from langchain.schema import Document
    from argus.core.agents import risk_classifier
    agent = risk_classifier.RiskClassifierAgent.__new__(risk_classifier.RiskClassifierAgent)
    agent.settings = SimpleNamespace()
    docs = complete_prohibition_screen
    agent.retriever = SimpleNamespace(has_corpus=lambda _:True,
        retrieve_for_classification=lambda *a,**kw:docs, format_passages=lambda _: 'Article 5')
    async def generate(*a,**kw):
        return {'risk_tier':'PROHIBITED','confidence':.9,'reasoning':'Mock reasoning',
                'citations':[{'article':'Article 5','point':'f'}],'obligations':[],
                'llm_provider':'gemini','llm_model':'mock-model','needs_review_reasons':[]}
    monkeypatch.setattr(risk_classifier,'get_llm',lambda _:SimpleNamespace(generate_json=generate))
    result = await agent._classify_single('EU_AI_ACT',risk_classifier.EU_AI_ACT_PROMPT,
        risk_classifier.EU_AI_ACT_FALLBACK_PROMPT,'Test system','Test purpose',None,None,[],[])
    assert result.needs_review
    assert 'incomplete_citation' in result.needs_review_reasons
    assert 'tier_citation_inconsistent:prohibited_without_article_5_paragraph' in result.needs_review_reasons
    assert result.citations[0]['article']=='Article 5'
    assert result.citations[0]['canonical_citation']=='Article 5(f)'


def test_prohibited_requires_paragraph_and_letter_and_article_fifty_requires_paragraph():
    assert tier_citation_review_reasons('PROHIBITED',[{'article':'Article 5(1)'}])
    assert canonicalize_citation({'article':'Article 50'})['citation_incomplete']
    assert not canonicalize_citation({'article':'Article 50','paragraph':'1','point':None,'incomplete_reason':'No lettered point'})['citation_incomplete']
    assert not canonicalize_citation({'article':'Article 5'}, supporting=False)['citation_incomplete']
