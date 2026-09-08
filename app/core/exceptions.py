"""Custom exceptions used across the pipeline for clear, catchable error handling."""


class DocumentIntelligenceError(Exception):
    """Base class for all pipeline errors."""


class UnsupportedFileTypeError(DocumentIntelligenceError):
    """Raised when the uploaded file extension is not supported."""


class FileTooLargeError(DocumentIntelligenceError):
    """Raised when the uploaded file exceeds MAX_FILE_SIZE_MB."""


class CorruptDocumentError(DocumentIntelligenceError):
    """Raised when a PDF/image cannot be opened or parsed at all."""


class EmptyDocumentError(DocumentIntelligenceError):
    """Raised (as a soft warning, not fatal) when a document has no extractable content."""


class OCRFailureError(DocumentIntelligenceError):
    """Raised when the OCR engine fails on a given page/region."""


class DocumentNotFoundError(DocumentIntelligenceError):
    """Raised when a requested document_id does not exist."""
