import pytest
from src.pipeline.relationship_engine import RelationshipEngine
from src.models.schema import Fact, RelationshipType

@pytest.fixture
def engine():
    return RelationshipEngine()

def test_case_1_corroboration(engine):
    f1 = Fact(
        fact_id="f1", pdf_id="pdf1", chunk_id="c1", page_number=1,
        source_text="John Smith resigned as director on March 15, 2024",
        char_start=0, char_end=48, fact_type="executive_change",
        subject="John Smith", predicate="resignation", value="March 15, 2024"
    )
    f2 = Fact(
        fact_id="f2", pdf_id="pdf2", chunk_id="c2", page_number=1,
        source_text="John Smith stepped down from Company A's board in March 2024",
        char_start=0, char_end=58, fact_type="executive_change",
        subject="John Smith", predicate="stepped down", value="March 2024"
    )

    rel = engine.classify_relationship(f1, f2)
    assert rel.relationship_type == RelationshipType.CORROBORATE
    assert rel.confidence > 0.80
    assert len(rel.reasoning) > 0

def test_case_2_contradiction(engine):
    f1 = Fact(
        fact_id="f1", pdf_id="pdf1", chunk_id="c1", page_number=1,
        source_text="John Smith resigned as director on March 15, 2024",
        char_start=0, char_end=48, fact_type="executive_change",
        subject="John Smith", predicate="resignation", value="March 15, 2024"
    )
    f3 = Fact(
        fact_id="f3", pdf_id="pdf3", chunk_id="c3", page_number=1,
        source_text="John Smith resigned on April 1, 2024",
        char_start=0, char_end=35, fact_type="executive_change",
        subject="John Smith", predicate="resignation", value="April 1, 2024"
    )

    rel = engine.classify_relationship(f1, f3)
    assert rel.relationship_type == RelationshipType.CONTRADICT
    assert rel.confidence > 0.80
    assert "April 1" in rel.reasoning or "conflict" in rel.reasoning.lower()

def test_case_3_reconcilable_temporal_scope(engine):
    f_q3 = Fact(
        fact_id="f1", pdf_id="pdf1", chunk_id="c1", page_number=1,
        source_text="Q3 2024 revenue was $5.2M",
        char_start=0, char_end=24, fact_type="financial_metric",
        subject="Company A", predicate="revenue", value="$5.2M", time_scope="Q3 2024"
    )
    f_fy = Fact(
        fact_id="f2", pdf_id="pdf2", chunk_id="c2", page_number=1,
        source_text="Global revenue reached $20M in 2024",
        char_start=0, char_end=34, fact_type="financial_metric",
        subject="Company A", predicate="revenue", value="$20M", time_scope="FY2024"
    )

    rel = engine.classify_relationship(f_q3, f_fy)
    assert rel.relationship_type == RelationshipType.RECONCILABLE
    assert rel.reconciliation_basis == "time_period_difference"
