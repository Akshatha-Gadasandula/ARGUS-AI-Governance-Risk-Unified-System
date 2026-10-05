"""
Risk Classifier Agent - classifies AI systems under EU AI Act and RBI guidelines using RAG and the configured LLM provider.
Core governance engine that determines regulatory obligations and risk tiers.
"""
import logging
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

from argus.config import settings
from argus.core.llm import get_llm
from argus.core.llm_schemas import ClassificationOutput
from argus.core.citations import canonicalize_citation, tier_citation_review_reasons
from argus.rag.retriever import RegulatoryRetriever

logger = logging.getLogger(__name__)


class Classification(str, Enum):
    """Enum for EU AI Act classifications."""
    PROHIBITED = "PROHIBITED"
    HIGH_RISK = "HIGH_RISK"
    LIMITED_RISK = "LIMITED_RISK"
    MINIMAL_RISK = "MINIMAL_RISK"
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass
class RegulatoryClassification:
    """Result of classification under a single regulatory framework."""
    framework: str
    risk_tier: str | None
    confidence: float | None
    reasoning: str
    citations: list[dict]  # [{article, title, excerpt}]
    obligations: list[str]
    llm_provider: str = "none"
    llm_model: str | None = None
    needs_review: bool = True
    needs_review_reasons: list[str] = field(default_factory=list)
    status: str = "assessed"
    retrieved_provisions: list[dict] = field(default_factory=list)
    dropped_citations: list[dict] = field(default_factory=list)
    exclusions_checked: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ClassificationResult:
    """Overall classification result across all frameworks."""
    system_id: str
    classifications: list[RegulatoryClassification]
    overall_risk_tier: str
    regulatory_citations: dict
    summary: str
    llm_provider: str = "none"
    llm_model: str | None = None
    needs_review: bool = True
    needs_review_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "system_id": self.system_id,
            "classifications": [c.to_dict() for c in self.classifications],
            "overall_risk_tier": self.overall_risk_tier,
            "regulatory_citations": self.regulatory_citations,
            "summary": self.summary,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "needs_review": self.needs_review,
            "needs_review_reasons": self.needs_review_reasons,
        }


# EU AI Act Classification Prompt
EU_AI_ACT_PROMPT = """You are a compliance expert specializing in EU AI Act (Regulation 2024/1689) for financial institutions.

CLASSIFICATION FRAMEWORK:

**Step 1 — PROHIBITED (Article 5):** Check for:
- Social scoring by public authorities
- Real-time biometric mass surveillance in public spaces
- Subliminal manipulation techniques
- Exploitation of vulnerable groups (children, disabled persons)
**If ANY match → PROHIBITED**

**Step 2 — HIGH_RISK (Annex III):** Check for:
- Critical infrastructure (energy, water, transport, communications)
- Educational access or assessment (school admission, assessment)
- Employment (recruitment, CV screening, promotion, termination, worker monitoring)
- Essential private/public services (credit scoring, insurance underwriting, benefits eligibility)
- Law enforcement (risk assessment, evidence evaluation, crime prediction)
- Migration, asylum, border control, visa decisions
- Administration of justice and democratic processes
**If ANY match → HIGH_RISK**

**Step 3 — LIMITED_RISK:** 
- AI-enabled chatbots and conversational systems
- Emotion recognition systems
- AI-generated media
- Recommendation systems with human interaction
→ LIMITED_RISK with transparency obligations

**Step 4 — Default: MINIMAL_RISK**

AI SYSTEM DESCRIPTION:
Name: {system_name}
Purpose: {system_purpose}
Model Type: {model_type}
Output Type: {output_type}
Data Sources: {data_sources}
Affected Demographics: {affected_demographics}
Jurisdictions: {jurisdictions}

RELEVANT EU AI ACT PASSAGES:
{retrieved_passages}

Think through each classification step carefully. Then respond ONLY with valid JSON:
{{
  "risk_tier": "HIGH_RISK",
  "confidence": 0.94,
  "reasoning": "Step 1 analysis: Not prohibited because... Step 2 analysis: HIGH_RISK classification applies because this system evaluates creditworthiness for loan decisions, which falls under Annex III Point 5(b)...",
  "citations": [
    {{"article": "Annex III, Point 5(b)", "title": "AI systems for assessment of creditworthiness", "excerpt": "AI systems intended to evaluate the creditworthiness of natural persons or establish their credit score"}}
  ],
  "obligations": [
    "Conformity assessment before deployment (Article 43)",
    "Technical documentation (Article 11 + Annex IV)",
    "Automatic operational logging (Article 12)",
    "Transparency to deployers (Article 13)",
    "Human oversight mechanism (Article 14)",
    "Accuracy and robustness testing (Article 15)",
    "Bias and discrimination monitoring (Article 10)",
    "Registration in EU AI database (Article 49)"
  ]
}}"""

