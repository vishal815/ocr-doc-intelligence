# OCR Document Intelligence Pipeline

A local, open-source document intelligence pipeline that extracts **text, headings, tables, and nested tables** from PDF and image documents while preserving **reading order, page information, and layout**.

Built for the **AI/ML Developer technical assignment at IVTEX Corporate Solutions Pvt. Ltd. (ICSPL)**.

**Repository:** [github.com/vishal815/ocr-doc-intelligence](https://github.com/vishal815/ocr-doc-intelligence)

---

## 1. Overview

Most OCR tools stop at extracting text. This project goes a step further by identifying the **structure of a document**:

- Headings
- Paragraphs
- Tables
- Tables nested inside table cells
- Reading order across multi-column pages
- Page and layout information

The pipeline runs **locally using open-source tools**, with no paid API, API key, hosted LLM, or external AI service required.

### Core capabilities

- Accepts PDF and image documents: PNG, JPG, BMP, and TIFF
- Detects whether a PDF contains a digital text layer or requires OCR
- Extracts headings, paragraphs, and tables
- Detects nested tables recursively
- Preserves logical reading order on multi-column pages
- Produces structured, machine-readable JSON
- Provides a plain-text representation of extracted content
- Provides a web UI and REST API for the same pipeline
- Handles invalid, corrupt, and oversized files gracefully

---

## 2. Problem Statement

The assignment required a document-intelligence system that could:

1. Accept scanned and digital documents
2. Extract text, tables, and nested tables while preserving structure
3. Preserve logical reading order, page information, and layout/position data
4. Produce structured JSON output retrievable through an API
5. Perform the extraction without depending on paid or external LLM APIs

Correctness and reliability were prioritized over UI complexity, so the main engineering effort is focused on the extraction pipeline.

---

## 3. Architecture

```text
                         ┌─────────────────────────┐
                         │      Upload (UI / API)   │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │ Validate file type/size │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │ Load document (PyMuPDF) │
                         └────────────┬────────────┘
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
              ┌─────────────────────┐    ┌────────────────────────┐
              │   Digital PDF page  │    │ Scanned / image page   │
              │   (has text layer)  │    │   (needs OCR)          │
              └──────────┬──────────┘    └───────────┬────────────┘
                         │                            │
                         ▼                            ▼
              ┌─────────────────────┐    ┌────────────────────────┐
              │ Direct text +       │    │ OpenCV preprocessing   │
              │ pdfplumber tables   │    │ (deskew, denoise, etc.)│
              └──────────┬──────────┘    └───────────┬────────────┘
                         │                            │
                         │                            ▼
                         │                 ┌────────────────────────┐
                         │                 │     Tesseract OCR      │
                         │                 └───────────┬────────────┘
                         │                             │
                         │                             ▼
                         │                 ┌────────────────────────┐
                         │                 │ OpenCV table detection │
                         │                 │ Recursive nested-table │
                         │                 │ detection              │
                         │                 └───────────┬────────────┘
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌────────────────────────────┐
                         │ Heading / paragraph        │
                         │ classification              │
                         └────────────┬───────────────┘
                                      │
                                      ▼
                         ┌────────────────────────────┐
                         │ Reading-order resolver     │
                         │ (column-band clustering)    │
                         └────────────┬───────────────┘
                                      │
                                      ▼
                         ┌────────────────────────────┐
                         │ Pydantic JSON assembly     │
                         └────────────┬───────────────┘
                                      │
                                      ▼
                         ┌────────────────────────────┐
                         │ SQLite + local file storage│
                         └────────────┬───────────────┘
                                      │
                                      ▼
                         ┌────────────────────────────┐
                         │ JSON / plain-text response │
                         └────────────────────────────┘
```

### Key design decision: branch early by document type

The pipeline first checks whether a PDF page already contains a digital text layer.

- **Digital PDF:** text and tables are extracted directly.
- **Scanned PDF/image:** the page is preprocessed and passed through OCR and computer-vision processing.

This avoids unnecessary OCR and generally provides better accuracy for digital PDFs.

### Nested-table strategy

The table detector first identifies the outer table grid. Each detected cell is then cropped and checked again for another table grid.

If a nested table is found, it is attached to the parent cell recursively in the JSON structure.

This approach uses the same deterministic table-detection logic at a smaller scope rather than relying on an LLM to guess whether a nested table exists.

### Reading-order strategy

Multi-column pages are a common OCR failure case. Instead of sorting all text blocks only by their vertical position, the pipeline:

1. Groups text blocks into column bands using their x-position.
2. Sorts blocks within each column by y-position.
3. Orders the column bands from left to right.

This produces a more natural human reading order.

---

## 4. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| PDF ingestion | **PyMuPDF (fitz)** | Reads PDFs, extracts digital text, and rasterizes pages |
| Digital-PDF table extraction | **pdfplumber** | Extracts tables from PDFs without requiring system-level Ghostscript |
| OCR engine | **Tesseract** via `pytesseract` | Offline OCR for scanned documents |
| Table & nested-table detection | **OpenCV** | Detects table grids using morphological line detection |
| Image preprocessing | **OpenCV** | Deskewing, denoising, and thresholding |
| Backend API | **FastAPI + Pydantic** | REST API and schema-validated JSON |
| UI | **Streamlit** | Interactive document upload and result visualization |
| Storage | **SQLite + local filesystem** | Lightweight persistence |
| Testing | **Pytest** | Automated tests |
| Packaging | **Docker** | Containerized deployment |

### Why no RAG or LLM?

This project is a **document-structure extraction problem**, not a retrieval or question-answering problem.

Therefore, the implementation does not use:

- LangChain
- Vector databases
- RAG
- Hosted LLM APIs

Adding those components would introduce unnecessary complexity without directly solving the assignment requirements.

---

## 5. How It Works — Step by Step

1. **Upload** — A PDF or image is submitted through the UI or `/documents/upload` API endpoint.
2. **Validation** — File extension and size are validated before processing.
3. **Loading** — PyMuPDF opens the document and inspects each page.
4. **Document-type detection** — Pages with a digital text layer use direct extraction; scanned pages use the OCR pipeline.
5. **Preprocessing** — Scanned pages are cleaned and normalized with OpenCV.
6. **OCR** — Tesseract extracts text and positional information.
7. **Table detection** — Tables are extracted directly from digital PDFs or detected with OpenCV on scanned pages.
8. **Nested-table detection** — Detected table cells are recursively checked for nested tables.
9. **Classification** — Text blocks are classified as headings or paragraphs using layout and font information.
10. **Reading-order resolution** — Document elements are ordered according to their page layout.
11. **JSON assembly** — Results are validated using Pydantic models.
12. **Storage & response** — Results are stored locally and returned as structured JSON or plain text.

---

## 6. Project Structure

```text
ocr-doc-intelligence/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Configuration, logging, exceptions
│   ├── ocr/              # Tesseract wrapper and image preprocessing
│   ├── pdf/              # PyMuPDF loader and PDF classification
│   ├── layout/           # Heading/paragraph classification and reading order
│   ├── tables/           # Table extraction and nested-table detection
│   ├── schemas/          # Pydantic models / JSON output contract
│   ├── services/         # Pipeline orchestration and text export
│   └── storage/          # SQLite models and file-storage helpers
├── streamlit_app.py      # Streamlit UI
├── tests/                # Pytest test suite
├── samples/              # Sample input documents
│   └── expected_output/  # Expected JSON and text outputs
├── data/                 # Runtime uploads/results (not committed)
├── Dockerfile
├── packages.txt          # System dependencies for Hugging Face Spaces
├── requirements.txt
└── README.md
```

---

## 7. Installation & Setup

### Prerequisites

- Python 3.10+
- Tesseract OCR

#### Windows

Install Tesseract using the **UB Mannheim Tesseract installer**:

https://github.com/UB-Mannheim/tesseract/wiki

After installation, make sure the Tesseract executable is available in your system `PATH`, or configure its path in the application.

#### macOS

```bash
brew install tesseract
```

#### Linux

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### Clone the repository

```bash
git clone https://github.com/vishal815/ocr-doc-intelligence.git
cd ocr-doc-intelligence
```

### Create a virtual environment

#### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## 8. Run the Application

### Run the UI

```bash
streamlit run streamlit_app.py
```

The Streamlit application will display a local URL in the terminal.

### Run the API

```bash
uvicorn app.main:app --reload
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

OpenAPI specification:

```text
http://localhost:8000/openapi.json
```

---

## 9. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/upload` | Upload a PDF or image and create a document |
| `GET` | `/documents/{id}` | Retrieve the full structured JSON result |
| `GET` | `/documents/{id}/text` | Retrieve the plain-text rendering |
| `GET` | `/health` | Health/liveness check |

### Example

Upload a document:

```bash
curl -F "file=@samples/table_report.pdf" http://localhost:8000/documents/upload
```

Retrieve the structured result:

```bash
curl http://localhost:8000/documents/<document_id>
```

---

## 10. Example Output

Sample inputs and expected outputs are stored under:

```text
samples/
samples/expected_output/
```

The sample set includes a nested-table example demonstrating the recursive table-detection approach.

### JSON structure

```json
{
  "document_id": "doc_001",
  "pages": [
    {
      "page_number": 1,
      "source": "digital_text_layer",
      "elements": [
        {
          "type": "heading",
          "text": "Invoice #2026-114",
          "reading_order": 1
        },
        {
          "type": "table",
          "reading_order": 2,
          "table": {
            "rows": 2,
            "cols": 2,
            "cells": [
              {
                "row": 0,
                "col": 0,
                "text": "Category"
              },
              {
                "row": 1,
                "col": 1,
                "text": "",
                "nested_table": {
                  "rows": 3,
                  "cols": 2,
                  "cells": [
                    {
                      "row": 0,
                      "col": 0,
                      "text": "Type"
                    },
                    {
                      "row": 0,
                      "col": 1,
                      "text": "Amount"
                    },
                    {
                      "row": 1,
                      "col": 0,
                      "text": "Tax"
                    },
                    {
                      "row": 1,
                      "col": 1,
                      "text": "5%"
                    }
                  ]
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

---

## 11. Demo Output

The following screenshots show the document upload, processing, and extraction results:

<img width="1913" height="813" alt="OCR pipeline demo" src="https://github.com/user-attachments/assets/037a4ebf-7466-4a9e-9d5b-3bde186cd3e1" />

<img width="1917" height="887" alt="OCR extraction result" src="https://github.com/user-attachments/assets/5c72228e-acec-4c4b-8b50-74f1799fe99f" />

<img width="1865" height="862" alt="OCR table result" src="https://github.com/user-attachments/assets/8bb7825c-03d5-4779-9f81-381a7c3a19b4" />

<img width="1440" height="777" alt="OCR JSON result" src="https://github.com/user-attachments/assets/437d3a0d-3ad1-45ec-8a3c-e2ae5f55c9f9" />

<img width="1912" height="886" alt="OCR document result" src="https://github.com/user-attachments/assets/a12a7f32-69de-4477-9fa6-e73b605b2c90" />

<img width="1908" height="900" alt="OCR pipeline interface" src="https://github.com/user-attachments/assets/aaffa8a0-7b8b-47e4-bb43-edeb3bb2741a" />

---

## 12. Testing

Run the complete test suite with:

```bash
pytest tests/ -v
```

The test suite covers the main extraction scenarios and failure cases, including:

- Plain-text PDFs
- Digital-PDF table extraction
- Scanned-image OCR
- Nested-table detection
- Multi-page documents
- Mixed text and table pages
- Two-column reading order
- Plain-text export
- Invalid files
- Corrupt files
- Oversized files

---

## 13. Known Limitations

- Nested-table detection is currently tested up to two levels deep.
- OCR accuracy depends on the quality and resolution of the input scan.
- Handwritten text is not supported because Tesseract is primarily designed for printed text.
- Very heavily skewed scans (beyond approximately 15°) are not automatically corrected by design. Aggressive rotation correction can produce false rotations on table-heavy pages and corrupt OCR positions.
- Processing is synchronous; high-volume workloads would benefit from a background task queue.

---

## 14. Future Improvements

- Optional PaddleOCR / PP-Structure backend for improved table recognition
- Asynchronous processing with job-status polling
- Bounding-box visualization overlays for quality assurance
- Multi-instance deployment with a shared PostgreSQL database
- Additional OCR language support
- Improved table detection for borderless tables

---

## 15. Deployment

The project is designed to support deployment on **Hugging Face Spaces** using the Streamlit SDK.

`packages.txt` can be used to install system-level dependencies such as Tesseract during deployment.

A `Dockerfile` is also included for deployment to Docker-compatible hosting platforms.

> Deployment configuration should be kept consistent with the currently deployed UI. If the application is switched from Streamlit to another framework, update the UI, run commands, and deployment metadata in this README accordingly.

---

## Author

**Vishal Lazrus**

AI/ML Engineer

- GitHub: [github.com/vishal815](https://github.com/vishal815)
- Portfolio: [vishal-lazrus-portfolio.vercel.app](https://vishal-lazrus-portfolio.vercel.app)

Submitted as a technical assignment for the **AI/ML Developer** role at **IVTEX Corporate Solutions Pvt. Ltd. (ICSPL)**.
