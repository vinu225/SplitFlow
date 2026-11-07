"""
Contract PDF Extraction and Source-Highlighted Verbatim Verification Service.
Uses PyMuPDF (fitz) to extract text, characters, and bounding boxes.
Validates that extracted quotes exist verbatim in the document before approving terms.
"""
import hashlib
import fitz  # PyMuPDF
from typing import Any
from app.currencies import to_minor_units

def compute_document_sha256(pdf_bytes: bytes) -> str:
    """Computes SHA-256 fingerprint of the raw PDF file."""
    return hashlib.sha256(pdf_bytes).hexdigest()

def extract_pdf_text_and_blocks(pdf_bytes: bytes) -> tuple[str, list[dict]]:
    """
    Extracts raw plain text and spatial bounding box blocks from PDF bytes.
    Returns (full_text, block_list).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text_parts = []
    blocks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        full_text_parts.append(page_text)

        # Extract text blocks with coordinates: (x0, y0, x1, y1, text, block_no, block_type)
        page_blocks = page.get_text("blocks")
        for b in page_blocks:
            blocks.append({
                "page": page_num + 1,
                "bbox": [round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)],
                "text": b[4].strip()
            })

    doc.close()
    return "\n".join(full_text_parts), blocks

def verify_source_quote(full_document_text: str, source_quote: str, expected_number_str: str) -> bool:
    """
    Validates that:
    1. The source_quote exists verbatim (normalized) inside the extracted document text.
    2. The extracted numerical value appears inside the source quote.
    Flags False if paraphrased or hallucinated.
    """
    if not source_quote or not full_document_text:
        return False

    norm_doc = " ".join(full_document_text.split()).lower()
    norm_quote = " ".join(source_quote.split()).lower()

    # Rule 1: Quote must be verbatim in document
    if norm_quote not in norm_doc:
        return False

    # Rule 2: Expected value must appear within the quote
    clean_val = expected_number_str.replace("$", "").replace(",", "").strip()
    if clean_val and clean_val not in norm_quote:
        return False

    return True

def locate_bounding_boxes_for_quote(pdf_bytes: bytes, quote: str) -> list[dict]:
    """
    Searches the PDF for instances of the quote string and returns precise page bounding boxes.
    Used by frontend to highlight verbatim source evidence.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    matches = []

    clean_quote = quote.strip()
    # Search first 60 chars if quote is long
    search_term = clean_quote[:60] if len(clean_quote) > 60 else clean_quote

    for page_num in range(len(doc)):
        page = doc[page_num]
        rects = page.search_for(search_term)
        for r in rects:
            matches.append({
                "page": page_num + 1,
                "bbox": [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)],
                "matched_text": search_term
            })

    doc.close()
    return matches

