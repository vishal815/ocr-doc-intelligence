"""
Builds a full TableData (with recursive nested tables) from a scanned-page
image, by:
  1. Detecting the outer/parent table grid (tables.detector).
  2. OCR-ing each cell's cropped region for its text.
  3. Re-running table detection INSIDE each cell's cropped region - if a
     smaller table grid is found there, it is attached as a `nested_table`.

This requires no LLM: nested tables are just "the same detector, applied
at a smaller scope", recursed with a depth limit to avoid infinite loops
on noisy images.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from app.core.logging_config import get_logger
from app.ocr.engine import extract_cell_text
from app.schemas.models import TableCell, TableData
from app.tables.detector import DetectedTable, cells_from_grid, detect_tables

logger = get_logger(__name__)

MAX_NESTING_DEPTH = 2
MIN_NESTED_CELL_SIZE = 40  # px - skip nested-detection on cells too small to contain a real sub-table


def build_table_data(gray: np.ndarray, table: DetectedTable, depth: int = 0) -> TableData:
    """Turn a DetectedTable grid into a fully populated TableData, recursing into cells."""
    grid_cells = cells_from_grid(table)
    n_rows = len(table.row_lines) - 1
    n_cols = len(table.col_lines) - 1
    cells: list[TableCell] = []

    for row, col, (x0, y0, x1, y1) in grid_cells:
        crop = gray[y0:y1, x0:x1]
        text = _ocr_cell_text(crop)
        nested = None
        if depth < MAX_NESTING_DEPTH and (x1 - x0) > MIN_NESTED_CELL_SIZE and (y1 - y0) > MIN_NESTED_CELL_SIZE:
            # Inset a few pixels before recursing: a cell crop starts exactly on the
            # parent grid's border line, and without insetting, that border line gets
            # mistaken for an extra internal row/column of the nested table.
            m = 4
            inset = gray[y0 + m : y1 - m, x0 + m : x1 - m]
            if inset.size > 0:
                nested = _detect_nested(inset, depth)
        cells.append(
            TableCell(
                row=row,
                col=col,
                text=text,
                bbox=[float(x0), float(y0), float(x1), float(y1)],
                nested_table=nested,
            )
        )
    return TableData(rows=n_rows, cols=n_cols, cells=cells)


def _ocr_cell_text(crop: np.ndarray) -> str:
    if crop.size == 0:
        return ""
    return extract_cell_text(crop)


def _detect_nested(crop: np.ndarray, depth: int) -> Optional[TableData]:
    inner_tables = detect_tables(crop)
    if not inner_tables:
        return None
    # take the largest inner table found within this cell
    inner = max(inner_tables, key=lambda t: (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1]))
    return build_table_data(crop, inner, depth=depth + 1)
