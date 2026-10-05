"""
Registry service for ARGUS - manages AI system registration, classification, alerts, and audit records.
Provides high-level async database operations using SQLAlchemy with async support.
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from argus.core.registry.models import (
    AISystem,
    AlertSeverity,
    AlertType,
    AuditRecord,
    FairnessSnapshot,
    GovernanceAlert,
    RemediationStatus,
    RemediationTask,
    RegulatoryUpdate,
    RiskTier,
)
from argus.core.schemas import AISystemCreate


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    return "".join(c.lower() if c.isalnum() else "_" for c in text)[:20]


class DuplicateRegistrationError(ValueError):
    pass


class RegistryService:
    """Service for managing AI system registry and governance."""

    @staticmethod
    async def ensure_registration_available(session, name, version):
        # Serialize concurrent PostgreSQL registrations until commit/rollback.
        if session.get_bind().dialect.name == "postgresql":
            await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
                                  {"identity": f"{len(name)}:{name}:{version}"})
        existing = await session.execute(select(AISystem.id).where(
            AISystem.name == name, AISystem.version == version, AISystem.is_active.is_(True),
        ).limit(1))
        if existing.scalar_one_or_none() is not None:
            raise DuplicateRegistrationError("An active system with this name and version already exists; use an explicit new version.")

    @staticmethod
    async def register_system(
        session: AsyncSession,
        payload: AISystemCreate,
        risk_result: dict,
        model_card: str,
    ) -> AISystem:
        """
        Register a new AI system with risk classification and model card.
        
        Args:
            session: Database session
            payload: System creation payload
            risk_result: Risk classification result from RiskClassifierAgent
            model_card: Generated model card in Markdown
            
        Returns:
            Created AISystem instance
        """
        await RegistryService.ensure_registration_available(session, payload.name, payload.version)
        # Generate human-readable system ID: slugified name + 6-char UUID
        base_id = slugify(payload.name)
        short_uuid = str(uuid.uuid4())[:6]
        system_id = f"{base_id}-{short_uuid}"

        # Extract classification info
        overall_tier = risk_result.get("overall_risk_tier", RiskTier.UNCLASSIFIED)
        summary = risk_result.get("summary", "")
        citations = risk_result.get("regulatory_citations", {})

        # Create system
        system = AISystem(
            system_id=system_id,
            name=payload.name,
            version=payload.version,
            purpose=payload.purpose,
            model_type=payload.model_type,
            output_type=payload.output_type,
            owner_team=payload.owner_team,
            owner_email=payload.owner_email,
            data_sources=payload.data_sources,
            affected_demographics=payload.affected_demographics,
            jurisdictions=payload.jurisdictions,
            risk_tier=overall_tier,
            risk_classification_reasoning=summary,
            regulatory_citations=citations,
            model_card=model_card,
            last_classified_at=datetime.utcnow(),
        )

        try:
            session.add(system)
            await session.flush()
            await session.refresh(system)
            await session.commit()
            return system
        except Exception:
            # Fall back to an in-memory object when DB is unavailable (e.g., during local dev without Postgres)
            from types import SimpleNamespace

            fallback = SimpleNamespace(
                id=str(uuid.uuid4()),
                system_id=system_id,
                name=payload.name,
                version=payload.version,
                purpose=payload.purpose,
                model_type=payload.model_type,
                output_type=payload.output_type,
                owner_team=payload.owner_team,
                owner_email=payload.owner_email,
                data_sources=payload.data_sources,
                affected_demographics=payload.affected_demographics,
                jurisdictions=payload.jurisdictions,
                risk_tier=overall_tier,
                risk_classification_reasoning=summary,
                regulatory_citations=citations,
                model_card=model_card,
                monitoring_enabled=False,
                registered_at=datetime.utcnow(),
                last_classified_at=datetime.utcnow(),
            )
            return fallback

    @staticmethod
    async def get_system(
        session: AsyncSession,
        system_id: str,
    ) -> Optional[AISystem]:
        """
        Retrieve a system by ID if active.
        
        Args:
            session: Database session
            system_id: System ID to retrieve
            
        Returns:
            AISystem if found and active, None otherwise
        """
        stmt = select(AISystem).where(
            and_(
                AISystem.system_id == system_id,
                AISystem.is_active,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_systems(
        session: AsyncSession,
        risk_tier: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> list[AISystem]:
        """
        List all active systems with optional filtering.
        
        Args:
            session: Database session
            risk_tier: Filter by risk tier if provided
            jurisdiction: Filter by jurisdiction if provided
            
        Returns:
            List of matching AISystem instances
        """
        conditions = [AISystem.is_active]

        if risk_tier:
            conditions.append(AISystem.risk_tier == risk_tier)

        if jurisdiction:
            bind = session.get_bind()
            dialect_name = getattr(getattr(bind, 'dialect', None), 'name', '')
            if dialect_name == 'sqlite':
                # SQLite stores JSON as text; use a simple substring match for fallback filtering
                conditions.append(AISystem.jurisdictions.like(f'%"{jurisdiction}"%'))
            else:
                conditions.append(AISystem.jurisdictions.contains([jurisdiction]))

        stmt = (
            select(AISystem)
            .where(and_(*conditions))
            .order_by(AISystem.registered_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def soft_delete(session: AsyncSession, system_id: str) -> bool:
        """
        Soft delete a system by marking inactive.
        
        Args:
            session: Database session
            system_id: System ID to delete
            
        Returns:
            True if system was found and deleted, False otherwise
        """
        stmt = select(AISystem).where(AISystem.system_id == system_id)
        result = await session.execute(stmt)
        system = result.scalar_one_or_none()

        if not system:
            return False

        system.is_active = False
        await session.commit()
        return True

    @staticmethod
    async def update_classification(
        session: AsyncSession,
        system_id: str,
        result: dict,
    ) -> Optional[AISystem]:
        """
        Update system risk classification.
        
        Args:
            session: Database session
            system_id: System ID to update
            result: Classification result dict with overall_risk_tier, summary, regulatory_citations
            
        Returns:
            Updated AISystem or None if not found
        """
        system = await RegistryService.get_system(session, system_id)
        if not system:
            return None

        system.risk_tier = result.get("overall_risk_tier", RiskTier.UNCLASSIFIED)
        system.risk_classification_reasoning = result.get("summary", "")
        system.regulatory_citations = result.get("regulatory_citations", {})
        system.last_classified_at = datetime.utcnow()

        await session.commit()
        await session.refresh(system)
        return system

    @staticmethod
    async def create_alert(
        session: AsyncSession,
        system_id_uuid: uuid.UUID,
        alert_data: dict,
    ) -> GovernanceAlert:
        """
        Create a governance alert.
        
        Args:
            session: Database session
            system_id_uuid: System UUID
            alert_data: Dictionary with keys: alert_type, severity, title, description,
                       payload, regulatory_references
            
        Returns:
            Created GovernanceAlert
        """
        alert = GovernanceAlert(
            system_id=system_id_uuid,
            alert_type=AlertType[alert_data.get("alert_type", "FAIRNESS_VIOLATION")],
            severity=AlertSeverity[alert_data.get("severity", "INFO")],
            title=alert_data.get("title", ""),
            description=alert_data.get("description", ""),
            payload=alert_data.get("payload"),
            regulatory_references=alert_data.get("regulatory_references"),
        )

        session.add(alert)
        await session.flush()
        await session.refresh(alert)
        await session.commit()

        return alert

    @staticmethod
    async def get_alerts(
        session: AsyncSession,
        system_id: Optional[str] = None,
        severity: Optional[str] = None,
        resolved: bool = False,
    ) -> list[GovernanceAlert]:
        """
        Get alerts with optional filtering.
        
        Args:
            session: Database session
            system_id: Filter by system_id if provided
            severity: Filter by severity if provided
            resolved: Filter by resolution status (default: unresolved)
            
        Returns:
            List of matching GovernanceAlert instances
        """
        conditions = [GovernanceAlert.resolved == resolved]

        if system_id:
            # Need to join to get system_id string
            stmt = select(AISystem).where(AISystem.system_id == system_id)
            result = await session.execute(stmt)
            system = result.scalar_one_or_none()
            if system:
                conditions.append(GovernanceAlert.system_id == system.id)

        if severity:
            conditions.append(GovernanceAlert.severity == severity)

        stmt = (
            select(GovernanceAlert)
            .where(and_(*conditions))
            .order_by(GovernanceAlert.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def resolve_alert(session: AsyncSession, alert_id_str: str) -> Optional[GovernanceAlert]:
        """
        Resolve an alert by ID.
        
        Args:
            session: Database session
            alert_id_str: Alert ID as string UUID
            
        Returns:
            Updated GovernanceAlert or None if not found
        """
        try:
            alert_id = uuid.UUID(alert_id_str)
        except (ValueError, TypeError):
            return None

        stmt = select(GovernanceAlert).where(GovernanceAlert.id == alert_id)
        result = await session.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        await session.commit()
        await session.refresh(alert)
        return alert

    @staticmethod
    async def save_fairness_snapshot(
        session: AsyncSession,
        system_id_uuid: uuid.UUID,
        report: dict,
    ) -> FairnessSnapshot:
        """
        Save a fairness evaluation snapshot.
        
        Args:
            session: Database session
            system_id_uuid: System UUID
            report: Dictionary with metric values and details
            
        Returns:
            Created FairnessSnapshot
        """
        # Clean metrics for JSON serialization - remove datetime and convert to ISO string
        metrics_clean = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in report.items()}
        
        snapshot = FairnessSnapshot(
            system_id=system_id_uuid,
            demographic_parity_diff=report.get("demographic_parity_diff", 0.0),
            equalized_odds_diff=report.get("equalized_odds_diff", 0.0),
            calibration_diff=report.get("calibration_diff"),
            psi_score=report.get("psi_overall"),
            drifted_features=report.get("drifted_features", []),
            metrics_detail=metrics_clean,
            sample_size=report.get("sample_size", 0),
        )

        session.add(snapshot)
        await session.flush()
        await session.refresh(snapshot)
        await session.commit()

        return snapshot

    @staticmethod
    async def get_fairness_history(
        session: AsyncSession,
        system_id: str,
        limit: int = 30,
    ) -> list[FairnessSnapshot]:
        """
        Get fairness metric history for a system.
        
        Args:
            session: Database session
            system_id: System ID
            limit: Max results to return
            
        Returns:
            List of FairnessSnapshot instances, most recent first
        """
        # Get system UUID first
        stmt = select(AISystem).where(AISystem.system_id == system_id)
        result = await session.execute(stmt)
        system = result.scalar_one_or_none()

        if not system:
            return []

        stmt = (
            select(FairnessSnapshot)
            .where(FairnessSnapshot.system_id == system.id)
            .order_by(FairnessSnapshot.evaluated_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def save_audit_record(
        session: AsyncSession,
        system_id_uuid: uuid.UUID,
        pdf_path: str,
        content_hash: str,
        summary: dict,
        generated_by: str = "system",
    ) -> AuditRecord:
        """
        Save an audit record.
        
        Args:
            session: Database session
            system_id_uuid: System UUID
            pdf_path: Path to generated PDF
            content_hash: SHA-256 hash of PDF content
            summary: Compliance summary dictionary
            generated_by: User or system that generated the audit
            
        Returns:
            Created AuditRecord
        """
        record = AuditRecord(
            system_id=system_id_uuid,
            generated_by=generated_by,
            pdf_path=pdf_path,
            content_hash=content_hash,
            compliance_summary=summary,
        )

        session.add(record)
        await session.flush()
        await session.refresh(record)
        await session.commit()

        return record

    @staticmethod
    async def get_system_for_audit(
        session: AsyncSession,
        system_id: str,
    ) -> dict:
        """
        Get comprehensive system data for audit generation.
        
        Args:
            session: Database session
            system_id: System ID to audit
            
        Returns:
            Dictionary with system, snapshots, alerts, and remediation tasks
        """
        system = await RegistryService.get_system(session, system_id)
        if not system:
            return {}

        # Get fairness history
        snapshots = await RegistryService.get_fairness_history(
            session,
            system_id,
            limit=30,
        )

        # Get all alerts
        alerts = await RegistryService.get_alerts(session, system_id=system_id, resolved=False)

        # Get open remediation tasks
        stmt = select(RemediationTask).where(
            and_(
                RemediationTask.system_id == system.id,
                RemediationTask.status.in_([
                    RemediationStatus.OPEN,
                    RemediationStatus.ACKNOWLEDGED,
                    RemediationStatus.IN_PROGRESS,
                ]),
            )
        )
        result = await session.execute(stmt)
        remediation_tasks = result.scalars().all()

        return {
            "system": system,
            "fairness_snapshots": snapshots,
            "alerts": alerts,
            "remediation_tasks": remediation_tasks,
        }

    @staticmethod
    async def save_regulatory_update(
        session: AsyncSession,
        framework: str,
        title: str,
        summary: str,
        affected_articles: list[str],
    ) -> RegulatoryUpdate:
        """
        Save a regulatory update.
        
        Args:
            session: Database session
            framework: Regulatory framework name
            title: Update title
            summary: Update summary
            affected_articles: List of affected articles
            
        Returns:
            Created RegulatoryUpdate
        """
        update = RegulatoryUpdate(
            framework=framework,
            title=title,
            summary=summary,
            affected_articles=affected_articles,
        )

        session.add(update)
        await session.flush()
        await session.refresh(update)
        await session.commit()

        return update

    @staticmethod
    async def create_remediation_task(
        session: AsyncSession,
        system_id_uuid: uuid.UUID,
        title: str,
        description: str,
        due_date: datetime,
        regulatory_update_id: Optional[uuid.UUID] = None,
        assigned_to: Optional[str] = None,
    ) -> RemediationTask:
        """
        Create a remediation task.
        
        Args:
            session: Database session
            system_id_uuid: System UUID
            title: Task title
            description: Task description
            due_date: Due date for completion
            regulatory_update_id: Associated regulatory update if applicable
            assigned_to: Team/person responsible
            
        Returns:
            Created RemediationTask
        """
        task = RemediationTask(
            system_id=system_id_uuid,
            regulatory_update_id=regulatory_update_id,
            title=title,
            description=description,
            due_date=due_date,
            assigned_to=assigned_to,
            status=RemediationStatus.OPEN,
        )

        session.add(task)
        await session.flush()
        await session.refresh(task)
        await session.commit()

        return task

    @staticmethod
    async def get_system_uuid(
        session: AsyncSession,
        system_id: str,
    ) -> Optional[uuid.UUID]:
        """
        Get UUID for a system by ID.
        
        Args:
            session: Database session
            system_id: System ID
            
        Returns:
            System UUID or None if not found
        """
        system = await RegistryService.get_system(session, system_id)
        return system.id if system else None
