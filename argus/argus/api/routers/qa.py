"""SQL-backed governance answers and single-attempt, grounded explanations."""
import json
import re

from fastapi import APIRouter, Depends
from langchain.schema import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_session, get_current_user
from argus.config import settings
from argus.core.llm import get_llm
from argus.core.llm_schemas import AnswerOutput
from argus.core.registry.models import AISystem, GovernanceAlert
from argus.core.schemas import QARequest, QAResponse
from argus.rag.retriever import RegulatoryRetriever

router = APIRouter()
DECLINE = "I can only answer questions about the ARGUS system registry, its governance alerts, and the indexed EU AI Act."
NOT_FOUND = "not found in the indexed text"


def value(item):
    return getattr(item, "value", item)


def system_row(system):
    return {"table": "ai_systems", "id": str(system.id), "system_id": system.system_id,
            "name": system.name, "risk_tier": value(system.risk_tier),
            "owner_team": system.owner_team, "owner_email": system.owner_email,
            "jurisdictions": system.jurisdictions}


def sql_answer(answer, rows, query_type="registry_query"):
    sources = [f"{r['table']}:{r['id']} - {r['name']} ({r['system_id']})" for r in rows]
    return QAResponse(answer=answer, sources=sources, row_sources=rows,
                      query_type=query_type, needs_review=False)


def matching_systems(question, systems):
    words = set(re.findall(r"[a-z0-9]+", question.lower()))
    ignored = {"system", "systems", "model", "engine", "filter", "ai", "v2"}
    matched = []
    for system in systems:
        identity = set(re.findall(r"[a-z0-9]+", system.name.lower())) - ignored
        if system.system_id.lower() in question.lower() or (identity and identity <= words):
            matched.append(system)
    return matched


def citation_chunks(frameworks):
    """Ground an explanation in the stored classification's citation identities."""
    chunks = []
    for data in frameworks.values():
        for citation in data.get("citations", []):
            label = citation.get("canonical_citation") or citation.get("article", "")
            article = re.search(r"(?:Article\s+)?(\d+)", citation.get("article", ""), re.I)
            annex = citation.get("annex") or (re.search(r"Annex\s+([IVXLCDM]+)", label, re.I) or [None, None])[1]
            if annex:
                point = re.search(r"(\d+)(?:\(([a-z])\))?", citation.get("point") or "")
                metadata = {"section_type": "annex", "annex_id": annex,
                            "annex_point": point[1] if point else "",
                            "annex_subpoint": point[2] if point else ""}
            else:
                metadata = {"section_type": "article", "article_number": int(article[1]) if article else None}
            chunks.append(Document(page_content=label + "\n" + (citation.get("excerpt") or ""), metadata=metadata))
    return chunks


async def explain_system(question, system):
    frameworks = {key: data for key, data in (system.regulatory_citations or {}).items()
                  if data.get("status") == "assessed" or data.get("risk_tier")}
    context = {**system_row(system), "classification_reasoning": system.risk_classification_reasoning,
               "frameworks": frameworks}
    original = "; ".join(f"{key}: {data.get('risk_tier')}, produced by {data.get('llm_provider', 'not recorded')} / {data.get('llm_model') or 'not recorded'}"
                         for key, data in frameworks.items()) or "Original provider/model not recorded"
    prefix = f"Stored tier: {value(system.risk_tier)}. Original classification: {original}. "
    fallback = {"answer": " ".join(data.get("reasoning", "") for data in frameworks.values())
                           or system.risk_classification_reasoning or "No stored reasoning available.", "citations": []}
    prompt = ("Explain the stored tier using only this registry classification context. Do not reclassify, "
              "invent reasons, or assert that a framework without an assessment was assessed. "
              "State the provider and model that produced the original tier.\n"
              + json.dumps(context, default=str) + "\nQuestion: " + question)
    result = await get_llm(settings).generate_json(prompt, AnswerOutput, fallback,
                 chunks=citation_chunks(frameworks), max_tokens=650, max_attempts=1)
    reasons = list(result.get("needs_review_reasons", []))
    for data in frameworks.values():
        reasons.extend(data.get("needs_review_reasons", []))
    return QAResponse(answer=prefix + result["answer"], sources=[f"ai_systems:{system.id} - {system.name} ({system.system_id})"],
        row_sources=[system_row(system)], stored_classification=context,
        citations=result.get("citations", []), llm_provider=result["llm_provider"], llm_model=result["llm_model"],
        needs_review=result.get("needs_review", False) or any(d.get("needs_review", False) for d in frameworks.values()),
        needs_review_reasons=list(dict.fromkeys(reasons)), query_type="registry_query")


