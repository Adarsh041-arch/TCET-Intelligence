# XLSX Generator (AST → openpyxl)

**File:** `app/document_generation/generators/xlsx_generator_v2.py`

## Architecture

Uses `openpyxl` (v3.1.5). Walks the shared AST.

## Design decisions

- **Tables** are the primary output. If the markdown contains at least one `table` AST node, each table gets its own sheet.
- **Non-tabular content** (paragraphs, lists, code blocks) — when no tables are present — goes into a single "Content" sheet with structured rows:
  - Headings → merged cells with dark header styling
  - Paragraphs → single-column text rows
  - List items → bullet column + text column
  - Code blocks → monospace rows with gray background

## Block → API mapping

| AST node | openpyxl API |
|---|---|
| `table` | `ws.cell(row, col, value=...)` per cell + header styling |
| `heading` | `ws.merge_cells()` + bold white-on-dark row |
| `paragraph` | `ws.cell()` with wrap_text |
| `block_code` | `ws.cell()` with `Courier New` font + gray fill |
| `list` | Bullet in col A, text in col B |

## Number/date type detection

Not currently implemented. All cell values are written as strings. For production, consider detecting numeric/date patterns and converting.

## Known quirks

- Sheet names are limited to 31 characters by Excel — truncated silently.
- Column widths are auto-sized based on content length, capped at 60.
- The `generate_preview()` method returns JSON metadata (not base64-encoded output) for frontend table display.
- Merged cells in heading rows may cause issues with some Excel readers — test with your target application.
