"""
Monitoring router - fairness and drift evaluation endpoints.
Handles system monitoring, alert management, and compliance status.
"""
import logging
import traceback
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from argus.api.deps import get_session, get_current_user
from argus.core.agents.drift_monitor import DriftFairnessMonitor
from argus.core.registry.models import GovernanceAlert
from argus.core.registry.service import RegistryService
from argus.core.schemas import (
    AlertResponse,
    AlertResolveRequest,
    ComplianceSummary,
    EvaluationRequest,
    EvaluationResponse,
    FairnessSnapshotResponse,
    ViolationSchema,
)
from argus.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize drift monitor
drift_monitor = DriftFairnessMonitor(settings)


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_system(
    request: EvaluationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Run fairness and drift evaluation for a system.
    
    Evaluates:
    - Demographic parity across sensitive groups
    - Equalized odds (error rate fairness)
    - Population Stability Index (PSI) for drift detection
    - Calibration differences across groups
    
    Creates alerts for any violations detected.
    
    Args:
        request: EvaluationRequest with predictions and data
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        EvaluationResponse with metrics and violations
        
    Raises:
        HTTPException: 404 if system not found or 400 if data invalid
    """
    try:
        # Verify system exists
        system_uuid = await RegistryService.get_system_uuid(session, request.system_id)
        if not system_uuid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System not found: {request.system_id}",
            )

        logger.info(f"Starting evaluation for {request.system_id}")

        # Convert data to arrays
        y_true = np.array(request.y_true, dtype=int)
        y_pred = np.array(request.y_pred, dtype=int)
        y_proba = np.array(request.y_proba, dtype=float)

        # Validate data
        if len(y_true) != len(y_pred) or len(y_pred) != len(y_proba):
            raise ValueError("Length mismatch in y_true, y_pred, y_proba")

        # Run evaluation
        report = drift_monitor.evaluate(
            system_id=request.system_id,
            y_true=y_true.tolist(),
            y_pred=y_pred.tolist(),
            y_proba=y_proba.tolist(),
            sensitive_feature_name=request.sensitive_feature_name,
            sensitive_feature_values=request.sensitive_feature_values,
            reference_data=request.reference_data,
            current_data=request.current_data,
        )

        # Save snapshot
        snapshot = await RegistryService.save_fairness_snapshot(
            session,
            system_uuid,
            {
                "demographic_parity_diff": report.demographic_parity_diff,
                "equalized_odds_diff": report.equalized_odds_diff,
                "calibration_diff": report.calibration_diff,
                "psi_overall": report.psi_overall,
                "psi_per_feature": report.psi_per_feature,
                "drifted_features": report.drifted_features,
                "sample_size": report.sample_size,
                "evaluated_at": report.evaluated_at,
            },
        )

        # Create alerts for violations
        alerts_created = 0
        for violation in report.violations:
            await RegistryService.create_alert(
                session,
                system_uuid,
                {
                    "alert_type": "FAIRNESS_VIOLATION" if violation.violation_type == "FAIRNESS" else "INPUT_DRIFT",
                    "severity": violation.severity,
                    "title": f"{violation.metric.replace('_', ' ').title()} Violation",
                    "description": violation.description,
                    "payload": {
                        "metric": violation.metric,
                        "value": violation.value,
                        "threshold": violation.threshold,
                        "affected_feature": violation.affected_feature,
                    },
                    "regulatory_references": [violation.regulatory_reference],
                },
            )
            alerts_created += 1

        logger.info(f"Evaluation complete: {alerts_created} alerts created")

        # Build response
        snapshot_response = FairnessSnapshotResponse.model_validate(snapshot)
        violations_response = [
            ViolationSchema(
                metric=v.metric,
                value=v.value,
                threshold=v.threshold,
                severity=v.severity,
                regulatory_reference=v.regulatory_reference,
            )
            for v in report.violations
        ]

        return EvaluationResponse(
            system_id=request.system_id,
            snapshot=snapshot_response,
            violations=violations_response,
            alerts_created=alerts_created,
            summary=f"Evaluated {len(y_true)} samples. DP: {report.demographic_parity_diff:.4f}, "
                   f"EO: {report.equalized_odds_diff:.4f}, PSI: {report.psi_overall:.4f}",
        )

    except ValueError as e:
        logger.error(f"Invalid evaluation data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evaluation failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.get("/systems/{system_id}/snapshots", response_model=list[FairnessSnapshotResponse])
async def get_fairness_snapshots(
    system_id: str,
    limit: int = 30,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get fairness metric history for a system.
    
    Args:
        system_id: System ID
        limit: Maximum results to return
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        List of FairnessSnapshotResponse ordered by date (most recent first)
    """
    try:
        snapshots = await RegistryService.get_fairness_history(session, system_id, limit=limit)
        return [FairnessSnapshotResponse.model_validate(s) for s in snapshots]
    except Exception as e:
        logger.error(f"Failed to retrieve snapshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve snapshots",
        )


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    system_id: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: bool = False,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get governance alerts with optional filtering.
    
    Args:
        system_id: Filter by system ID
        severity: Filter by severity (INFO, WARNING, CRITICAL)
        resolved: Show resolved alerts if True, unresolved if False
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        List of AlertResponse objects
    """
    try:
        alerts = await RegistryService.get_alerts(
            session,
            system_id=system_id,
            severity=severity,
            resolved=resolved,
        )
        return [AlertResponse.model_validate(a) for a in alerts]
    except Exception as e:
        logger.error(f"Failed to retrieve alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts",
        )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get a specific alert by ID.
    
    Args:
        alert_id: Alert UUID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        AlertResponse for the alert
        
    Raises:
        HTTPException: 404 if alert not found
    """
    try:
        try:
            alert_uuid = uuid.UUID(alert_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid alert ID format",
            )

        result = await session.execute(
            select(GovernanceAlert).where(GovernanceAlert.id == alert_uuid)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert not found: {alert_id}",
            )
        return AlertResponse.model_validate(alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert",
        )


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    request: AlertResolveRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Mark an alert as resolved.
    
    Args:
        alert_id: Alert UUID
        request: Resolve request with resolved_by field
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated AlertResponse
        
    Raises:
        HTTPException: 404 if alert not found
    """
    try:
        alert = await RegistryService.resolve_alert(session, alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert not found: {alert_id}",
            )
        logger.info(f"Alert resolved: {alert_id} (by {request.resolved_by})")
        return AlertResponse.model_validate(alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert",
        )


@router.get("/systems/{system_id}/compliance", response_model=ComplianceSummary)
async def get_compliance_status(
    system_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get compliance status summary for a system.
    
    Args:
        system_id: System ID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        ComplianceSummary with compliance metrics
        
    Raises:
        HTTPException: 404 if system not found
    """
    try:
        system = await RegistryService.get_system(session, system_id)
        if not system:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System not found: {system_id}",
            )

        # Get alerts and tasks
        alerts = await RegistryService.get_alerts(session, system_id=system_id, resolved=False)
        
        # Count open vs resolved alerts
        open_alerts = len([a for a in alerts if not a.resolved])

        # Simple compliance score: 100 - (critical_alerts * 25 + warning_alerts * 10)
        critical_count = len([a for a in alerts if a.severity.value == "CRITICAL"])
        warning_count = len([a for a in alerts if a.severity.value == "WARNING"])
        compliance_score = max(0, 100 - (critical_count * 25 + warning_count * 10))

        # Check remediation tasks
        audit_data = await RegistryService.get_system_for_audit(session, system_id)
        remediation_tasks = audit_data.get("remediation_tasks", [])
        open_tasks = len([t for t in remediation_tasks if t.status.value in ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]])

        return ComplianceSummary(
            system_id=system_id,
            risk_tier=system.risk_tier.value,
            compliance_score=compliance_score,
            checks_passed=max(0, 10 - critical_count - warning_count),
            checks_failed=critical_count + warning_count,
            open_alerts=open_alerts,
            open_remediation_tasks=open_tasks,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get compliance status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve compliance status",
        )
