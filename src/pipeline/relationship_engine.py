import uuid
import json
import logging
import time
from datetime import datetime
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.schema import (
    Fact, Relationship, RelationshipEvaluationResult, RelationshipType
)
from src.llm.client import init_chat_model, DeterministicMockLLM
from src.llm.prompts import (
    RELATIONSHIP_CLASSIFICATION_SYSTEM_PROMPT,
    RELATIONSHIP_CLASSIFICATION_USER_PROMPT
)

logger = logging.getLogger(__name__)

class RelationshipEngine:
    """Evaluates and classifies cross-document factual relationships using LLM reasoning."""

    def __init__(self, llm=None):
        self.llm = llm or init_chat_model()

    def _invoke_structured(self, structured_llm, prompt_content):
        return structured_llm.invoke([
            {"role": "system", "content": RELATIONSHIP_CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content}
        ])

    def _invoke_raw(self, full_prompt):
        return self.llm.invoke(full_prompt)

    def classify_relationship(self, fact1: Fact, fact2: Fact) -> Relationship:
        """
        Classifies relationship between two facts with structured reasoning and calibrated confidence.
        """
        if isinstance(self.llm, DeterministicMockLLM):
            eval_result = self.llm.evaluate_relationship(fact1, fact2)
        else:
            prompt_content = RELATIONSHIP_CLASSIFICATION_USER_PROMPT.format(
                fact1_pdf_id=fact1.pdf_id,
                fact1_page=fact1.page_number,
                fact1_type=fact1.fact_type,
                fact1_subject=fact1.subject,
                fact1_predicate=fact1.predicate,
                fact1_value=fact1.value,
                fact1_unit=fact1.unit or "N/A",
                fact1_time_scope=fact1.time_scope or "N/A",
                fact1_source_text=fact1.source_text,
                fact2_pdf_id=fact2.pdf_id,
                fact2_page=fact2.page_number,
                fact2_type=fact2.fact_type,
                fact2_subject=fact2.subject,
                fact2_predicate=fact2.predicate,
                fact2_value=fact2.value,
                fact2_unit=fact2.unit or "N/A",
                fact2_time_scope=fact2.time_scope or "N/A",
                fact2_source_text=fact2.source_text
            )

            # Pacing for Groq Free Tier (30 RPM limit -> ~2.5s per request)
            time.sleep(2.5)
            
            try:
                extraction_model_name = getattr(self.llm, "model_name", "llm-structured").lower()
                if hasattr(self.llm, "with_structured_output") and "qwen" not in extraction_model_name:
                    structured_llm = self.llm.with_structured_output(RelationshipEvaluationResult)
                    eval_result = self._invoke_structured(structured_llm, prompt_content)
                else:
                    full_prompt = f"{RELATIONSHIP_CLASSIFICATION_SYSTEM_PROMPT}\n\n{prompt_content}\n\nReturn JSON: {{'relationship_type': 'CORROBORATE'|'CONTRADICT'|'RECONCILABLE'|'UNRELATED', 'confidence': float, 'reasoning': str, 'reconciliation_basis': str|null}}"
                    resp = self._invoke_raw(full_prompt)
                    raw_text = resp.content if hasattr(resp, "content") else str(resp)
                    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(cleaned)
                    eval_result = RelationshipEvaluationResult(**parsed)
            except Exception as e:
                logger.warning(f"LLM relationship classification failed: {e}. Falling back to deterministic reasoner.")
                mock = DeterministicMockLLM()
                eval_result = mock.evaluate_relationship(fact1, fact2)

        return Relationship(
            relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
            fact_a_id=fact1.fact_id,
            fact_b_id=fact2.fact_id,
            relationship_type=eval_result.relationship_type,
            confidence=eval_result.confidence,
            reasoning=eval_result.reasoning,
            reconciliation_basis=eval_result.reconciliation_basis,
            created_at=datetime.utcnow()
        )
