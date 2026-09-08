import json
from datetime import datetime
from typing import Generator
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Text, LargeBinary, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from src.config import settings

Base = declarative_base()

# Primary document model (kept as PDFModel for compatibility)
class PDFModel(Base):
    __tablename__ = "documents"

    pdf_id = Column(String(64), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    checksum = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 idempotency
    upload_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    total_pages = Column(Integer, default=1)
    parser_metadata = Column(Text, default="{}")

    chunks = relationship("ChunkModel", back_populates="pdf", cascade="all, delete-orphan")
    facts = relationship("FactModel", back_populates="pdf", cascade="all, delete-orphan")

# Alias for newer naming conventions
DocumentModel = PDFModel

class ChunkModel(Base):
    __tablename__ = "chunks"

    chunk_id = Column(String(64), primary_key=True, index=True)
    pdf_id = Column(String(64), ForeignKey("documents.pdf_id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)

    pdf = relationship("PDFModel", back_populates="chunks")
    facts = relationship("FactModel", back_populates="chunk", cascade="all, delete-orphan")

class FactModel(Base):
    __tablename__ = "facts"

    fact_id = Column(String(64), primary_key=True, index=True)
    pdf_id = Column(String(64), ForeignKey("documents.pdf_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(64), ForeignKey("chunks.chunk_id", ondelete="CASCADE"), nullable=False, index=True)

    # New fields to store grounding information
    page_number = Column(Integer, nullable=False)
    source_text = Column(Text, nullable=False)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    fact_type = Column(String(64), nullable=False)
    unit = Column(String(64), nullable=True)
    time_scope = Column(String(64), nullable=True)
    
    subject = Column(String(255), nullable=False, index=True)
    predicate = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(64), default="string")
    
    # Generic extensible JSONB / JSON attributes
    attributes_json = Column(Text, default="{}")
    
    # Evidence & Provenance JSON
    evidence_json = Column(Text, default="{}", nullable=False)
    confidence = Column(Float, default=1.0)
    
    # Metadata
    extracted_at = Column(DateTime, default=datetime.utcnow)
    extraction_model = Column(String(128), default="llm-1")

    pdf = relationship("PDFModel", back_populates="facts")
    chunk = relationship("ChunkModel", back_populates="facts")
    embedding = relationship("FactEmbeddingModel", back_populates="fact", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "fact_id": self.fact_id,
            "pdf_id": self.pdf_id,
            "chunk_id": self.chunk_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "value": self.value,
            "value_type": self.value_type,
            "attributes": json.loads(self.attributes_json) if self.attributes_json else {},
            "evidence": json.loads(self.evidence_json) if self.evidence_json else {},
            "confidence": self.confidence,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
            "extraction_model": self.extraction_model,
        }

class RelationshipModel(Base):
    __tablename__ = "relationships"

    relationship_id = Column(String(64), primary_key=True, index=True)
    fact_a_id = Column(String(64), ForeignKey("facts.fact_id", ondelete="CASCADE"), nullable=False, index=True)
    fact_b_id = Column(String(64), ForeignKey("facts.fact_id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(32), nullable=False, index=True)  # CORROBORATE, CONTRADICT, RECONCILABLE, UNRELATED
    confidence = Column(Float, nullable=False)
    
    # Structured decision factors
    decision_factors_json = Column(Text, default="{}")
    reason = Column(Text, nullable=False)
    evidence_json = Column(Text, default="[]")
    context_used_json = Column(Text, default="[]")
    
    model_version = Column(String(64), default="llm-2")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "relationship_id": self.relationship_id,
            "fact_a_id": self.fact_a_id,
            "fact_b_id": self.fact_b_id,
            "relationship": self.relationship_type,
            "confidence": self.confidence,
            "decision_factors": json.loads(self.decision_factors_json) if self.decision_factors_json else {},
            "reason": self.reason,
            "evidence": json.loads(self.evidence_json) if self.evidence_json else [],
            "context_used": json.loads(self.context_used_json) if self.context_used_json else [],
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class FactEmbeddingModel(Base):
    __tablename__ = "fact_embeddings"

    fact_id = Column(String(64), ForeignKey("facts.fact_id", ondelete="CASCADE"), primary_key=True)
    embedding_bytes = Column(LargeBinary, nullable=False)  # serialized numpy array / pgvector

    fact = relationship("FactModel", back_populates="embedding")

# Database engine setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
