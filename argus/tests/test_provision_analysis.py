from scripts.analyse_labelled_provisions import canonical, analyse_case


def case(expected, citations, exclusions=()):
    return {'id':1,'name':'Test','difficulty':'clear','expected_provision':expected,'reasoning':'Original reasoning',
            'response':{'regulatory_citations':{'EU_AI_ACT':{'citations':citations,'exclusions_checked':list(exclusions)}}}}


def test_strict_does_not_join_fields_but_normalized_uses_explicit_identity():
    result=analyse_case(case('Annex III 5(b)',[{'article':'Annex III','annex':'III','point':'5(b)'}]))
    assert not result['strict_match'] and result['normalized_match']
    assert result['failure_type']=='formatting mismatch'


def test_article_five_shorthand_rule_is_uniform_and_does_not_invent_missing_letters():
    assert canonical({'article':'Article 5(f)'})==canonical({'article':'Article 5(1)(f)'})
    assert canonical({'article':'Article 5','point':'c'})==canonical({'article':'Article 5(1)(c)'})
    result=analyse_case(case('Article 5(1)(c)',[{'article':'Article 5','excerpt':'Social scoring under Article 5(1)(c)'}]))
    assert not result['normalized_match']
    assert result['failure_type']=='formatting / missing structured clause specificity'


def test_different_provisions_do_not_normalize_and_none_ignores_checked_exclusions():
    result=analyse_case(case('Article 50(1)',[{'article':'Article 6'}]))
    assert not result['strict_match'] and not result['normalized_match']
    assert result['failure_type']=='genuinely different or missing provision'
    result=analyse_case(case('none',[],[{'article':'Article 5'}]))
    assert result['strict_match'] and result['normalized_match']
