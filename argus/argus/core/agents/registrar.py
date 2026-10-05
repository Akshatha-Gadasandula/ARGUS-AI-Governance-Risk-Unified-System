"""
Registrar Agent - processes new AI system intake and generates model cards via LLM.
Infers missing metadata and enriches system descriptions with AI-generated model cards.
"""
import logging

from argus.config import settings
from argus.core.llm import get_llm
from argus.core.llm_schemas import RegistrationOutput
from argus.core.schemas import AISystemCreate

logger = logging.getLogger(__name__)


class RegistrarAgent:
    """
    Autonomous agent for system registration and model card generation.
    Uses the configured LLM provider to extract metadata and generate comprehensive model cards.
    """

    SYSTEM_PROMPT = """You are an AI governance specialist with deep expertise in model risk management, 
responsible AI practices, and regulatory compliance. Your job is to analyze AI system descriptions 
and generate comprehensive documentation."""

    EXTRACTION_PROMPT = """Analyze this AI system description and return ONLY valid JSON with these fields:

System Name: {name}
Purpose: {purpose}
Owner Team: {owner_team}
Data Sources: {data_sources}
Jurisdictions: {jurisdictions}
Model Type (if specified): {model_type}
Output Type (if specified): {output_type}
Affected Demographics (if any): {affected_demographics}

Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
  "inferred_model_type": "gradient_boosting | neural_network | random_forest | regression | nlp | computer_vision | rule_based | other",
  "inferred_output_type": "binary_classification | multiclass | regression | ranking | generation | other",
  "inferred_affected_demographics": ["age", "income", "location", ...],
  "data_sensitivity": "HIGH | MEDIUM | LOW",
  "model_card": "# Model Card: {name}\\n\\n## Purpose\\nDetailed purpose and use case...\\n\\n## Model Type\\n{model_type}\\n\\n## Output Type\\n{output_type}\\n\\n## Data\\nDescription of training and inference data...\\n\\n## Performance\\nExpected performance characteristics...\\n\\n## Risk Considerations\\nPotential risks and mitigations...\\n\\n## Human Oversight\\nRequired human involvement...\\n\\n## Known Limitations\\nKey limitations and constraints..."
}}"""

    def __init__(self, settings_obj=None):
        """
        Initialize Registrar Agent.
        
        Args:
            settings_obj: Settings object (defaults to global settings)
        """
        self.settings = settings_obj or settings
        # Client will be initialized lazily to avoid import-time and environment issues
        self.client = None

    async def process(
        self,
        payload: AISystemCreate,
    ) -> tuple[AISystemCreate, str]:
        """
        Process system intake and generate metadata and model card.
        
        Args:
            payload: System creation request
            
        Returns:
            Tuple of (enriched_payload, model_card_string)
        """
        logger.info(f"Processing registration for system: {payload.name}")

        # Build extraction prompt
        prompt = self.EXTRACTION_PROMPT.format(
            name=payload.name,
            purpose=payload.purpose,
            owner_team=payload.owner_team,
            data_sources=", ".join(payload.data_sources) or "Not specified",
            jurisdictions=", ".join(payload.jurisdictions),
            model_type=payload.model_type or "Not specified",
            output_type=payload.output_type or "Not specified",
            affected_demographics=", ".join(payload.affected_demographics) or "Not specified",
        )

        text = (payload.purpose or "").lower()
        inferred_output = "other"
        inferred_model = "other"
        inferred_affected = payload.affected_demographics or []

        if any(k in text for k in ["predict", "probability", "class", "approve", "reject", "loan", "default"]):
            inferred_output = "binary_classification"
        if any(k in text for k in ["text", "nlp", "language", "token"]):
            inferred_model = "nlp"
        elif any(k in text for k in ["image", "vision", "pixel"]):
            inferred_model = "computer_vision"
        elif any(k in text for k in ["tree", "forest", "xgboost", "gradient"]):
            inferred_model = "gradient_boosting"

        fallback = {
            "inferred_model_type": inferred_model,
            "inferred_output_type": inferred_output,
            "inferred_affected_demographics": inferred_affected,
            "data_sensitivity": "MEDIUM",
            "model_card": f"# Model Card: {payload.name}\n\n## Purpose\n{payload.purpose or 'N/A'}\n\n## Model Type\n{inferred_model}\n\n## Output Type\n{inferred_output}\n\n## Known Limitations\nFallback model card generated without LLM."
        }


        result = await get_llm(self.settings).generate_json(
            prompt, RegistrationOutput, fallback, system=self.SYSTEM_PROMPT, max_tokens=2000,
        )

        # Enrich payload with inferred fields (from LLM or fallback)
        enriched_payload = AISystemCreate(
            name=payload.name,
            llm_provider=result["llm_provider"],
            llm_model=result["llm_model"],
            needs_review=result["needs_review"],
            version=payload.version,
            purpose=payload.purpose,
            model_type=payload.model_type or result.get("inferred_model_type"),
            output_type=payload.output_type or result.get("inferred_output_type"),
            owner_team=payload.owner_team,
            owner_email=payload.owner_email,
            data_sources=payload.data_sources,
            affected_demographics=payload.affected_demographics or result.get(
                "inferred_affected_demographics", []
            ),
            jurisdictions=payload.jurisdictions,
            prediction_endpoint=payload.prediction_endpoint,
        )

        model_card = result.get("model_card", f"# Model Card: {payload.name}\n\nNo model card generated.")

        model_card += f"\n\nLLM provider: {result['llm_provider']}\nLLM model: {result['llm_model'] or 'none'}\nNeeds review: {result['needs_review']}"
        return enriched_payload, model_card
