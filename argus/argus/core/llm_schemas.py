"""Schemas validated before any generated result is used or cached."""
from typing import Literal

import re
from pydantic import BaseModel, Field, model_validator


class Citation(BaseModel):
    article: str
    title: str = ""
    excerpt: str = ""
    annex: str | None = None
    point: str | None = None
    citation_role: Literal["supporting", "exclusion_checked"] = "supporting"


class SupportingCitation(Citation):
    paragraph: str | None = Field(..., description='Explicit article paragraph number, or null if unknown/not applicable')
    point: str | None = Field(..., description='Explicit lettered article point or Annex point, or null with incomplete_reason for Articles 5/50')
    incomplete_reason: str | None = Field(..., description='Explain any null paragraph or point for supporting Articles 5/50; Article 50 paragraphs without lettered points may say not applicable')

    @model_validator(mode='after')
    def explicit_article_identity(self):
        own = re.match(r'^\s*(?:Article\s+)?(5|50)(?:\b|\()', self.article, re.I)
        if own and self.citation_role != 'exclusion_checked':
            if self.paragraph is not None and not self.paragraph.isdigit():
                raise ValueError('Article paragraph must be an explicit number or null')
            if own[1]=='5' and self.point is not None and not re.fullmatch(r'[a-h]',self.point,re.I):
                raise ValueError('Article 5 point must be one explicit letter a-h or null')
            if (self.paragraph is None or self.point is None) and not (self.incomplete_reason or '').strip():
                raise ValueError('Supporting Article 5/50 needs paragraph and point, or null with incomplete_reason')
        return self


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
    citations: list[SupportingCitation]
    exclusions_checked: list[Citation] = Field(default_factory=list, description="Provisions checked and excluded, rather than supporting the assigned tier")
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
