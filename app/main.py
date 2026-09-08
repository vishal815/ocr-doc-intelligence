from fastapi import FastAPI

from app.api.routes import router
from app.core.logging_config import setup_logging
from app.storage.db import init_db

setup_logging()

app = FastAPI(
    title="OCR Document Intelligence Pipeline",
    description="Extracts text, headings, tables, and nested tables from PDF/image documents "
    "while preserving layout and reading order - using only local, open-source OCR "
    "(no paid/external LLM APIs).",
    version="1.0.0",
)

init_db()

app.include_router(router)
