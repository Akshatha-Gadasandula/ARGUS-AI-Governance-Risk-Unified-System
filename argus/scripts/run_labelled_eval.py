"""Fixed-label measurement over HTTP; never tune inputs or repeat a POST.

Run from the nested project directory with Docker Compose running. The backend
must have LLM_PROVIDER=gemini and a fresh process call cap of 34 or less.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from argus.core.citations import canonicalize_citation
TIERS = ['PROHIBITED', 'HIGH_RISK', 'LIMITED_RISK', 'MINIMAL_RISK']
FROZEN = ['tests/fixtures/labelled_set.json', 'argus/config.py',
          'argus/core/agents/registrar.py', 'argus/core/agents/risk_classifier.py',
          'argus/core/llm.py', 'argus/core/llm_schemas.py', 'argus/rag/retriever.py',
          'argus/core/agents/drift_monitor.py']


def docker_json(code, value=None):
    result = subprocess.run(['docker', 'compose', 'exec', '-T', 'backend',
                             'python', '-c', code], cwd=ROOT, input=value,
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Backend diagnostic failed; raw stderr suppressed')
    return json.loads(result.stdout)


def sanitized(value):
    # Read credentials only inside the backend; never expose them to this runner.
    return docker_json("import sys,json; from argus.config import settings; "
                       "from argus.core.llm import LLMService; "
                       "print(LLMService(settings)._redact(sys.stdin.read()))",
                       json.dumps(value, ensure_ascii=False))


def usage_records():
    return docker_json("import json; from pathlib import Path; "
                       "p=Path('/app/logs/llm_usage.jsonl'); "
                       "print(json.dumps([json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []))")


def summarize_usage(records):
    return {'live_calls': sum(not r.get('cache_hit') and r['status'] in
                             ('ok', 'invalid_json', 'provider_error', 'quota_error') for r in records),
            'input_tokens': sum(r.get('input_tokens') or 0 for r in records),
            'output_tokens': sum(r.get('output_tokens') or 0 for r in records),
            'cache_hits': sum(bool(r.get('cache_hit')) for r in records),
            'quota_or_429_errors': sum(r['status'] == 'quota_error' for r in records),
            'statuses': [r['status'] for r in records]}


def citation_identity(citation):
    label = citation.get('article', '')
    article = re.search(r'\bArticle\s+(\d+)((?:\([0-9a-z]+\))*)', label, re.I)
    if article:
        suffix = article[2].lower()
        if not suffix and citation.get('point'):
            suffix = ''.join('(' + part.lower() + ')' for part in re.findall(r'[0-9]+|[a-z]', citation['point'], re.I))
        return ('article', article[1], suffix)
    annex = re.search(r'\bAnnex\s+([IVXLCDM]+)(?:,?\s+(?:point\s+)?(\d+)(?:\(([a-z])\))?)?', label, re.I)
    annex_id = citation.get('annex') or (annex[1] if annex else None)
    point = citation.get('point') or ((annex[2] or '') + ('(' + annex[3] + ')' if annex and annex[3] else '') if annex else '')
    return ('annex', annex_id.upper(), point.lower()) if annex_id else ('unknown', label, '')


def citation_label(citation):
    kind, number, point = citation_identity(citation)
    if kind == 'article':
        return f'Article {number}{point}'
    if kind == 'annex':
        return f'Annex {number}' + (f' {point}' if point else '')
    return number


def provision_matches(expected, supporting, exclusions):
    if expected == 'none':
        return not supporting
    expected_identity = citation_identity({'article': expected})
    return any(citation_identity(c) == expected_identity for c in supporting + exclusions)


def grounded(citation, provisions):
    kind, number, point = citation_identity(citation)
    if kind == 'article':
        return any(m.get('section_type') == 'article' and str(m.get('article_number')) == number for m in provisions)
    if kind == 'annex':
        match = re.fullmatch(r'(\d+)(?:\(([a-z])\))?', point) if point else None
        return any(m.get('section_type') == 'annex' and m.get('annex_id') == number
                   and (not point or (match and str(m.get('annex_point')) == match[1]
                                      and (not match[2] or m.get('annex_subpoint') == match[2]))) for m in provisions)
    return False


def score_case(case, response):
    framework = response['regulatory_citations'].get('EU_AI_ACT', {})
    citations = framework.get('citations', [])
    exclusions = framework.get('exclusions_checked', [])
    checks = [{'citation': c, 'role': role, 'grounded': grounded(c, framework.get('retrieved_provisions', []))}
              for role, items in [('supporting', citations), ('exclusion_checked', exclusions)] for c in items]
    return {**case, 'predicted_tier': response['risk_tier'],
            'tier_correct': response['risk_tier'] == case['expected_tier'],
            'cited_provisions': [citation_label(c) for c in citations],
            'exclusions_checked': [citation_label(c) for c in exclusions],
            'provision_match': provision_matches(case['expected_provision'], citations, exclusions),
            'strict_provision_match': (not citations if case['expected_provision'] == 'none' else any(c.get('article') == case['expected_provision'] for c in citations + exclusions)),
            'canonical_provision_match': (not citations if case['expected_provision'] == 'none' else any(not canonicalize_citation(c)['citation_incomplete'] and canonicalize_citation(c)['canonical_citation'] == canonicalize_citation({'article':case['expected_provision']})['canonical_citation'] for c in citations + exclusions)),
            'canonical_citations': [canonicalize_citation(c)['canonical_citation'] for c in citations],
            'grounded': all(c['grounded'] for c in checks), 'grounding_checks': checks,
            'needs_review': framework.get('needs_review'),
            'needs_review_reasons': framework.get('needs_review_reasons', []),
            'confidence': framework.get('confidence'), 'reasoning': framework.get('reasoning', ''),
            'llm_provider': framework.get('llm_provider'), 'llm_model': framework.get('llm_model'),
            'dropped_citations': framework.get('dropped_citations', []), 'response': response}


def metrics(results, clear_total=13):
    clear = [r for r in results if r['difficulty'] == 'clear']
    matrix = {expected: {predicted: 0 for predicted in TIERS + ['UNCLASSIFIED']} for expected in TIERS}
    for r in clear:
        matrix[r['expected_tier']].setdefault(r['predicted_tier'], 0)
        matrix[r['expected_tier']][r['predicted_tier']] += 1
    full_matrix = {expected: {predicted: 0 for predicted in TIERS + ['UNCLASSIFIED']} for expected in TIERS}
    for r in results:
        full_matrix[r['expected_tier']].setdefault(r['predicted_tier'], 0)
        full_matrix[r['expected_tier']][r['predicted_tier']] += 1
    return {'tier_correct':sum(r['tier_correct'] for r in results), 'tier_evaluated':len(results),
            'strict_provision_matches':sum(r.get('strict_provision_match', False) for r in results),
            'canonical_provision_matches':sum(r.get('canonical_provision_match', False) for r in results),
            'confusion_matrix_all':full_matrix,
            'clear_correct': sum(r['tier_correct'] for r in clear), 'clear_total': clear_total,
            'clear_evaluated': len(clear), 'ambiguous': [{k:r[k] for k in ('id','expected_tier','predicted_tier','tier_correct','provision_match')} for r in results if r['difficulty']=='ambiguous'],
            'confusion_matrix_clear': matrix,
            'review_case_ids': [r['id'] for r in results if r['needs_review']],
            'provision_matches': sum(r['provision_match'] for r in results),
            'provision_evaluated': len(results)}


def markdown(report):
    summary = report['metrics']
    lines = ['# Fixed labelled evaluation', '',
             f"Run status: {report['status']}. Completed {len(report['results'])}/{report.get('case_count',15)} cases.",
             f"Tier accuracy: {summary['tier_correct']}/{summary['tier_evaluated']}.",
             f"Strict provision matches (raw article string): {summary['strict_provision_matches']}/{summary['provision_evaluated']}.",
             f"Canonicalized provision matches (explicit fields, no inferred Article 5 paragraph): {summary['canonical_provision_matches']}/{summary['provision_evaluated']}.",
             f"Clear-case accuracy: {summary['clear_correct']}/{summary['clear_total']}; {summary['clear_evaluated']} clear cases evaluated.",
             'Unevaluated cases are UNVERIFIED and are not counted as incorrect predictions.',
             f"Provision identity matches: {summary['provision_matches']}/{summary['provision_evaluated']}.",
             f"Needs review: {len(summary['review_case_ids'])} cases; IDs {summary['review_case_ids']}.",
             'Provision matching includes checked exclusions. Article paragraph/subparagraph labels must match explicitly; prose mentions do not count. Scope/exception qualifiers require reading the reasoning and are not separately validated.',
             'Grounding checks provision identity, not whether the interpretation or quoted excerpt is correct. Empty citation sets pass the identity check vacuously.', '',
             '| ID | Name | Difficulty | Expected tier | Predicted tier | Expected provision | Supporting citations | Exclusions checked | Strict | Canonicalized | Grounded | Needs review / reasons | Confidence |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in report['results']:
        row = [r['id'], r['name'], r['difficulty'], r['expected_tier'], r['predicted_tier'], r['expected_provision'], ', '.join(r['canonical_citations']) or 'none', ', '.join(r['exclusions_checked']) or 'none', r['strict_provision_match'], r['canonical_provision_match'], r['grounded'], f"{r['needs_review']} / {', '.join(r['needs_review_reasons']) or 'none'}", r['confidence']]
        lines.append('| ' + ' | '.join(str(v).replace('|','/').replace('\n',' ') for v in row) + ' |')
    lines += ['', '## Confusion matrix (all cases, expected rows / predicted columns)', '',
              '| Expected | ' + ' | '.join(TIERS + ['UNCLASSIFIED']) + ' |',
              '|---|' + '---|' * 5]
    for expected, row in summary['confusion_matrix_all'].items():
        lines.append('| ' + expected + ' | ' + ' | '.join(str(row.get(t, 0)) for t in TIERS + ['UNCLASSIFIED']) + ' |')
    lines += ['', '## Ambiguous cases and incorrect predictions', '']
    for r in report['results']:
        if not r['tier_correct'] or r['difficulty'] == 'ambiguous':
            lines += [f"### {r['id']}: {r['name']}", '', f"Expected {r['expected_tier']}; predicted {r['predicted_tier']}; confidence {r['confidence']}.", '', r['reasoning'], '']
    lines += ['## Usage and cleanup', '', json.dumps(report['usage'], indent=2), '',
              f"DELETE endpoint results: {json.dumps(report['cleanup'])}", '',
              f"Stop reason: {report.get('stop_reason') or 'none'}", '',
              '## Frozen input hashes', '', json.dumps(report['frozen_hashes'], indent=2), '']
    return '\n'.join(lines)


def request(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'}, method=method), timeout=240) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def run(base_url, set_path, result_path, report_path, call_cap=34):
    cases = json.loads(set_path.read_text(encoding='utf-8'))
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('The fixed owner set must be nonempty with unique IDs')
    if result_path.exists() or report_path.exists():
        raise ValueError('Output already exists; refusing to overwrite recorded results')
    estimate = len(cases) * 2
    print(json.dumps({'estimated_live_calls':estimate, 'hard_cap':call_cap}), flush=True)
    if not 0 < call_cap <= 34 or estimate > call_cap:
        raise RuntimeError('Estimate exceeds allowed call cap; no registration attempted')
    config = docker_json("import json; from argus.config import settings; from argus.core.llm import get_llm; s=get_llm(settings); print(json.dumps({'gemini':s.name=='gemini','bounded':0<settings.llm_max_calls<=" + str(call_cap) + "}))")
    if not config['gemini'] or not config['bounded']:
        raise RuntimeError('Backend must select Gemini and enforce the requested process cap')
    paths = [name for name in FROZEN if name != 'tests/fixtures/labelled_set.json'] + [str(set_path.resolve().relative_to(ROOT)), 'argus/core/citations.py', 'scripts/run_labelled_eval.py']
    frozen = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
    log_start = len(usage_records())
    report = {'status':'running', 'run_id':uuid.uuid4().hex[:8], 'estimated_live_calls':estimate,
              'case_count':len(cases), 'call_cap':call_cap,
              'frozen_hashes':frozen, 'results':[], 'cleanup':[], 'stop_reason':None}
    created = []
    def save():
        report['usage'] = summarize_usage(usage_records()[log_start:])
        report['metrics'] = metrics(report['results'], sum(c['difficulty']=='clear' for c in cases))
        safe = sanitized(report)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding='utf-8')
        report_path.write_text(markdown(safe), encoding='utf-8')
    try:
        for case in cases:
            if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in frozen.items()):
                raise RuntimeError('Frozen input changed; measurement stopped')
            before = usage_records()[log_start:]
            if summarize_usage(before)['live_calls'] >= call_cap:
                raise RuntimeError('Live call cap reached')
            payload = {'name':f"eval-{report['run_id']}-{case['id']:02d}-{case['name']}",
                       'purpose':case['purpose'], 'owner_team':'Labelled evaluation',
                       'version':'1.0.0', 'jurisdictions':['EU']}
            status, response = request('POST', base_url+'/api/v1/registry/systems', payload)
            created.append(response['system_id'])
            response = sanitized(response)
            result = score_case(case, response)
            result['http_status'] = status
            report['results'].append(result)
            print(json.dumps({k:v for k,v in result.items() if k not in ('response','purpose','grounding_checks')}, ensure_ascii=False), flush=True)
            records = usage_records()[log_start:]
            save()
            new = records[len(before):]
            if any(r['status']=='provider_error' for r in new) or (new and new[-1]['status'] in ('quota_error','call_cap')):
                raise RuntimeError('Provider/auth/model error or exhausted quota backoff/call cap')
            if summarize_usage(records)['live_calls'] >= call_cap:
                raise RuntimeError('Live call cap reached')
        report['status'] = 'complete'
    except Exception as error:
        report['status'] = 'stopped'
        # Never persist arbitrary HTTP/SDK errors which could contain credentials.
        report['stop_reason'] = str(error) if type(error) is RuntimeError else type(error).__name__
        print(json.dumps({'STOPPED':report['stop_reason']}), flush=True)
    finally:
        # Recover committed registrations if a response was lost before its ID arrived.
        try:
            _, active = request('GET', base_url+'/api/v1/registry/systems')
            for system in active:
                if system['name'].startswith(f"eval-{report['run_id']}-") and system['system_id'] not in created:
                    created.append(system['system_id'])
        except Exception:
            report['cleanup_discovery'] = 'UNVERIFIED: active registry lookup failed'
        for system_id in created:
            try:
                status, _ = request('DELETE', base_url+'/api/v1/registry/systems/'+system_id)
                report['cleanup'].append({'system_id':system_id,'status':status})
            except Exception:
                report['cleanup'].append({'system_id':system_id,'status':'UNVERIFIED: DELETE failed'})
        save()
        print(json.dumps({'status':report['status'],'metrics':report['metrics'],'usage':report['usage'],'cleanup_count':len(report['cleanup'])}, ensure_ascii=False), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:8000')
    parser.add_argument('--set', type=Path, default=ROOT/'tests/fixtures/labelled_set.json')
    parser.add_argument('--results', type=Path, default=ROOT/'tests/fixtures/labelled_results.json')
    parser.add_argument('--report', type=Path, default=ROOT/'docs/labelled_eval_report.md')
    parser.add_argument('--call-cap', type=int, default=34)
    args = parser.parse_args()
    report = run(args.base_url.rstrip('/'), args.set, args.results, args.report, args.call_cap)
    raise SystemExit(0 if report['status']=='complete' else 1)


if __name__ == '__main__':
    main()
