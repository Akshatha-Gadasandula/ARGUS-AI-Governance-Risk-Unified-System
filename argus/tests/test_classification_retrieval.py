from types import SimpleNamespace
import pytest
from langchain.schema import Document
from argus.rag.retriever import RegulatoryRetriever
from argus.rag.prohibition_screen import article_five_screen, prohibited_screen_complete


def screen_docs():
    texts=['1. The following AI practices shall be prohibited: (a) the placing alpha; (b) the placing beta;',
           '(c) the placing gamma; (d) the placing delta;',
           '(e) the placing epsilon; (f) the placing zeta; (g) the placing eta; (h) the use theta; 2. The use safeguards.']
    return [Document(page_content='Article 5 - Prohibited AI practices\n'+body,
        metadata={'section_type':'article','article_number':5,'chunk_index':i}) for i,body in enumerate(texts)]


def fake_retriever():
    screen=screen_docs()
    fixed=[Document(page_content=f'Article {n}',metadata={'section_type':'article','article_number':n}) for n in (6,50)]
    annex=Document(page_content='Annex III 5(b)',metadata={'section_type':'annex','annex_id':'III','annex_point':'5','annex_subpoint':'b'})
    extra=Document(page_content='Article 10',metadata={'section_type':'article','article_number':10})
    def search(query,k,filter):
        if filter.get('article_number'):
            return [(next(d for d in fixed if d.metadata['article_number']==filter['article_number']),.7)]
        if filter.get('annex_id'):
            return [(annex,.2)]
        assert filter=={'section_type':{'$in':['article','annex']}}
        return [(screen[0],.8),(extra,.1)]
    retriever=RegulatoryRetriever.__new__(RegulatoryRetriever)
    retriever.has_corpus=lambda _:True
    retriever.retrieve=lambda *a,**kw:[]
    retriever.stores={'regulations_eu_ai_act':SimpleNamespace(similarity_search_with_score=search)}
    retriever.article_five_chunks_with_score=lambda store,query:[(d,.8+i*.01) for i,d in enumerate(screen)]
    return retriever


def test_every_screen_chunk_is_pinned_with_other_provisions_and_extra():
    retriever=fake_retriever()
    for query in ('alpha description','different description'):
        result=retriever.retrieve_for_classification_with_score('EU_AI_ACT',query)
        assert len(result)==7
        assert [d.metadata['chunk_index'] for d,_ in result if d.metadata.get('article_number')==5]==[0,1,2]
        assert [s for _,s in result]==sorted(s for _,s in result)
        assert {d.metadata.get('article_number') for d,_ in result}>={5,6,50,10}
        assert any(d.metadata.get('annex_id')=='III' for d,_ in result)


def test_missing_clause_or_continuation_fails_screen_coverage():
    docs=screen_docs()
    assert prohibited_screen_complete(docs)
    assert not prohibited_screen_complete([docs[0],docs[2]])
    missing=Document(page_content=docs[2].page_content.replace('(f) the placing zeta;',''),metadata=docs[2].metadata)
    assert not prohibited_screen_complete([docs[0],docs[1],missing])
    boundary=Document(page_content=docs[2].page_content.replace('2. The use safeguards.',''),metadata=docs[2].metadata)
    assert not prohibited_screen_complete([docs[0],docs[1],boundary])
    assert len(article_five_screen([(d,0) for d in docs]))==3


def test_empty_corpus_does_not_initialize_a_vector_store():
    retriever=RegulatoryRetriever.__new__(RegulatoryRetriever)
    retriever.has_corpus=lambda _:False
    assert retriever.retrieve_for_classification_with_score('RBI','query')==[]


@pytest.mark.asyncio
async def test_same_description_different_registrar_outputs_same_chunk_ids_and_exclusions_exempt(monkeypatch):
    from argus.core.agents import risk_classifier
    agent=risk_classifier.RiskClassifierAgent.__new__(risk_classifier.RiskClassifierAgent)
    agent.settings=SimpleNamespace()
    agent.retriever=fake_retriever()
    async def generate(*a,**kw):
        return {'risk_tier':'MINIMAL_RISK','confidence':.9,'reasoning':'Mock', 'citations':[],
            'exclusions_checked':[{'article':'Article 5'}], 'obligations':[],
            'llm_provider':'none','llm_model':None,'needs_review_reasons':[]}
    monkeypatch.setattr(risk_classifier,'get_llm',lambda _:SimpleNamespace(generate_json=generate))
    results=[]
    for model,output in [('nlp','ranking'),('other','binary_classification')]:
        results.append(await agent._classify_single('EU_AI_ACT',risk_classifier.EU_AI_ACT_PROMPT,
            risk_classifier.EU_AI_ACT_FALLBACK_PROMPT,'Mock','Same submitted purpose',model,output,[],[]))
    assert results[0].retrieved_provisions==results[1].retrieved_provisions
    assert all(not r.needs_review for r in results)
    assert all(not r.exclusions_checked[0]['citation_incomplete'] for r in results)


@pytest.mark.asyncio
async def test_incomplete_context_withholds_tier_and_never_calls_llm(monkeypatch):
    from argus.core.agents import risk_classifier
    agent=risk_classifier.RiskClassifierAgent.__new__(risk_classifier.RiskClassifierAgent)
    agent.settings=SimpleNamespace()
    agent.retriever=SimpleNamespace(has_corpus=lambda _:True,
        retrieve_for_classification=lambda *a,**kw:screen_docs()[:2])
    def forbidden(*a,**kw):
        raise AssertionError('LLM must not be accessed')
    monkeypatch.setattr(risk_classifier,'get_llm',forbidden)
    result=await agent.classify('mock','Mock','Purpose',None,None,[],[],['EU'])
    assert result.overall_risk_tier is None and result.needs_review
    assert result.to_dict()['status']=='context_incomplete'
    assert result.classifications[0].risk_tier is None
    assert result.classifications[0].status=='context_incomplete'
    assert result.needs_review_reasons==['prohibited_screen_incomplete']


def test_api_incomplete_context_exposes_null_tier_and_review():
    import json
    from pathlib import Path
    from argus.core.schemas import AISystemResponse
    saved=json.loads((Path(__file__).parent/'fixtures/heldout_results.json').read_text())
    response=saved['results'][0]['response']
    response['risk_tier']='UNCLASSIFIED'  # Required database enum uses an unclassified sentinel.
    response['regulatory_citations']['EU_AI_ACT'].update(status='context_incomplete',risk_tier=None,
        needs_review=True,needs_review_reasons=['prohibited_screen_incomplete'])
    result=AISystemResponse.model_validate(response)
    assert result.risk_tier is None and result.needs_review
    assert result.status=='context_incomplete'
    assert result.needs_review_reasons==['prohibited_screen_incomplete']
