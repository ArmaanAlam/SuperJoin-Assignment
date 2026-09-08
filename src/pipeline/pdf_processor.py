import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pdfplumber

from src.models.schema import Chunk
from src.config import settings

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Extracts text and constructs grounded overlapping chunks from PDF documents."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def extract_text_with_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from PDF preserving page numbers.
        Returns a list of dicts: [{"page_number": int, "text": str}]
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

        pages_data = []
        with pdfplumber.open(pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                # Clean redundant whitespace while keeping paragraph structure
                cleaned_text = "\n".join([line.strip() for line in text.split("\n") if line.strip()])
                pages_data.append({
                    "page_number": idx,
                    "text": cleaned_text
                })
        return pages_data

    def chunk_document(self, pdf_id: str, pages_data: List[Dict[str, Any]]) -> List[Chunk]:
        """
        Chunks text into overlapping segments, preserving paragraph boundaries when possible.
        Tracks character offsets and page numbers.
        """
        chunks: List[Chunk] = []

        for p_data in pages_data:
            page_num = p_data["page_number"]
            page_text = p_data["text"]

            if not page_text.strip():
                continue

            # If page text is within chunk size, create a single chunk
            if len(page_text) <= self.chunk_size:
                chunk_id = f"chk_{pdf_id}_p{page_num}_0"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    pdf_id=pdf_id,
                    page_number=page_num,
                    text=page_text,
                    char_start=0,
                    char_end=len(page_text)
                ))
                continue

            # Multi-chunk sliding window with paragraph awareness
            paragraphs = page_text.split("\n")
            current_chunk_text = ""
            current_start_char = 0
            chunk_index = 0

            cursor = 0
            for para in paragraphs:
                para_len = len(para) + 1  # include newline
                if len(current_chunk_text) + len(para) > self.chunk_size and current_chunk_text:
                    # Finalize current chunk
                    chunk_id = f"chk_{pdf_id}_p{page_num}_{chunk_index}"
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        pdf_id=pdf_id,
                        page_number=page_num,
                        text=current_chunk_text.strip(),
                        char_start=current_start_char,
                        char_end=cursor
                    ))
                    chunk_index += 1

                    # Retain overlap from end of current chunk
                    overlap_chars = current_chunk_text[-self.chunk_overlap:] if len(current_chunk_text) > self.chunk_overlap else current_chunk_text
                    current_start_char = max(0, cursor - len(overlap_chars))
                    current_chunk_text = overlap_chars + "\n" + para
                else:
                    if current_chunk_text:
                        current_chunk_text += "\n" + para
                    else:
                        current_chunk_text = para
                cursor += para_len

            if current_chunk_text.strip():
                chunk_id = f"chk_{pdf_id}_p{page_num}_{chunk_index}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    pdf_id=pdf_id,
                    page_number=page_num,
                    text=current_chunk_text.strip(),
                    char_start=current_start_char,
                    char_end=len(page_text)
                ))

        return chunks
