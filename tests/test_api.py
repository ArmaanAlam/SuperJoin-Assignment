import time
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.models.database import Base, engine, SessionLocal
from scripts.create_demo_pdfs import create_all_demo_pdfs

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def _wait_for_job(job_id: str, timeout: int = 30):
    start = time.time()
    while time.time() - start < timeout:
        res = client.get(f"/api/pdf/status/{job_id}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] == "completed":
            return data["result"]
        elif data["status"] == "failed":
            raise RuntimeError(f"Job failed: {data.get('error')}")
        time.sleep(0.5)
    raise TimeoutError("Job timed out")

def test_api_root_and_health():
    # Test HTML web UI serving
    response = client.get("/")
    assert response.status_code == 200

    # Test health check endpoint
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "online"

def test_api_upload_and_inspect_endpoints():
    pdf_paths = create_all_demo_pdfs()
    
    # 1. Upload PDF 1
    with open(pdf_paths[0], "rb") as f:
        file_bytes = f.read()
    resp = client.post("/api/pdf/upload", files={"file": ("doc1.pdf", file_bytes, "application/pdf")})
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    assert resp.json()["status"] == "queued"
    
    result = _wait_for_job(job_id)
    pdf1_id = result["pdf_id"]
    assert result["facts_count"] >= 1

    # 2. List PDFs
    resp_list = client.get("/api/pdfs")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    # 3. Get facts for PDF
    resp_facts = client.get(f"/api/pdfs/{pdf1_id}/facts")
    assert resp_facts.status_code == 200
    facts_list = resp_facts.json()
    assert len(facts_list) >= 1
    fact1_id = facts_list[0]["fact_id"]

    # 4. Get specific fact with evidence
    resp_single_fact = client.get(f"/api/facts/{fact1_id}")
    assert resp_single_fact.status_code == 200
    assert "evidence" in resp_single_fact.json()
    assert resp_single_fact.json()["grounding_valid"] is True

    # 5. Upload PDF 2 to trigger cross-document relationships
    with open(pdf_paths[1], "rb") as f:
        file_bytes2 = f.read()
    resp2 = client.post("/api/pdf/upload", files={"file": ("doc2.pdf", file_bytes2, "application/pdf")})
    assert resp2.status_code == 200
    job2_id = resp2.json()["job_id"]
    _wait_for_job(job2_id)

    # 6. Check corroborations endpoint
    resp_corrobs = client.get("/api/relationships/corroborations")
    assert resp_corrobs.status_code == 200
    assert isinstance(resp_corrobs.json(), list)

