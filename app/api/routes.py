from __future__ import annotations

import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.core.exceptions import (
    CorruptDocumentError,
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.core.logging_config import get_logger
from app.schemas.models import DocumentResult, UploadResponse
from app.services.pipeline import process_document
from app.services.text_export import document_to_text
from app.services.validation import validate_upload
from app.storage import db, files

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()

    try:
        validate_upload(file.filename, content)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    document_id = str(uuid.uuid4())
    saved_path = files.save_upload(document_id, file.filename, content)
    db.create_document_record(document_id, file.filename)

    try:
        result = process_document(document_id, file.filename, saved_path)
    except CorruptDocumentError as exc:
        db.update_document_status(document_id, "failed", str(exc))
        raise HTTPException(status_code=422, detail=f"Unreadable document: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - never let an unexpected error 500 without context
        logger.exception("Unexpected pipeline failure for %s", document_id)
        db.update_document_status(document_id, "failed", str(exc))
        raise HTTPException(status_code=500, detail="Internal processing error.") from exc

    db.update_document_status(document_id, result.status, result.error)
    db.save_result_json(document_id, result.model_dump())

    return UploadResponse(
        document_id=document_id,
        status=result.status,
        message="Document processed successfully." if result.status == "processed" else "Processing failed.",
    )


@router.get("/documents/{document_id}", response_model=DocumentResult)
def get_document(document_id: str):
    record = db.get_document_record(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    result_json = db.load_result_json(document_id)
    if result_json is None:
        return DocumentResult(
            document_id=document_id,
            filename=record["filename"],
            page_count=0,
            status=record["status"],
            error=record.get("error"),
        )
    return DocumentResult(**result_json)


@router.get("/documents/{document_id}/text", response_class=PlainTextResponse)
def get_document_text(document_id: str):
    record = db.get_document_record(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    result_json = db.load_result_json(document_id)
    if result_json is None:
        raise HTTPException(status_code=422, detail="Document has no processed result yet.")

    result = DocumentResult(**result_json)
    return document_to_text(result)
