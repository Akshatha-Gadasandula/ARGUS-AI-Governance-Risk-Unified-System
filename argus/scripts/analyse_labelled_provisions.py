"""Read-only rescoring of frozen records; never change model outputs or labels."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULE = (
    "Canonical own-identity projection: parse the expected string and each returned citation's "
    "article/annex/point fields into article-or-annex, number/id, paragraph/point and subparagraph. "
    "Ignore case, whitespace, commas, the word 'point', and the expected-label qualifiers "
    "'fraud exception'/'scope'. Combine separately supplied identity fields. Only for Article 5, "
    "a lone letter has implicit paragraph 1: 5(f) = 5(1)(f). Never infer a clause from a title, "
    "excerpt, reasoning, or expected answer; a bare Article 5 remains underspecified. "
    "For expected 'none', both scores require an empty supporting-citation list; checked exclusions "
    "are allowed. Non-none matching searches supporting citations and checked exclusions alike. "
    "This is a single identity-projection rule applied uniformly, not a validation of scope or legal interpretation."
)


def canonical(citation):
    label = citation.get('article', '')
    article = re.search(r'\barticle\s*(\d+)((?:\([0-9a-z]+\))*)', label, re.I)
    if article:
        parts = re.findall(r'\(([0-9a-z]+)\)', article[2], re.I)
        if not parts and citation.get('point'):
            parts = re.findall(r'\d+|[a-z]', citation['point'], re.I)
        parts = [p.lower() for p in parts]
        if article[1] == '5' and len(parts) == 1 and parts[0].isalpha():
            parts.insert(0, '1')
        return ('article', article[1], tuple(parts))
    annex = re.search(r'\bannex\s+([ivxlcdm]+)(?:,?\s+(?:point\s+)?(\d+)(?:\(([a-z])\))?)?', label, re.I)
    annex_id = citation.get('annex') or (annex[1] if annex else None)
    if annex_id:
        point = citation.get('point')
        if point:
            parts = re.findall(r'\d+|[a-z]', point, re.I)
        else:
            parts = [p for p in (annex[2], annex[3]) if p] if annex else []
        return ('annex', annex_id.upper(), tuple(p.lower() for p in parts))
    return ('unknown', label, ())


def analyse_case(case):
    framework = case['response']['regulatory_citations']['EU_AI_ACT']
    support = framework.get('citations', [])
    exclusions = framework.get('exclusions_checked', [])
    citations = support + exclusions
    expected = case['expected_provision']
    strict = not support if expected == 'none' else any(c.get('article') == expected for c in citations)
    expected_id = canonical({'article': expected})
    normalized = not support if expected == 'none' else any(canonical(c) == expected_id for c in citations)
    failure_type = None
    detail = None
    if not strict:
        if normalized:
            failure_type = 'formatting mismatch'
            detail = 'The canonical own identity matches, but the raw article string does not exactly equal the owner label.'
        elif expected != 'none' and any(canonical(c)[:2] == expected_id[:2] and not canonical(c)[2] for c in citations):
            failure_type = 'formatting / missing structured clause specificity'
            detail = 'The correct article/annex is named, but the required clause is absent from the identity fields; normalization cannot recover it.'
        else:
            failure_type = 'genuinely different or missing provision'
            detail = 'No returned own identity matches the expected provision, or supporting citations were returned where none was expected.'
    return {'id':case['id'],'name':case['name'],'difficulty':case['difficulty'],
            'expected_provision':expected,'strict_match':strict,'normalized_match':normalized,
            'strict_normalized_differ':strict != normalized,'failure_type':failure_type,'failure_detail':detail,
            'raw_supporting_citations':support,'raw_exclusions_checked':exclusions,
            'reasoning':case['reasoning']}


def analyse(report):
    cases = [analyse_case(c) for c in report['results']]
    clear = [c for c in cases if c['difficulty']=='clear']
    return {'normalization_rule':RULE,
            'strict_definition':"Exact, case-sensitive equality between the owner's expected_provision string and a returned citation.article string. No field joining or spelling/punctuation changes. For 'none', no supporting citations.",
            'strict_matches':sum(c['strict_match'] for c in cases),'normalized_matches':sum(c['normalized_match'] for c in cases),
            'total':len(cases),'strict_clear_matches':sum(c['strict_match'] for c in clear),
            'normalized_clear_matches':sum(c['normalized_match'] for c in clear),'clear_total':len(clear),
            'differing_case_ids':[c['id'] for c in cases if c['strict_normalized_differ']], 'cases':cases}


def render(analysis):
    lines = ['# Provision checks: strict score is primary', '',
             f"**Strict provision match: {analysis['strict_matches']}/{analysis['total']}.** Clear cases: {analysis['strict_clear_matches']}/{analysis['clear_total']}.",
             f"Normalized provision match: {analysis['normalized_matches']}/{analysis['total']}. Clear cases: {analysis['normalized_clear_matches']}/{analysis['clear_total']}.",
             f"Cases where strict and normalized differ: {analysis['differing_case_ids']}.", '',
             analysis['strict_definition'], '', analysis['normalization_rule'], '',
             'The original recorded case objects, original runner scores, labels, prompts, thresholds and retrieval are preserved. The scores below are a separate post-run analysis.', '',
             '| ID | Expected provision | Strict | Normalized | Failure classification |',
             '|---|---|---|---|---|']
    for case in analysis['cases']:
        lines.append(f"| {case['id']} | {case['expected_provision']} | {case['strict_match']} | {case['normalized_match']} | {case['failure_type'] or 'none'} |")
    lines += ['', '## Failed strict checks: raw structured format and reasoning', '']
    for case in analysis['cases']:
        if not case['strict_match']:
            lines += [f"### Case {case['id']}: {case['name']}", '',
                      f"Expected: {case['expected_provision']}. Failure: {case['failure_type']}. {case['failure_detail']}", '',
                      'Structured citations returned (including role and split identity fields):', '',
                      chr(96)*3+'json', json.dumps({'supporting':case['raw_supporting_citations'],'exclusions_checked':case['raw_exclusions_checked']},indent=2,ensure_ascii=False), chr(96)*3, '',
                      'Model reasoning:', '', '> '+case['reasoning'].replace('\n','\n> '), '']
    return '\n'.join(lines)


def main():
    results = ROOT/'tests/fixtures/labelled_results.json'
    original = results.read_bytes()
    report = json.loads(original)
    if report['status']=='running':
        raise RuntimeError('Wait for measurement and cleanup to finish before final analysis')
    analysis = analyse(report)
    (ROOT/'tests/fixtures/labelled_provision_analysis.json').write_text(json.dumps(analysis,indent=2,ensure_ascii=False),encoding='utf-8')
    document = ROOT/'docs/labelled_eval_report.md'
    previous = document.read_text(encoding='utf-8')
    if previous.startswith('# Provision checks: strict score is primary'):
        previous = previous.split('\n# Original runner measurement (preserved)\n',1)[1]
    document.write_text(render(analysis)+'\n# Original runner measurement (preserved)\n'+previous,encoding='utf-8')
    assert results.read_bytes()==original
    print(json.dumps({k:v for k,v in analysis.items() if k!='cases'},ensure_ascii=False))


if __name__=='__main__':
    main()
