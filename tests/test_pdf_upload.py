import io
import uuid

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

# Import the FastAPI app from the project
from src.api.main import app

client = TestClient(app)


def _create_dummy_pdf() -> bytes:
    """Generate a minimal one‑page PDF in memory using ReportLab.
    Returns the PDF content as bytes.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, "FactLayer test PDF – dummy content")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def dummy_pdf_bytes():
    """Fixture that provides PDF bytes for the test."""
    return _create_dummy_pdf()


def test_upload_pdf_returns_job_id(dummy_pdf_bytes):
    """Upload the generated PDF and assert the response contains a job_id and a queued status."""
    files = {"file": ("test_dummy.pdf", dummy_pdf_bytes, "application/pdf")}
    response = client.post("/api/pdf/upload", files=files)

    assert response.status_code == 200, "Upload endpoint should return 200 OK"

    json_body = response.json()
    assert "job_id" in json_body, "Response must include a job_id"
    assert "status" in json_body, "Response must include a status field"

    try:
        uuid.UUID(json_body["job_id"])
    except ValueError:
        pytest.fail("job_id is not a valid UUID")

    assert json_body["status"] == "queued", "Initial status should be 'queued'"
