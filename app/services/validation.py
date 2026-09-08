from __future__ import annotations

from pathlib import Path

from app.core.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError


def validate_upload(filename: str, content: bytes) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"'{suffix}' is not supported. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise FileTooLargeError(f"File is {size_mb:.1f}MB, max allowed is {MAX_FILE_SIZE_MB}MB")
