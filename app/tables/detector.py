"""
Table detection for SCANNED / image pages, using classic OpenCV
morphological line detection. No LLM, no external API - just
horizontal/vertical line extraction and grid reconstruction.

Strategy:
  1. Binarize the image.
  2. Extract long horizontal lines and long vertical lines separately
     using morphological erosion/dilation with wide/tall kernels.
  3. Combine them into a "grid mask" -> contours = candidate table regions.
  4. For each candidate table region, find the row/column line
     positions to reconstruct a cell grid.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

MIN_TABLE_AREA_RATIO = 0.02  # a table region must cover at least this fraction of the page area


@dataclass
class DetectedTable:
    bbox: Tuple[int, int, int, int]  # x0, y0, x1, y1 in image pixel coords
    row_lines: List[int]  # y-positions of horizontal grid lines
    col_lines: List[int]  # x-positions of vertical grid lines


def _binarize(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15
    )


def detect_tables(gray: np.ndarray) -> List[DetectedTable]:
    """Detect table-like grid regions in a grayscale OpenCV image."""
    h, w = gray.shape
    bin_img = _binarize(gray)

    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 25, 10), 1))
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 25, 10)))

    horiz_lines = cv2.erode(bin_img, horiz_kernel, iterations=1)
    horiz_lines = cv2.dilate(horiz_lines, horiz_kernel, iterations=1)

    vert_lines = cv2.erode(bin_img, vert_kernel, iterations=1)
    vert_lines = cv2.dilate(vert_lines, vert_kernel, iterations=1)

    grid_mask = cv2.add(horiz_lines, vert_lines)
    contours, _ = cv2.findContours(grid_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    page_area = h * w
    tables: List[DetectedTable] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if (cw * ch) / page_area < MIN_TABLE_AREA_RATIO:
            continue
        region_h = horiz_lines[y : y + ch, x : x + cw]
        region_v = vert_lines[y : y + ch, x : x + cw]
        row_lines = _line_positions(region_h, axis=1, offset=y)
        col_lines = _line_positions(region_v, axis=0, offset=x)
        if len(row_lines) < 3 or len(col_lines) < 3:
            continue  # need at least a 2x2 cell grid to be a meaningful table (not just a stray box)
        tables.append(DetectedTable(bbox=(x, y, x + cw, y + ch), row_lines=row_lines, col_lines=col_lines))
    return tables


def _line_positions(mask: np.ndarray, axis: int, offset: int) -> List[int]:
    """Collapse a line mask along an axis to find distinct line positions (row or col centers)."""
    projection = np.sum(mask > 0, axis=axis)
    threshold = projection.max() * 0.5 if projection.max() > 0 else 0
    active = projection > threshold
    positions: List[int] = []
    in_run = False
    run_start = 0
    for i, val in enumerate(active):
        if val and not in_run:
            in_run = True
            run_start = i
        elif not val and in_run:
            in_run = False
            positions.append(offset + (run_start + i) // 2)
    if in_run:
        positions.append(offset + (run_start + len(active)) // 2)
    return positions


def cells_from_grid(table: DetectedTable) -> List[Tuple[int, int, Tuple[int, int, int, int]]]:
    """Given detected row/col lines, produce (row_idx, col_idx, cell_bbox) tuples."""
    cells = []
    for r in range(len(table.row_lines) - 1):
        for c in range(len(table.col_lines) - 1):
            x0, x1 = table.col_lines[c], table.col_lines[c + 1]
            y0, y1 = table.row_lines[r], table.row_lines[r + 1]
            cells.append((r, c, (x0, y0, x1, y1)))
    return cells
