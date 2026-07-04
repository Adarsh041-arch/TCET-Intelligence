import io
import re
import base64
from typing import Dict, Any, Optional
from app.document_generation.generators.base import BaseGenerator
from app.document_generation.templates.template_manager import template_manager


class PDFGenerator(BaseGenerator):
    @property
    def format(self) -> str:
        return "pdf"

    @property
    def mime_type(self) -> str:
        return "application/pdf"

    @property
    def file_extension(self) -> str:
        return ".pdf"

    def generate(self, html: str, template: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> bytes:
        styled_html = self._prepare_html(html, template)
        try:
            return self._generate_with_playwright(styled_html)
        except ImportError:
            return self._generate_with_fpdf(styled_html)

    def generate_preview(self, html: str, template: Optional[Dict[str, Any]] = None) -> bytes:
        return self.generate(html, template)

    def _prepare_html(self, html: str, template: Optional[Dict] = None) -> str:
        if template:
            return template_manager.apply_template(html, template)

        base_styles = """
        <style>
            @page { margin: 20mm; }
            body {
                font-family: Arial, sans-serif;
                font-size: 12pt;
                line-height: 1.6;
                color: #333;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: Arial, sans-serif;
                color: #1a1a2e;
                margin-top: 1.2em;
                margin-bottom: 0.5em;
            }
            h1 { font-size: 24pt; }
            h2 { font-size: 20pt; }
            h3 { font-size: 16pt; }
            h4 { font-size: 14pt; }
            table { border-collapse: collapse; width: 100%; margin: 1em 0; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background: #f5f5f5; font-weight: bold; }
            pre { background: #f5f5f5; border: 1px solid #ddd; padding: 12px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 10pt; overflow-x: auto; }
            code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: 'Courier New', monospace; }
            blockquote { border-left: 4px solid #ccc; margin: 1em 0; padding: 0.5em 1em; color: #666; background: #fafafa; }
            img { max-width: 100%; height: auto; }
            hr { border: none; border-top: 2px solid #ccc; margin: 1.5em 0; }
            ul, ol { margin: 0.5em 0; padding-left: 2em; }
            li { margin: 0.3em 0; }
            .page-break { page-break-before: always; }
        </style>
        """
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{base_styles}
</head>
<body>
{html}
</body>
</html>"""

    def _generate_with_playwright(self, html: str) -> bytes:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"},
                print_background=True,
            )
            browser.close()
            return pdf_bytes

    def _generate_with_fpdf(self, html: str) -> bytes:
        import os
        from fpdf import FPDF

        class _StyledPDF(FPDF):
            def header(self):
                self.set_font(self._uni_family, "B", 10)
                self.set_text_color(160, 160, 160)
                self.cell(0, 8, "", align="R", new_x="LMARGIN", new_y="NEXT")

            def footer(self):
                self.set_y(-15)
                self.set_font(self._uni_family, "I", 8)
                self.set_text_color(160, 160, 160)
                self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

        pdf = _StyledPDF()

        # Register a Unicode TTF font so symbols like ₹, €, ₿ etc. work
        font_family = "Helvetica"  # default fallback
        font_candidates = [
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        for font_path in font_candidates:
            if os.path.isfile(font_path):
                try:
                    pdf.add_font("UniFont", "", font_path)
                    pdf.add_font("UniFont", "B", font_path)
                    pdf.add_font("UniFont", "I", font_path)
                    font_family = "UniFont"
                except Exception:
                    pass
                break

        pdf._uni_family = font_family

        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_font(font_family, size=11)

        # fpdf2's write_html does NOT understand <style>, <head>, <script>, <!DOCTYPE>, etc.
        # Strip them so they don't render as visible text.
        clean = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<script[^>]*>.*?</script>", "", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<head[^>]*>.*?</head>", "", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<!DOCTYPE[^>]*>", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"</?(?:html|body|meta)[^>]*>", "", clean, flags=re.IGNORECASE)
        clean = clean.strip()

        # fpdf2's write_html natively handles: h1-h6, b, i, u, a, br, hr,
        # ul/ol/li, table/tr/th/td, pre/code, blockquote, img, p, sup, sub
        pdf.write_html(clean)

        return pdf.output()


def pdf_generate(html: str, template: Optional[Dict] = None, metadata: Optional[Dict] = None) -> bytes:
    gen = PDFGenerator()
    return gen.generate(html, template, metadata)
