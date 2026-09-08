"""
Pydantic models that define the structured output contract of the pipeline.
These map 1:1 to the JSON schema documented in the README.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


BBox = List[float]  # [x0, y0, x1, y1] in page pixel coordinates


class TableCell(BaseModel):
    row: int
    col: int
    text: str = ""
    bbox: Optional[BBox] = None
    nested_table: Optional["TableData"] = None


class TableData(BaseModel):
    rows: int
    cols: int
    cells: List[TableCell] = Field(default_factory=list)


class DocumentElement(BaseModel):
    id: str
    type: str  # "heading" | "paragraph" | "table"
    text: Optional[str] = None
    reading_order: int
    bbox: Optional[BBox] = None
    confidence: Optional[float] = None
    table: Optional[TableData] = None


class PageResult(BaseModel):
    page_number: int
    source: str  # "digital_text_layer" | "ocr"
    status: str = "ok"  # "ok" | "failed"
    warning: Optional[str] = None
    elements: List[DocumentElement] = Field(default_factory=list)


class DocumentResult(BaseModel):
    document_id: str
    filename: str
    page_count: int
    status: str  # "processing" | "processed" | "failed"
    error: Optional[str] = None
    pages: List[PageResult] = Field(default_factory=list)


class UploadResponse(BaseModel):
    document_id: str
    status: str
    message: str


TableCell.model_rebuild()
