import pytest
from pydantic import ValidationError
from argus.core.llm_schemas import SupportingCitation, ClassificationOutput, Citation


def test_supporting_fields_are_required_in_output_schema():
    fields=SupportingCitation.model_json_schema()['required']
    assert {'paragraph','point','incomplete_reason'} <= set(fields)
    with pytest.raises(ValidationError):
        SupportingCitation(article='Article 5(1)(f)')


@pytest.mark.parametrize('article',['Article 5','Article 50'])
def test_missing_identity_requires_null_reason(article):
    with pytest.raises(ValidationError):
        SupportingCitation(article=article,paragraph=None,point=None,incomplete_reason=None)
    assert SupportingCitation(article=article,paragraph=None,point=None,incomplete_reason='Unknown in retrieved text')


def test_explicit_identity_and_article_fifty_no_lettered_point_are_valid():
    assert SupportingCitation(article='Article 5',paragraph='1',point='f',incomplete_reason=None)
    assert SupportingCitation(article='Article 50',paragraph='1',point=None,incomplete_reason='Paragraph has no lettered point')
    assert Citation(article='Article 5')  # Exclusions retain their permissive schema.
    result=ClassificationOutput(risk_tier='MINIMAL_RISK',confidence=.9,reasoning='Mock',citations=[],
        exclusions_checked=[{'article':'Article 5'}],obligations=[])
    assert result.exclusions_checked[0].article=='Article 5'


def test_article_five_unknown_point_requires_null_instead_of_invented_identity():
    with pytest.raises(ValidationError):
        SupportingCitation(article='Article 5',paragraph='1',point='unknown',incomplete_reason=None)
