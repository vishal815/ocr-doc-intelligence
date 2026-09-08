"""
Table extraction for DIGITAL pages (PDFs that already have a text layer).
Uses pdfplumber, a pure-Python library with no external binary dependency
(unlike Camelot, which needs Ghostscript) - much more reliable to install
and run within a 48-hour window.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pdfplumber

from app.core.logging_config import get_logger
from app.schemas.models import TableCell, TableData

logger = get_logger(__name__)


def extract_digital_tables(file_path: Path, page_number: int) -> List[Tuple[TableData, List[float]]]:
    """
    Extract tables from a single digital (1-indexed) page.
    Returns a list of (TableData, bbox) tuples. bbox is the table's
    bounding box on the page in PDF point coordinates.
    """
    results: List[Tuple[TableData, List[float]]] = []
    with pdfplumber.open(file_path) as pdf:
        if page_number - 1 >= len(pdf.pages):
            return results
        page = pdf.pages[page_number - 1]
        found_tables = page.find_tables()
        for t in found_tables:
            raw_rows = t.extract()
            if not raw_rows:
                continue
            cells: List[TableCell] = []
            for r, row in enumerate(raw_rows):
                for c, val in enumerate(row):
                    cells.append(TableCell(row=r, col=c, text=(val or "").strip()))
            table_data = TableData(rows=len(raw_rows), cols=max(len(r) for r in raw_rows), cells=cells)
            bbox = [float(t.bbox[0]), float(t.bbox[1]), float(t.bbox[2]), float(t.bbox[3])]
            results.append((table_data, bbox))
    return results
