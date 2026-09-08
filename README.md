---
<img width="1913" height="813" alt="Screenshot 2026-09-08 092826" src="https://github.com/user-attachments/assets/037a4ebf-7466-4a9e-9d5b-3bde186cd3e1" />
<img width="1917" height="887" alt="Screenshot 2026-09-08 092726" src="https://github.com/user-attachments/assets/5c72228e-acec-4c4b-8b50-74f1799fe99f" />
<img width="1865" height="862" alt="Screenshot 2026-09-08 092613" src="https://github.com/user-attachments/assets/8bb7825c-03d5-4779-9f81-381a7c3a19b4" />
<img width="1440" height="777" alt="Screenshot 2026-09-08 092551" src="https://github.com/user-attachments/assets/437d3a0d-3ad1-45ec-8a3c-e2ae5f55c9f9" />
<img width="1912" height="886" alt="Screenshot 2026-09-08 092516" src="https://github.com/user-attachments/assets/a12a7f32-69de-4477-9fa6-e73b605b2c90" />
<img width="1908" height="900" alt="Screenshot 2026-09-08 092409" src="https://github.com/user-attachments/assets/aaffa8a0-7b8b-47e4-bb43-edeb3bb2741a" />

---

# OCR Document Intelligence Pipeline

**A local, open-source pipeline that extracts text, headings, tables, and nested tables from PDF and image documents while preserving reading order and page layout — built for the ICSPL AI/ML Developer technical assignment.**

