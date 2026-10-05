"""Offline context measurement with the installed MiniLM WordPiece tokenizer."""
import json
import re
from pathlib import Path
from argus.config import settings
from argus.rag.retriever import RegulatoryRetriever
from argus.core.agents.risk_classifier import EU_AI_ACT_PROMPT
from argus.core.llm_schemas import ClassificationOutput
from argus.rag.prohibition_screen import prohibited_screen_complete


def main():
    root=Path(__file__).resolve().parents[1]
    retriever=RegulatoryRetriever(settings.database_url)
    retriever.retrieve('EU_AI_ACT','prohibition screen',k=1)
    store=retriever.stores['regulations_eu_ai_act']
    tokenizer=retriever.embeddings.client.tokenizer
    def count(value):
        return len(tokenizer.encode(value,add_special_tokens=False,truncation=False))
    cases=json.loads((root/'tests/fixtures/heldout_set.json').read_text())
    records=[]
    for case in cases:
        query=case['purpose']
        all_five=store.similarity_search_with_score(query,k=1000,filter={'section_type':'article','article_number':5})
        ordered=sorted(all_five,key=lambda x:x[0].metadata['chunk_index'])
        screen=[]
        for pair in ordered:
            screen.append(pair)
            if re.search(r'\b2\.\s+The use',pair[0].page_content):
                break
        if hasattr(retriever,'article_five_chunks_with_score'):
            selected=retriever.retrieve_for_classification_with_score('EU_AI_ACT',query)
        else:
            selected=list(screen)
            for filter in ({'section_type':'article','article_number':6},{'section_type':'article','article_number':50},{'section_type':'annex','annex_id':'III'}):
                selected.extend(store.similarity_search_with_score(query,k=1,filter=filter))
            identity=lambda doc:(doc.page_content,str(doc.metadata))
            seen={identity(doc) for doc,_ in selected}
            for pair in store.similarity_search_with_score(query,k=len(selected)+1,filter={'section_type':{'$in':['article','annex']}}):
                if identity(pair[0]) not in seen:
                    selected.append(pair)
                    break
        docs=[doc for doc,_ in selected]
        text=retriever.format_passages(docs)
        prompt=EU_AI_ACT_PROMPT.format(system_name=case['name'],system_purpose=query,model_type='Unspecified',
            output_type='Unspecified',data_sources='Not specified',affected_demographics='Not specified',
            jurisdictions='EU, IN',retrieved_passages=text)
        effective='\n'+prompt+'\nReturn only JSON matching this schema:\n'+json.dumps(ClassificationOutput.model_json_schema(),sort_keys=True)
        effective+='\nCite only provisions in these retrieved chunks. Omit unsupported citations:\n'+json.dumps([{'text':doc.page_content,'metadata':doc.metadata} for doc in docs],sort_keys=True,ensure_ascii=False)
        record={'id':case['id'],'chunks':len(docs),'screen_complete':prohibited_screen_complete(docs),'article_5_chunk_ids':[d.metadata['chunk_index'] for d in docs if d.metadata.get('article_number')==5],
            'context_wordpiece_tokens':count(text),'effective_input_wordpiece_tokens':count(effective)}
        records.append(record)
        print(json.dumps(record),flush=True)
    output={'tokenizer':'sentence-transformers/all-MiniLM-L6-v2 WordPiece; no truncation; Gemini count UNVERIFIED',
        'records':records,'max_context_tokens':max(r['context_wordpiece_tokens'] for r in records),
        'max_effective_input_tokens':max(r['effective_input_wordpiece_tokens'] for r in records)}
    (root/'logs/prohibition_context_tokens.json').write_text(json.dumps(output,indent=2))


if __name__=='__main__':
    main()
