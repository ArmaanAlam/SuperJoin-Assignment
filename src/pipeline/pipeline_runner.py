import hashlib


def calculate_checksum(file_path: str) -> str:
    """Calculate SHA-256 checksum of a file, reading in chunks for efficiency."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            sha256.update(block)
    return sha256.hexdigest()

import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from src.models.database import (
    PDFModel, ChunkModel, FactModel, RelationshipModel, FactEmbeddingModel, get_db, init_db, SessionLocal
)
from src.models.schema import Fact, Chunk, Relationship, RelationshipType
from src.pipeline.pdf_processor import PDFProcessor
from src.pipeline.fact_extractor import FactExtractor
from src.pipeline.embedding_engine import EmbeddingEngine
from src.pipeline.relationship_engine import RelationshipEngine

logger = logging.getLogger(__name__)

class PipelineRunner:
    """End-to-end ingestion and knowledge graph orchestrator."""

    def __init__(
        self,
        pdf_processor: Optional[PDFProcessor] = None,
        fact_extractor: Optional[FactExtractor] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        relationship_engine: Optional[RelationshipEngine] = None
    ):
        init_db()
        self.pdf_processor = pdf_processor or PDFProcessor()
        self.fact_extractor = fact_extractor or FactExtractor()
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.relationship_engine = relationship_engine or RelationshipEngine()

    def process_pdf(self, pdf_path: str, filename: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Executes full ingestion pipeline for a PDF document.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            path = Path(pdf_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {pdf_path}")

            fname = filename or path.name
            pdf_id = f"pdf_{uuid.uuid4().hex[:8]}"

            logger.info(f"Starting processing for PDF: {fname} (ID: {pdf_id})")

            # 1. PDF Text & Page Extraction
            pages_data = self.pdf_processor.extract_text_with_pages(str(path))
            total_pages = len(pages_data)

            pdf_record = PDFModel(
                pdf_id=pdf_id,
                filename=fname,
                checksum=calculate_checksum(str(path)),
                upload_path=str(path.absolute()),
                uploaded_at=datetime.utcnow(),
                total_pages=total_pages
            )
            db.add(pdf_record)
            db.commit()

            # 2. Chunking
            chunks: List[Chunk] = self.pdf_processor.chunk_document(pdf_id, pages_data)
            for chk in chunks:
                chk_record = ChunkModel(
                    chunk_id=chk.chunk_id,
                    pdf_id=chk.pdf_id,
                    page_number=chk.page_number,
                    text=chk.text,
                    char_start=chk.char_start,
                    char_end=chk.char_end
                )
                db.add(chk_record)
            db.commit()

            # 3. Dynamic Fact Extraction & Grounding
            new_facts: List[Fact] = []
            for chk in chunks:
                extracted = self.fact_extractor.extract_facts_from_chunk(chk)
                new_facts.extend(extracted)

            logger.info(f"Extracted {len(new_facts)} grounded facts from {fname}")

            # Store facts and compute embeddings
            new_embeddings: Dict[str, Any] = {}
            for fact in new_facts:
                fact_rec = FactModel(
                    fact_id=fact.fact_id,
                    pdf_id=fact.pdf_id,
                    chunk_id=fact.chunk_id,
                    page_number=fact.page_number,
                    source_text=fact.source_text,
                    char_start=fact.char_start,
                    char_end=fact.char_end,
                    fact_type=fact.fact_type,
                    subject=fact.subject,
                    predicate=fact.predicate,
                    value=fact.value,
                    unit=fact.unit,
                    time_scope=fact.time_scope,
                    confidence=fact.confidence,
                    attributes_json=json.dumps(fact.attributes),
                    extracted_at=fact.extracted_at,
                    extraction_model=fact.extraction_model
                )
                db.add(fact_rec)

                # Vector Embedding
                emb_vec = self.embedding_engine.embed_fact(fact)
                new_embeddings[fact.fact_id] = emb_vec
                
                emb_rec = FactEmbeddingModel(
                    fact_id=fact.fact_id,
                    embedding_bytes=self.embedding_engine.serialize_embedding(emb_vec)
                )
                db.add(emb_rec)

            db.commit()

            # 4. Cross-Document Similarity & Relationship Classification
            # Fetch all existing facts from other PDFs
            all_existing_fact_recs = db.query(FactModel).filter(FactModel.pdf_id != pdf_id).all()
            existing_facts: List[Fact] = []
            existing_embeddings: Dict[str, Any] = {}

            for f_rec in all_existing_fact_recs:
                f_obj = Fact(
                    fact_id=f_rec.fact_id,
                    pdf_id=f_rec.pdf_id,
                    chunk_id=f_rec.chunk_id,
                    page_number=f_rec.page_number,
                    source_text=f_rec.source_text,
                    char_start=f_rec.char_start,
                    char_end=f_rec.char_end,
                    fact_type=f_rec.fact_type,
                    subject=f_rec.subject,
                    predicate=f_rec.predicate,
                    value=f_rec.value,
                    unit=f_rec.unit,
                    time_scope=f_rec.time_scope,
                    confidence=f_rec.confidence,
                    attributes=json.loads(f_rec.attributes_json) if f_rec.attributes_json else {},
                    extracted_at=f_rec.extracted_at,
                    extraction_model=f_rec.extraction_model
                )
                existing_facts.append(f_obj)
                
                # Fetch embedding if stored
                emb_db = db.query(FactEmbeddingModel).filter(FactEmbeddingModel.fact_id == f_rec.fact_id).first()
                if emb_db:
                    existing_embeddings[f_rec.fact_id] = self.embedding_engine.deserialize_embedding(emb_db.embedding_bytes)

            discovered_relationships: List[Relationship] = []

            for new_fact in new_facts:
                candidate_pairs = self.embedding_engine.find_similar_candidates(
                    query_fact=new_fact,
                    existing_facts=existing_facts,
                    existing_embeddings=existing_embeddings,
                    top_k=15,
                    threshold=0.55
                )

                for candidate_fact, sim_score in candidate_pairs:
                    # Avoid duplicate relationship pairs
                    existing_rel = db.query(RelationshipModel).filter(
                    ((RelationshipModel.fact_a_id == new_fact.fact_id) & (RelationshipModel.fact_b_id == candidate_fact.fact_id)) |
                    ((RelationshipModel.fact_a_id == candidate_fact.fact_id) & (RelationshipModel.fact_b_id == new_fact.fact_id))
                ).first()

                    if existing_rel:
                        continue

                    # Classify relationship
                    rel = self.relationship_engine.classify_relationship(new_fact, candidate_fact)
                    if rel.relationship_type != RelationshipType.UNRELATED:
                        rel_record = RelationshipModel(
                            relationship_id=rel.relationship_id,
                            fact_a_id=rel.fact_a_id,
                            fact_b_id=rel.fact_b_id,
                            relationship_type=rel.relationship_type.value,
                            confidence=rel.confidence,
                            reason=rel.reasoning,
                            created_at=rel.created_at
                        )
                        db.add(rel_record)
                        discovered_relationships.append(rel)

            db.commit()

            return {
                "pdf_id": pdf_id,
                "filename": fname,
                "total_pages": total_pages,
                "chunks_count": len(chunks),
                "facts_count": len(new_facts),
                "facts": [f.model_dump() for f in new_facts],
                "relationships_count": len(discovered_relationships),
                "relationships": [r.model_dump() for r in discovered_relationships]
            }

        finally:
            if close_db:
                db.close()
