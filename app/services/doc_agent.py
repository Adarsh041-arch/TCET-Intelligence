"""Documentation agent — generates documents via chat in documentation mode.

Takes user's natural language request, generates markdown content via LLM,
passes it to the document generation pipeline, and returns download/preview URLs.
"""
import json
import uuid
import os
from typing import AsyncGenerator, Dict, Any, Optional, List
from app.services.llm import llm_service
from app.document_generation.storage.file_storage import file_storage
from app.document_generation.templates.template_manager import template_manager
from app.document_generation.registry import GeneratorRegistry
from app.document_generation.markdown_ast import parse as ast_parse
from app.prompts.documentation import DOCUMENTATION_SYSTEM_PROMPT
from app.services.doc_feature_extractor import extract_features


# Formats that work with v2 generators
V2_FORMATS = {"docx", "pptx", "xlsx"}


async def stream_documentation_agent(
    query: str,
    chat_history: List[Dict[str, Any]],
    attached_files: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream documentation mode responses.

    Yields events:
      {"type": "thinking", "text": "..."}  — reasoning steps
      {"type": "token", "text": "..."}     — response tokens
      {"type": "document", ...}            — final document result
    """
    yield {"type": "thinking", "text": "Understanding your document request..."}

    # 1. Extract features from any attached reference documents
    doc_features = []
    if attached_files:
        yield {"type": "thinking", "text": f"Analyzing {len(attached_files)} reference document(s)..."}
        docs_base = os.path.join(os.getcwd(), "data", "uploads")
        for fname in attached_files:
            fpath = os.path.join(docs_base, fname)
            if os.path.exists(fpath):
                features = extract_features(fpath)
                doc_features.append({"filename": fname, "features": features})
                yield {"type": "thinking", "text": f"Extracted features from {fname}: {json.dumps(features, default=str)[:200]}"}

    # 2. Build the LLM prompt
    features_context = ""
    if doc_features:
        features_context = "\nReference document features:\n"
        for df in doc_features:
            features_context += f"- {df['filename']}: {json.dumps(df['features'], default=str)}\n"

    system_prompt = DOCUMENTATION_SYSTEM_PROMPT + (
        "\n\nIMPORTANT: First decide what format and content the user wants. "
        "Generate the complete markdown content for the document. "
        "Then, to actually create the document, call the generate_document tool.\n\n"
        "RESPONSE FORMAT: Your response should include:\n"
        "1. A brief description of what you're creating\n"
        "2. The generated markdown content (in a code block)\n"
        "3. The format suggestion\n"
        "ALWAYS generate a complete document — don't just describe what you would do."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-5:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = f"User request: {query}\n{features_context}" if features_context else f"User request: {query}"
    messages.append({"role": "user", "content": user_content})

    # 3. Get LLM response (the markdown content)
    yield {"type": "thinking", "text": "Generating document content..."}

    try:
        response = llm_service.chat(messages)
        markdown_content = response.strip()

        # Strip code fences if present
        if markdown_content.startswith("```"):
            lines = markdown_content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            markdown_content = "\n".join(lines).strip()

        yield {"type": "thinking", "text": "Generating document file..."}

        # 4. Detect format from the user query
        fmt = _detect_format(query)
        job_id = str(uuid.uuid4())

        # 5. Generate the document
        is_v2 = fmt in V2_FORMATS
        effective_fmt = f"{fmt}-v2" if is_v2 else fmt
        template = template_manager.get_template("default")
        gen = GeneratorRegistry.get(effective_fmt)
        file_bytes = gen.generate(markdown_content, template, {})

        filename = f"document_{job_id[:8]}.{fmt}"
        filepath = file_storage.store_file(file_bytes, filename, job_id)
        download_url = file_storage.get_download_url(job_id, filename)
        preview_url = f"/api/document-gen/preview/{job_id}/{filename}?format={fmt}"

        yield {"type": "thinking", "text": "Document generated successfully!"}

        # 6. Stream the markdown content as the assistant response
        words = markdown_content.split(" ")
        for i, w in enumerate(words):
            chunk = w + (" " if i < len(words) - 1 else "")
            yield {"type": "token", "text": chunk}

        # 7. Yield the document result
        yield {
            "type": "document",
            "download_url": download_url,
            "preview_url": preview_url,
            "format": fmt,
            "filename": filename,
            "size": len(file_bytes),
        }

    except Exception as e:
        yield {"type": "thinking", "text": f"Error: {e}"}
        yield {"type": "token", "text": f"Sorry, I encountered an error while generating the document: {e}"}


def _detect_format(query: str) -> str:
    """Detect the desired output format from the user's query."""
    q = query.lower()
    if any(w in q for w in ["word", "docx", ".docx", "word document"]):
        return "docx"
    if any(w in q for w in ["pdf", ".pdf", "pdf document"]):
        return "pdf"
    if any(w in q for w in ["powerpoint", "ppt", "pptx", ".pptx", "slides", "presentation"]):
        return "pptx"
    if any(w in q for w in ["excel", "xlsx", ".xlsx", "spreadsheet", "sheet"]):
        return "xlsx"
    return "docx"


def _is_document_regeneration_query(query: str) -> bool:
    """Check if user is asking to modify a previously generated document."""
    q = query.lower()
    keywords = ["change", "modify", "update", "regenerate", "edit", "different", "instead",
                "style", "format", "color", "font", "layout", "add", "remove", "fix"]
    return any(k in q for k in keywords)