# Fallback EU AI Act Prompt (with hardcoded examples)
EU_AI_ACT_FALLBACK_PROMPT = """You are a compliance expert specializing in EU AI Act (Regulation 2024/1689) for financial institutions.

CLASSIFICATION FRAMEWORK:

**Step 1 — PROHIBITED (Article 5):** 
- Social scoring by public authorities
- Real-time biometric mass surveillance
- Subliminal manipulation
- Exploitation of vulnerable groups
→ If ANY match: PROHIBITED

**Step 2 — HIGH_RISK (Annex III):**
- Critical infrastructure systems
- Educational systems (admissions, assessment)
- Employment systems (hiring, promotion, termination, monitoring)
- Essential services (credit, insurance, benefits)
- Law enforcement (risk assessment, crime prediction)
- Migration/asylum/border control
- Justice and democratic processes
→ If ANY match: HIGH_RISK

**Step 3 — LIMITED_RISK:**
- Chatbots and conversational AI
- Emotion recognition
- Generated media
- Recommendation systems with human interaction
→ LIMITED_RISK

**Step 4 — Default: MINIMAL_RISK**

AI SYSTEM DESCRIPTION:
Name: {system_name}
Purpose: {system_purpose}
Model Type: {model_type}
Output Type: {output_type}
Data Sources: {data_sources}
Affected Demographics: {affected_demographics}

EXAMPLES:
- Credit scoring system for loan decisions → HIGH_RISK (Annex III 5(b))
- Fraud detection for payment transactions → HIGH_RISK (financial institution)
- Resume screening for hiring → HIGH_RISK (employment - Annex III 4(a))
- Customer service chatbot → LIMITED_RISK (conversational AI)
- Product recommendation engine → MINIMAL_RISK

Analyze this system step-by-step. Respond ONLY with valid JSON:
{{
  "risk_tier": "HIGH_RISK",
  "confidence": 0.90,
  "reasoning": "Step 1: Not prohibited. Step 2: This {system_purpose} falls under high-risk category as it directly affects essential financial decisions.",
  "citations": [
    {{"article": "Annex III", "title": "High-risk AI systems", "excerpt": "AI systems in the areas listed..."}}
  ],
  "obligations": [
    "Conformity assessment (Article 43)",
    "Technical documentation (Article 11)",
    "Automatic logging (Article 12)",
    "Human oversight (Article 14)",
    "Accuracy testing (Article 15)",
    "Database registration (Article 49)"
  ]
}}"""

# RBI Prompt
RBI_PROMPT = """You are a compliance expert specializing in RBI Model Risk Management Guidelines for Indian banks.

CLASSIFICATION FRAMEWORK:

**TIER 1 — CRITICAL/HIGH PRIORITY:**
- Customer-facing credit decisions
- Anti-money laundering (AML) and Know Your Customer (KYC)
- Fraud detection and prevention
- Capital adequacy calculations
- Stress testing models
→ Highest scrutiny, quarterly validation required

**TIER 2 — MEDIUM RISK:**
- Marketing and customer segmentation
- Internal risk models
- Data quality monitoring
→ Semi-annual validation required

**TIER 3 — LOW RISK:**
- Non-customer-facing operational models
- Utility and administrative systems
→ Annual or ad-hoc validation

AI SYSTEM DESCRIPTION:
Name: {system_name}
Purpose: {system_purpose}
Model Type: {model_type}
Output Type: {output_type}
Data Sources: {data_sources}
Affected Demographics: {affected_demographics}

RELEVANT RBI GUIDANCE:
{retrieved_passages}

Analyze for:
1. Customer impact (direct or indirect financial decisions)
2. Regulatory capital implications
3. Compliance and AML risk
4. Data and model governance requirements

Respond ONLY with valid JSON:
{{
  "risk_tier": "TIER_1_CRITICAL",
  "confidence": 0.92,
  "reasoning": "This system directly affects credit decisions affecting retail customers. Falls under Tier 1 per RBI Model Risk Guidelines Section 3.1.1...",
  "citations": [
    {{"article": "Section 3.1.1", "title": "Credit Model Classification", "excerpt": "Models directly affecting credit decisions to customers require highest governance standards"}}
  ],
  "obligations": [
    "Quarterly model validation (Section 4.2)",
    "Independent review board (Section 5.1)",
    "Performance monitoring dashboard (Section 6.1)",
    "Quarterly stress testing (Section 7.2)",
    "Annual governance review (Section 8.1)"
  ]
}}"""

