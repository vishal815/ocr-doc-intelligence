"""
Document loader: opens PDFs/images and decides, per page, whether a page
has a usable digital text layer or needs OCR (scanned/image page).

This branch is the single most important architectural decision in the
pipeline: digital pages get exact, instant text; scanned pages fall back
to OCR. We never OCR a page that already has real text.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
from PIL import Image

from app.core.config import RENDER_DPI
from app.core.exceptions import CorruptDocumentError

# A page is considered "digital" if it has at least this many characters
# of extractable text. Anything below this is treated as a scanned image.
MIN_DIGITAL_TEXT_CHARS = 20


@dataclass
class PageSource:
    page_number: int  # 1-indexed
    is_digital: bool
    text_layer: Optional[str]  # raw extracted text, only if digital
    image: Optional[Image.Image]  # rendered PIL image, only if scanned
    width: float
    height: float
    text_dict: Optional[dict] = None  # PyMuPDF "dict" layout output, digital pages only


def load_document(file_path: Path) -> List[PageSource]:
    """
    Load a PDF or a single image file and return one PageSource per page.
    Raises CorruptDocumentError if the file cannot be opened at all.
    """
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            return _load_pdf(file_path)
        else:
            return _load_image(file_path)
    except CorruptDocumentError:
        raise
    except Exception as exc:  # noqa: BLE001 - we intentionally convert any failure
        raise CorruptDocumentError(f"Could not open document: {exc}") from exc


def _load_pdf(file_path: Path) -> List[PageSource]:
    doc = fitz.open(file_path)
    if doc.page_count == 0:
        raise CorruptDocumentError("PDF has zero pages.")

    pages: List[PageSource] = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        rect = page.rect
        if len(text.strip()) >= MIN_DIGITAL_TEXT_CHARS:
            text_dict = page.get_text("dict")
            pages.append(
                PageSource(
                    page_number=i,
                    is_digital=True,
                    text_layer=text,
                    image=None,
                    width=rect.width,
                    height=rect.height,
                    text_dict=text_dict,
                )
            )
        else:
            # Scanned / image-only page -> render to an image for OCR
            zoom = RENDER_DPI / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            pages.append(
                PageSource(
                    page_number=i,
                    is_digital=False,
                    text_layer=None,
                    image=img,
                    width=pix.width,
                    height=pix.height,
                )
            )
    doc.close()
    return pages


def _load_image(file_path: Path) -> List[PageSource]:
    img = Image.open(file_path).convert("RGB")
    return [
        PageSource(
            page_number=1,
            is_digital=False,
            text_layer=None,
            image=img,
            width=img.width,
            height=img.height,
        )
    ]
