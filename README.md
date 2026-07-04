# TCET Intelligence - Advanced RAG & Agentic Chatbot

A production-ready enterprise chatbot platform for Thakur College of Engineering and Technology, built with **FastAPI**, **React + Vite**, and local LLM inference via **Ollama**. Features RAG with adaptive partial/global document loading, SQL database execution, MCP filesystem agent, web search with image galleries, and document generation.

---

## Core Features

- **Adaptive RAG Engine** — Automatically decides between partial (top-5 chunks) and global (full document) retrieval based on query intent
- **MCP Filesystem Agent** — Read, write, and manage files through an LLM-powered agent using the Model Context Protocol
- **SQL Database Connector** — Query SQLite/MySQL/PostgreSQL databases in natural language
- **Web Search with Images** — Tavily-powered search with inline source citations and image galleries
- **Document Q&A** — Upload PDF, DOCX, XLSX, CSV, TXT files; index them locally with ChromaDB
- **Document Generation** — Generate formatted DOCX, PDF, PPTX, XLSX documents via sandboxed Python execution
- **TCET Docs Management** — Index and search college-managed documents (syllabus, notices, timetables, etc.)
- **Claude-Style UI** — Clean chat interface with collapsible sidebar, mode toggles, and source references
- **Streamlit Alternative** — Lightweight Streamlit frontend as an alternative to the React UI
- **Authentication** — JWT-based login with admin/user roles

---

## Project Structure

```
.
├── app/
│   ├── api/                # FastAPI endpoints (auth, chat, admin, SQL)
│   ├── core/               # Config parsing (config.json), utilities
│   ├── document_generation/ # DOCX/PDF/PPTX/XLSX generation with sandbox
│   ├── documents/          # Text extraction and chunking pipeline
│   ├── graphs/             # LangGraph conversational agent workflow
│   ├── models/             # SQLite database model wrapper
│   ├── prompts/            # System prompts for each query type
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # LLM, embeddings, vector store, MCP agent, web search, auth
│   └── main.py             # FastAPI entry point
├── data/
│   ├── chroma/             # ChromaDB persistent vector store
│   ├── uploads/            # Uploaded user documents
│   └── tcet_docs/          # College-managed documents
├── frontend/
│   ├── src/
│   │   ├── components/     # React components (ChatPanel, Sidebar, Modals, Pages)
│   │   ├── context/        # Auth context provider
│   │   ├── services/       # HTTP API client
│   │   ├── App.jsx         # Layout shell
│   │   └── index.css       # Main stylesheet
│   └── vite.config.js
├── config.json             # Global settings (Ollama URL, model, chunk params, etc.)
├── latency_test.py         # Latency benchmark for all critical operations
├── streamlit_app.py        # Alternative Streamlit frontend
├── run_all.bat             # One-click launcher
└── requirements.txt
```

---

## RAG: Partial vs Global Loading

The system intelligently chooses between two retrieval strategies based on query intent:

| Query Type | Strategy | Example |
|---|---|---|
| **Topic-specific** | Partial — top 5 most relevant chunks | "What is the attendance policy?" |
| **Document-specific** | Global — ALL chunks of the matching document | "Show me the full fees structure document" |

Detection uses a two-stage approach:
1. **Keyword fast-path** — Instant match on phrases like "show me", "full document", "read the file"
2. **LLM fallback** — A lightweight classification call for ambiguous queries

---

## MCP Filesystem Agent

The MCP agent uses `@modelcontextprotocol/server-filesystem` with a configurable recursion limit:

| Parameter | Default | Description |
|---|---|---|
| `recursion_limit` | 20 | Max tool-call + reasoning steps per query |
| `timeout` | 180s | Hard deadline for filesystem operations |

---

## Latency Benchmarks

Measured on local hardware (Ollama + SQLite + ChromaDB). Average of 5 iterations:

| Category | Avg Latency | Fastest | Slowest |
|---|---|---|---|
| Vector Store (embed + search) | ~245ms | 1.3ms (count) | 5631ms (first cold embed) |
| LLM Generation | ~350ms | 0ms (cached) | 1642ms |
| Database (SQLite) | ~3ms | 2.7ms | 7.7ms |
| Auth (bcrypt + JWT) | ~328ms | 0.1ms (JWT) | 868ms (bcrypt) |
| Doc Processing (chunking) | ~0.4ms | 0.3ms | 0.9ms |

---

## Configuration

Edit `config.json` to customize behavior:

```json
{
    "ollama_base_url": "http://localhost:11434",
    "llm_model": "gemma4:31b-cloud",
    "embedding_model": "nomic-embed-text:latest",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "top_k": 5,
    "similarity_threshold": 0.45,
    "mcp_allowed_directory": "C:/Users/.../Desktop",
    "admin_username": "admin",
    "admin_password": "admin123"
}
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Ollama installed and running

### Setup

```bash
# Clone and setup
git clone <repo-url>
cd TCET-Chatbot
setup.bat

# Pull models
ollama pull gemma4:31b-cloud
ollama pull nomic-embed-text:latest
```

---

## Running

### Full Stack
```bash
.\run_all.bat
```
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- API Docs: `http://localhost:8000/docs`

### Streamlit Only
```bash
streamlit run streamlit_app.py
```

---

## Default Credentials

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| User | (register via UI) | — |

---

## Troubleshooting

- **Slow LLM response** — Ensure Ollama is running (`ollama serve`)
- **Reset vector store** — Delete `data/chroma/` and re-upload documents
- **MCP agent fails** — Verify `mcp_allowed_directory` in config.json and that `npx` is available
