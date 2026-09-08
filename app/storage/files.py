from __future__ import annotations

from pathlib import Path

from app.core.config import UPLOAD_DIR


def save_upload(document_id: str, original_filename: str, content: bytes) -> Path:
    suffix = Path(original_filename).suffix.lower()
    dest = UPLOAD_DIR / f"{document_id}{suffix}"
    dest.write_bytes(content)
    return dest
