import os
import shutil
import logging
import json
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.models.database import (
    get_db, init_db, PDFModel, ChunkModel, FactModel, RelationshipModel, Base, engine
)
from src.models.schema import Fact, Relationship, PDFDocument
from src.pipeline.pipeline_runner import PipelineRunner
from src.pipeline.relationship_engine import RelationshipEngine
from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fact_knowledge_api")

pipeline_runner = PipelineRunner()
relationship_engine = RelationshipEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Fact Knowledge Layer API initialized successfully.")
    yield

app = FastAPI(
    title="Fact Knowledge Layer API",
    description="Cross-document factual claim extraction, grounding, and reasoning engine.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static directory
frontend_dir = Path("./frontend")
frontend_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/")
def serve_ui():
    """Serves the Stitch-designed Veritas FactMesh UI."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "status": "online",
        "service": "Fact Knowledge Layer API",
        "endpoints": ["/docs", "/api/pdf/upload", "/api/pdfs"]
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Fact Knowledge Layer API"
    }

from uuid import uuid4
import threading
from fastapi import BackgroundTasks

# In-memory thread-safe status job store
_job_store: Dict[str, Dict[str, Any]] = {}
_job_store_lock = threading.Lock()

def _set_job_status(job_id: str, status: str, result: Any = None, error: Optional[str] = None) -> None:
    with _job_store_lock:
        _job_store[job_id] = {
            "status": status,
            "result": result,
            "error": error
        }

def _process_job(job_id: str, file_path: str, filename: str):
    """Background worker executing the full pipeline and cleaning up temporary files."""
    db = None
    try:
        from src.models.database import SessionLocal
        db = SessionLocal()
        _set_job_status(job_id, "processing")
        result = pipeline_runner.process_pdf(file_path, filename=filename, db=db)
        _set_job_status(job_id, "completed", result=result)
        logger.info(f"Job {job_id} ({filename}) completed successfully.")
    except Exception as exc:
        logger.error(f"Job {job_id} ({filename}) failed: {exc}", exc_info=True)
        _set_job_status(job_id, "failed", error=str(exc))
    finally:
        if db is not None:
            db.close()
        if getattr(settings, "CLEANUP_AFTER_PROCESSING", False):
            try:
                Path(file_path).unlink(missing_ok=True)
                logger.info(f"Cleaned up temporary upload file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete temporary upload file {file_path}: {e}")

@app.post("/api/pdf/upload")
def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload PDF document and queue background processing job."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    job_id = str(uuid4())
    file_path = settings.UPLOAD_DIR / f"{job_id}_{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        _set_job_status(job_id, "queued")
        background_tasks.add_task(_process_job, job_id, str(file_path), file.filename)

        return {
            "status": "queued",
            "job_id": job_id,
            "message": f"File {file.filename} queued for ingestion."
        }
    except Exception as e:
        logger.error(f"Error initiating upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pdf/status/{job_id}")
def get_pdf_status(job_id: str):
    """Check processing status of queued PDF job."""
    with _job_store_lock:
        job = _job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job.get("result"),
        "error": job.get("error")
    }

@app.get("/api/pdfs")
def list_pdfs(db: Session = Depends(get_db)):
    """List all ingested PDF documents with fact counts."""
    pdfs = db.query(PDFModel).order_by(PDFModel.uploaded_at.desc()).all()
    results = []
    for pdf in pdfs:
        count = db.query(FactModel).filter(FactModel.pdf_id == pdf.pdf_id).count()
        results.append({
            "pdf_id": pdf.pdf_id,
            "filename": pdf.filename,
            "uploaded_at": pdf.uploaded_at.isoformat() if pdf.uploaded_at else None,
            "total_pages": pdf.total_pages,
            "facts_count": count
        })
    return results

@app.get("/api/pdfs/{pdf_id}/facts")
def get_pdf_facts(pdf_id: str, db: Session = Depends(get_db)):
    """Get all extracted grounded facts for a specific PDF."""
    pdf = db.query(PDFModel).filter(PDFModel.pdf_id == pdf_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found.")
    
    facts = db.query(FactModel).filter(FactModel.pdf_id == pdf_id).all()
    return [f.to_dict() for f in facts]

@app.get("/api/facts/{fact_id}")
def get_fact_by_id(fact_id: str, db: Session = Depends(get_db)):
    """Get a specific fact along with full source evidence and chunk context."""
    fact = db.query(FactModel).filter(FactModel.fact_id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")
    
    chunk = db.query(ChunkModel).filter(ChunkModel.chunk_id == fact.chunk_id).first()
    pdf = db.query(PDFModel).filter(PDFModel.pdf_id == fact.pdf_id).first()

    return {
        "fact": fact.to_dict(),
        "pdf_filename": pdf.filename if pdf else "Unknown",
        "chunk_context": chunk.text if chunk else "",
        "grounding_valid": True,
        "evidence": {
            "page_number": fact.page_number,
            "source_text": fact.source_text,
            "char_start": fact.char_start,
            "char_end": fact.char_end
        }
    }

@app.get("/api/facts/{fact_id}/relationships")
def get_fact_relationships(fact_id: str, db: Session = Depends(get_db)):
    """Get all relationships involving a specific fact."""
    rels = db.query(RelationshipModel).filter(
        (RelationshipModel.fact_a_id == fact_id) | (RelationshipModel.fact_b_id == fact_id)
    ).all()

    results = []
    for r in rels:
        target_id = r.fact_b_id if r.fact_a_id == fact_id else r.fact_a_id
        target_fact = db.query(FactModel).filter(FactModel.fact_id == target_id).first()
        results.append({
            "relationship": r.to_dict(),
            "target_fact": target_fact.to_dict() if target_fact else None
        })
    return results

@app.get("/api/relationships/contradictions")
def get_all_contradictions(db: Session = Depends(get_db)):
    """Get all detected cross-document contradictions."""
    rels = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "CONTRADICT").all()
    return _format_relationships_with_facts(rels, db)

@app.get("/api/relationships/corroborations")
def get_all_corroborations(db: Session = Depends(get_db)):
    """Get all detected cross-document corroborations."""
    rels = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "CORROBORATE").all()
    return _format_relationships_with_facts(rels, db)

@app.get("/api/relationships/reconcilables")
def get_all_reconcilables(db: Session = Depends(get_db)):
    """Get all detected cross-document reconcilable cases."""
    rels = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "RECONCILABLE").all()
    return _format_relationships_with_facts(rels, db)

@app.get("/api/facts/compare")
def compare_facts(fact1_id: str = Query(...), fact2_id: str = Query(...), db: Session = Depends(get_db)):
    """Directly compare any two facts and evaluate their relationship on-demand."""
    f1 = db.query(FactModel).filter(FactModel.fact_id == fact1_id).first()
    f2 = db.query(FactModel).filter(FactModel.fact_id == fact2_id).first()

    if not f1 or not f2:
        raise HTTPException(status_code=404, detail="One or both facts not found.")

    fact1_obj = Fact(**f1.to_dict())
    fact2_obj = Fact(**f2.to_dict())

    rel = relationship_engine.classify_relationship(fact1_obj, fact2_obj)
    return {
        "fact1": f1.to_dict(),
        "fact2": f2.to_dict(),
        "evaluation": rel.model_dump()
    }

@app.post("/api/reset")
def reset_database():
    """Reset database and clear uploaded demo data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"status": "success", "message": "Database reset successfully."}

def _format_relationships_with_facts(rels: List[RelationshipModel], db: Session) -> List[Dict[str, Any]]:
    results = []
    for r in rels:
        f1 = db.query(FactModel).filter(FactModel.fact_id == r.fact_a_id).first()
        f2 = db.query(FactModel).filter(FactModel.fact_id == r.fact_b_id).first()
        pdf1 = db.query(PDFModel).filter(PDFModel.pdf_id == f1.pdf_id).first() if f1 else None
        pdf2 = db.query(PDFModel).filter(PDFModel.pdf_id == f2.pdf_id).first() if f2 else None

        results.append({
            "relationship": r.to_dict(),
            "fact1": f1.to_dict() if f1 else None,
            "fact1_document": pdf1.filename if pdf1 else "Unknown",
            "fact2": f2.to_dict() if f2 else None,
            "fact2_document": pdf2.filename if pdf2 else "Unknown",
        })
    return results
