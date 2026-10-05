"""
Pydantic models for request/response validation in ARGUS API.
Provides type safety and automatic OpenAPI documentation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class AISystemCreate(BaseModel):
    """Request schema for registering a new AI system."""
    llm_provider: str = "none"
    llm_model: Optional[str] = None
    needs_review: bool = True
    name: str = Field(..., min_length=1, max_length=255, description="System name")
    version: str = Field(
        default="1.0.0",
        max_length=50,
        description="System version identifier",
    )
    purpose: str = Field(
        ...,
        min_length=20,
        description="Detailed purpose and use case of the AI system",
    )
    model_type: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Type of model: gradient_boosting, neural_network, etc.",
    )
    output_type: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Output type: binary_classification, regression, etc.",
    )
    owner_team: str = Field(
        ...,
        max_length=255,
        description="Team responsible for the system",
    )
    owner_email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Email of system owner or maintainer",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="List of data source names or identifiers",
    )
    affected_demographics: list[str] = Field(
        default_factory=list,
        description="Demographic groups potentially affected by system",
    )
    jurisdictions: list[str] = Field(
        default_factory=lambda: ["EU"],
        description="Applicable jurisdictions: EU, IN, etc.",
    )
    prediction_endpoint: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL of the prediction endpoint for monitoring",
    )


class EvaluationRequest(BaseModel):
    """Request schema for fairness and drift evaluation."""
    system_id: str = Field(..., description="System ID to evaluate")
    y_true: list[int] = Field(..., description="Ground truth labels (0/1)")
    y_pred: list[int] = Field(..., description="Binary predictions (0/1)")
    y_proba: list[float] = Field(..., description="Predicted probabilities [0-1]")
    sensitive_feature_name: str = Field(
        ...,
        description="Name of the sensitive feature (e.g., age_group)",
    )
    sensitive_feature_values: list[str] = Field(
        ...,
        description="Values of sensitive feature for each sample",
    )
    reference_data: list[dict] = Field(
        ...,
        description="Reference/training distribution sample",
    )
    current_data: list[dict] = Field(
        ...,
        description="Current production batch for drift detection",
    )


class AuditRequest(BaseModel):
    """Request schema for audit dossier generation."""
    system_id: str = Field(..., description="System ID to audit")
    requested_by: str = Field(
        default="system",
        description="User or system requesting the audit",
    )


class QARequest(BaseModel):
    """Request schema for governance Q&A."""
    question: str = Field(..., min_length=5, description="Governance question")


class AlertResolveRequest(BaseModel):
    """Request schema for resolving an alert."""
    resolved_by: str = Field(
        default="user",
        description="User or system resolving the alert",
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class CitationSchema(BaseModel):
    """Citation from regulatory document."""
    article: str = Field(..., description="Article/section reference")
    title: str = Field(..., description="Title of the provision")
    excerpt: str = Field(..., description="Relevant excerpt from the text")

    model_config = {"from_attributes": True}


class FrameworkClassification(BaseModel):
    """Classification result for a single regulatory framework."""
    llm_provider: str = "none"
    llm_model: Optional[str] = None
    needs_review: bool = True
    needs_review_reasons: list[str] = Field(default_factory=list)
    status: str = "assessed"
    framework: str = Field(..., description="Framework name: EU_AI_ACT, RBI, etc.")
    risk_tier: Optional[str] = Field(..., description="Risk tier classification")
    confidence: Optional[float] = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Detailed reasoning for classification")
    citations: list[CitationSchema] = Field(..., description="Supporting regulatory citations")
    exclusions_checked: list[CitationSchema] = Field(default_factory=list)
    obligations: list[str] = Field(..., description="Regulatory obligations")

    model_config = {"from_attributes": True}


class AISystemResponse(BaseModel):
    """Full AI system detail response."""
    llm_provider: str = "none"
    status: str = 'assessed'
    llm_model: Optional[str] = None
    needs_review: bool = True
    needs_review_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def classification_provenance(self):
        entries = [item for item in (self.regulatory_citations or {}).values() if item.get("status", "assessed") in ('assessed','context_incomplete')]
        if any(item.get('status')=='context_incomplete' for item in entries):
            self.status='context_incomplete'
        if entries and not any(item.get('status','assessed')=='assessed' for item in entries):
            self.risk_tier = None
        producers = {(item.get("llm_provider", "none"), item.get("llm_model")) for item in entries}
        if len(producers) == 1:
            self.llm_provider, self.llm_model = next(iter(producers))
        elif producers:
            self.llm_provider, self.llm_model = "mixed", None
        self.needs_review_reasons = sorted({reason for item in entries for reason in item.get("needs_review_reasons", [])})
        self.needs_review = bool(self.needs_review_reasons)
        return self
    id: str = Field(..., description="System UUID")
    system_id: str = Field(..., description="Human-readable system ID")
    name: str = Field(..., description="System name")
    version: str = Field(..., description="System version")
    purpose: str = Field(..., description="System purpose")
    model_type: Optional[str] = Field(..., description="Model type")
    output_type: Optional[str] = Field(..., description="Output type")
    owner_team: str = Field(..., description="Owner team")
    owner_email: Optional[str] = Field(..., description="Owner email")
    data_sources: list[str] = Field(..., description="Data sources")
    affected_demographics: list[str] = Field(..., description="Affected demographics")
    jurisdictions: list[str] = Field(..., description="Applicable jurisdictions")
    risk_tier: Optional[str] = Field(..., description="Current risk tier; null when the classification context is incomplete")
    risk_classification_reasoning: Optional[str] = Field(
        ...,
        description="Reasoning for risk classification",
    )
    regulatory_citations: Optional[dict] = Field(..., description="Regulatory citations")
    model_card: Optional[str] = Field(..., description="Generated model card in Markdown")
    monitoring_enabled: bool = Field(..., description="Whether monitoring is enabled")
    registered_at: datetime = Field(..., description="Registration timestamp")
    last_classified_at: Optional[datetime] = Field(
        ...,
        description="Last classification timestamp",
    )

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_to_str(cls, v):
        return str(v) if v else None


class AISystemSummary(BaseModel):
    """Compact AI system list view."""
    system_id: str = Field(..., description="System ID")
    name: str = Field(..., description="System name")
    risk_tier: str = Field(..., description="Risk tier")
    owner_team: str = Field(..., description="Owner team")
    jurisdictions: list[str] = Field(..., description="Jurisdictions")
    monitoring_enabled: bool = Field(..., description="Monitoring status")
    registered_at: datetime = Field(..., description="Registration date")

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    """Governance alert response."""
    id: str = Field(..., description="Alert UUID")
    system_id: str = Field(..., description="Associated system ID")
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Severity level")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    payload: Optional[dict] = Field(..., description="Structured alert data")
    regulatory_references: Optional[list[str]] = Field(
        ...,
        description="Regulatory references",
    )
    resolved: bool = Field(..., description="Resolution status")
    resolved_at: Optional[datetime] = Field(..., description="Resolution timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}
    
    @field_validator("id", "system_id", mode="before")
    def convert_id_to_str(cls, v):
        return str(v) if v else None


class ViolationSchema(BaseModel):
    """Fairness or drift violation."""
    metric: str = Field(..., description="Metric name")
    value: float = Field(..., description="Measured value")
    threshold: float = Field(..., description="Threshold value")
    severity: str = Field(..., description="Severity level")
    regulatory_reference: str = Field(..., description="Relevant regulation")

    model_config = {"from_attributes": True}


class FairnessSnapshotResponse(BaseModel):
    """Fairness metrics snapshot."""
    id: str = Field(..., description="Snapshot UUID")
    system_id: str = Field(..., description="System ID")
    demographic_parity_diff: float = Field(..., description="Demographic parity difference")
    equalized_odds_diff: float = Field(..., description="Equalized odds difference")
    psi_score: Optional[float] = Field(..., description="Population Stability Index")
    drifted_features: list[str] = Field(..., description="Features with detected drift")
    sample_size: int = Field(..., description="Number of samples evaluated")
    evaluated_at: datetime = Field(..., description="Evaluation timestamp")

    model_config = {"from_attributes": True}
    
    @field_validator("id", "system_id", mode="before")
    def convert_id_to_str(cls, v):
        return str(v) if v else None


class EvaluationResponse(BaseModel):
    """Evaluation result with metrics and violations."""
    system_id: str = Field(..., description="System ID")
    snapshot: FairnessSnapshotResponse = Field(..., description="Fairness metrics snapshot")
    violations: list[ViolationSchema] = Field(..., description="Detected violations")
    alerts_created: int = Field(..., description="Number of alerts created")
    summary: str = Field(..., description="Summary of evaluation results")

    model_config = {"from_attributes": True}


class AuditRecordResponse(BaseModel):
    """Audit record response."""
    id: str = Field(..., description="Record UUID")
    system_id: str = Field(..., description="System ID")
    generated_by: str = Field(..., description="Generated by user/system")
    pdf_path: str = Field(..., description="Path to generated PDF")
    content_hash: Optional[str] = Field(..., description="SHA-256 hash of PDF")
    compliance_summary: Optional[dict] = Field(..., description="Compliance checklist")
    generated_at: datetime = Field(..., description="Generation timestamp")

    model_config = {"from_attributes": True}


class QAResponse(BaseModel):
    """Q&A response with sources."""
    llm_provider: str = "none"
    llm_model: Optional[str] = None
    needs_review: bool = True
    citations: list[dict] = Field(default_factory=list)
    answer: str = Field(..., description="Answer to the question")
    sources: list[str] = Field(..., description="Source references")
    query_type: str = Field(..., description="Classified query type")

    model_config = {"from_attributes": True}


class SystemStats(BaseModel):
    """System statistics for dashboard."""
    total_systems: int = Field(..., description="Total registered systems")
    high_risk_count: int = Field(..., description="Count of high-risk systems")
    critical_alerts_count: int = Field(..., description="Active critical alerts")
    pending_audits: int = Field(..., description="Audits due soon")

    model_config = {"from_attributes": True}


class ComplianceSummary(BaseModel):
    """Compliance status summary."""
    system_id: str = Field(..., description="System ID")
    risk_tier: str = Field(..., description="Risk tier")
    compliance_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Compliance percentage",
    )
    checks_passed: int = Field(..., description="Number of passing checks")
    checks_failed: int = Field(..., description="Number of failing checks")
    open_alerts: int = Field(..., description="Count of open alerts")
    open_remediation_tasks: int = Field(..., description="Count of open remediation tasks")

    model_config = {"from_attributes": True}
