# PDF Generator (HTML → weasyprint)

**File:** `app/document_generation/generators/pdf_generator.py`

## Architecture

Keeps the HTML intermediate path — this is the one generator where HTML-as-intermediate is correct, since weasyprint renders real CSS layout.

## Current state

- **Primary:** Playwright (Chromium) for PDF generation via `page.pdf()`
- **Fallback:** fpdf2's `write_html()` (limited HTML subset)

## Future direction

- Standardize on **weasyprint** as the single PDF backend — drop both Playwright (heavy dependency) and fpdf2 (limited HTML support).
- Audit `apply_template()` CSS for print correctness:
  - `page-break-inside: avoid` on tables and code blocks
  - `@page` margin rules (currently hardcoded as 20mm)
  - Explicit font embedding via `@font-face` so PDFs don't silently reflow

## Block → CSS mapping

Since PDF uses the HTML pipeline, blocks are first converted to HTML via `markdown_to_html()` (the legacy converter), then wrapped with `template_manager.apply_template()`.

## Known quirks

- Playwright requires a Chromium binary download (~300MB).
- fpdf2's `write_html()` does not support `<style>`, `<head>`, or `<script>` tags — these must be stripped before rendering.
- Unicode fonts (₹, €, ₿) need explicit TTF registration in fpdf2 path.
- page-break behavior differs between Playwright and weasyprint — test both if keeping both backends.
