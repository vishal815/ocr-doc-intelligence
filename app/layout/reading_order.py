"""
Reading-order resolver.

Fixes the classic multi-column OCR problem where raw top-to-bottom
ordering interleaves text from different columns. Approach:

  1. Cluster all elements' x-centers into "column bands" by looking for
     large horizontal gaps between sorted x-centers (no columns crossing
     that gap).
  2. Order bands left -> right.
  3. Within each band, sort elements top -> bottom (by y0).

This is deterministic and needs no ML - just geometry.
"""
from __future__ import annotations

from typing import List

from app.core.config import COLUMN_GAP_RATIO


def assign_reading_order(elements: List[dict], page_width: float) -> List[dict]:
    """
    elements: list of dicts each containing at least a "bbox": [x0,y0,x1,y1].
    Returns the same list with a "reading_order" key added (1-indexed),
    and re-ordered accordingly.
    """
    if not elements:
        return elements

    centers = sorted((e["bbox"][0] + e["bbox"][2]) / 2 for e in elements)
    gap_threshold = page_width * COLUMN_GAP_RATIO

    # Find column band boundaries: a "gap" between consecutive sorted
    # x-centers bigger than the threshold starts a new column band.
    band_edges = [centers[0]]
    for prev, curr in zip(centers, centers[1:]):
        if curr - prev > gap_threshold:
            band_edges.append(curr)

    def band_index(x_center: float) -> int:
        idx = 0
        for i, edge in enumerate(band_edges):
            if x_center >= edge:
                idx = i
        return idx

    for e in elements:
        x_center = (e["bbox"][0] + e["bbox"][2]) / 2
        e["_band"] = band_index(x_center)

    elements.sort(key=lambda e: (e["_band"], e["bbox"][1], e["bbox"][0]))

    for i, e in enumerate(elements, start=1):
        e["reading_order"] = i
        e.pop("_band", None)

    return elements
