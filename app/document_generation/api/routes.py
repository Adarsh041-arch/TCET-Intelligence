import os
import uuid
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.document_generation.registry import GeneratorRegistry
from app.document_generation.converters.markdown_converter import markdown_to_html
from app.document_generation.preview.preview_generator import preview_generator
from app.document_generation.sandbox.sandbox_executor import sandbox_executor
from app.document_generation.storage.file_storage import file_storage
from app.document_generation.templates.template_manager import template_manager
from app.document_generation.templates.template_manager import template_manager as tm
from app.document_generation.generators.docx_generator import DOCXGenerator, docx_generate
from app.document_generation.generators.docx_generator_v2 import DOCXGeneratorV2, docx_generate_v2
from app.document_generation.generators.pdf_generator import PDFGenerator, pdf_generate
from app.document_generation.generators.pptx_generator import PPTXGenerator, pptx_generate
from app.document_generation.generators.pptx_generator_v2 import PPTXGeneratorV2, pptx_generate_v2
from app.document_generation.generators.xlsx_generator import XLSXGenerator, xlsx_generate
from app.document_generation.generators.xlsx_generator_v2 import XLSXGeneratorV2, xlsx_generate_v2

router = APIRouter(prefix="/api/document-gen", tags=["Document Generation"])


class GenerateRequest(BaseModel):
    markdown: Optional[str] = None
    html: Optional[str] = None
    format: str = Field(..., description="Output format: docx, pdf, pptx, xlsx")
    template_id: Optional[str] = "default"
    metadata: Optional[dict] = {}
    filename: Optional[str] = None
    generator_version: Optional[str] = Field("v1", description="v1 (legacy HTML pipeline) or v2 (AST pipeline)")


class GenerateResponse(BaseModel):
    success: bool
    job_id: str
    format: str
    filename: str
    size: int
    download_url: str
    preview_url: Optional[str] = None


class PreviewRequest(BaseModel):
    markdown: Optional[str] = None
    html: Optional[str] = None
    format: str = Field(..., description="Output format: docx, pdf, pptx, xlsx")
    template_id: Optional[str] = "default"


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str


GENERATOR_MODULES = {
    "docx": "app.document_generation.generators.docx_generator",
    "docx-v2": "app.document_generation.generators.docx_generator_v2",
    "pdf": "app.document_generation.generators.pdf_generator",
    "pptx": "app.document_generation.generators.pptx_generator",
    "pptx-v2": "app.document_generation.generators.pptx_generator_v2",
    "xlsx": "app.document_generation.generators.xlsx_generator",
    "xlsx-v2": "app.document_generation.generators.xlsx_generator_v2",
}


def _register_generators():
    GeneratorRegistry.register("docx", DOCXGenerator)
    GeneratorRegistry.register("docx-v2", DOCXGeneratorV2)
    GeneratorRegistry.register("pdf", PDFGenerator)
    GeneratorRegistry.register("pptx", PPTXGenerator)
    GeneratorRegistry.register("pptx-v2", PPTXGeneratorV2)
    GeneratorRegistry.register("xlsx", XLSXGenerator)
    GeneratorRegistry.register("xlsx-v2", XLSXGeneratorV2)

_register_generators()


