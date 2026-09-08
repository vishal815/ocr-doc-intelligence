"""
Central configuration for the OCR Document Intelligence Pipeline.
All tunables live here so nothing is hard-coded deep inside the pipeline.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Storage locations
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
RESULTS_DIR = BASE_DIR / "data" / "results"
DB_PATH = BASE_DIR / "data" / "app.db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Upload limits
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

# OCR / rendering
RENDER_DPI = int(os.getenv("RENDER_DPI", "200"))
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "eng")

# Heading heuristics
HEADING_FONT_SIZE_RATIO = 1.15  # a line is a "heading" if font size >= ratio * page median

# Reading-order column clustering
COLUMN_GAP_RATIO = 0.04  # fraction of page width treated as a "gap" between columns
