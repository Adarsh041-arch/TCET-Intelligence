# DOCX Generator (AST → python-docx)

**File:** `app/document_generation/generators/docx_generator_v2.py`

## Architecture

Uses `python-docx` (v1.2.0). Walks the shared AST directly — no HTML intermediate.

## Block → API mapping

| AST node | python-docx API |
|---|---|
| `heading` | `doc.add_heading(text, level=N)` |
| `paragraph` | `doc.add_paragraph()` + run-level inline rendering |
| `list` | `doc.add_paragraph(style="List Bullet")` / `"List Number"` |
| `block_code` | `doc.add_paragraph()` with `Courier New` font run |
| `block_quote` | `doc.add_paragraph()` + left indent + italic |
| `table` | `doc.add_table(rows, cols)` + `Table Grid` style |
| `thematic_break` | `doc.add_paragraph("___")` |
| `image` | `doc.add_picture(src)` with `Inches(4)` width fallback |

## Inline rendering

Inline children (`text`, `strong`, `emphasis`, `codespan`, `link`) are rendered as separate runs within a single paragraph. Hyperlinks use OOXML `w:hyperlink` elements with `r:id` relationships.

## Known quirks

- `List Bullet N` styles only exist up to `List Bullet 9` in python-docx. Beyond depth 9, falls back to `List Bullet`.
- `doc.add_picture()` requires a filesystem path or file-like object; data URIs are skipped.
- Empty paragraphs after headings are normal — markdown blank lines produce empty `paragraph` nodes which are dropped.
- Font embedding is not supported by python-docx natively; use PDF for guaranteed font fidelity.
