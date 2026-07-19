import base64
import json
from typing import Dict, Any, Optional
from app.document_generation.generators.docx_generator_v2 import DOCXGeneratorV2
from app.document_generation.generators.pdf_generator import PDFGenerator
from app.document_generation.generators.pptx_generator_v2 import PPTXGeneratorV2
from app.document_generation.generators.xlsx_generator_v2 import XLSXGeneratorV2


class PreviewGenerator:
    @staticmethod
    def generate(html: str, format: str, template: Optional[Dict] = None) -> Dict[str, Any]:
        format = format.lower()
        if format == "docx":
            return PreviewGenerator._docx_preview(html, template)
        elif format == "pdf":
            return PreviewGenerator._pdf_preview(html, template)
        elif format == "pptx":
            return PreviewGenerator._pptx_preview(html, template)
        elif format == "xlsx":
            return PreviewGenerator._xlsx_preview(html, template)
        else:
            raise ValueError(f"Unsupported preview format: {format}")

    @staticmethod
    def _docx_preview(html: str, template: Optional[Dict] = None) -> Dict[str, Any]:
        gen = DOCXGeneratorV2()
        try:
            docx_bytes = gen.generate_preview(html, template)
            preview_html = _extract_text_from_docx_preview(docx_bytes)
            return {
                "type": "html",
                "content": preview_html,
                "format": "docx",
            }
        except Exception as e:
            return {
                "type": "text",
                "content": f"Preview generation failed: {e}",
                "format": "docx",
            }

    @staticmethod
    def _pdf_preview(html: str, template: Optional[Dict] = None) -> Dict[str, Any]:
        gen = PDFGenerator()
        try:
            pdf_bytes = gen.generate_preview(html, template)
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return {
                "type": "pdf",
                "content": b64,
                "format": "pdf",
                "inline": True,
            }
        except Exception as e:
            return {
                "type": "text",
                "content": f"Preview generation failed: {e}",
                "format": "pdf",
            }

    @staticmethod
    def _pptx_preview(html: str, template: Optional[Dict] = None) -> Dict[str, Any]:
        gen = PPTXGeneratorV2()
        try:
            pngs = gen.generate_preview(html, template)
            images = []
            for png_data in pngs:
                images.append(base64.b64encode(png_data).decode("utf-8"))
            return {
                "type": "carousel",
                "content": images,
                "format": "pptx",
            }
        except Exception as e:
            return {
                "type": "text",
                "content": f"Preview generation failed: {e}",
                "format": "pptx",
            }

    @staticmethod
    def _xlsx_preview(html: str, template: Optional[Dict] = None) -> Dict[str, Any]:
        gen = XLSXGeneratorV2()
        try:
            preview_data = gen.generate_preview(html, template)
            return {
                "type": "table",
                "content": preview_data,
                "format": "xlsx",
            }
        except Exception as e:
            return {
                "type": "text",
                "content": f"Preview generation failed: {e}",
                "format": "xlsx",
            }


def _extract_text_from_docx_preview(docx_bytes: bytes) -> str:
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "<div>" + "".join(f"<p>{p}</p>" for p in paragraphs[:50]) + "</div>"
    except Exception:
        return "<p>Preview not available</p>"


preview_generator = PreviewGenerator()
