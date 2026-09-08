"""
Renders a DocumentResult (the structured JSON) into a plain-text version -
same content, in reading order, with tables drawn as simple grids. Useful
for a quick human read, diffing, or feeding into something downstream that
just wants text rather than JSON.
"""
from __future__ import annotations

from app.schemas.models import DocumentResult, TableData


def _render_table(table: TableData, indent: str = "") -> list[str]:
    lines: list[str] = []
    grid: dict[tuple[int, int], str] = {}
    nested: list[tuple[int, int, TableData]] = []

    for cell in table.cells:
        grid[(cell.row, cell.col)] = cell.text or ""
        if cell.nested_table is not None:
            nested.append((cell.row, cell.col, cell.nested_table))

    for r in range(table.rows):
        row_cells = [grid.get((r, c), "") for c in range(table.cols)]
        lines.append(indent + " | ".join(row_cells))

    for row, col, sub_table in nested:
        lines.append(f"{indent}  [nested table in cell ({row},{col})]")
        lines.extend(_render_table(sub_table, indent=indent + "    "))

    return lines


def document_to_text(result: DocumentResult) -> str:
    """Flatten a processed DocumentResult into readable plain text."""
    lines: list[str] = [f"# {result.filename}", ""]

    for page in result.pages:
        lines.append(f"--- Page {page.page_number} (source: {page.source}) ---")
        if page.warning:
            lines.append(f"[warning: {page.warning}]")

        for element in sorted(page.elements, key=lambda e: e.reading_order):
            if element.type == "heading":
                lines.append("")
                lines.append(f"## {element.text}")
            elif element.type == "paragraph":
                lines.append(element.text or "")
            elif element.type == "table" and element.table is not None:
                lines.append("")
                lines.extend(_render_table(element.table))
                lines.append("")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