<!-- 🔗 **Live Demo:** _add your Hugging Face Space link here_
🔗 **Repository:** [_add your GitHub link here_](https://github.com/vishal815/ocr-doc-intelligence) -->
-- **Repository:** [GitHub link here_](https://github.com/vishal815/ocr-doc-intelligence) --

---

## 1. Overview

Most OCR tools stop at "read the text." This project goes a step further: it understands the **structure** of a document — what's a heading, what's a paragraph, what's a table, and whether a table has another table nested inside one of its cells — and reconstructs the correct **reading order**, even across multi-column layouts and multiple pages.

The entire pipeline runs **locally, with zero paid APIs or API keys** — no OpenAI, Gemini, Groq, or Claude calls anywhere in the system. Every extraction decision is made by open-source libraries and classical computer-vision techniques, which keeps the system fully offline-capable, free to run, and fully explainable (every output can be traced back to a specific, inspectable step).

**Core capabilities:**
- Accepts both PDF and image documents (PNG, JPG, BMP, TIFF)
- Automatically detects whether a PDF has a real text layer (digital) or needs OCR (scanned)
- Extracts headings, paragraphs, and tables — including **tables nested inside table cells**
- Reconstructs correct reading order on multi-column pages
- Outputs a structured, machine-readable JSON, and a plain-text rendering
- Provides both a visual UI (Streamlit) and a REST API (FastAPI) for the same pipeline
- Handles invalid, corrupt, or oversized files gracefully, without crashing

---

## 2. Problem Statement

The assignment required building a document-intelligence system that could:
1. Accept scanned and digital documents
2. Extract text, tables, and nested tables while preserving structure
3. Preserve logical reading order, page information, and layout/position data
4. Produce structured JSON output, retrievable through an API
5. Do all of this **without depending on any paid or external LLM API**

Correctness and reliability were explicitly prioritized over UI complexity — so this project focuses its engineering effort on the extraction pipeline itself, with a clean but purposefully simple interface layered on top.

---

## 3. Architecture

```
                        ┌─────────────────────────┐
                        │   Upload (UI / API)      │
                        └────────────┬─────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │  Validate file type/size │
                        └────────────┬─────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │  Load document (PyMuPDF) │
                        └────────────┬─────────────┘
                                     ▼
                     ┌───────────────┴────────────────┐
                     ▼                                 ▼
          ┌─────────────────────┐           ┌───────────────────────┐
          │  Digital PDF page   │           │   Scanned / image page │
          │  (has text layer)   │           │   (no text layer)      │
          └──────────┬──────────┘           └───────────┬────────────┘
                     ▼                                   ▼
          ┌─────────────────────┐           ┌───────────────────────┐
          │  Direct text +      │           │  OpenCV preprocessing  │
          │  pdfplumber tables  │           │  (deskew, denoise)     │
          └──────────┬──────────┘           └───────────┬────────────┘
                     │                                   ▼
                     │                        ┌───────────────────────┐
                     │                        │   Tesseract OCR        │
                     │                        └───────────┬────────────┘
                     │                                    ▼
                     │                        ┌───────────────────────┐
                     │                        │ OpenCV grid-based      │
                     │                        │ table detection        │
                     │                        │ (recursive → nested    │
                     │                        │ tables inside cells)   │
                     │                        └───────────┬────────────┘
                     └───────────────────┬────────────────┘
                                          ▼
                          ┌───────────────────────────┐
                          │ Heading/paragraph          │
                          │ classification             │
                          └─────────────┬──────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │ Reading-order resolver     │
                          │ (column-band clustering)   │
                          └─────────────┬──────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │ Pydantic JSON assembly     │
                          └─────────────┬──────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │ SQLite + file storage      │
                          └─────────────┬──────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │ JSON / plain-text response │
                          └───────────────────────────┘
```

### Key design decision: branch early on document type
Rather than forcing every page through OCR, the pipeline checks first whether a PDF page already has a digital text layer. If it does, text and tables are extracted directly — this is faster and more accurate than OCR. Only pages without a text layer (genuine scans or images) go through the OCR + computer-vision path. This single decision is responsible for most of the pipeline's accuracy on digital PDFs.

### Nested-table strategy
Table detection runs once to find the outer/parent table grid. For every detected cell, the same detector is re-applied to just that cell's cropped region — if a second grid is found inside, it's a nested table, attached recursively in the JSON. No LLM or heuristic guessing is involved; it's the same deterministic detector applied at a smaller scope.

### Reading-order strategy
Multi-column pages are a classic OCR failure mode — plain OCR often reads line-by-line across the full page width, interleaving two columns into one jumbled sequence. This pipeline clusters text blocks into column bands by x-position first, then sorts within each band by y-position, and finally orders the bands left to right — producing the reading order a human would actually use.

---

## 4. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| PDF ingestion | **PyMuPDF (fitz)** | Fast; provides both the text layer (when present) and page rasterization |
| Digital-PDF table extraction | **pdfplumber** | Pure-Python, no system dependencies (Camelot requires Ghostscript) |
| OCR engine | **Tesseract** (via pytesseract) | Free, fully offline, no API key required |
| Scanned-page table & nested-table detection | **OpenCV** (morphological line detection, applied recursively) | Transparent, testable, no external model downloads |
| Image preprocessing | **OpenCV** | Deskew, denoise, adaptive thresholding before OCR |
| Backend API | **FastAPI + Pydantic** | Schema-validated JSON contract, async-ready |
| UI | **Streamlit** | Visual pipeline walkthrough and result explorer |
| Storage | **SQLite** + local filesystem | Zero-setup persistence, appropriate for this scope |
| Testing | **Pytest** | 13 tests covering the main extraction scenarios and failure modes |
| Packaging | **Docker** | Single-command deployment |

**No LangChain, no vector database, no RAG, and no hosted LLM API are used anywhere in this project.** This is a structure-extraction problem, not a retrieval or question-answering problem — none of those tools solve any requirement here, and adding them would be unjustified complexity.

---

## 5. How It Works — Step by Step

1. **Upload** — a file is submitted through the Streamlit UI or the `/documents/upload` API endpoint.
2. **Validation** — file extension and size are checked before any processing begins.
3. **Loading** — PyMuPDF opens the document and inspects each page for a text layer.
4. **Branching** — digital pages go through direct text/table extraction; scanned pages are preprocessed and OCR'd.
5. **Table detection** — grid lines are detected via OpenCV (scanned path) or PDF structure (digital path); each cell is checked for a nested table.
6. **Classification** — text blocks are labeled as headings or paragraphs based on font size and position.
7. **Reading-order resolution** — all elements on a page are ordered to match natural human reading order.
8. **Assembly** — everything is validated against a Pydantic schema and assembled into a single structured JSON per document.
9. **Storage & response** — the result is saved to SQLite/disk and returned as JSON, or as plain text via a separate endpoint.

---

## 6. Project Structure

```
ocr-doc-intelligence/
├── app/
│   ├── api/            # FastAPI routes: upload, retrieve JSON, retrieve text, health
│   ├── core/            # Configuration, logging, custom exceptions
│   ├── ocr/             # Tesseract wrapper + image preprocessing
│   ├── pdf/             # PyMuPDF loader, digital-vs-scanned detection
│   ├── layout/          # Heading/paragraph classification, reading-order resolver
│   ├── tables/          # Digital-table extraction, OCR/OpenCV table detection, nested-table recursion
│   ├── schemas/         # Pydantic models — the JSON output contract
│   ├── services/        # pipeline.py (orchestration), text_export.py, validation.py
│   └── storage/         # SQLite models + file storage helpers
├── streamlit_app.py     # Streamlit UI — calls the pipeline directly
├── tests/               # Pytest suite (13 tests)
├── samples/             # Sample input documents + generator script
│   └── expected_output/ # Matching JSON + text outputs for each sample
├── data/                # Runtime uploads/results (not committed)
├── Dockerfile
├── packages.txt         # System-level dependencies for Hugging Face Spaces (Tesseract, etc.)
├── requirements.txt
└── README.md
```

---

## 7. Installation & Setup

### Prerequisites
- Python 3.10+
- Tesseract OCR installed at the system level:
  - **Windows:** [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - **macOS:** `brew install tesseract`
  - **Linux:** `sudo apt-get install tesseract-ocr`

### Setup
```bash
git clone <repo-url>
cd ocr-doc-intelligence

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Run the UI (recommended for a walkthrough)
```bash
streamlit run streamlit_app.py
```

### Run the API
```bash
uvicorn app.main:app --reload
```
Interactive API docs are available at `http://localhost:8000/docs`.

---

## 8. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/upload` | Upload a PDF or image. Returns `{document_id, status}`. |
| `GET` | `/documents/{id}` | Returns the full structured JSON result. |
| `GET` | `/documents/{id}/text` | Returns a plain-text rendering of the result. |
| `GET` | `/health` | Liveness check. |

**Example:**
```bash
curl -F "file=@samples/table_report.pdf" http://localhost:8000/documents/upload
curl http://localhost:8000/documents/<document_id>
```

---

## 9. Example Output

Sample inputs and their exact pipeline output are included in `samples/` and `samples/expected_output/` — including `nested_table.png`, which demonstrates a real, correctly parsed nested table (not a placeholder).

**JSON structure (excerpt):**
```json
{
  "document_id": "doc_001",
  "pages": [
    {
      "page_number": 1,
      "source": "digital_text_layer",
      "elements": [
        {"type": "heading", "text": "Invoice #2026-114", "reading_order": 1},
        {
          "type": "table",
          "reading_order": 2,
          "table": {
            "rows": 2, "cols": 2,
            "cells": [
              {"row": 0, "col": 0, "text": "Category"},
              {"row": 1, "col": 1, "text": "", "nested_table": {
                "rows": 3, "cols": 2,
                "cells": [
                  {"row": 0, "col": 0, "text": "Type"}, {"row": 0, "col": 1, "text": "Amount"},
                  {"row": 1, "col": 0, "text": "Tax"},  {"row": 1, "col": 1, "text": "5%"}
                ]
              }}
            ]
          }
        }
      ]
    }
  ]
}
```

**Screenshots**

_Upload & pipeline view:_
`![Upload UI](screenshots/upload-ui.png)`

_Table extraction result:_
`![Table Output](screenshots/table-output.png)`

_Structured JSON view:_
`![JSON Output](screenshots/json-output.png)`

> Replace the paths above with your actual screenshot files once added to a `screenshots/` folder.

---

## 10. Testing

```bash
pytest tests/ -v
```

13 tests covering: plain-text PDF, digital-PDF tables, scanned-image OCR, a genuine nested table (verified with correct row/column text), multi-page documents, mixed text+table pages, two-column reading order, plain-text export, and invalid/corrupt/oversized file handling.

---

## 11. Known Limitations

- Nested-table detection is recursive up to 2 levels deep (untested beyond that)
- OCR accuracy depends on scan quality — low-DPI or noisy scans may misread characters
- Handwritten text is not supported (Tesseract is a printed-text engine)
- Very heavily skewed scans (beyond ~15°) are not auto-corrected, by design — this bound exists because table-heavy pages can otherwise trigger a false rotation that corrupts OCR positions (found and fixed during testing)
- Processing is synchronous; a task queue would be needed for high-volume batch use

---

## 12. Future Improvements

- Optional PaddleOCR/PP-Structure backend for higher table-recognition accuracy
- Asynchronous processing with job-status polling
- Bounding-box visualization overlay for QA
- Multi-instance deployment with a shared Postgres store

---

## 13. Deployment

Deployed on **Hugging Face Spaces** (Streamlit SDK) — `packages.txt` handles the Tesseract system dependency automatically, and the metadata block at the top of this README configures the Space. A `Dockerfile` is also included for deployment to any Docker-compatible host (e.g. Render).

---

## Author

**Vishal Lazrus**
AI/ML Engineer | GitHub: [github.com/vishal815](https://github.com/vishal815) | Portfolio: [vishal-lazrus-portfolio.vercel.app](https://vishal-lazrus-portfolio.vercel.app)

Submitted as a technical assignment for the **AI/ML Developer** role at **IVTEX Corporate Solutions Pvt. Ltd. (ICSPL)**.