# RBI Fallback Prompt
RBI_FALLBACK_PROMPT = """You are a compliance expert specializing in RBI Model Risk Management Guidelines.

CLASSIFICATION FRAMEWORK:

**TIER 1 — CRITICAL:**
- Customer credit decisions
- AML/KYC decisions
- Fraud detection
- Capital calculations
→ Quarterly validation

**TIER 2 — MEDIUM:**
- Customer segmentation
- Internal risk models
→ Semi-annual validation

**TIER 3 — LOW:**
- Operational systems
- Administrative models
→ Annual validation

AI SYSTEM:
Name: {system_name}
Purpose: {system_purpose}
Model Type: {model_type}

If system is about: credit, fraud, AML, KYC → TIER_1_CRITICAL
If system is about: marketing, segmentation → TIER_2_MEDIUM
If system is about: operations → TIER_3_LOW

Respond with valid JSON:
{{
  "risk_tier": "TIER_1_CRITICAL",
  "confidence": 0.85,
  "reasoning": "Based on {system_purpose}, classified as Tier 1 critical per RBI guidelines.",
  "citations": [
    {{"article": "Section 3", "title": "Model Risk Classification", "excerpt": "Models affecting customer-facing decisions require highest governance"}}
  ],
  "obligations": [
    "Quarterly validation",
    "Independent review",
    "Performance monitoring",
    "Stress testing",
    "Annual governance review"
  ]
}}"""


