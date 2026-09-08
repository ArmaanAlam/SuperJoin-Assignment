from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class RelationshipType(str, Enum):
    CORROBORATE = "CORROBORATE"
    CONTRADICT = "CONTRADICT"
    RECONCILABLE = "RECONCILABLE"
    UNRELATED = "UNRELATED"
    NOT_COMPARABLE = "NOT_COMPARABLE"

class Evidence(BaseModel):
    page: int = Field(description="Page number in source document (1-indexed)")
    chunk_id: str = Field(description="Unique identifier of the source text chunk")
    quote: str = Field(description="Exact verbatim quote from the source text chunk")

class Fact(BaseModel):
    fact_id: str = Field(description="Unique UUID for this extracted fact")
    pdf_id: str = Field(description="Identifier of the source PDF document")
    chunk_id: str = Field(description="Chunk identifier containing the fact")
    page_number: int = Field(description="Page number where the fact appears")
    source_text: str = Field(description="Exact verbatim quote from the source")
    char_start: int = Field(description="Start character offset of the quote in the chunk")
    char_end: int = Field(description="End character offset of the quote in the chunk")
    fact_type: str = Field(description="Dynamic type inferred by LLM 1")
    subject: str = Field(description="Entity the fact is about")
    predicate: str = Field(description="Attribute or action being claimed")
    value: Union[str, float, int, bool] = Field(description="Claimed value or state")
    unit: Optional[str] = Field(default=None, description="Measurement unit if applicable")
    time_scope: Optional[str] = Field(default=None, description="Temporal scope if applicable")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Dynamic extra attributes")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_model: str = Field(default="default")

    def to_embedding_text(self) -> str:
        parts = [self.subject, self.predicate, str(self.value)]
        if self.unit:
            parts.append(f"({self.unit})")
        if self.time_scope:
            parts.append(f"[{self.time_scope}]")
        return " ".join(parts)

class ExtractedFactItem(BaseModel):
    """Schema used during dynamic LLM 1 extraction from text chunk."""
    source_text: str = Field(description="Exact verbatim quote from the text chunk")
    fact_type: str = Field(description="Inferred fact type")
    subject: str = Field(description="Entity or subject of the fact")
    predicate: str = Field(description="Attribute or action being claimed")
    value: Union[str, float, int, bool] = Field(description="Claimed value or state")
    unit: Optional[str] = Field(default=None)
    time_scope: Optional[str] = Field(default=None)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    attributes: Dict[str, Any] = Field(default_factory=dict)

class ExtractionResult(BaseModel):
    facts: List[ExtractedFactItem] = Field(default_factory=list)

class DecisionFactors(BaseModel):
    same_subject: Optional[bool] = None
    same_predicate: Optional[bool] = None
    unit_compatible: Optional[bool] = None
    same_period: Optional[bool] = None
    same_scope: Optional[bool] = None
    definition_compatible: Optional[bool] = None

class PDFDocument(BaseModel):
    pdf_id: str
    filename: str
    upload_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    total_pages: int
    fact_count: Optional[int] = 0

class RelationshipEvidenceItem(BaseModel):
    document_id: str
    page: int
    quote: str

class Relationship(BaseModel):
    relationship_id: str
    fact_a_id: str = Field(description="Fact A identifier")
    fact_b_id: str = Field(description="Fact B identifier")
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0)
    decision_factors: DecisionFactors = Field(default_factory=DecisionFactors)
    reasoning: str = Field(description="Grounded explanation of relationship")
    reconciliation_basis: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RelationshipEvaluationResult(BaseModel):
    relationship_type: RelationshipType = Field(description="CORROBORATE, CONTRADICT, RECONCILABLE, or UNRELATED")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Detailed reasoning")
    reconciliation_basis: Optional[str] = None
    decision_factors: DecisionFactors = Field(default_factory=DecisionFactors)

class Chunk(BaseModel):
    chunk_id: str
    pdf_id: str = Field(description="Identifier of the source PDF document")
    page_number: int
    text: str
    char_start: int
    char_end: int

class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    checksum: str
    upload_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    total_pages: int
    facts_count: Optional[int] = 0
