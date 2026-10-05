import pytest
from argus.core.agents.risk_classifier import split_citation_roles
from argus.core.llm import ground_citations
from langchain.schema import Document


@pytest.mark.parametrize("tier", ["MINIMAL_RISK", "LIMITED_RISK"])
def test_article_five_is_an_exclusion_for_lower_tiers(tier):
    article = {"article":"Article 5", "title":"Prohibited practices"}
    support, exclusions = split_citation_roles(tier, [article], [])
    assert not support and exclusions == [article]


def test_explicitly_excluded_provision_is_not_supporting_even_if_grounded():
    article = {"article":"Article 6", "citation_role":"exclusion_checked"}
    support, exclusions = split_citation_roles("MINIMAL_RISK", [article], [])
    assert not support and exclusions == [article]
    result, review = ground_citations({"exclusions_checked":exclusions}, [Document(page_content="Article 6", metadata={"section_type":"article","article_number":6})])
    assert result["exclusions_checked"] == [article] and not review


def test_prohibited_tier_retains_article_five_and_unsupported_exclusions_are_dropped():
    article = {"article":"Article 5"}
    support, exclusions = split_citation_roles("PROHIBITED", [article], [])
    assert support == [article] and not exclusions
    result, review = ground_citations({"exclusions_checked":[{"article":"Article 999"}]}, [])
    assert not result["exclusions_checked"] and review