class RiskClassifierAgent:
    """
    Autonomous agent for classifying AI systems against EU AI Act and RBI guidelines.
    Uses RAG for regulatory context and Claude for intelligent classification.
    """

    # Framework mapping: jurisdiction → (framework_name, main_prompt, fallback_prompt)
    FRAMEWORK_MAP = {
        "EU": ("EU_AI_ACT", EU_AI_ACT_PROMPT, EU_AI_ACT_FALLBACK_PROMPT),
        "IN": ("RBI", RBI_PROMPT, RBI_FALLBACK_PROMPT),
    }

    # Risk tier priority for aggregation
    TIER_PRIORITY = {
        Classification.PROHIBITED: 4,
        Classification.HIGH_RISK: 3,
        Classification.LIMITED_RISK: 2,
        Classification.MINIMAL_RISK: 1,
        Classification.UNCLASSIFIED: 0,
    }

    def __init__(self, settings_obj=None):
        """
        Initialize Risk Classifier Agent.
        
        Args:
            settings_obj: Settings object (defaults to global settings)
        """
        self.settings = settings_obj or settings
        self.client = None
        self.retriever = RegulatoryRetriever(self.settings.database_url)

    def _fallback_classification(
        self,
        framework_name: str,
        system_name: str,
        system_purpose: str,
        model_type: Optional[str],
        output_type: Optional[str],
    ) -> 'RegulatoryClassification':
        """Fallback deterministic classification when the LLM client is unavailable."""
        text = (system_purpose or "").lower()
        risk_tier = Classification.MINIMAL_RISK.value
        confidence = 0.55
        reasoning = "Fallback rule-based classification used because LLM client was unavailable."

        if any(k in text for k in ["credit", "loan", "default", "insurance", "admission", "hiring"]):
            risk_tier = Classification.HIGH_RISK.value
            confidence = 0.75
            reasoning = "System handles sensitive decision-making and is classified as high risk by fallback rules."
        elif any(k in text for k in ["chatbot", "monitor", "recommend", "content", "translation"]):
            risk_tier = Classification.LIMITED_RISK.value
            confidence = 0.65
            reasoning = "System is likely limited risk under generic AI governance criteria."

        return RegulatoryClassification(
            framework=framework_name,
            risk_tier=risk_tier,
            confidence=confidence,
            reasoning=reasoning,
            citations=[],
            obligations=["Document risk decision", "Monitor performance", "Apply governance controls"],
        )

    async def classify(
        self,
        system_id: str,
        name: str,
        purpose: str,
        model_type: Optional[str],
        output_type: Optional[str],
        data_sources: list[str],
        affected_demographics: list[str],
        jurisdictions: list[str],
    ) -> ClassificationResult:
        """
        Classify AI system against applicable regulatory frameworks.
        
        Args:
            system_id: System identifier
            name: System name
            purpose: System purpose description
            model_type: Type of model
            output_type: Type of output
            data_sources: Data sources used
            affected_demographics: Affected demographics
            jurisdictions: Applicable jurisdictions
            
        Returns:
            ClassificationResult with per-framework results and aggregated tier
        """
        logger.info(f"Classifying system {system_id} under {len(jurisdictions)} jurisdiction(s)")

        classifications = []
        regulatory_citations = {}

        for jurisdiction in jurisdictions:
            if jurisdiction not in self.FRAMEWORK_MAP:
                logger.warning(f"Unsupported jurisdiction: {jurisdiction}")
                continue

            framework_name, main_prompt, fallback_prompt = self.FRAMEWORK_MAP[jurisdiction]

            classification = await self._classify_single(
                framework_name=framework_name,
                main_prompt=main_prompt,
                fallback_prompt=fallback_prompt,
                system_name=name,
                system_purpose=purpose,
                model_type=model_type,
                output_type=output_type,
                data_sources=data_sources,
                affected_demographics=affected_demographics,
            )

            if classification:
                classifications.append(classification)
                regulatory_citations[framework_name] = {
                    "risk_tier": classification.risk_tier,
                    "llm_provider": classification.llm_provider,
                    "llm_model": classification.llm_model,
                    "needs_review": classification.needs_review,
                    "needs_review_reasons": classification.needs_review_reasons,
                    "status": classification.status,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning,
                    "retrieved_provisions": classification.retrieved_provisions,
                    "dropped_citations": classification.dropped_citations,
                    "exclusions_checked": classification.exclusions_checked,
                    "citations": classification.citations,
                    "obligations": classification.obligations,
                }

        # Aggregate to overall risk tier (highest priority wins)
        assessed = [c for c in classifications if c.status == "assessed"]
        if assessed:
            risk_tiers_priority = [
                self.TIER_PRIORITY.get(Classification(c.risk_tier), 0)
                for c in assessed
            ]
            max_priority_idx = risk_tiers_priority.index(max(risk_tiers_priority))
            overall_tier = assessed[max_priority_idx].risk_tier
        else:
            overall_tier = Classification.UNCLASSIFIED.value

        # Build summary
        summary = f"Assessed {len(assessed)} framework(s): "
        summary += ", ".join(f"{c.framework}={c.risk_tier if c.status == 'assessed' else c.status}" for c in classifications)

        producers = {(c.llm_provider, c.llm_model) for c in assessed}
        provider, model = next(iter(producers)) if len(producers) == 1 else ("mixed", None) if producers else ("none", None)
        result = ClassificationResult(
            system_id=system_id,
            classifications=classifications,
            overall_risk_tier=overall_tier,
            regulatory_citations=regulatory_citations,
            summary=summary,
            llm_provider=provider,
            llm_model=model,
            needs_review=any(c.needs_review_reasons for c in assessed),
            needs_review_reasons=sorted({reason for c in assessed for reason in c.needs_review_reasons}),
        )

        logger.info(f"Classification complete: {overall_tier} (confidence: "
                   f"{sum(c.confidence for c in assessed) / len(assessed) if assessed else 0:.2f})")

        return result

    async def _classify_single(
        self,
        framework_name: str,
        main_prompt: str,
        fallback_prompt: str,
        system_name: str,
        system_purpose: str,
        model_type: Optional[str],
        output_type: Optional[str],
        data_sources: list[str],
        affected_demographics: list[str],
    ) -> Optional[RegulatoryClassification]:
        """
        Classify system under a single framework.
        
        Args:
            framework_name: Framework name
            main_prompt: Main classification prompt template
            fallback_prompt: Fallback prompt if RAG returns nothing
            system_name: System name
            system_purpose: System purpose
            model_type: Model type
            output_type: Output type
            data_sources: Data sources
            affected_demographics: Affected demographics
            
        Returns:
            RegulatoryClassification or None on error
        """
        logger.info(f"Classifying under {framework_name}")

        if not self.retriever.has_corpus(framework_name):
            return RegulatoryClassification(
                framework=framework_name, risk_tier=None, confidence=None,
                reasoning="No indexed corpus; framework not assessed.", citations=[], obligations=[],
                status="not_assessed_no_corpus", needs_review=False,
            )

        # Try RAG retrieval
        query = f"{system_purpose} {model_type or ''} {output_type or ''}"
        retrieved_passages = self.retriever.retrieve_for_classification(framework_name, query, k=5)

        if retrieved_passages:
            prompt_text = main_prompt
            retrieved_text = self.retriever.format_passages(retrieved_passages)
        else:
            logger.info(f"No RAG results for {framework_name}, using fallback prompt")
            prompt_text = fallback_prompt
            retrieved_text = "(No regulatory documents in knowledge base - using generic guidelines)"

        # Format prompt
        formatted_prompt = prompt_text.format(
            system_name=system_name,
            system_purpose=system_purpose,
            model_type=model_type or "Unspecified",
            output_type=output_type or "Unspecified",
            data_sources=", ".join(data_sources) or "Not specified",
            affected_demographics=", ".join(affected_demographics) or "Not specified",
            jurisdictions="EU, IN" if framework_name == "EU_AI_ACT" else "IN",
            retrieved_passages=retrieved_text,
        )

        fallback = self._fallback_classification(
            framework_name, system_name, system_purpose, model_type, output_type,
        )
        result = await get_llm(self.settings).generate_json(
            formatted_prompt, ClassificationOutput, fallback.to_dict(),
            chunks=retrieved_passages, max_tokens=1500,
        )

        # Map tier values (normalize RBI tiers to standard risk_tier format)
        risk_tier = result.get("risk_tier", "UNCLASSIFIED")
        if "TIER" in risk_tier:
            # RBI tier format
            if "CRITICAL" in risk_tier or "1" in risk_tier:
                risk_tier = "HIGH_RISK"
            elif "MEDIUM" in risk_tier or "2" in risk_tier:
                risk_tier = "LIMITED_RISK"
            else:
                risk_tier = "MINIMAL_RISK"

        reasons = list(result.get("needs_review_reasons", []))
        if result.get("confidence", 0.5) < 0.7:
            reasons.append("confidence_below_0.7")
        if not retrieved_passages:
            reasons.append("no_retrieved_chunks")
        supporting, exclusions = split_citation_roles(risk_tier, result.get("citations", []), result.get("exclusions_checked", []))
        supporting = [canonicalize_citation(c) for c in supporting]
        exclusions = [canonicalize_citation(c) for c in exclusions]
        if framework_name == "EU_AI_ACT":
            reasons.extend(tier_citation_review_reasons(risk_tier, supporting))
            if any(c['citation_incomplete'] for c in supporting + exclusions):
                reasons.append("incomplete_citation")
        reasons = list(dict.fromkeys(reasons))
        classification = RegulatoryClassification(
            framework=framework_name,
            risk_tier=risk_tier,
            confidence=float(result.get("confidence", 0.5)),
            reasoning=result.get("reasoning", ""),
            citations=supporting,
            obligations=result.get("obligations", []),
            llm_provider=result["llm_provider"],
            llm_model=result["llm_model"],
            needs_review=bool(reasons),
            needs_review_reasons=reasons,
            retrieved_provisions=[doc.metadata for doc in retrieved_passages],
            dropped_citations=result.get("dropped_citations", []),
            exclusions_checked=exclusions,
        )

        logger.info(f"{framework_name} classification: {risk_tier} (confidence: {classification.confidence:.2f})")
        return classification


def split_citation_roles(tier, citations, exclusions):
    supporting, checked = [], list(exclusions)
    for citation in citations:
        article_five = bool(re.search(r"\bArticle\s+5\b", citation.get("article", ""), re.I)) or citation.get("article") == "5"
        article_six = bool(re.search(r"\bArticle\s+6\b", citation.get("article", ""), re.I)) or citation.get("article") == "6"
        excluded = citation.get("citation_role") == "exclusion_checked"
        if excluded or (tier in ("MINIMAL_RISK", "LIMITED_RISK") and article_five) or (tier == "MINIMAL_RISK" and article_six):
            if citation not in checked:
                checked.append(citation)
        else:
            supporting.append(citation)
    return supporting, checked
