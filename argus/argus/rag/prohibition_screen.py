"""Select and validate the complete Article 5 paragraph 1 screen."""
import re

START = re.compile(r'\b1\.\s+The following AI practices shall be prohibited',re.I)
END = re.compile(r'\b2\.\s+The use',re.I)
POINT = re.compile(r'\(([a-h])\)\s+(?:the placing|the use)\b',re.I)


def article_five_screen(pairs):
    """Include the boundary chunk containing paragraph 1's final continuation."""
    ordered=sorted(pairs,key=lambda pair:int(pair[0].metadata.get('chunk_index',0)))
    selected=[]
    started=False
    for pair in ordered:
        body=pair[0].page_content.split('\n',1)[-1]
        if not started:
            started=bool(START.search(body))
        if started:
            selected.append(pair)
            if END.search(body):
                break
    return selected


def prohibited_screen_complete(docs):
    """Check paragraph boundaries, contiguous chunk IDs and all eight clauses."""
    pairs=[(doc,0) for doc in docs if doc.metadata.get('section_type')=='article'
           and str(doc.metadata.get('article_number'))=='5']
    screen=article_five_screen(pairs)
    if not screen:
        return False
    texts=[doc.page_content.split('\n',1)[-1] for doc,_ in screen]
    joined=' '.join(texts)
    boundary=END.search(joined)
    if not START.search(joined) or not boundary:
        return False
    paragraph=joined[:boundary.start()]
    indices=[int(doc.metadata.get('chunk_index',0)) for doc,_ in screen]
    return indices==list(range(indices[0],indices[-1]+1)) and set(POINT.findall(paragraph.lower()))==set('abcdefgh')