async def regulation_answer(question):
    requested = re.search(r"\barticle\s+(\d+)", question, re.I)
    retriever = RegulatoryRetriever(settings.database_url)
    try:
        chunks = retriever.retrieve("EU_AI_ACT", question, k=5,
                    filter={"section_type": "article", "article_number": int(requested[1])} if requested else None)
    finally:
        retriever.engine.dispose()
    if requested:
        chunks = [doc for doc in chunks if str(doc.metadata.get("article_number")) == requested[1]]
    if not chunks:
        return QAResponse(answer=NOT_FOUND, sources=[], citations=[], query_type="compliance_query",
                          status="not_found", needs_review=True, needs_review_reasons=["no_retrieved_chunks"])
    prompt = ("Answer only from the retrieved EU AI Act text below. Cite the provision. "
              "Do not use regulatory facts from memory. If the text does not establish the requested fact, "
              f"say '{NOT_FOUND}'.\nQuestion: {question}")
    fallback = {"answer": "LLM answer unavailable. Indexed text: " + "\n".join(doc.page_content for doc in chunks),
                "citations": []}
    result = await get_llm(settings).generate_json(prompt, AnswerOutput, fallback,
                     chunks=chunks, max_tokens=700, max_attempts=1)
    sources = list(dict.fromkeys(f"{d.metadata.get('citation', d.metadata.get('article', 'EU AI Act'))} - "
                   f"{d.metadata.get('source', 'indexed text')}, p. {d.metadata.get('page_number', 'not recorded')}" for d in chunks))
    reasons = list(result.get("needs_review_reasons", []))
    if not result.get("citations"):
        reasons.append("missing_citation")
    return QAResponse(answer=result["answer"], citations=result.get("citations", []), sources=sources,
        llm_provider=result["llm_provider"], llm_model=result["llm_model"],
        needs_review=bool(reasons) or result.get("needs_review", False),
        needs_review_reasons=list(dict.fromkeys(reasons)), query_type="compliance_query")


@router.post("/ask", response_model=QAResponse)
async def answer_question(request: QARequest, session: AsyncSession = Depends(get_session),
                          current_user: dict = Depends(get_current_user)):
    question = request.question.strip()
    lower = question.lower().replace("-", " ")
    if re.search(r"\barticle\s+\d+\b|\bEU AI Act\b", question, re.I):
        return await regulation_answer(question)
    # Route only supported registry operations; no provider lookup or call for other topics.
    if not re.search(r"\b(system|systems|registered|registry|alerts?|tier|risk|owns?|owners?|jurisdictions?)\b", lower):
        return QAResponse(answer=DECLINE, sources=[], query_type="out_of_scope", status="declined", needs_review=False)
    if not re.search(r"\b(how many|which|list|show|who|what|why)\b", lower):
        return QAResponse(answer=DECLINE, sources=[], query_type="out_of_scope", status="declined", needs_review=False)
    systems = (await session.execute(select(AISystem).where(AISystem.is_active).order_by(AISystem.system_id))).scalars().all()
    matches = matching_systems(question, systems)
    if "why" in lower:
        if len(matches) != 1:
            return sql_answer("Specify one registered system to explain its stored classification.", [system_row(s) for s in matches])
        return await explain_system(question, matches[0])
    if "alert" in lower:
        chosen = matches or systems
        statement = select(GovernanceAlert).where(GovernanceAlert.resolved.is_(False),
                      GovernanceAlert.system_id.in_([s.id for s in chosen]))
        if "critical" in lower:
            statement = statement.where(GovernanceAlert.severity == "CRITICAL")
        alerts = (await session.execute(statement.order_by(GovernanceAlert.id))).scalars().all()
        by_id = {s.id: s for s in chosen}
        rows = [{"table": "governance_alerts", "id": str(a.id), "system_id": by_id[a.system_id].system_id,
                 "name": by_id[a.system_id].name, "severity": value(a.severity), "resolved": a.resolved,
                 "title": a.title} for a in alerts]
        if "how many" in lower:
            label = ", ".join(f"{s.name} ({s.system_id})" for s in chosen)
            return sql_answer(f"{label}: {len(alerts)} open{' critical' if 'critical' in lower else ''} alerts.", rows + [system_row(s) for s in chosen], "alert_query")
        affected = [s for s in chosen if any(a.system_id == s.id for a in alerts)]
        return sql_answer("Systems with unresolved" + (" critical" if "critical" in lower else "") + " alerts: " +
                          (", ".join(f"{s.name} ({s.system_id})" for s in affected) or "none") + ".", rows, "alert_query")
    chosen = matches or systems
    tiers = {"high risk": "HIGH_RISK", "minimal risk": "MINIMAL_RISK", "limited risk": "LIMITED_RISK", "prohibited": "PROHIBITED"}
    for phrase, tier in tiers.items():
        if phrase in lower:
            chosen = [s for s in chosen if value(s.risk_tier) == tier]
    if "jurisdiction" in lower:
        requested = re.search(r"\b(EU|IN|UK|US)\b", question)
        if requested:
            chosen = [s for s in chosen if requested[1] in s.jurisdictions]
    rows = [system_row(s) for s in chosen]
    if "how many" in lower:
        answer = f"{len(chosen)} active AI systems are registered matching this query."
    elif re.search(r"\b(owns?|owners?)\b", lower):
        answer = "; ".join(f"{s.name} ({s.system_id}): owner team {s.owner_team}; owner email {s.owner_email or 'not recorded'}" for s in chosen) or "No matching systems."
    else:
        answer = "; ".join(f"{s.name} ({s.system_id}): {value(s.risk_tier)}; jurisdictions {', '.join(s.jurisdictions)}" for s in chosen) or "No matching systems."
    return sql_answer(answer, rows)
