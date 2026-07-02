import asyncio
import logging
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

from app.core.config import config
from app.models.database import db

logger = logging.getLogger(__name__)


def _find_npx() -> str:
    """Locate the npx executable, searching common install paths."""
    if os.name != "nt":
        return "npx"
    candidates = [
        "npx.cmd",
        os.path.join(os.environ.get("ProgramFiles", ""), "nodejs", "npx.cmd"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "nodejs", "npx.cmd"),
        os.path.join(os.environ.get("APPDATA", ""), "npm", "npx.cmd"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "fnm", "nodejs", "npx.cmd"),
    ]
    for p in candidates:
        if p == "npx.cmd":
            resolved = shutil.which("npx.cmd") or shutil.which("npx")
            if resolved:
                logger.info("Found npx via PATH: %s", resolved)
                return resolved
        elif os.path.isfile(p):
            logger.info("Found npx at: %s", p)
            return p
    fallback = R"C:\Program Files\nodejs\npx.cmd"
    if os.path.isfile(fallback):
        logger.info("Found npx at fallback: %s", fallback)
        return fallback
    logger.warning("npx not found, using bare 'npx.cmd'")
    return "npx.cmd"


def _ensure_node_on_path(env: dict) -> dict:
    """Ensure Node.js directories are in the subprocess PATH."""
    node_dirs = [
        os.environ.get("ProgramFiles", "") + "\\nodejs",
        os.environ.get("ProgramFiles(x86)", "") + "\\nodejs",
        os.environ.get("APPDATA", "") + "\\npm",
        os.environ.get("LOCALAPPDATA", "") + "\\fnm\\nodejs",
    ]
    path = env.get("PATH", "")
    parts = path.split(";")
    added = 0
    for d in node_dirs:
        if d and os.path.isdir(d) and d not in parts:
            parts.insert(0, d)
            added += 1
    if added:
        env["PATH"] = ";".join(parts)
    return env


def _get_allowed_dirs(user_id: Optional[str] = None) -> List[str]:
    """Return the list of allowed directories for a user.
    
    If user_id is provided, returns their per-user directories from the DB.
    Falls back to the global config mcp_allowed_directory if no per-user dirs exist.
    Falls further back to the app data/upload folder.
    """
    dirs = []
    if user_id:
        dirs = db.get_user_directories(user_id)
    if not dirs:
        default = config.mcp_allowed_directory
        if default:
            dirs = [os.path.normpath(default)]
        else:
            default = os.path.join(os.getcwd(), "data")
            os.makedirs(default, exist_ok=True)
            dirs = [os.path.normpath(default)]
    return dirs


def _unpack_error(e: Exception) -> str:
    if hasattr(e, "exceptions") and e.exceptions:
        parts = []
        for ex in e.exceptions:
            parts.append(_unpack_error(ex))
        return "; ".join(parts)
    return f"[{type(e).__name__}] {e}"


