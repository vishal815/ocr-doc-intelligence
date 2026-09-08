"""
Generates sample test documents into samples/ :
  1. simple_text.pdf      - heading + paragraphs (digital text layer)
  2. table_report.pdf     - heading + paragraph + a table (digital)
  3. two_column.pdf       - a 2-column layout (digital, tests reading order)
  4. scanned_like.png     - a rendered image (simulates a scanned page, forces OCR path)
  5. invalid.txt          - an unsupported file type, for error-handling tests
  6. nested_table.png     - a table image where one cell contains a nested sub-table,
                            for the OCR + OpenCV nested-table-detection path
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent


def make_simple_text_pdf():
    path = OUT / "simple_text.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 740, "Quarterly Report")
    c.setFont("Helvetica", 11)
    c.drawString(72, 710, "This report summarizes the performance of the sales team for Q1 2026.")
    c.drawString(72, 695, "Revenue grew steadily across all regions during the quarter.")
    c.save()


def make_table_report_pdf():
    path = OUT / "table_report.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 740, "Invoice 2026-114")
    c.setFont("Helvetica", 11)
    c.drawString(72, 715, "Billed to: Acme Corp")

    data = [["Item", "Qty", "Price"], ["Widget", "5", "$10"], ["Gadget", "2", "$25"]]
    x0, y0 = 72, 640
    row_h, col_w = 22, 120
    for r, row in enumerate(data):
        for col_idx, val in enumerate(row):
            x = x0 + col_idx * col_w
            y = y0 - r * row_h
            c.rect(x, y, col_w, row_h)
            c.drawString(x + 5, y + 6, str(val))
    c.save()


def make_two_column_pdf():
    path = OUT / "two_column.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 750, "Two Column Layout Test")
    c.setFont("Helvetica", 10)
    left_lines = ["Column A line 1", "Column A line 2", "Column A line 3"]
    right_lines = ["Column B line 1", "Column B line 2", "Column B line 3"]
    for i, line in enumerate(left_lines):
        c.drawString(72, 700 - i * 20, line)
    for i, line in enumerate(right_lines):
        c.drawString(320, 700 - i * 20, line)
    c.save()


def make_scanned_like_image():
    path = OUT / "scanned_like.png"
    img = Image.new("RGB", (800, 400), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    draw.text((40, 30), "Scanned Document Sample", fill="black", font=font)
    draw.text((40, 90), "This text was rendered as an image to simulate a scan.", fill="black", font=font_small)
    draw.text((40, 130), "The pipeline must OCR this instead of reading a text layer.", fill="black", font=font_small)
    img.save(path)


def make_nested_table_image():
    """
    A table image with an outer 2x2 grid where the bottom-right cell contains
    a smaller nested 3x2 grid - exercises the recursive nested-table detector
    on the OCR/OpenCV (scanned-page) path.
    """
    path = OUT / "nested_table.png"
    img = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(img)
    try:
        font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except OSError:
        font_b = font = ImageFont.load_default()

    draw.text((30, 15), "Vendor Invoice Summary", fill="black", font=font_b)

    ox0, oy0 = 40, 70
    row_h = [60, 220]
    col_w = [280, 480]
    ox1, oy1 = ox0 + sum(col_w), oy0 + sum(row_h)

    for y in [oy0, oy0 + row_h[0], oy1]:
        draw.line([(ox0, y), (ox1, y)], fill="black", width=3)
    for x in [ox0, ox0 + col_w[0], ox1]:
        draw.line([(x, oy0), (x, oy1)], fill="black", width=3)

    draw.text((ox0 + 10, oy0 + 18), "Category", fill="black", font=font)
    draw.text((ox0 + col_w[0] + 10, oy0 + 18), "Details", fill="black", font=font)
    draw.text((ox0 + 10, oy0 + row_h[0] + 18), "Tax Breakdown", fill="black", font=font)

    nx0, ny0 = ox0 + col_w[0] + 20, oy0 + row_h[0] + 55
    n_col_w = [200, 160]
    n_row_h = [40, 40, 40]
    nx1, ny1 = nx0 + sum(n_col_w), ny0 + sum(n_row_h)

    for y in [ny0, ny0 + n_row_h[0], ny0 + n_row_h[0] + n_row_h[1], ny1]:
        draw.line([(nx0, y), (nx1, y)], fill="black", width=2)
    for x in [nx0, nx0 + n_col_w[0], nx1]:
        draw.line([(x, ny0), (x, ny1)], fill="black", width=2)

    for r, row in enumerate([["Type", "Amount"], ["Tax", "5%"], ["Total", "$52.50"]]):
        y = ny0 + sum(n_row_h[:r]) + 12
        draw.text((nx0 + 8, y), row[0], fill="black", font=font)
        draw.text((nx0 + n_col_w[0] + 8, y), row[1], fill="black", font=font)

    img.save(path)


def make_invalid_file():
    path = OUT / "invalid.txt"
    path.write_text("This is not a supported document type.")


if __name__ == "__main__":
    make_simple_text_pdf()
    make_table_report_pdf()
    make_two_column_pdf()
    make_scanned_like_image()
    make_nested_table_image()
    make_invalid_file()
    print("Sample files generated in", OUT)
