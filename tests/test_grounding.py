import pytest
from src.pipeline.fact_extractor import FactExtractor
from src.models.schema import Chunk

def test_grounding_valid_offsets():
    extractor = FactExtractor()
    chunk_text = "Corporate update: In our governance update, John Smith resigned as director on March 15, 2024."
    chunk = Chunk(
        chunk_id="chk_1",
        pdf_id="pdf_1",
        page_number=1,
        text=chunk_text,
        char_start=0,
        char_end=len(chunk_text)
    )

    facts = extractor.extract_facts_from_chunk(chunk)
    assert len(facts) >= 1
    
    for f in facts:
        # Verify that slicing chunk.text using [char_start:char_end] matches source_text exactly
        extracted_slice = chunk.text[f.char_start:f.char_end]
        assert extracted_slice.lower() == f.source_text.lower()
        assert f.confidence > 0.0

def test_grounding_rejects_hallucination():
    extractor = FactExtractor()
    chunk_text = "Company A reported strong financial performance."
    # Direct quote locator test
    span = extractor._locate_exact_quote(chunk_text, "Non-existent hallucinated quote")
    assert span is None
