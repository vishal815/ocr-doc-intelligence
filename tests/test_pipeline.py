from pathlib import Path

from app.services.pipeline import process_document

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_simple_text_pdf_extracts_heading_and_paragraphs():
    result = process_document("d1", "simple_text.pdf", SAMPLES / "simple_text.pdf")
    assert result.status == "processed"
    assert result.page_count == 1
    types = [el.type for el in result.pages[0].elements]
    assert "heading" in types
    assert "paragraph" in types
    heading = next(el for el in result.pages[0].elements if el.type == "heading")
    assert "Quarterly Report" in heading.text


def test_table_pdf_extracts_correct_grid():
    result = process_document("d2", "table_report.pdf", SAMPLES / "table_report.pdf")
    tables = [el for el in result.pages[0].elements if el.type == "table"]
    assert len(tables) == 1
    table = tables[0].table
    assert table.rows == 3
    assert table.cols == 3
    header_texts = {c.text for c in table.cells if c.row == 0}
    assert header_texts == {"Item", "Qty", "Price"}


def test_two_column_reading_order_groups_columns_together():
    result = process_document("d3", "two_column.pdf", SAMPLES / "two_column.pdf")
    ordered_text = [el.text for el in sorted(result.pages[0].elements, key=lambda e: e.reading_order)]
    # Column A's 3 lines must appear consecutively (not interleaved with column B)
    idx_a = [i for i, t in enumerate(ordered_text) if t and t.startswith("Column A")]
    idx_b = [i for i, t in enumerate(ordered_text) if t and t.startswith("Column B")]
    assert idx_a == sorted(idx_a)
    assert max(idx_a) < min(idx_b)  # all of column A comes before all of column B


def test_scanned_image_is_routed_through_ocr():
    result = process_document("d4", "scanned_like.png", SAMPLES / "scanned_like.png")
    assert result.status == "processed"
    assert result.pages[0].source == "ocr"
    all_text = " ".join(el.text or "" for el in result.pages[0].elements)
    assert "Scanned" in all_text or "scanned" in all_text.lower()


def test_nested_table_is_detected_and_parsed():
    result = process_document("d7", "nested_table.png", SAMPLES / "nested_table.png")
    assert result.status == "processed"
    tables = [el for el in result.pages[0].elements if el.type == "table"]
    assert len(tables) == 1
    outer = tables[0].table
    assert outer.rows == 2 and outer.cols == 2

    nested_cell = next(c for c in outer.cells if c.row == 1 and c.col == 1)
    assert nested_cell.nested_table is not None
    assert nested_cell.nested_table.rows == 3
    assert nested_cell.nested_table.cols == 2
    nested_texts = {c.text for c in nested_cell.nested_table.cells}
    assert "Type" in nested_texts and "Tax" in nested_texts and "5%" in nested_texts


def test_corrupt_document_returns_failed_status(tmp_path):
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"not a real pdf")
    result = process_document("d5", "bad.pdf", bad_pdf)
    assert result.status == "failed"
    assert result.error is not None


def test_empty_pdf_page_does_not_crash(tmp_path):
    import fitz

    empty_pdf = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(empty_pdf)
    doc.close()

    result = process_document("d6", "empty.pdf", empty_pdf)
    assert result.status == "processed"
    assert result.pages[0].elements == []
    assert result.pages[0].warning is not None
