"""
SQLAlchemy ORM models for ARGUS registry and governance system.
Defines the complete data model including AI systems, alerts, fairness snapshots, regulatory updates, and audit records.
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


# ============================================================================
# ENUMS
# ============================================================================

class RiskTier(str, enum.Enum):
    """Risk classification tiers per EU AI Act."""
    PROHIBITED = "PROHIBITED"
    HIGH_RISK = "HIGH_RISK"
    LIMITED_RISK = "LIMITED_RISK"
    MINIMAL_RISK = "MINIMAL_RISK"
    UNCLASSIFIED = "UNCLASSIFIED"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertType(str, enum.Enum):
    """Types of governance alerts."""
    FAIRNESS_VIOLATION = "FAIRNESS_VIOLATION"
    INPUT_DRIFT = "INPUT_DRIFT"
    OUTPUT_DRIFT = "OUTPUT_DRIFT"
    REGULATORY_CHANGE = "REGULATORY_CHANGE"
    AUDIT_DUE = "AUDIT_DUE"


class RemediationStatus(str, enum.Enum):
    """Status of remediation tasks."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"


# ============================================================================
# MODELS
# ============================================================================

class AISystem(Base):
    """
    Core AI system registry. Tracks every AI system governed by ARGUS.
    Primary entity linking to alerts, fairness snapshots, remediation tasks, and audit records.
    """
    __tablename__ = "ai_systems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    system_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    purpose: Mapped[str] = mapped_column(Text)
    model_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    output_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_team: Mapped[str] = mapped_column(String(255))
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data_sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    affected_demographics: Mapped[list[str]] = mapped_column(JSON, default=list)
    jurisdictions: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["EU"])
    risk_tier: Mapped[RiskTier] = mapped_column(
        Enum(RiskTier),
        default=RiskTier.UNCLASSIFIED,
    )
    risk_classification_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    regulatory_citations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    model_card: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_classified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    prediction_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    alerts: Mapped[list["GovernanceAlert"]] = relationship(
        back_populates="system",
        cascade="all, delete-orphan",
    )
    fairness_snapshots: Mapped[list["FairnessSnapshot"]] = relationship(
        back_populates="system",
        cascade="all, delete-orphan",
    )
    remediation_tasks: Mapped[list["RemediationTask"]] = relationship(
        back_populates="system",
        cascade="all, delete-orphan",
    )
    audit_records: Mapped[list["AuditRecord"]] = relationship(
        back_populates="system",
        cascade="all, delete-orphan",
    )


class GovernanceAlert(Base):
    """
    Governance alerts triggered by fairness violations, drift, regulatory changes, or audit requirements.
    """
    __tablename__ = "governance_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_systems.id"),
        index=True,
    )
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), index=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    regulatory_references: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    system: Mapped[AISystem] = relationship(back_populates="alerts")


class FairnessSnapshot(Base):
    """
    Historical snapshot of fairness metrics for an AI system at a point in time.
    Used for tracking fairness and drift over time.
    """
    __tablename__ = "fairness_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_systems.id"),
        index=True,
    )
    demographic_parity_diff: Mapped[float] = mapped_column(Float)
    equalized_odds_diff: Mapped[float] = mapped_column(Float)
    calibration_diff: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    psi_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    drifted_features: Mapped[list[str]] = mapped_column(JSON, default=list)
    metrics_detail: Mapped[dict] = mapped_column(JSON)
    sample_size: Mapped[int] = mapped_column(Integer)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    system: Mapped[AISystem] = relationship(back_populates="fairness_snapshots")


class RegulatoryUpdate(Base):
    """
    Regulatory updates from external sources (EU AI Act amendments, RBI guidance, etc.).
    Used to trigger regulatory propagation and remediation task creation.
    """
    __tablename__ = "regulatory_updates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    framework: Mapped[str] = mapped_column(String(100), index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    affected_articles: Mapped[list[str]] = mapped_column(JSON)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    remediation_tasks: Mapped[list["RemediationTask"]] = relationship(
        back_populates="regulatory_update",
        cascade="all, delete-orphan",
    )


class RemediationTask(Base):
    """
    Remediation tasks created to address fairness violations, drift, or regulatory requirements.
    Tracks assignment, status, and resolution.
    """
    __tablename__ = "remediation_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_systems.id"),
        index=True,
    )
    regulatory_update_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regulatory_updates.id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[RemediationStatus] = mapped_column(
        Enum(RemediationStatus),
        default=RemediationStatus.OPEN,
        index=True,
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    system: Mapped[AISystem] = relationship(back_populates="remediation_tasks")
    regulatory_update: Mapped[Optional[RegulatoryUpdate]] = relationship(
        back_populates="remediation_tasks"
    )


class AuditRecord(Base):
    """
    Generated audit dossiers for compliance documentation.
    Stores PDF path, content hash, and compliance summary for traceability.
    """
    __tablename__ = "audit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_systems.id"),
        index=True,
    )
    generated_by: Mapped[str] = mapped_column(String(200))
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    compliance_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    system: Mapped[AISystem] = relationship(back_populates="audit_records")
