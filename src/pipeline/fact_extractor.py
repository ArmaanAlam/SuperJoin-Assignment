import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional, Tuple
import time
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.schema import Fact, Chunk, ExtractedFactItem, ExtractionResult
from src.llm.client import init_chat_model, DeterministicMockLLM
from src.llm.prompts import FACT_EXTRACTION_SYSTEM_PROMPT, FACT_EXTRACTION_USER_PROMPT

logger = logging.getLogger(__name__)

class FactExtractor:
    """Extracts grounded facts from document chunks with dynamic schemas."""

    def __init__(self, llm=None):
        self.llm = llm or init_chat_model()

    def _locate_exact_quote(self, chunk_text: str, quote: str) -> Optional[Tuple[int, int]]:
        """
        Locates the exact character span [start, end] of quote within chunk_text.
        Provides robust normalization fallback if spacing slightly differs.
        """
        if not quote or not chunk_text:
            return None

        # 1. Direct exact match
        idx = chunk_text.find(quote)
        if idx != -1:
            return (idx, idx + len(quote))

        # 2. Case-insensitive exact match
        idx = chunk_text.lower().find(quote.lower())
        if idx != -1:
            return (idx, idx + len(quote))

        # 3. Normalized whitespace search
        norm_quote = " ".join(quote.split())
        words = norm_quote.split()
        if not words:
            return None

        first_word = words[0]
        start_search = 0
        while True:
            pos = chunk_text.lower().find(first_word.lower(), start_search)
            if pos == -1:
                break
            
            # Check if sequence of words matches from pos
            segment = chunk_text[pos:]
            norm_segment = " ".join(segment.split())
            if norm_segment.startswith(norm_quote):
                # Count length in original text
                matched_chars = 0
                word_count = 0
                for token in chunk_text[pos:].split():
                    word_count += 1
                    if word_count == len(words):
                        # Found end
                        sub = chunk_text[pos:pos + len(" ".join(chunk_text[pos:].split()[:word_count])) + 10]
                        # Trim to exact end
                        end_pos = pos + len(quote)
                        return (pos, min(len(chunk_text), pos + len(quote)))
            start_search = pos + 1

        return None

    def _invoke_structured(self, structured_llm, prompt):
        return structured_llm.invoke([
            {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

    def _invoke_raw(self, prompt):
        return self.llm.invoke(prompt)

    def extract_facts_from_chunk(self, chunk: Chunk) -> List[Fact]:
        """Extracts facts from a chunk and enforces strict grounding validation."""
        raw_facts: List[ExtractedFactItem] = []

        if isinstance(self.llm, DeterministicMockLLM):
            extraction_result = self.llm.extract_facts(chunk.text)
            raw_facts = extraction_result.facts
            extraction_model_name = getattr(self.llm, "model_name", "deterministic-mock")
        else:
            extraction_model_name = getattr(self.llm, "model_name", "llm-structured").lower()
            # Pacing for Groq Free Tier (30 RPM limit -> ~2.5s per request)
            time.sleep(2.5)
            
            try:
                # Use structured output or standard prompt invocation
                if hasattr(self.llm, "with_structured_output") and "qwen" not in extraction_model_name:
                    structured_llm = self.llm.with_structured_output(ExtractionResult)
                    prompt = FACT_EXTRACTION_USER_PROMPT.format(text=chunk.text)
                    result = self._invoke_structured(structured_llm, prompt)
                    if isinstance(result, ExtractionResult):
                        raw_facts = result.facts
                else:
                    json_instruction = "\n\nCRITICAL: You MUST return a valid JSON object matching this schema exactly: {\"facts\": [{\"source_text\": \"...\", \"fact_type\": \"...\", \"subject\": \"...\", \"predicate\": \"...\", \"value\": \"...\", \"unit\": null, \"time_scope\": null, \"confidence\": 0.9, \"attributes\": {}}]}"
                    prompt = f"{FACT_EXTRACTION_SYSTEM_PROMPT}{json_instruction}\n\n{FACT_EXTRACTION_USER_PROMPT.format(text=chunk.text)}"
                    res = self._invoke_raw(prompt)
                    # Attempt to parse json from content
                    content = res.content if hasattr(res, "content") else str(res)
                    # Clean markdown codeblocks if any
                    content = content.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(content)
                    raw_facts = [ExtractedFactItem(**item) for item in parsed.get("facts", [])]
            except Exception as e:
                logger.warning(f"LLM extraction encountered issue: {e}. Falling back to deterministic extractor.")
                mock = DeterministicMockLLM()
                raw_facts = mock.extract_facts(chunk.text).facts
                extraction_model_name = "fallback-deterministic-extractor"

        grounded_facts: List[Fact] = []

        for item in raw_facts:
            span = self._locate_exact_quote(chunk.text, item.source_text)
            
            if span:
                char_start, char_end = span
                # Strict verification
                extracted_slice = chunk.text[char_start:char_end]
                # Grounded fact
                fact = Fact(
                    fact_id=f"fact_{uuid.uuid4().hex[:10]}",
                    pdf_id=chunk.pdf_id,
                    chunk_id=chunk.chunk_id,
                    page_number=chunk.page_number,
                    source_text=extracted_slice,
                    char_start=char_start,
                    char_end=char_end,
                    fact_type=item.fact_type,
                    subject=item.subject,
                    predicate=item.predicate,
                    value=item.value,
                    unit=item.unit,
                    time_scope=item.time_scope,
                    confidence=item.confidence,
                    attributes=item.attributes,
                    extracted_at=datetime.utcnow(),
                    extraction_model=extraction_model_name
                )
                grounded_facts.append(fact)
            else:
                logger.warning(f"Grounding validation rejected hallucinated quote: '{item.source_text}'")

        return grounded_facts
