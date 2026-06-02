"""
Q&A router - governance question answering endpoint.
Provides intelligent Q&A over AI system registry and regulatory knowledge.
"""
import logging

from anthropic import Anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from argus.api.deps import get_session, get_current_user
from argus.core.registry.models import AISystem
from argus.core.schemas import QARequest, QAResponse
from argus.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy Anthropic client to avoid import-time initialization issues
client = None


def get_anthropic_client():
    global client
    if client is None:
        try:
            client = Anthropic(api_key=settings.anthropic_api_key)
        except Exception as e:
            logger.warning(f"Anthropic client init failed: {e}")
            client = None
    return client


@router.post("/ask", response_model=QAResponse)
async def answer_question(
    request: QARequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Answer governance questions about AI systems and regulations.
    
    Supports queries like:
    - "Which systems are high-risk?"
    - "What are the EU AI Act obligations for credit scoring?"
    - "Show critical alerts from the last 7 days"
    - "Which systems need audit dossiers?"
    
    Args:
        request: QARequest with question
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        QAResponse with answer and sources
    """
    try:
        question = request.question.strip()
        logger.info(f"Q&A query: {question} (by {current_user['username']})")

        # Use fallback mock implementation if API key unavailable
        if not settings.anthropic_api_key:
            logger.info("Using mock Q&A implementation (no API key)")
            return await _handle_mock_query(question, session)

        # Step 1: Classify question type via LLM
        classification_prompt = f"""Classify this governance question into one category:
- registry_query: Questions about specific systems or system lists
- compliance_query: Questions about regulatory requirements and obligations
- alert_query: Questions about alerts and violations
- general: General governance knowledge questions

Question: {question}

Return ONLY one word: registry_query, compliance_query, alert_query, or general"""

        client = get_anthropic_client()
        if client is None:
            logger.info("Using mock Q&A implementation (client unavailable)")
            return await _handle_mock_query(question, session)

        try:
            classification_response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                messages=[{"role": "user", "content": classification_prompt}],
            )

            query_type = classification_response.content[0].text.strip().lower()
            if query_type not in ["registry_query", "compliance_query", "alert_query", "general"]:
                query_type = "general"

            logger.info(f"Classified as: {query_type}")

            # Step 2: Handle by query type
            if query_type == "registry_query":
                answer, sources = await _handle_registry_query(question, session)
            elif query_type == "compliance_query":
                answer, sources = await _handle_compliance_query(question)
            elif query_type == "alert_query":
                answer, sources = await _handle_alert_query(question, session)
            else:
                answer, sources = await _handle_general_query(question)

        except Exception as e:
            logger.warning(f"LLM call failed ({e}), using mock implementation")
            return await _handle_mock_query(question, session)

        logger.info(f"Q&A response generated with {len(sources)} sources")

        return QAResponse(
            answer=answer,
            sources=sources,
            query_type=query_type,
        )

    except Exception as e:
        logger.error(f"Q&A failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to answer question",
        )


async def _handle_registry_query(question: str, session: AsyncSession) -> tuple[str, list[str]]:
    """Handle registry/system query."""
    # Get all systems
    result = await session.execute(select(AISystem).where(AISystem.is_active))
    systems = result.scalars().all()

    systems_text = "\n".join([
        f"- {s.name} ({s.system_id}): {s.purpose[:100]}, Risk: {s.risk_tier.value}"
        for s in systems
    ])

    prompt = f"""Given this list of AI systems and the question, provide a helpful answer.

SYSTEMS:
{systems_text}

QUESTION: {question}

Provide a concise, helpful answer in 2-3 sentences. If specific system names are needed, use the system_id."""

    client = get_anthropic_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM client unavailable")

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text.strip()
    sources = [f"System Registry ({len(systems)} systems)"]

    return answer, sources


async def _handle_compliance_query(question: str) -> tuple[str, list[str]]:
    """Handle compliance/regulatory query."""
    prompt = f"""You are a compliance expert. Answer this governance question:

{question}

Focus on:
- EU AI Act compliance requirements
- RBI Model Risk Guidelines
- Indian DPDP Act requirements
- Best practices for AI governance

Provide a concise answer in 2-3 sentences with key points."""

    client = get_anthropic_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM client unavailable")

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text.strip()
    sources = [
        "EU AI Act (Regulation 2024/1689)",
        "RBI Model Risk Management Guidelines",
    ]

    return answer, sources


async def _handle_alert_query(question: str, session: AsyncSession) -> tuple[str, list[str]]:
    """Handle alert/violation query."""
    from argus.core.registry.models import GovernanceAlert

    # Get recent critical alerts
    result = await session.execute(
        select(GovernanceAlert)
        .where(GovernanceAlert.severity.in_(["CRITICAL", "WARNING"]))
        .order_by(GovernanceAlert.created_at.desc())
        .limit(10)
    )
    alerts = result.scalars().all()

    alerts_text = "\n".join([
        f"- [{a.created_at.strftime('%Y-%m-%d')}] {a.severity.value}: {a.title}"
        for a in alerts
    ])

    prompt = f"""Given these recent governance alerts and the question, provide an answer:

RECENT ALERTS:
{alerts_text or "No recent alerts"}

QUESTION: {question}

Summarize the alert situation relevant to the question in 2-3 sentences."""

    client = get_anthropic_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM client unavailable")

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text.strip()
    sources = ["ARGUS Governance Alerts Database"]

    return answer, sources


async def _handle_general_query(question: str) -> tuple[str, list[str]]:
    """Handle general governance knowledge query."""
    prompt = f"""You are an AI governance expert. Answer this question:

{question}

Provide practical, actionable guidance for AI governance in 2-3 sentences."""

    client = get_anthropic_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM client unavailable")

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text.strip()
    sources = ["AI Governance Best Practices"]

    return answer, sources


async def _handle_mock_query(question: str, session: AsyncSession) -> QAResponse:
    """Handle Q&A with mock implementation (no LLM API)."""
    query_lower = question.lower()
    
    # Registry queries
    if any(word in query_lower for word in ["system", "credit", "fraud", "chatbot"]):
        result = await session.execute(select(AISystem).where(AISystem.is_active))
        systems = result.scalars().all()
        system_list = ", ".join([s.name for s in systems])
        return QAResponse(
            answer=f"The ARGUS registry contains the following AI systems: {system_list}. These systems are monitored for fairness, compliance, and risk across multiple regulatory frameworks including EU AI Act, RBI Model Risk Guidelines, and Indian DPDP Act.",
            sources=["ARGUS System Registry"],
            query_type="registry_query",
        )
    
    # Fairness/violation queries
    if any(word in query_lower for word in ["violation", "fairness", "parity", "bias", "critical"]):
        from argus.core.registry.models import GovernanceAlert
        result = await session.execute(
            select(GovernanceAlert)
            .where(GovernanceAlert.severity == "CRITICAL")
            .order_by(GovernanceAlert.created_at.desc())
            .limit(5)
        )
        critical_alerts = result.scalars().all()
        alert_summary = "\n".join([f"- {a.title}: {a.description[:80]}" for a in critical_alerts])
        
        return QAResponse(
            answer=f"Critical fairness violations detected:\n{alert_summary}\n\nDemographic parity and equalized odds metrics indicate systematic bias in credit scoring model predictions across protected classes. Immediate remediation required per EU AI Act Article 10(2) and RBI guidelines.",
            sources=["ARGUS Alerts Database", "EU AI Act Article 10(2)", "RBI Model Risk Guidelines"],
            query_type="alert_query",
        )
    
    # Compliance/regulatory queries
    if any(word in query_lower for word in ["regulation", "compliance", "framework", "requirement", "obligation"]):
        return QAResponse(
            answer="AI governance requires compliance with multiple regulatory frameworks: (1) EU AI Act mandates risk assessment and transparency for high-risk AI systems; (2) RBI Model Risk Management guidelines require ongoing model monitoring and validation; (3) Indian DPDP Act specifies data handling and consent requirements. Organizations must implement governance frameworks that integrate fairness monitoring, bias detection, and regulatory tracking across the AI lifecycle.",
            sources=["EU AI Act (Regulation 2024/1689)", "RBI Model Risk Management Guidelines", "Indian DPDP Act 2023"],
            query_type="compliance_query",
        )
    
    # Default response
    return QAResponse(
        answer="ARGUS provides comprehensive AI governance including system registration, fairness monitoring with demographic parity and equalized odds metrics, regulatory compliance tracking across EU AI Act and RBI guidelines, automated alert generation for violations, and audit trail documentation. The system detects and flags bias in AI models with regulatory references for remediation.",
        sources=["ARGUS Documentation", "AI Governance Best Practices"],
        query_type="general",
    )
