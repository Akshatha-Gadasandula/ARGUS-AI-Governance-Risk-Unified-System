import json
from scripts.run_labelled_eval import ROOT, metrics, provision_matches, grounded


def test_fixed_labelled_set_has_owner_cases_and_no_labels_in_purposes():
    cases=json.loads((ROOT/'tests/fixtures/labelled_set.json').read_text())
    assert [c['id'] for c in cases]==list(range(1,16))
    assert [c['id'] for c in cases if c['difficulty']=='ambiguous']==[6,15]
    assert all('Article' not in c['purpose'] and not any(t in c['purpose'] for t in ('PROHIBITED','HIGH_RISK','LIMITED_RISK','MINIMAL_RISK')) for c in cases)


def test_provision_matching_keeps_paragraphs_and_exclusion_roles_distinct():
    assert not provision_matches('Article 50(1)', [{'article':'Article 50'}], [])
    assert provision_matches('Article 50(1)', [{'article':'Article 50(1)'}], [])
    assert provision_matches('Annex III 5(b) fraud exception', [], [{'article':'Annex III, point 5(b)'}])
    assert provision_matches('none', [], [{'article':'Article 5'}])
    assert not provision_matches('none', [{'article':'Article 6'}], [])


def test_grounding_and_partial_accuracy_do_not_invent_predictions():
    assert not grounded({'article':'Article 999'}, [{'section_type':'article','article_number':5}])
    result=metrics([{'id':1,'difficulty':'clear','expected_tier':'HIGH_RISK','predicted_tier':'MINIMAL_RISK','tier_correct':False,'needs_review':True,'provision_match':False}])
    assert result['clear_evaluated']==1 and result['clear_total']==13
    assert result['clear_correct']==0
    assert result['confusion_matrix_clear']['HIGH_RISK']['MINIMAL_RISK']==1
    assert result['review_case_ids']==[1]


def test_heldout_call_estimate_stops_before_any_provider_or_http_access(tmp_path, monkeypatch):
    from scripts import run_labelled_eval as runner
    import pytest
    path=tmp_path/'owner_set.json'
    path.write_text(json.dumps([{'id':i} for i in range(13)]))
    def forbidden(*a,**kw):
        raise AssertionError('No provider diagnostic or HTTP request is permitted')
    monkeypatch.setattr(runner,'docker_json',forbidden)
    monkeypatch.setattr(runner,'request',forbidden)
    with pytest.raises(RuntimeError,match='Estimate exceeds'):
        runner.run('http://unused',path,tmp_path/'results.json',tmp_path/'report.md',24)


def test_heldout_metrics_use_actual_set_size_and_separate_scores():
    records=[{'id':1,'difficulty':'clear','expected_tier':'PROHIBITED','predicted_tier':'PROHIBITED',
              'tier_correct':True,'needs_review':True,'provision_match':False,
              'strict_provision_match':False,'canonical_provision_match':True}]
    result=metrics(records,1)
    assert result['clear_total']==1 and result['tier_correct']==1
    assert result['strict_provision_matches']==0 and result['canonical_provision_matches']==1
    assert result['confusion_matrix_all']['PROHIBITED']['PROHIBITED']==1
