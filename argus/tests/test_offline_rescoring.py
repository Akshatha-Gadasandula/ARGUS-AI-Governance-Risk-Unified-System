from scripts.rescore_heldout_offline import rescore_case


def case(tier,expected,support,exclusions,reasons):
    return {'id':1,'predicted_tier':tier,'expected_provision':expected,'needs_review':True,
        'canonical_provision_match':False,'response':{'regulatory_citations':{'EU_AI_ACT':{
            'citations':support,'exclusions_checked':exclusions,'needs_review_reasons':reasons}}}}


def test_incomplete_checked_exclusions_do_not_require_review():
    record=case('MINIMAL_RISK','none',[],[{'article':'Article 5'}],['incomplete_citation'])
    result=rescore_case(record)
    assert not result['offline_needs_review'] and result['offline_canonical_match']
    assert record['response']['regulatory_citations']['EU_AI_ACT']['needs_review_reasons']==['incomplete_citation']


def test_supporting_article_fifty_without_paragraph_is_flagged_without_inference():
    result=rescore_case(case('LIMITED_RISK','Article 50(1)',[{'article':'Article 50'}],[],[]))
    assert result['offline_needs_review_reasons']==['incomplete_citation']
    assert not result['offline_canonical_match']


def test_existing_non_completeness_reasons_survive_rescoring():
    result=rescore_case(case('MINIMAL_RISK','none',[],[{'article':'Article 5'}],['incomplete_citation','dropped_citation','confidence_below_0.7']))
    assert result['offline_needs_review_reasons']==['dropped_citation','confidence_below_0.7']
