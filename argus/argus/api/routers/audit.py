"""
Audit router - audit dossier generation and retrieval endpoints.
Generates and retrieves regulator-ready PDF audit dossiers.
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from argus.api.deps import get_session, get_current_user
from argus.core.agents.audit_generator import AuditGeneratorAgent
from argus.core.registry.models import AuditRecord
from argus.core.registry.service import RegistryService
from argus.core.schemas import AuditRecordResponse, AuditRequest
from argus.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy audit generator to avoid import-time side effects
audit_generator = None


def _serialize_audit_record(record: AuditRecord) -> AuditRecordResponse:
    """Convert an ORM audit record into the API response schema."""
    return AuditRecordResponse(
        id=str(record.id),
        system_id=str(record.system_id),
        generated_by=record.generated_by,
        pdf_path=record.pdf_path,
        content_hash=record.content_hash,
        compliance_summary=record.compliance_summary,
        generated_at=record.generated_at,
    )


@router.post("/generate-dossier", response_model=AuditRecordResponse, status_code=status.HTTP_201_CREATED)
async def generate_dossier(
    request: AuditRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a complete audit dossier PDF for a system.
    
    Includes:
    - System overview and classification
    - Risk tier and regulatory obligations
    - Fairness and drift monitoring history
    - Open alerts and remediation tasks
    - Compliance checklist
    
    Generation typically completes in under 30 seconds.
    
    Args:
        request: AuditRequest with system_id and requested_by
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        AuditRecordResponse with PDF path and metadata
        
    Raises:
        HTTPException: 404 if system not found or 500 if generation fails
    """
    try:
        # Verify system exists
        system = await RegistryService.get_system(session, request.system_id)
        if not system:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System not found: {request.system_id}",
            )

        logger.info(f"Generating audit dossier for {request.system_id} (requested by {request.requested_by})")

        # Generate dossier
        global audit_generator
        if audit_generator is None:
            audit_generator = AuditGeneratorAgent(settings)

        record = await audit_generator.generate(
            session,
            request.system_id,
            requested_by=request.requested_by,
        )

        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate audit dossier",
            )

        logger.info(f"Audit dossier generated: {request.system_id}")
        
        return _serialize_audit_record(record)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Failed to generate audit dossier: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate audit dossier",
        )


@router.get("/records", response_model=list[AuditRecordResponse])
async def get_audit_records(
    system_id: Optional[str] = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all audit records with optional filtering.
    
    Args:
        system_id: Filter by system ID if provided
        limit: Maximum results to return
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        List of AuditRecordResponse objects
    """
    try:
        query = select(AuditRecord).order_by(AuditRecord.generated_at.desc()).limit(limit)

        if system_id:
            # Get system UUID first
            system = await RegistryService.get_system(session, system_id)
            if system:
                query = query.where(AuditRecord.system_id == system.id)
            else:
                return []

        result = await session.execute(query)
        records = result.scalars().all()

        return [_serialize_audit_record(r) for r in records]

    except Exception as e:
        logger.error(f"Failed to retrieve audit records: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit records",
        )


@router.get("/records/{record_id}", response_model=AuditRecordResponse)
async def get_audit_record(
    record_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get a specific audit record by ID.
    
    Args:
        record_id: Audit record UUID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        AuditRecordResponse for the record
        
    Raises:
        HTTPException: 404 if record not found
    """
    try:
        import uuid
        try:
            record_uuid = uuid.UUID(record_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid record ID format",
            )

        query = select(AuditRecord).where(AuditRecord.id == record_uuid)
        result = await session.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit record not found: {record_id}",
            )

        return _serialize_audit_record(record)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve audit record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit record",
        )


@router.get("/records/{record_id}/download")
async def download_audit_pdf(
    record_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Download the PDF audit dossier.
    
    Args:
        record_id: Audit record UUID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        FileResponse streaming the PDF file
        
    Raises:
        HTTPException: 404 if record or PDF not found
    """
    try:
        import uuid
        try:
            record_uuid = uuid.UUID(record_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid record ID format",
            )

        query = select(AuditRecord).where(AuditRecord.id == record_uuid)
        result = await session.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit record not found: {record_id}",
            )

        if not record.pdf_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not available for this record",
            )

        pdf_path = Path(record.pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF file not found on disk",
            )

        logger.info(f"Downloading audit PDF: {record_id}")

        return FileResponse(
            path=pdf_path,
            filename=pdf_path.name,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_path.name}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download audit PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download PDF",
        )
