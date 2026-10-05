"""Recompute output flags without changing recorded responses or calling any model."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from argus.core.citations import canonicalize_citation, tier_citation_review_reasons

TITLE='offline rescoring, NOT a new measurement; the model outputs are unchanged'


def rescore_case(case):
    framework=case['response']['regulatory_citations']['EU_AI_ACT']
    support=[canonicalize_citation(c) for c in framework.get('citations',[])]
    exclusions=[canonicalize_citation(c,supporting=False) for c in framework.get('exclusions_checked',[])]
    reasons=[r for r in framework.get('needs_review_reasons',[]) if r!='incomplete_citation' and not r.startswith('tier_citation_inconsistent:')]
    reasons+=tier_citation_review_reasons(case['predicted_tier'],support)
    if any(c['citation_incomplete'] for c in support):
        reasons.append('incomplete_citation')
    expected=case['expected_provision']
    canonical=not support if expected=='none' else any(not c['citation_incomplete'] and c['canonical_citation']==canonicalize_citation({'article':expected})['canonical_citation'] for c in support+exclusions)
    return {'id':case['id'],'original_needs_review':case['needs_review'],'offline_needs_review':bool(reasons),
        'offline_needs_review_reasons':list(dict.fromkeys(reasons)),
        'original_canonical_match':case['canonical_provision_match'],'offline_canonical_match':canonical,
        'supporting_incomplete':any(c['citation_incomplete'] for c in support),
        'unchanged_tier':case['predicted_tier']}


def main():
    protected=[ROOT/'tests/fixtures/heldout_set.json',ROOT/'tests/fixtures/heldout_results.json',ROOT/'docs/heldout_eval_report.md']
    originals={p:p.read_bytes() for p in protected}
    records=json.loads(originals[protected[1]])
    cases=[rescore_case(c) for c in records['results']]
    output={'heading':TITLE,'scope':'Supporting completeness and deterministic output flags only; no new retrieval, guard replay, schema repair, inferred clauses or model generation.',
        'original_review_count':sum(c['original_needs_review'] for c in cases),
        'offline_review_count':sum(c['offline_needs_review'] for c in cases),
        'offline_review_case_ids':[c['id'] for c in cases if c['offline_needs_review']],
        'original_canonical_matches':sum(c['original_canonical_match'] for c in cases),
        'offline_canonical_matches':sum(c['offline_canonical_match'] for c in cases),'cases':cases}
    (ROOT/'tests/fixtures/offline_heldout_rescoring.json').write_text(json.dumps(output,indent=2))
    lines=['# '+TITLE,'',output['scope'],'',
        f"Needs review: {output['original_review_count']}/{len(cases)} originally; {output['offline_review_count']}/{len(cases)} offline. Offline cases: {output['offline_review_case_ids']}.",
        f"Canonical matches: {output['original_canonical_matches']}/{len(cases)} originally; {output['offline_canonical_matches']}/{len(cases)} offline.",'',
        '| Case | Original review | Offline review | Offline reasons | Original canonical match | Offline canonical match |',
        '|---|---|---|---|---|---|']
    for c in cases:
        lines.append(f"| {c['id']} | {c['original_needs_review']} | {c['offline_needs_review']} | {', '.join(c['offline_needs_review_reasons']) or 'none'} | {c['original_canonical_match']} | {c['offline_canonical_match']} |")
    lines+=['','Case 5 remains incorrectly MINIMAL_RISK and loses its output-completeness flag because only checked exclusions were incomplete. This rescoring does not rerun classification or correct its missing prohibition context. New retrieval/safety behavior needs a future live measurement to establish its effect.','',
        'All model response fields, tiers, reasoning and recorded files are unchanged. Old responses are not validated/repaired against the new generation schema; no missing paragraphs or points are invented.']
    (ROOT/'docs/offline_heldout_rescoring.md').write_text('\n'.join(lines))
    assert all(p.read_bytes()==b for p,b in originals.items())
    print(json.dumps({k:v for k,v in output.items() if k!='cases'}))


if __name__=='__main__':
    main()
