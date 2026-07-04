# PPTX Generator (AST → python-pptx)

**File:** `app/document_generation/generators/pptx_generator_v2.py`

## Architecture

Uses `python-pptx` (v1.0.2). Walks the shared AST. Slide splitting is handled by `_split_slides()`.

## Slide splitting heuristic

`_split_slides(blocks)` — named, testable function:

- Each H1/H2 starts a new slide
- A `thematic_break` (`---`) also splits
- If no splits occur, all content lands on one slide
- Empty slides produce a blank placeholder slide

## Block → API mapping

| AST node | python-pptx API |
|---|---|
| `heading` | `slide.shapes.add_textbox()` + bold, colored run |
| `paragraph` | `slide.shapes.add_textbox()` + word-wrapped text frame |
| `list` | `slide.shapes.add_textbox()` with bullet-prefixed paragraphs |
| `block_code` | `slide.shapes.add_textbox()` with `Courier New` |
| `table` | `slide.shapes.add_table(rows, cols)` |
| `block_quote` | Indented textbox with italic gray text |

## Inline rendering

Inline tokens are **flattened** to text (bold/italic lost in slides since python-pptx runs within a single text frame don't easily support mixed formatting at this level). For richer formatting, consider per-character runs.

## Known quirks

- `slide_layouts[6]` is used (blank layout). Index depends on template; custom templates may have different layout indices.
- Text overflow beyond slide height (`Inches(6.5)`) is silently truncated.
- Table row heights are estimated at `0.4 * rows` inches.
- `add_picture()` is not implemented for PPTX yet — images are skipped.
- Placeholder indices (e.g. `slide.placeholders[0]`) vary by layout; using `add_textbox()` is more predictable.