def _extract_extension(query: str) -> Optional[str]:
    m = re.search(r"\.(\w{1,5})\s+files?", query, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _build_listing_prompt(query: str, dirs_str: str) -> str:
    ext = _extract_extension(query)
    if ext:
        return (
            f"User asked: {query}\n\n"
            f"Call list_directory ONCE on the target folder. "
            f"From the returned listing, pick out only the *.{ext} files "
            f"and present them in your answer. Do NOT call list_directory "
            f"more than once."
        )
    return query


async def stream_mcp_agent(
    query: str,
    chat_history: List[Dict[str, str]],
    user_id: Optional[str] = None,
):
    """Async generator. Yields {'type': 'thinking'|'final', 'text': str} live
    as the agent works, then one {'type': 'final', 'text': str} with the answer."""
    allowed_dirs = _get_allowed_dirs(user_id)

    env = os.environ.copy()
    env["npm_config_update_notifier"] = "false"
    env = _ensure_node_on_path(env)
    npx_path = _find_npx()

    server_params = StdioServerParameters(
        command=npx_path,
        args=["-y", "@modelcontextprotocol/server-filesystem", *allowed_dirs],
        env=env,
    )

    dirs_str = ", ".join(allowed_dirs)
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)

                llm = ChatOllama(
                    model=config.llm_model,
                    base_url=config.ollama_base_url,
                    num_ctx=4096,
                )

                agent = create_react_agent(llm, tools)

                messages = [
                    {
                        "role": "system",
                        "content": (
                            f"You are an advanced filesystem agent with FULL read/write access to: {dirs_str}. "
                            "YOU HAVE SPECIALIZED TOOLS to interact with files and folders. "
                            "CRITICAL INSTRUCTIONS: "
                            "1. ALWAYS use your provided tools to fulfill the user's request. "
                            f"2. You MUST provide the FULL ABSOLUTE PATH starting with one of the allowed directories in all tool calls. "
                            f"   Allowed directories: {dirs_str}. "
                            "   Do NOT use relative paths like '.' or general paths. "
                            "3. NEVER say 'I am an AI and cannot access files'. Execute the required tool immediately. "
                            "4. To find files by extension, call list_directory ONCE on the target folder, "
                            "   then filter the returned filenames yourself by extension in your final answer. "
                            "   Do NOT call list_directory more than once for the same directory."
                        ),
                    }
                ]

                for msg in chat_history[-5:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

                user_content = _build_listing_prompt(query, dirs_str)
                messages.append({
                    "role": "user",
                    "content": user_content,
                })

                logger.info(
                    "Invoking agent for user %s (query length=%d, history=%d)",
                    user_id, len(query), len(chat_history),
                )

                all_msgs = list(messages)

                async for event in agent.astream(
                    {"messages": messages},
                    config={"recursion_limit": 6},
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
                                    for k in ("path", "paths", "source", "destination", "pattern", "oldText", "newText"):
                                        if k in targs:
                                            v = targs[k]
                                            summary[k] = (v[:80] + "...") if isinstance(v, str) and len(v) > 80 else v
                                    if not summary:
                                        summary = {k: v for k, v in list(targs.items())[:3]}
                                    yield {"type": "thinking", "text": f"→ {tname} {summary}"}

                            elif typename == "ToolMessage":
                                tname = getattr(m, "name", "?")
                                content = getattr(m, "content", "")
                                snippet = content[:120].replace("\n", " ") if isinstance(content, str) else ""
                                yield {"type": "thinking", "text": f"← {tname} {snippet}"}

                final_msg = all_msgs[-1] if all_msgs else None
                output = final_msg.content if final_msg and hasattr(final_msg, "content") else None
                yield {"type": "final", "text": output or "Filesystem operation completed with no output."}

                logger.info("Agent finished for user %s", user_id)
    except Exception as e:
        error_str = _unpack_error(e)
        logger.error("MCP agent error for user %s: %s", user_id, error_str, exc_info=True)
        if "Access denied" in error_str or "outside the allowed directory" in error_str:
            yield {"type": "final", "text": "The requested file or folder is outside the allowed directory, so access was denied."}
        else:
            yield {"type": "final", "text": f"Filesystem error: {error_str}"}


async def _collect_mcp_agent(
    query: str,
    chat_history: List[Dict[str, str]],
    user_id: Optional[str] = None,
) -> tuple[str, list[str]]:
    """Collect all events from stream_mcp_agent into (final_text, thinking_steps)."""
    thinking: list[str] = []
    final_text = "Filesystem operation completed with no output."
    async for event in stream_mcp_agent(query, chat_history, user_id):
        if event["type"] == "thinking":
            thinking.append(event["text"])
        else:
            final_text = event["text"]
    return final_text, thinking


def run_mcp_filesystem_agent(
    query: str,
    chat_history: List[Dict[str, str]] = None,
    user_id: Optional[str] = None,
) -> str:
    """Synchronous wrapper to run the MCP agent."""
    if chat_history is None:
        chat_history = []

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            resp, _ = loop.run_until_complete(
                _collect_mcp_agent(query, chat_history, user_id)
            )
            return resp
        else:
            resp, _ = loop.run_until_complete(
                _collect_mcp_agent(query, chat_history, user_id)
            )
            return resp
    except RuntimeError:
        resp, _ = asyncio.run(_collect_mcp_agent(query, chat_history, user_id))
        return resp
