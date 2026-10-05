"""Capture classification contexts without generating an LLM response."""
import json
from pathlib import Path
from argus.config import settings
from argus.rag.retriever import RegulatoryRetriever


def main():
    root = Path(__file__).resolve().parents[1]
    retriever = RegulatoryRetriever(settings.database_url)
    labels = json.loads((root / 'tests/fixtures/labelled_set.json').read_text())
    records = json.loads((root / 'tests/fixtures/labelled_results.json').read_text())
    prior = {c['id']: c['response'] for c in records['results']}
    for case in labels:
        if case['id'] not in (4, 5, 10, 13):
            continue
        response = prior[case['id']]
        query = f"{case['purpose']} {response.get('model_type') or ''} {response.get('output_type') or ''}"
        docs = retriever.retrieve_for_classification('EU_AI_ACT', query, k=5)
        print(f"Case {case['id']}: {case['name']}")
        for doc in docs:
            meta = doc.metadata
            print(json.dumps({'section_type':meta.get('section_type'),
                'article':meta.get('article_number'), 'annex':meta.get('annex_id'),
                'point':meta.get('annex_point'), 'subpoint':meta.get('annex_subpoint'),
                'first_100_chars':doc.page_content[:100]}, ensure_ascii=False))
        print(json.dumps({'article_50_in_context': any(d.metadata.get('article_number') == 50 for d in docs),
            'article_5_in_context': any(d.metadata.get('article_number') == 5 for d in docs),
            'article_5_chunk_text': [d.page_content for d in docs if d.metadata.get('article_number') == 5]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
