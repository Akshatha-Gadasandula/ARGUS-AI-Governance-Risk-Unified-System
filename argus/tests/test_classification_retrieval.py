from types import SimpleNamespace
from langchain.schema import Document
from argus.rag.retriever import RegulatoryRetriever


def test_four_pinned_provisions_and_one_unique_candidate_keep_distance_order():
    recital = Document(page_content="Recital", metadata={"section_type": "recital"})
    article = Document(page_content="Article 6", metadata={"section_type": "article", "article_number": 6})
    prohibition = Document(page_content="Article 5", metadata={"section_type": "article", "article_number": 5})
    transparency = Document(page_content="Article 50", metadata={"section_type": "article", "article_number": 50})
    annex = Document(page_content="Annex III 5(b)", metadata={"section_type": "annex", "annex_id": "III", "annex_point": "5"})
    others = [Document(page_content=f"Article {n}", metadata={"section_type": "article", "article_number": n}) for n in (10, 12, 14, 15)]
    queries = []
    def search(query, k, filter):
        queries.append((k, filter))
        if filter.get("article_number") == 6:
            return [(article, .8)]
        if filter.get("article_number") == 5:
            return [(prohibition, .7)]
        if filter.get("article_number") == 50:
            return [(transparency, .9)]
        if filter.get("annex_id") == "III":
            return [(annex, .6)]
        assert filter == {"section_type": {"$in": ["article", "annex"]}}
        return [(others[0], .1), (article, .8), (others[1], .2), (annex, .6), (others[2], .3), (others[3], .4)]
    retriever = RegulatoryRetriever.__new__(RegulatoryRetriever)
    retriever.has_corpus = lambda _: True
    retriever.retrieve = lambda *a, **kw: []
    retriever.stores = {"regulations_eu_ai_act": SimpleNamespace(similarity_search_with_score=search)}
    result = retriever.retrieve_for_classification_with_score("EU_AI_ACT", "query")
    assert len(result) == 5
    assert [score for _, score in result] == [.1, .6, .7, .8, .9]
    assert prohibition in [d for d, _ in result] and transparency in [d for d, _ in result]
    assert article in [d for d, _ in result] and annex in [d for d, _ in result]
    assert recital not in [d for d, _ in result]


def test_empty_corpus_does_not_initialize_a_vector_store():
    retriever = RegulatoryRetriever.__new__(RegulatoryRetriever)
    retriever.has_corpus = lambda _: False
    assert retriever.retrieve_for_classification_with_score("RBI", "query") == []
