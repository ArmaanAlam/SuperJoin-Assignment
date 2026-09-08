import pytest
from pathlib import Path
from src.pipeline.pdf_processor import PDFProcessor
from scripts.create_demo_pdfs import create_all_demo_pdfs

@pytest.fixture(scope="module")
def sample_pdfs():
    return create_all_demo_pdfs()

def test_pdf_extraction_page_tracking(sample_pdfs):
    processor = PDFProcessor()
    pdf_path = sample_pdfs[0]
    
    pages_data = processor.extract_text_with_pages(pdf_path)
    assert len(pages_data) >= 1
    assert pages_data[0]["page_number"] == 1
    assert "Company A" in pages_data[0]["text"]
    assert "John Smith" in pages_data[0]["text"]

def test_chunking_with_character_boundaries(sample_pdfs):
    processor = PDFProcessor(chunk_size=400, chunk_overlap=80)
    pdf_path = sample_pdfs[0]
    pages_data = processor.extract_text_with_pages(pdf_path)
    
    chunks = processor.chunk_document("test_pdf_1", pages_data)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.pdf_id == "test_pdf_1"
        assert chunk.page_number >= 1
        assert len(chunk.text) > 0
        assert chunk.char_end >= chunk.char_start
