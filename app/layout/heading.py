"""
Heading vs paragraph classification.

Digital pages: PyMuPDF's "dict" text extraction gives per-span font size,
so a line is classified as a heading when its font size is meaningfully
larger than the page's median font size (a simple, explainable rule -
no ML model needed).

Scanned pages: no font-size metadata exists, so we use OCR line *height*
(taller text ~= bigger font) as the analogous proxy signal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.core.config import HEADING_FONT_SIZE_RATIO


@dataclass
class TextLine:
    text: str
    bbox: List[float]  # [x0, y0, x1, y1]
    size: float  # font size (digital) or line height in px (scanned)


def extract_lines_from_digital_dict(text_dict: dict) -> List[TextLine]:
    """Flatten PyMuPDF's page.get_text('dict') output into TextLine objects."""
    lines: List[TextLine] = []
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            x0 = min(s["bbox"][0] for s in spans)
            y0 = min(s["bbox"][1] for s in spans)
            x1 = max(s["bbox"][2] for s in spans)
            y1 = max(s["bbox"][3] for s in spans)
            avg_size = sum(s.get("size", 0) for s in spans) / len(spans)
            lines.append(TextLine(text=text, bbox=[x0, y0, x1, y1], size=avg_size))
    return lines


def classify_lines(lines: List[TextLine]) -> List[dict]:
    """
    Return a list of {"text", "bbox", "type"} where type is
    "heading" or "paragraph", based on relative font size / line height.
    """
    if not lines:
        return []
    sizes = [l.size for l in lines if l.size > 0]
    # Baseline = smallest text size on the page. Body/paragraph text is
    # virtually always the smallest font on a page, and headings are
    # always >= body size - this is far more stable with few lines than
    # a median or mode would be.
    baseline_size = min(sizes) if sizes else 0
    threshold = baseline_size * HEADING_FONT_SIZE_RATIO

    results = []
    for line in lines:
        is_heading = (
            baseline_size > 0
            and line.size >= threshold
            and line.size > baseline_size
            and len(line.text) < 120
        )
        results.append(
            {
                "text": line.text,
                "bbox": line.bbox,
                "type": "heading" if is_heading else "paragraph",
            }
        )
    return results
