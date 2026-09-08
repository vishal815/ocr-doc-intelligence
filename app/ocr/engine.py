"""
OCR engine wrapper. Uses Tesseract (via pytesseract) as the core, local,
open-source OCR engine - no API keys, fully offline.

Also applies basic OpenCV preprocessing (grayscale, denoise, deskew,
adaptive threshold) before OCR to improve accuracy on scanned pages.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import cv2
import numpy as np
import pytesseract
from PIL import Image

from app.core.config import TESSERACT_LANG
from app.core.exceptions import OCRFailureError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OCRWord:
    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float

    @property
    def bbox(self) -> List[float]:
        return [float(self.left), float(self.top), float(self.left + self.width), float(self.top + self.height)]


def preprocess_image(img: Image.Image) -> np.ndarray:
    """Deskew + denoise + binarize a PIL image, return an OpenCV array ready for OCR."""
    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # Deskew using the minAreaRect of all non-white pixels
    coords = np.column_stack(np.where(gray < 250))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        # Only correct mild, realistic scan skew. minAreaRect over all foreground
        # pixels is unreliable on pages dominated by table grid lines (straight,
        # axis-aligned rectangles can throw the angle estimate toward +/-90 deg),
        # so anything beyond a plausible hand-scan skew is treated as a bad
        # estimate and ignored rather than applied.
        if 0.5 < abs(angle) < 15:
            (h, w) = gray.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return thresh


def run_ocr(img: Image.Image) -> List[OCRWord]:
    """
    Run Tesseract OCR on a preprocessed image and return word-level results
    with bounding boxes and confidence scores.
    """
    try:
        processed = preprocess_image(img)
        data = pytesseract.image_to_data(
            processed, lang=TESSERACT_LANG, output_type=pytesseract.Output.DICT
        )
    except Exception as exc:  # noqa: BLE001
        raise OCRFailureError(f"Tesseract OCR failed: {exc}") from exc

    words: List[OCRWord] = []
    n = len(data.get("text", []))
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        words.append(
            OCRWord(
                text=text,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
                conf=conf,
            )
        )
    return words


def extract_cell_text(crop: np.ndarray, border_margin: int = 6) -> str:
    """
    OCR a single table-cell crop (already grayscale). Cell crops are small and
    usually include the cell's own border lines right at the edge - running the
    full page-level preprocessing (deskew + adaptive threshold) on such a small,
    border-dominated image tends to wipe out the text entirely. So this uses a
    lighter path: trim the border lines off, pad with white space, and OCR
    directly - no deskew, no adaptive threshold.
    """
    h, w = crop.shape[:2]
    m = min(border_margin, h // 3, w // 3)
    inset = crop[m : h - m, m : w - m] if h > 2 * m and w > 2 * m else crop
    if inset.size == 0:
        return ""
    padded = cv2.copyMakeBorder(inset, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
    try:
        return pytesseract.image_to_string(padded, lang=TESSERACT_LANG).strip()
    except Exception:  # noqa: BLE001 - a single bad cell must never kill the pipeline
        logger.warning("Cell OCR failed; leaving text empty.")
        return ""
