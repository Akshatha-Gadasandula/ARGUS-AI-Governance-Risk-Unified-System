"""No LLM calls: inspect query-dependent Article 5 pins before measurement."""
import json
import re
from pathlib import Path
from argus.config import settings
from argus.rag.retriever import RegulatoryRetriever


def main():
    root=Path(__file__).resolve().parents[1]
    cases=json.loads((root/'tests/fixtures/heldout_set.json').read_text())
    retriever=RegulatoryRetriever(settings.database_url)
    results=[]
    for case_id, letter in [(5,'b'),(9,'f')]:
        case=next(c for c in cases if c['id']==case_id)
        # Registrar-inferred model/output types do not exist yet: use purpose only.
        query=f"{case['purpose']}  "
        docs=retriever.retrieve_for_classification_with_score('EU_AI_ACT',query)
        doc,distance=next((d,s) for d,s in docs if d.metadata.get('article_number')==5)
        clause=re.search(rf'\({letter}\)\s+the placing',doc.page_content,re.I)
        record={'id':case_id,'name':case['name'],'query_basis':'purpose only; before Registrar inference',
            'distance':float(distance),'metadata':doc.metadata,'text':doc.page_content,
            'checked_paragraph':f'1({letter})','contains_target_clause_text':bool(clause)}
        results.append(record)
        print(json.dumps(record,ensure_ascii=False),flush=True)
    (root/'logs/heldout_article5_pins.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