@router.post("/generate", response_model=GenerateResponse)
async def generate_document(request: GenerateRequest):
    if not request.markdown and not request.html:
        raise HTTPException(status_code=400, detail="Either markdown or html must be provided")

    if request.format.lower() not in GeneratorRegistry.list_supported():
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {request.format}. Supported: {GeneratorRegistry.list_supported()}",
        )

    fmt = request.format.lower()
    gen_version = request.generator_version or "v1"
    v2_formats = {"docx", "pptx", "xlsx"}
    is_v2 = gen_version == "v2" and fmt in v2_formats
    effective_fmt = f"{fmt}-v2" if is_v2 else fmt

    job_id = str(uuid.uuid4())

    try:
        if is_v2:
            input_text = request.markdown or request.html or ""
            template = template_manager.get_template(request.template_id or "default")
            workspace = file_storage.create_workspace(job_id)
            filename = request.filename or f"document_{job_id[:8]}.{fmt}"
            gen = GeneratorRegistry.get(effective_fmt)
            file_bytes = gen.generate(input_text, template, request.metadata)
        else:
            if request.markdown and not request.html:
                html_content = markdown_to_html(request.markdown)
            elif request.html:
                html_content = request.html
                from app.document_generation.utils.sanitizer import sanitize_html
                html_content = sanitize_html(html_content)
            else:
                html_content = markdown_to_html(request.markdown)

            template = template_manager.get_template(request.template_id or "default")
            workspace = file_storage.create_workspace(job_id)
            filename = request.filename or f"document_{job_id[:8]}.{fmt}"
            styled_html = tm.apply_template(html_content, template)

            gen = GeneratorRegistry.get(fmt)
            file_bytes = gen.generate(styled_html, template, request.metadata)

        filepath = file_storage.store_file(file_bytes, filename, job_id)
        file_size = len(file_bytes)

        download_url = file_storage.get_download_url(job_id, filename)

        preview_url = None
        if fmt in ("docx", "pdf", "pptx", "xlsx"):
            preview_url = f"/api/document-gen/preview/{job_id}/{filename}?format={fmt}"

        return GenerateResponse(
            success=True,
            job_id=job_id,
            format=fmt,
            filename=filename,
            size=file_size,
            download_url=download_url,
            preview_url=preview_url,
        )

    except Exception as e:
        file_storage.cleanup_workspace(job_id)
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")


@router.post("/preview")
async def preview_document(request: PreviewRequest):
    if not request.markdown and not request.html:
        raise HTTPException(status_code=400, detail="Either markdown or html must be provided")

    try:
        if request.markdown:
            html_content = markdown_to_html(request.markdown)
        else:
            html_content = request.html
            from app.document_generation.utils.sanitizer import sanitize_html
            html_content = sanitize_html(html_content)

        template = template_manager.get_template(request.template_id or "default")
        from app.document_generation.templates.template_manager import template_manager as tm
        styled_html = tm.apply_template(html_content, template)

        preview_data = preview_generator.generate(styled_html, request.format, template)
        return {"success": True, "preview": preview_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@router.get("/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    filepath = file_storage.get_file_path(job_id, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found or expired")

    ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    return FileResponse(
        path=filepath,
        media_type=media_types.get(ext, "application/octet-stream"),
        filename=filename,
    )


@router.get("/preview/{job_id}/{filename}")
async def preview_file(job_id: str, filename: str, format: str = Query(...)):
    filepath = file_storage.get_file_path(job_id, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Preview file not found")

    if format == "pdf":
        return FileResponse(
            path=filepath,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    file_bytes = file_storage.read_file(filepath)
    if not file_bytes:
        raise HTTPException(status_code=404, detail="File not found")

    preview_data = preview_generator.generate("", format)
    return {"success": True, "preview": preview_data}


@router.get("/formats")
async def list_formats():
    return {
        "formats": [
            {
                "id": "docx",
                "name": "Word Document (legacy)",
                "extension": ".docx",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            {
                "id": "docx-v2",
                "name": "Word Document (v2)",
                "extension": ".docx",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            {
                "id": "pdf",
                "name": "PDF Document",
                "extension": ".pdf",
                "mime": "application/pdf",
            },
            {
                "id": "pptx",
                "name": "PowerPoint Presentation (legacy)",
                "extension": ".pptx",
                "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            },
            {
                "id": "pptx-v2",
                "name": "PowerPoint Presentation (v2)",
                "extension": ".pptx",
                "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            },
            {
                "id": "xlsx",
                "name": "Excel Spreadsheet (legacy)",
                "extension": ".xlsx",
                "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            {
                "id": "xlsx-v2",
                "name": "Excel Spreadsheet (v2)",
                "extension": ".xlsx",
                "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
        ]
    }


@router.get("/templates", response_model=list[TemplateInfo])
async def list_templates():
    return template_manager.list_templates()


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    tmpl = template_manager.get_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return tmpl
