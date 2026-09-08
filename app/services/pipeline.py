"""
The pipeline orchestrator. This is the single place that ties together:
  loader -> (digital: text+tables via pdfplumber) OR (scanned: OCR+OpenCV tables)
  -> heading/paragraph classification -> reading-order resolution
  -> Pydantic DocumentResult assembly.

Each page is processed independently and failures on one page never
crash the whole document (they're recorded as page-level "failed" status).
"""
from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path

from app.core.exceptions import CorruptDocumentError, EmptyDocumentError
from app.core.logging_config import get_logger
from app.layout.heading import classify_lines, extract_lines_from_digital_dict
from app.layout.reading_order import assign_reading_order
from app.ocr.engine import run_ocr
from app.pdf.loader import PageSource, load_document
from app.schemas.models import DocumentElement, DocumentResult, PageResult
from app.tables.detector import detect_tables
from app.tables.digital import extract_digital_tables
from app.tables.nested import build_table_data

logger = get_logger(__name__)


def process_document(document_id: str, filename: str, file_path: Path) -> DocumentResult:
    try:
        pages: list[PageSource] = load_document(file_path)
    except CorruptDocumentError as exc:
        return DocumentResult(
            document_id=document_id, filename=filename, page_count=0, status="failed", error=str(exc)
        )

    page_results: list[PageResult] = []
    any_content = False

    for page_source in pages:
        try:
            page_result = (
                _process_digital_page(file_path, page_source)
                if page_source.is_digital
                else _process_scanned_page(page_source)
            )
        except Exception as exc:  # noqa: BLE001 - one bad page must not kill the document
            logger.exception("Page %s failed", page_source.page_number)
            page_result = PageResult(
                page_number=page_source.page_number,
                source="digital_text_layer" if page_source.is_digital else "ocr",
                status="failed",
                warning=str(exc),
                elements=[],
            )
        if page_result.elements:
            any_content = True
        page_results.append(page_result)

    status = "processed"
    if not any_content:
        status = "processed"  # still a valid (if empty) result - warning is on the pages
    return DocumentResult(
        document_id=document_id,
        filename=filename,
        page_count=len(pages),
        status=status,
        pages=page_results,
    )


def _process_digital_page(file_path: Path, page_source: PageSource) -> PageResult:
    table_results = extract_digital_tables(file_path, page_source.page_number)
    table_regions = [bbox for _, bbox in table_results]

    lines = extract_lines_from_digital_dict(page_source.text_dict or {})
    # Drop text lines that fall inside a detected table's bbox - that text
    # is already captured, cell-by-cell, inside the table element itself.
    lines = [l for l in lines if not _inside_any(l.bbox, table_regions)]
    classified = classify_lines(lines)

    elements_raw: list[dict] = [
        {"type": c["type"], "text": c["text"], "bbox": c["bbox"]} for c in classified
    ]

    for table_data, bbox in table_results:
        elements_raw.append({"type": "table", "text": None, "bbox": bbox, "table": table_data})

    elements_raw = assign_reading_order(elements_raw, page_source.width)

    elements = [
        DocumentElement(
            id=f"p{page_source.page_number}_el{i}",
            type=e["type"],
            text=e.get("text"),
            reading_order=e["reading_order"],
            bbox=e["bbox"],
            table=e.get("table"),
        )
        for i, e in enumerate(elements_raw, start=1)
    ]

    warning = None if elements else "No extractable content found on this page."
    return PageResult(
        page_number=page_source.page_number,
        source="digital_text_layer",
        status="ok",
        warning=warning,
        elements=elements,
    )


def _process_scanned_page(page_source: PageSource) -> PageResult:
    img = page_source.image
    arr = np.array(img.convert("L"))  # grayscale

    elements_raw: list[dict] = []

    tables = detect_tables(arr)
    table_regions = [t.bbox for t in tables]

    for t in tables:
        table_data = build_table_data(arr, t)
        x0, y0, x1, y1 = t.bbox
        elements_raw.append(
            {"type": "table", "text": None, "bbox": [float(x0), float(y0), float(x1), float(y1)], "table": table_data}
        )

    # OCR the whole page, then keep only words OUTSIDE detected table regions
    # (table text was already captured, cell-by-cell, above - avoids duplication).
    words = run_ocr(img)
    non_table_words = [w for w in words if not _inside_any(w.bbox, table_regions)]
    text_lines = _group_words_into_lines(non_table_words)
    classified = classify_lines(text_lines)
    for c in classified:
        elements_raw.append({"type": c["type"], "text": c["text"], "bbox": c["bbox"]})

    elements_raw = assign_reading_order(elements_raw, page_source.width)

    elements = [
        DocumentElement(
            id=f"p{page_source.page_number}_el{i}",
            type=e["type"],
            text=e.get("text"),
            reading_order=e["reading_order"],
            bbox=e["bbox"],
            confidence=e.get("confidence"),
            table=e.get("table"),
        )
        for i, e in enumerate(elements_raw, start=1)
    ]

    warning = None if elements else "No extractable content found on this page (OCR returned nothing)."
    return PageResult(
        page_number=page_source.page_number,
        source="ocr",
        status="ok",
        warning=warning,
        elements=elements,
    )


def _inside_any(bbox, regions) -> bool:
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for rx0, ry0, rx1, ry1 in regions:
        if rx0 <= cx <= rx1 and ry0 <= cy <= ry1:
            return True
    return False


def _group_words_into_lines(words) -> list:
    """Group OCR words that share roughly the same y-band into text lines."""
    from app.layout.heading import TextLine

    if not words:
        return []
    words = sorted(words, key=lambda w: (w.top, w.left))
    lines: list[TextLine] = []
    current: list = [words[0]]
    for w in words[1:]:
        prev = current[-1]
        if abs(w.top - prev.top) <= max(prev.height, w.height) * 0.6:
            current.append(w)
        else:
            lines.append(_line_from_words(current))
            current = [w]
    if current:
        lines.append(_line_from_words(current))
    return lines


def _line_from_words(words) -> "TextLine":  # noqa: F821 - forward ref, imported inline above
    from app.layout.heading import TextLine

    words = sorted(words, key=lambda w: w.left)
    text = " ".join(w.text for w in words)
    x0 = min(w.left for w in words)
    y0 = min(w.top for w in words)
    x1 = max(w.left + w.width for w in words)
    y1 = max(w.top + w.height for w in words)
    avg_height = sum(w.height for w in words) / len(words)
    return TextLine(text=text, bbox=[float(x0), float(y0), float(x1), float(y1)], size=avg_height)
