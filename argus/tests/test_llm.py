"""Mock-only provider, budget, cache, schema, grounding, and caller regressions."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from langchain.schema import Document

from argus.config import Settings
from argus.core.llm import (
    AnthropicProvider, GeminiProvider, LLMProvider, LLMService,
    ProcessBudget, ProviderResponse, ground_citations,
)
from argus.core.llm_schemas import AnswerOutput, ClassificationOutput


class Clock:
    def __init__(self):
        self.now = 0
        self.delays = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.delays.append(seconds)
        self.now += seconds


class FakeProvider(LLMProvider):
    name = "gemini"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, model, prompt, schema, system, max_tokens):
        self.calls.append((model, prompt))
        outcome = self.responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return ProviderResponse(outcome, 17, 8)


def settings(**overrides):
    # Credentials and model identifiers are fixtures, never deployment values.
    return Settings(_env_file=None, **{
        "llm_provider": "gemini", "gemini_api_key": "fake-test-credential",
        "gemini_model": "model-from-test-env", "llm_max_rpm": 60, **overrides,
    })


def service(tmp_path, responses, **overrides):
    clock = Clock()
    provider = FakeProvider(responses)
    budget = ProcessBudget(clock.time, clock.sleep)
    llm = LLMService(settings(**overrides), provider=provider, budget=budget,
                     cache_dir=tmp_path / "cache", log_path=tmp_path / "usage.jsonl")
    return llm, provider, clock


ANSWER = json.dumps({"answer": "Grounded answer", "citations": []})
FALLBACK = {"answer": "Rule-based answer", "citations": []}


def test_cache_hit_makes_no_second_call_and_survives_service_recreation(tmp_path):
    llm, provider, _ = service(tmp_path, [ANSWER])
    first = llm.generate("same prompt", AnswerOutput, FALLBACK)
    second = LLMService(llm.settings, provider=provider, budget=llm.budget,
                        cache_dir=llm.cache_dir, log_path=llm.log_path).generate("same prompt", AnswerOutput, FALLBACK)
    assert first == second
    assert len(provider.calls) == llm.budget.calls == 1
    usage = [json.loads(line) for line in llm.log_path.read_text().splitlines()]
    assert usage[0]["input_tokens"] == 17 and usage[0]["output_tokens"] == 8
    assert usage[1]["cache_hit"] and usage[1]["input_tokens"] == 0
    assert usage[0]["provider"] == "gemini"


def test_shared_process_call_cap_triggers_fallback_even_across_services(tmp_path):
    llm, provider, _ = service(tmp_path, [ANSWER], llm_max_calls=1)
    llm.generate("first", AnswerOutput, FALLBACK)
    other = LLMService(llm.settings, provider=provider, budget=llm.budget,
                       cache_dir=llm.cache_dir, log_path=llm.log_path)
    result = other.generate("second", AnswerOutput, FALLBACK)
    assert len(provider.calls) == 1
    assert result["answer"] == FALLBACK["answer"]
    assert result["llm_provider"] == "none" and result["llm_model"] is None
    assert result["fallback_reason"] == "call_cap"


@pytest.mark.parametrize("error", [SimpleNamespace(status_code=429), SimpleNamespace(code=429), SimpleNamespace(message="quota exhausted")])
def test_429_or_quota_backoff_is_bounded(tmp_path, error):
    failure = RuntimeError(getattr(error, "message", "rate limit"))
    if hasattr(error, "status_code"):
        failure.status_code = error.status_code
    if hasattr(error, "code"):
        failure.code = error.code
    llm, provider, clock = service(tmp_path, [failure, failure, failure])
    result = llm.generate("quota", AnswerOutput, FALLBACK)
    assert len(provider.calls) == llm.budget.calls == 3
    assert clock.delays == [1, 2]
    assert result["fallback_reason"] == "quota_error"


def test_retry_attempts_respect_call_cap(tmp_path):
    failure = RuntimeError("quota")
    llm, provider, _ = service(tmp_path, [failure], llm_max_calls=1)
    assert llm.generate("quota", AnswerOutput, FALLBACK)["fallback_reason"] == "call_cap"
    assert len(provider.calls) == 1


@pytest.mark.parametrize("invalid", ["not json", '{"answer": 123}', '{}'])
def test_invalid_json_or_schema_retried_once_then_fallback(tmp_path, invalid):
    llm, provider, _ = service(tmp_path, [invalid, invalid])
    result = llm.generate("invalid", AnswerOutput, FALLBACK)
    assert len(provider.calls) == 2
    assert result["fallback_reason"] == "invalid_json"
    assert result["llm_provider"] == "none" and result["needs_review"]
    assert not list(llm.cache_dir.glob("*.json"))


def test_valid_json_retry_can_be_cached(tmp_path):
    llm, provider, _ = service(tmp_path, ["invalid", ANSWER])
    result = llm.generate("retry", AnswerOutput, FALLBACK)
    assert result == llm.generate("retry", AnswerOutput, FALLBACK)
    assert len(provider.calls) == 2
    assert result["needs_review_reasons"] == ["schema_repair"]


def test_throttle_spaces_calls_without_sleeping_on_cache_hits(tmp_path):
    llm, _, clock = service(tmp_path, [ANSWER, ANSWER], llm_max_rpm=5)
    llm.generate("a", AnswerOutput, FALLBACK)
    llm.generate("a", AnswerOutput, FALLBACK)
    llm.generate("b", AnswerOutput, FALLBACK)
    assert clock.delays == [12]


def test_ungrounded_citation_is_dropped_and_cache_preserves_review_flag(tmp_path):
    chunks = [Document(page_content="Article 10 - Data and data governance", metadata={"section_type": "article", "article_number": 10})]
    text = json.dumps({"answer": "Assess the data.", "citations": [{"article": "Article 10", "title": "Data"}, {"article": "Article 999", "title": "Invented"}]})
    llm, provider, _ = service(tmp_path, [text])
    result = llm.generate("grounding", AnswerOutput, FALLBACK, chunks=chunks)
    assert [c["article"] for c in result["citations"]] == ["Article 10"]
    assert result["needs_review"]
    assert llm.generate("grounding", AnswerOutput, FALLBACK, chunks=chunks)["needs_review"]
    assert len(provider.calls) == 1
    cached = json.loads(next(llm.cache_dir.glob("*.json")).read_text())
    assert [c["article"] for c in cached["citations"]] == ["Article 10"]
    assert [c["article"] for c in cached["dropped_citations"]] == ["Article 999"]


def test_annex_subpoint_and_reference_in_another_provision_are_not_confused():
    chunks = [Document(page_content="Annex III, point 5(b), referred to in Article 6(2)", metadata={"section_type": "annex", "annex_id": "III", "annex_point": "5", "annex_subpoint": "b"})]
    result, review = ground_citations({"citations": [{"article": "Annex III, point 5(b)"}, {"article": "Annex III, point 5(c)"}, {"article": "Article 6"}]}, chunks)
    assert result["citations"] == [{"article": "Annex III, point 5(b)"}]
    assert review


def test_non_citation_text_does_not_change_citation_grounding():
    result, review = ground_citations({"answer": "Comply with Article 999", "citations": []}, [])
    assert not review and "Article 999" in result["answer"]


def test_citation_title_and_excerpt_do_not_change_own_identity():
    chunks = [Document(page_content="Annex III point 5(b)", metadata={"section_type": "annex", "annex_id": "III", "annex_point": "5", "annex_subpoint": "b"})]
    citation = {"article": "Annex III point 5(b)", "title": "Referred to in Article 6(2)", "excerpt": "See Article 999"}
    result, review = ground_citations({"citations": [citation]}, chunks)
    assert result["citations"] == [citation] and not review


def test_all_references_in_a_citation_must_be_grounded():
    chunks = [Document(page_content="Annex III", metadata={"section_type": "annex", "annex_id": "III"})]
    result, review = ground_citations({"citations": [
        {"article": "Annex III and Article 999"},
        {"article": "Article 999", "annex": "III"},
        {"article": "Annex III and Annex IV"},
    ]}, chunks)
    assert not result["citations"] and review


def test_changed_retrieved_context_changes_cache_key(tmp_path):
    llm, provider, _ = service(tmp_path, [ANSWER, ANSWER])
    llm.generate("context", AnswerOutput, FALLBACK, chunks=[Document(page_content="first")])
    llm.generate("context", AnswerOutput, FALLBACK, chunks=[Document(page_content="second")])
    assert len(provider.calls) == 2


def test_secret_is_absent_from_logs_and_cache_even_if_echoed(tmp_path):
    secret = "fake-test-credential"
    llm, provider, _ = service(tmp_path, [json.dumps({"answer": secret, "citations": []})])
    result = llm.generate("echo " + secret, AnswerOutput, FALLBACK)
    assert secret not in json.dumps(result)
    assert secret not in provider.calls[0][1]
    assert all(secret not in file.read_text() for file in tmp_path.rglob("*") if file.is_file())


@pytest.mark.parametrize("values,expected", [
    ({"anthropic_api_key": "fake-anthropic", "claude_model": "model-from-test-env"}, "anthropic"),
    ({"gemini_api_key": "fake-gemini", "gemini_model": "model-from-test-env"}, "gemini"),
    ({}, "none"),
    ({"llm_provider": "none", "gemini_api_key": "fake-gemini"}, "none"),
])
def test_provider_auto_selection_and_explicit_none(values, expected, tmp_path):
    config = {"llm_provider": "", "anthropic_api_key": "", "gemini_api_key": "", "claude_model": "", "gemini_model": "", **values}
    llm = LLMService(Settings(_env_file=None, **config), cache_dir=tmp_path, log_path=tmp_path / "usage")
    assert llm.name == expected


def test_missing_gemini_model_is_a_configuration_error():
    with pytest.raises(ValueError, match="GEMINI_MODEL"):
        LLMService(settings(gemini_model=""))


@pytest.mark.parametrize("model", ["display name", "Display", '"api-id"', "'api-id'", "models/api-id", "api\tid"])
def test_invalid_gemini_model_id_fails_during_settings_startup(model):
    with pytest.raises(ValueError, match="use the API model ID, not the display name"):
        settings(gemini_model=model)


def test_api_model_id_format_is_accepted():
    assert settings(gemini_model="api-model-id-1.0").gemini_model == "api-model-id-1.0"


def test_gemini_adapter_uses_official_json_schema_api_without_sdk_retries(monkeypatch):
    from google import genai
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text=ANSWER, usage_metadata=SimpleNamespace(prompt_token_count=17, candidates_token_count=8))
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(genai, "Client", factory)
    response = GeminiProvider("fake-test-credential").generate("model-from-test-env", "prompt", AnswerOutput, "system", 500)
    assert factory.call_args.kwargs["http_options"].retry_options.attempts == 1
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "model-from-test-env"
    assert kwargs["config"].response_mime_type == "application/json"
    assert kwargs["config"].response_schema is AnswerOutput
    assert response.input_tokens == 17


def test_anthropic_legacy_sdk_constructs_on_updated_httpx_without_network(monkeypatch):
    from anthropic.resources import Messages
    fake = SimpleNamespace(content=[SimpleNamespace(type="text", text=ANSWER)], usage=SimpleNamespace(input_tokens=17, output_tokens=8))
    create = MagicMock(return_value=fake)
    monkeypatch.setattr(Messages, "create", create)
    provider = AnthropicProvider("fake-test-credential")
    try:
        response = provider.generate("model-from-test-env", "prompt", AnswerOutput, "system", 500)
        assert provider._client.max_retries == 0
        assert create.call_args.kwargs["model"] == "model-from-test-env"
        assert response.output_tokens == 8
    finally:
        if provider._client:
            provider._client.close()


def test_registrar_provenance_and_model_card_are_gemini_labelled(tmp_path, monkeypatch):
    from argus.core.agents import registrar
    from argus.core.schemas import AISystemCreate
    result = json.dumps({"inferred_model_type": "other", "inferred_output_type": "binary_classification", "inferred_affected_demographics": [], "data_sensitivity": "MEDIUM", "model_card": "# Model card"})
    llm, _, _ = service(tmp_path, [result])
    monkeypatch.setattr(registrar, "get_llm", lambda _: llm)
    payload = AISystemCreate(name="Test", purpose="Evaluate credit applications for lending decisions", owner_team="Test")
    enriched, card = asyncio.run(registrar.RegistrarAgent(llm.settings).process(payload))
    assert enriched.llm_provider == "gemini" and enriched.llm_model == llm.model
    assert "LLM provider: gemini" in card and "Claude" not in card


def test_risk_classification_persists_grounding_and_provenance(tmp_path, monkeypatch):
    from argus.core.agents import risk_classifier
    doc = Document(page_content="Article 10 - Data", metadata={"section_type": "article", "article_number": 10})
    retriever = SimpleNamespace(has_corpus=lambda _: True, retrieve_for_classification=lambda *args, **kwargs: [doc], format_passages=lambda _: doc.page_content)
    monkeypatch.setattr(risk_classifier, "RegulatoryRetriever", lambda _: retriever)
    text = json.dumps({"risk_tier": "HIGH_RISK", "confidence": 0.8, "reasoning": "Data governance", "citations": [{"article": "Article 10"}, {"article": "Article 999"}], "obligations": ["Review data"]})
    llm, _, _ = service(tmp_path, [text])
    monkeypatch.setattr(risk_classifier, "get_llm", lambda _: llm)
    result = asyncio.run(risk_classifier.RiskClassifierAgent(llm.settings).classify("test", "Test", "Credit scoring", None, None, [], [], ["EU"]))
    stored = result.to_dict()["regulatory_citations"]["EU_AI_ACT"]
    assert stored["llm_provider"] == "gemini" and stored["llm_model"] == llm.model
    assert stored["needs_review"] and len(stored["citations"]) == 1
    assert result.llm_provider == "gemini"


def test_missing_framework_corpus_skips_llm_and_does_not_require_review(monkeypatch):
    from argus.core.agents import risk_classifier
    monkeypatch.setattr(risk_classifier, "RegulatoryRetriever", lambda _: SimpleNamespace(has_corpus=lambda _: False))
    monkeypatch.setattr(risk_classifier, "get_llm", lambda _: pytest.fail("No-corpus framework must not call the LLM"))
    result = asyncio.run(risk_classifier.RiskClassifierAgent(settings()).classify("test", "Test", "Credit scoring", None, None, [], [], ["IN"]))
    framework = result.regulatory_citations["RBI"]
    assert framework["status"] == "not_assessed_no_corpus"
    assert framework["risk_tier"] is None and framework["confidence"] is None
    assert not framework["citations"] and not framework["obligations"]
    assert not framework["needs_review"] and not result.needs_review
    assert result.overall_risk_tier == "UNCLASSIFIED"


@pytest.mark.parametrize("confidence,has_chunks,expected", [(0.69, True, ["confidence_below_0.7"]), (0.7, True, []), (0.95, False, ["no_retrieved_chunks"])])
def test_framework_review_reasons(tmp_path, monkeypatch, confidence, has_chunks, expected):
    from argus.core.agents import risk_classifier
    doc = Document(page_content="Article 6", metadata={"section_type": "article", "article_number": 6})
    retriever = SimpleNamespace(has_corpus=lambda framework: framework == "EU_AI_ACT", retrieve_for_classification=lambda *a, **kw: [doc] if has_chunks else [], format_passages=lambda _: doc.page_content)
    monkeypatch.setattr(risk_classifier, "RegulatoryRetriever", lambda _: retriever)
    llm, provider, _ = service(tmp_path, [json.dumps({"risk_tier": "MINIMAL_RISK", "confidence": confidence, "reasoning": "Assessment", "citations": [], "obligations": []})])
    monkeypatch.setattr(risk_classifier, "get_llm", lambda _: llm)
    result = asyncio.run(risk_classifier.RiskClassifierAgent(llm.settings).classify("test", "Test", "Email filtering", None, None, [], [], ["EU", "IN"]))
    assert result.regulatory_citations["EU_AI_ACT"]["needs_review_reasons"] == expected
    assert result.needs_review == bool(expected)


def test_no_key_registrar_remains_rule_based(tmp_path, monkeypatch):
    from argus.core.agents import registrar
    from argus.core.schemas import AISystemCreate
    llm = LLMService(Settings(_env_file=None, llm_provider="none", anthropic_api_key="", gemini_api_key=""), cache_dir=tmp_path, log_path=tmp_path / "usage")
    monkeypatch.setattr(registrar, "get_llm", lambda _: llm)
    payload = AISystemCreate(name="Test", purpose="Predict loan defaults using gradient boosting trees", owner_team="Test")
    enriched, _ = asyncio.run(registrar.RegistrarAgent(llm.settings).process(payload))
    assert enriched.llm_provider == "none" and enriched.llm_model is None
    assert enriched.model_type == "gradient_boosting"


def test_compliance_qa_sends_retrieved_chunks_and_records_provider(tmp_path, monkeypatch):
    from argus.api.routers import qa
    from argus.core.schemas import QARequest
    doc = Document(page_content="Article 14 - Human oversight", metadata={"section_type": "article", "article_number": 14, "citation": "Article 14"})
    monkeypatch.setattr(qa, "RegulatoryRetriever", lambda _: SimpleNamespace(retrieve=lambda *args, **kwargs: [doc]))
    text = json.dumps({"answer": "Use human oversight under Article 14.", "citations": [{"article": "Article 14"}, {"article": "Article 999"}]})
    llm, provider, _ = service(tmp_path, ['{"query_type":"compliance_query"}', text])
    monkeypatch.setattr(qa, "get_llm", lambda _: llm)
    result = asyncio.run(qa.answer_question(QARequest(question="What human oversight obligations apply?"), None, {"username": "test"}))
    assert result.llm_provider == "gemini" and result.llm_model == llm.model
    assert result.needs_review and len(result.citations) == 1
    assert "Article 14 - Human oversight" in provider.calls[1][1]


def test_regulatory_update_flags_citations_without_retrieved_sources(tmp_path, monkeypatch):
    from argus.core.agents import reg_propagation
    text = json.dumps({"framework": "EU_AI_ACT", "title": "Update", "summary": "Review oversight", "affected_articles": ["Article 14"], "urgency": "MEDIUM", "required_actions": ["Review"]})
    llm, _, _ = service(tmp_path, [text])
    monkeypatch.setattr(reg_propagation, "get_llm", lambda _: llm)
    result = asyncio.run(reg_propagation.RegPropagationAgent(llm.settings)._extract_update("Update text"))
    assert result["llm_provider"] == "gemini" and result["llm_model"] == llm.model
    assert result["needs_review"] and result["affected_articles"] == []
