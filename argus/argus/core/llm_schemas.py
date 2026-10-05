"""Schemas validated before any generated result is used or cached."""
from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    article: str
    title: str = ""
    excerpt: str = ""
    annex: str | None = None
    point: str | None = None


class RegistrationOutput(BaseModel):
    inferred_model_type: Literal["gradient_boosting", "neural_network", "random_forest", "regression", "nlp", "computer_vision", "rule_based", "other"]
    inferred_output_type: Literal["binary_classification", "multiclass", "regression", "ranking", "generation", "other"]
    inferred_affected_demographics: list[str]
    data_sensitivity: Literal["HIGH", "MEDIUM", "LOW"]
    model_card: str


class ClassificationOutput(BaseModel):
    risk_tier: Literal["PROHIBITED", "HIGH_RISK", "LIMITED_RISK", "MINIMAL_RISK", "UNCLASSIFIED", "TIER_1_CRITICAL", "TIER_2_MEDIUM", "TIER_3_LOW"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    citations: list[Citation]
    obligations: list[str]


class AnswerOutput(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)


class QueryTypeOutput(BaseModel):
    query_type: Literal["registry_query", "compliance_query", "alert_query", "general"]


class UpdateOutput(BaseModel):
    framework: Literal["EU_AI_ACT", "RBI", "DPDP", "EBA", "OTHER"]
    title: str
    summary: str
    affected_articles: list[str]
    urgency: Literal["HIGH", "MEDIUM", "LOW"]
    required_actions: list[str]


class AffectedSystemsOutput(BaseModel):
    system_ids: list[str]
