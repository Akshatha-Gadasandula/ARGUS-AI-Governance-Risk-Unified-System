"""
Registry router - AI system registration and management endpoints.
Handles system intake, classification, and model card generation.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_session, get_current_user
from argus.core.agents.registrar import RegistrarAgent
from argus.core.agents.risk_classifier import RiskClassifierAgent
from argus.core.registry.service import RegistryService
from argus.core.schemas import (
    AISystemCreate,
    AISystemResponse,
    AISystemSummary,
)
from argus.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Agents will be instantiated lazily to avoid heavy imports at module import time
registrar_agent = None
risk_classifier_agent = None


@router.post("/systems", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
async def register_system(
    payload: AISystemCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Register a new AI system with full governance workflow.
    
    1. Registers system via Registrar Agent (metadata extraction + model card generation)
    2. Classifies system risk under applicable frameworks via Risk Classifier Agent
    3. Stores complete system record in database
    
    Args:
        payload: System creation request
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        AISystemResponse with full system details
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        logger.info(f"Registering system: {payload.name} (by {current_user['username']})")

        # Step 1: Run Registrar Agent (enrich metadata + generate model card)
        global registrar_agent
        if registrar_agent is None:
            registrar_agent = RegistrarAgent(settings)

        enriched_payload, model_card = await registrar_agent.process(payload)
        logger.info(f"Registrar enrichment complete for {payload.name}")

        # Step 2: Run Risk Classifier Agent
        global risk_classifier_agent
        if risk_classifier_agent is None:
            risk_classifier_agent = RiskClassifierAgent(settings)

        classification_result = await risk_classifier_agent.classify(
            system_id=enriched_payload.name,
            name=enriched_payload.name,
            purpose=enriched_payload.purpose,
            model_type=enriched_payload.model_type,
            output_type=enriched_payload.output_type,
            data_sources=enriched_payload.data_sources,
            affected_demographics=enriched_payload.affected_demographics,
            jurisdictions=enriched_payload.jurisdictions,
        )
        logger.info(f"Risk classification complete: {classification_result.overall_risk_tier}")

        # Step 3: Save to database
        system = await RegistryService.register_system(
            session,
            enriched_payload,
            classification_result.to_dict(),
            model_card,
        )
        logger.info(f"System registered: {system.system_id}")

        # Convert to response schema
        return AISystemResponse.model_validate(system)

    except Exception as e:
        logger.error(f"System registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        )


@router.get("/systems", response_model=list[AISystemSummary])
async def list_systems(
    risk_tier: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    List all registered AI systems with optional filtering.
    
    Args:
        risk_tier: Filter by risk tier (PROHIBITED, HIGH_RISK, LIMITED_RISK, MINIMAL_RISK)
        jurisdiction: Filter by jurisdiction (EU, IN, etc.)
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        List of AISystemSummary objects
    """
    try:
        systems = await RegistryService.list_systems(
            session,
            risk_tier=risk_tier,
            jurisdiction=jurisdiction,
        )
        return [AISystemSummary.model_validate(s) for s in systems]
    except Exception as e:
        logger.error(f"Failed to list systems: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve systems",
        )


@router.get("/systems/{system_id}", response_model=AISystemResponse)
async def get_system(
    system_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get detailed information for a specific AI system.
    
    Args:
        system_id: System ID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        AISystemResponse with full details
        
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
        return AISystemResponse.model_validate(system)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system",
        )


@router.delete("/systems/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system(
    system_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Soft delete an AI system (marks as inactive).
    
    Args:
        system_id: System ID
        session: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException: 404 if system not found
    """
    try:
        deleted = await RegistryService.soft_delete(session, system_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System not found: {system_id}",
            )
        logger.info(f"System deleted: {system_id} (by {current_user['username']})")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete system",
        )


@router.post("/systems/{system_id}/reclassify", response_model=AISystemResponse)
async def reclassify_system(
    system_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Re-run risk classification for a system.
    
    Useful when regulatory guidelines change or new regulatory documents are ingested.
    
    Args:
        system_id: System ID to re-classify
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated AISystemResponse
        
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

        # Re-classify
        classification_result = await risk_classifier_agent.classify(
            system_id=system_id,
            name=system.name,
            purpose=system.purpose,
            model_type=system.model_type,
            output_type=system.output_type,
            data_sources=system.data_sources,
            affected_demographics=system.affected_demographics,
            jurisdictions=system.jurisdictions,
        )

        # Update in database
        updated_system = await RegistryService.update_classification(
            session,
            system_id,
            classification_result.to_dict(),
        )

        logger.info(f"System reclassified: {system_id} → {classification_result.overall_risk_tier}")
        return AISystemResponse.model_validate(updated_system)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reclassify system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reclassify system",
        )


@router.get("/systems/{system_id}/model-card")
async def get_model_card(
    system_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get the model card for a system in Markdown format.
    
    Args:
        system_id: System ID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        Model card as Markdown string
        
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

        return {
            "system_id": system_id,
            "model_card": system.model_card or "No model card available",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve model card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model card",
        )
