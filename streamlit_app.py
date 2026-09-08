"""
Streamlit UI for the OCR Document Intelligence Pipeline.

This calls the SAME pipeline functions used by the FastAPI service directly
(app.services.pipeline) - there is no second server, no HTTP hop, and no
LLM/RAG/agent involved anywhere. It exists purely to make the pipeline's
stages and structured output easy to see and demo.
"""
from __future__ import annotations

import json
import sys
import tempfile
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.schemas.models import DocumentResult
from app.services.pipeline import process_document
from app.services.text_export import document_to_text
from app.services.validation import validate_upload
from app.core.exceptions import UnsupportedFileTypeError, FileTooLargeError, CorruptDocumentError

st.set_page_config(page_title="OCR Document Intelligence", page_icon="📄", layout="wide")

PIPELINE_STAGES = [
    ("📤", "Upload & Validate"),
    ("📄", "Load (PyMuPDF)"),
    ("🔀", "Digital vs Scanned"),
    ("🔎", "OCR / Text Layer"),
    ("🧱", "Table Detection"),
    ("🪆", "Nested Tables"),
    ("↕️", "Reading Order"),
    ("🗂️", "Structured JSON"),
]

st.markdown(
    """
    <style>
    .stage-box {
        text-align: center; padding: 10px 4px; border-radius: 10px;
        background: #1e2530; border: 1px solid #333; font-size: 0.82rem;
    }
    .stage-box.active { background: #2b3a55; border: 1px solid #5b8def; }
    .stage-box.done { background: #17301f; border: 1px solid #3fae59; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_pipeline(active_index: int | None, done: bool = False):
    cols = st.columns(len(PIPELINE_STAGES))
    for i, (icon, label) in enumerate(PIPELINE_STAGES):
        cls = "stage-box"
        if done or (active_index is not None and i < active_index):
            cls += " done"
        elif active_index is not None and i == active_index:
            cls += " active"
        cols[i].markdown(f"<div class='{cls}'>{icon}<br>{label}</div>", unsafe_allow_html=True)


st.title("📄 OCR Document Intelligence Pipeline")
st.caption(
    "PDF/image → text, headings, tables & nested tables, in reading order — "
    "100% local/open-source OCR, no paid LLM APIs."
)

with st.sidebar:
    st.header("About this project")
    st.markdown(
        "- **PDF ingestion:** PyMuPDF (digital text layer vs scanned-page detection)\n"
        "- **Digital-PDF tables:** pdfplumber\n"
        "- **Scanned OCR:** Tesseract\n"
        "- **Scanned tables + nested tables:** OpenCV grid detection, recursive\n"
        "- **No OpenAI / Gemini / Groq / Claude API used anywhere in this pipeline**"
    )
    st.divider()
    st.caption("Assignment: AI/ML 'Vishal Lazurs' ")

uploaded = st.file_uploader(
    "Upload a PDF or image (PNG/JPG/BMP/TIFF)", type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff"]
)

if uploaded is not None:
    content = uploaded.getvalue()

    try:
        validate_upload(uploaded.name, content)
    except UnsupportedFileTypeError as exc:
        st.error(f"Unsupported file type: {exc}")
        st.stop()
    except FileTooLargeError as exc:
        st.error(f"File too large: {exc}")
        st.stop()

    stage_placeholder = st.empty()
    with stage_placeholder.container():
        render_pipeline(active_index=0)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / uploaded.name
        tmp_path.write_bytes(content)

        with stage_placeholder.container():
            render_pipeline(active_index=2)

        try:
            with st.spinner("Running the pipeline (loader → OCR/text → tables → reading order)..."):
                result: DocumentResult = process_document(str(uuid.uuid4()), uploaded.name, tmp_path)
        except CorruptDocumentError as exc:
            st.error(f"Unreadable document: {exc}")
            st.stop()

    stage_placeholder.empty()
    render_pipeline(active_index=None, done=True)

    if result.status == "failed":
        st.error(f"Processing failed: {result.error}")
        st.stop()

    st.success(f"Processed **{result.page_count}** page(s).")

    tab_summary, tab_pages, tab_json, tab_text = st.tabs(
        ["📊 Summary", "📑 Page-by-page", "🗂️ Structured JSON", "📝 Plain Text"]
    )

    with tab_summary:
        col1, col2, col3 = st.columns(3)
        col1.metric("Pages", result.page_count)
        n_tables = sum(1 for p in result.pages for e in p.elements if e.type == "table")
        col2.metric("Tables found", n_tables)
        sources = {p.source for p in result.pages}
        col3.metric("Processing path", " + ".join(sorted(sources)) if sources else "-")

    with tab_pages:
        for page in result.pages:
            with st.expander(f"Page {page.page_number} — source: {page.source}", expanded=(page.page_number == 1)):
                if page.warning:
                    st.warning(page.warning)
                for el in sorted(page.elements, key=lambda e: e.reading_order):
                    if el.type == "heading":
                        st.markdown(f"### {el.text}")
                    elif el.type == "paragraph":
                        st.write(el.text)
                    elif el.type == "table" and el.table is not None:
                        st.markdown("**Table**")
                        grid = [["" for _ in range(el.table.cols)] for _ in range(el.table.rows)]
                        has_nested = False
                        for c in el.table.cells:
                            text = c.text or ""
                            if c.nested_table is not None:
                                has_nested = True
                                text += " 🪆"
                            if c.row < el.table.rows and c.col < el.table.cols:
                                grid[c.row][c.col] = text
                        st.table(grid)
                        if has_nested:
                            st.caption("🪆 = cell contains a nested table (see Structured JSON tab for detail)")

    with tab_json:
        st.json(result.model_dump())
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(result.model_dump(), indent=2),
            file_name=f"{uploaded.name}.json",
            mime="application/json",
        )

    with tab_text:
        text_output = document_to_text(result)
        st.text(text_output)
        st.download_button(
            "⬇️ Download Text",
            data=text_output,
            file_name=f"{uploaded.name}.txt",
            mime="text/plain",
        )
else:
    render_pipeline(active_index=None)
    st.info("Upload a document above to run it through the pipeline.")
