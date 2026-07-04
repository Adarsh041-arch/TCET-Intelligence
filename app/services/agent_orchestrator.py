"""Multi-mode agent orchestrator.

When the user toggles multiple modes, this service creates a LangGraph ReAct agent
that has access to all corresponding tools and can plan/execute multi-step tasks.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional, AsyncGenerator

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from app.core.config import config
from app.prompts.general import GENERAL_CHAT_PROMPT
from app.services.llm import llm_service
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

MODE_LABELS = {
    "rag": "College Document Search",
    "sql": "Database Query",
    "web": "Web Search",
    "documentation": "Document Generation",
    "filesystem": "Filesystem Access",
    "general": "General Knowledge",
}

MODE_DESCRIPTIONS = {
    "rag": "Search TCET-managed college documents (syllabus, attendance policy, fee structure, timetables, etc.) for relevant information.",
    "sql": "Execute natural-language queries against connected databases to retrieve structured data.",
    "web": "Search the web for current, real-time information on any topic.",
    "documentation": "Generate formatted documents (DOCX, PDF, PPTX, XLSX) from descriptions.",
    "filesystem": "Read and write files on the server within allowed directories.",
    "general": "Answer questions from the model's own knowledge (no external tools).",
}


def build_tools(modes: List[str], user_id: Optional[str] = None) -> list:
    """Build the list of LangChain tools for the given active modes."""

    tools = []

    if "rag" in modes:
        @tool
        async def search_tcet_docs(query: str) -> str:
            """Search TCET college documents (syllabus, attendance policy, fee structure, timetables, etc.) for information matching the query. Returns relevant document excerpts and their sources."""
            try:
                filter_dict = {"source": "tcet_managed"}
                docs = vector_store.retrieve_similar(
                    query, top_k=config.top_k, threshold=config.similarity_threshold,
                    filter_dict=filter_dict,
                )
                if not docs:
                    return "No relevant documents found in the TCET document store."
                lines = []
                for d in docs:
                    content = d.get("content", "")[:500]
                    filename = d.get("filename", "unknown")
                    sim = d.get("similarity", 0)
                    lines.append(f"[{filename}] (score={sim:.2f})\n{content}")
                return "\n\n".join(lines)
            except Exception as e:
                logger.error(f"search_tcet_docs error: {e}", exc_info=True)
                return f"Error searching TCET documents: {e}"

        tools.append(search_tcet_docs)

    if "sql" in modes:
        @tool
        async def get_table_schemas() -> str:
            """List all available database tables and their column names/types. Call this first before query_database."""
            try:
                from app.services.sql_connector import db_connector
                if not db_connector.current_connection:
                    return "No database is currently connected."
                tables = db_connector.get_tables()
                if not tables:
                    return "No tables found in the database."
                parts = []
                for table in tables:
                    schema = db_connector.get_table_schema(table)
                    cols = schema.get("columns", [])
                    col_strs = [f"{c['name']} ({c['type']})" for c in cols]
                    parts.append(f"Table: {table}\n  Columns: {', '.join(col_strs)}")
                return "\n\n".join(parts)
            except Exception as e:
                return f"Error getting schemas: {e}"

        @tool
        async def query_database(natural_language_query: str) -> str:
            """Convert a natural language question into SQL, execute it against the connected database, and return the results."""
            try:
                from app.services.sql_connector import db_connector
                if not db_connector.current_connection:
                    return "No database is currently connected."
                tables = db_connector.get_tables()
                schema_parts = []
                for table in tables:
                    schema = db_connector.get_table_schema(table)
                    cols = schema.get("columns", [])
                    col_strs = [f"{c['name']} ({c['type']})" for c in cols]
                    schema_parts.append(f"{table}: {', '.join(col_strs)}")
                table_info = "\n".join(schema_parts)
                sql_query = llm_service.generate_sql_query(natural_language_query, table_info)
                if not sql_query or sql_query.startswith("Error"):
                    return f"Could not generate SQL query: {sql_query}"
                sql_result = db_connector.execute_query(sql_query)
                response = llm_service.generate_sql_response(natural_language_query, sql_result)
                return response
            except Exception as e:
                return f"Error executing database query: {e}"

        tools.append(get_table_schemas)
        tools.append(query_database)

    if "web" in modes:
        @tool
        async def web_search(query: str) -> str:
            """Search the web for current, up-to-date information using Tavily. Returns search results with sources."""
            try:
                from app.services.web_search import web_search_service
                from app.models.database import db
                api_key = db.get_api_key(user_id, "tavily") if user_id else None
                if not api_key:
                    return "Web search is not configured. Please configure a Tavily API key."
                search_res = web_search_service.search(query, api_key)
                context = search_res.get("context", "")
                sources = search_res.get("sources", [])
                result = context + "\n\nSources:\n"
                for s in sources:
                    result += f"- {s.get('title', 'Untitled')}: {s.get('url', '')}\n"
                return result
            except Exception as e:
                return f"Error searching the web: {e}"

        tools.append(web_search)

    if "filesystem" in modes:
        import shutil
        import glob as glob_mod

        def _normalize_path(path: str, user_id: Optional[str] = None) -> str:
            """Resolve a path and verify it's within an allowed directory."""
            from app.services.mcp_agent import _get_allowed_dirs
            allowed = _get_allowed_dirs(user_id)
            abs_path = os.path.abspath(os.path.normpath(path))
            for d in allowed:
                allowed_abs = os.path.abspath(os.path.normpath(d))
                if abs_path.startswith(allowed_abs + os.sep) or abs_path == allowed_abs:
                    return abs_path
            raise PermissionError(
                f"Access denied: '{path}' is not within allowed directories: {', '.join(allowed)}"
            )

        @tool
        def list_directory(path: str = ".") -> str:
            """List files and directories in a folder. Path must be within allowed directories."""
            try:
                resolved = _normalize_path(path, user_id)
                entries = os.listdir(resolved)
                lines = []
                for e in sorted(entries):
                    full = os.path.join(resolved, e)
                    suffix = "/" if os.path.isdir(full) else ""
                    lines.append(f"{e}{suffix}")
                return "\n".join(lines) if lines else "(empty directory)"
            except Exception as e:
                return f"Error listing directory: {e}"

        @tool
        def read_file(path: str) -> str:
            """Read the contents of a text file. Path must be within allowed directories."""
            try:
                resolved = _normalize_path(path, user_id)
                if not os.path.isfile(resolved):
                    return f"File not found: {path}"
                with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return content
            except Exception as e:
                return f"Error reading file: {e}"

        @tool
        def write_file(path: str, content: str) -> str:
            """Write content to a file (creates or overwrites). Path must be within allowed directories."""
            try:
                resolved = _normalize_path(path, user_id)
                os.makedirs(os.path.dirname(resolved) or ".", exist_ok=True)
                with open(resolved, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"File written: {path} ({len(content)} bytes)"
            except Exception as e:
                return f"Error writing file: {e}"

        @tool
        def search_files(pattern: str, path: str = ".") -> str:
            """Search for files by glob pattern (e.g. '*.txt', '**/*.py'). Path must be within allowed directories."""
            try:
                resolved = _normalize_path(path, user_id)
                matches = glob_mod.glob(os.path.join(resolved, pattern), recursive=True)
                if not matches:
                    return f"No files matching '{pattern}' found in {path}"
                lines = []
                for m in sorted(matches):
                    rel = os.path.relpath(m, resolved)
                    lines.append(rel)
                return "\n".join(lines)
            except Exception as e:
                return f"Error searching files: {e}"

        @tool
        def get_file_info(path: str) -> str:
            """Get metadata about a file or directory (size, modified time, type). Path must be within allowed directories."""
            try:
                resolved = _normalize_path(path, user_id)
                if not os.path.exists(resolved):
                    return f"Path not found: {path}"
                stat = os.stat(resolved)
                kind = "directory" if os.path.isdir(resolved) else "file"
                size = stat.st_size
                from datetime import datetime
                mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                return f"Path: {path}\nType: {kind}\nSize: {size} bytes\nModified: {mtime}\nAbsolute: {resolved}"
            except Exception as e:
                return f"Error getting file info: {e}"

        tools.append(list_directory)
        tools.append(read_file)
        tools.append(write_file)
        tools.append(search_files)
        tools.append(get_file_info)

    if "documentation" in modes:
        from app.document_generation.storage.file_storage import file_storage
        from app.document_generation.registry import GeneratorRegistry
        from app.document_generation.templates.template_manager import template_manager
        from app.prompts.documentation import DOCUMENTATION_SYSTEM_PROMPT
        import uuid

        V2_FORMATS = {"docx", "pptx", "xlsx"}

        @tool
        def generate_document(description: str, format: str = "docx") -> str:
            """
            Generate a formatted document from a description.
            format can be: docx (Word), pdf, pptx (PowerPoint), or xlsx (Excel).
            Returns a download URL for the generated document.
            """
            import re
            try:
                from app.services.doc_agent import _detect_format
                fmt = _detect_format(description) or format
                effective_fmt = fmt if fmt in ("docx", "pdf", "pptx", "xlsx") else "docx"
                is_v2 = effective_fmt in V2_FORMATS
                reg_fmt = f"{effective_fmt}-v2" if is_v2 else effective_fmt
                markdown_content = llm_service.chat([
                    {"role": "system", "content": DOCUMENTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": description},
                ])
                if markdown_content.startswith("```"):
                    lines = markdown_content.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    markdown_content = "\n".join(lines).strip()
                markdown_content = re.sub(r"<[^>]+>", "", markdown_content)
                job_id = str(uuid.uuid4())
                ext = f".{effective_fmt}"
                filename = f"document_{job_id[:8]}{ext}"
                gen = GeneratorRegistry.get(reg_fmt)
                template = template_manager.get_template("default")
                result = gen.generate(markdown_content, template, {})
                file_storage.store_file(result, filename, job_id)
                download_url = file_storage.get_download_url(job_id, filename)
                return f"{download_url}"
            except Exception as e:
                return f"Error generating document: {e}"

        tools.append(generate_document)

    return tools


def build_system_prompt(modes: List[str]) -> str:
    """Build a system prompt that describes the available tools."""
    labels = [MODE_LABELS.get(m, m) for m in modes]
    caps = ", ".join(labels)

    tool_descriptions = []
    for m in modes:
        desc = MODE_DESCRIPTIONS.get(m, "")
        if desc:
            tool_descriptions.append(f"- {MODE_LABELS.get(m, m)}: {desc}")

    tools_section = "\n".join(tool_descriptions)

    prompt = f"""You are a multi-capability AI assistant with access to the following tools: {caps}.

## Available Capabilities
{tools_section}

## Instructions
- You have access to multiple tools. Use them as needed to fulfill the user's request.
- Analyze the user's request, break it down into steps, and call the appropriate tools.
- You can combine information from multiple sources (e.g., search documents, query databases, search the web) to provide comprehensive answers.
- If the user asks for a document, use the generate_document tool.
- If the user asks about college policies or TCET-specific information, search TCET documents first.
- If the user asks for current/real-time information, search the web first.
- If the user asks about data in connected databases, use the SQL tools.
- If the user asks to read, write, list, or search files, use the filesystem tools (list_directory, read_file, write_file, search_files, get_file_info).
- All filesystem operations are restricted to the user's allowed directories.
- **When a tool returns a URL, include that URL exactly as returned — do not rewrite or construct your own URL.**

For each major step, briefly announce what you're doing before calling the tool."""
    return prompt.strip()


def _build_llm() -> ChatOllama:
    return ChatOllama(
        model=config.llm_model,
        base_url=config.ollama_base_url,
        num_ctx=8192,
    )


async def stream_multi_agent(
    query: str,
    chat_history: List[Dict[str, str]],
    modes: List[str],
    user_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Async generator that streams agent events.

    Yields dicts with:
      - type: "thinking" | "milestone" | "token" | "final"
      - text: content text (for thinking, milestone, token, final)
    """
    tools = build_tools(modes, user_id)
    if not tools:
        # Fallback: no tools available for selected modes
        yield {"type": "milestone", "text": "No tools available for the selected modes. Falling back to general chat."}
        yield {"type": "token", "text": "No tools available."}
        yield {"type": "final", "text": "No tools available."}
        return

    llm = _build_llm()
    agent = create_react_agent(llm, tools)

    system_prompt = build_system_prompt(modes)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-5:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    logger.info(
        "Multi-agent starting for user %s, modes=%s, query_len=%d",
        user_id, modes, len(query),
    )

    all_msgs = list(messages)
    try:
        yield {"type": "milestone", "text": "Planning the approach..."}

        async for event in agent.astream(
            {"messages": messages},
            config={"recursion_limit": 25},
            stream_mode="updates",
        ):
            for node_name, update in event.items():
                if "messages" not in update:
                    continue
                new_msgs = update["messages"]
                all_msgs.extend(new_msgs)

                for m in new_msgs:
                    typename = type(m).__name__

                    if typename == "AIMessage":
                        tcalls = getattr(m, "tool_calls", [])
                        for tc in tcalls:
                            tname = tc.get("name", "?")
                            targs = tc.get("args", {})
                            summary = {}
                            for k in ("query", "description", "natural_language_query", "sql_query", "format"):
                                if k in targs:
                                    v = targs[k]
                                    summary[k] = (v[:80] + "...") if isinstance(v, str) and len(v) > 80 else v
                            if not summary:
                                summary = {k: v for k, v in list(targs.items())[:2]}
                            yield {"type": "milestone", "text": f"Using {tname}"}
                            yield {"type": "thinking", "text": f"→ Calling {tname} with {json.dumps(summary)}"}

                        tcalls = getattr(m, "tool_calls", [])
                        if not tcalls:
                            content = getattr(m, "content", "") or ""
                            if content:
                                yield {"type": "thinking", "text": content[:300]}

                    elif typename == "ToolMessage":
                        tname = getattr(m, "name", "?")
                        content = getattr(m, "content", "")
                        snippet = content[:150].replace("\n", " ") if isinstance(content, str) else ""
                        yield {"type": "thinking", "text": f"← {tname} returned: {snippet}"}

        # Extract final answer
        final_msg = all_msgs[-1] if all_msgs else None
        output = final_msg.content if final_msg and hasattr(final_msg, "content") else ""
        if not output:
            output = "Task completed."

        # Stream the final answer token by token
        words = output.split(" ")
        for i, w in enumerate(words):
            chunk = w + (" " if i < len(words) - 1 else "")
            yield {"type": "token", "text": chunk}

        yield {"type": "final", "text": output}
        logger.info("Multi-agent finished for user %s", user_id)

    except Exception as e:
        logger.error("Multi-agent error for user %s: %s", user_id, e, exc_info=True)
        yield {"type": "milestone", "text": f"Agent error: {e}"}
        yield {"type": "final", "text": f"An error occurred: {e}"}
