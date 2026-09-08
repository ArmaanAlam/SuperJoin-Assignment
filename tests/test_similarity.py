import pytest
import numpy as np
from src.pipeline.embedding_engine import EmbeddingEngine
from src.models.schema import Fact

def test_embedding_generation_and_candidate_search():
    engine = EmbeddingEngine()

    fact1 = Fact(
        fact_id="f1",
        pdf_id="doc1",
        chunk_id="c1",
        page_number=1,
        source_text="John Smith resigned as director on March 15, 2024",
        char_start=0,
        char_end=48,
        fact_type="executive_change",
        subject="John Smith",
        predicate="resignation",
        value="March 15, 2024",
        confidence=0.95
    )

    fact2 = Fact(
        fact_id="f2",
        pdf_id="doc2",
        chunk_id="c2",
        page_number=1,
        source_text="John Smith stepped down from Company A's board in March 2024",
        char_start=0,
        char_end=58,
        fact_type="executive_change",
        subject="John Smith",
        predicate="stepped down",
        value="March 2024",
        confidence=0.95
    )

    fact3 = Fact(
        fact_id="f3",
        pdf_id="doc3",
        chunk_id="c3",
        page_number=1,
        source_text="Headquarters in Austin, Texas",
        char_start=0,
        char_end=28,
        fact_type="location",
        subject="Company A",
        predicate="headquarters_location",
        value="Austin, Texas",
        confidence=0.95
    )

    v1 = engine.embed_fact(fact1)
    v2 = engine.embed_fact(fact2)
    v3 = engine.embed_fact(fact3)

    assert isinstance(v1, np.ndarray)
    assert len(v1) > 0

    # Test candidate retrieval for fact1 among [fact2, fact3]
    candidates = engine.find_similar_candidates(
        query_fact=fact1,
        existing_facts=[fact2, fact3],
        existing_embeddings={"f2": v2, "f3": v3},
        top_k=5,
        threshold=0.50
    )

    assert len(candidates) >= 1
    top_candidate_fact, score = candidates[0]
    assert top_candidate_fact.fact_id == "f2"
    assert score >= 0.50
