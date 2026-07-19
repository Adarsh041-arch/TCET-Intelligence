# TCET Intelligence - Advanced RAG & Agentic Chatbot

A production-ready enterprise chatbot platform for Thakur College of Engineering and Technology, built with **FastAPI**, **React + Vite**, and local LLM inference via **Ollama**. Features RAG with adaptive partial/global document loading, SQL database execution, MCP filesystem agent, web search with image galleries, document generation, and long-term user memory.

---

## Core Features

- **Adaptive RAG Engine** — Automatically decides between partial (top-5 chunks) and global (full document) retrieval based on query intent
- **MCP Filesystem Agent** — Read, write, and manage files through an LLM-powered agent using the Model Context Protocol
- **SQL Database Connector** — Query SQLite/MySQL/PostgreSQL databases in natural language
- **Web Search with Images** — Tavily-powered search with inline source citations and image galleries
- **Document Q&A** — Upload PDF, DOCX, XLSX, CSV, TXT files; index them locally with ChromaDB
- **Document Generation** — Generate formatted DOCX, PDF, PPTX, XLSX documents via sandboxed Python execution
- **TCET Docs Management** — Index and search college-managed documents (syllabus, notices, timetables, etc.)
- **Long-Term User Memory** — ChromaDB-based memory system that stores user preferences, personal info, and conversation facts across sessions
- **Multi-Mode Agent Orchestrator** — LangGraph ReAct agent that can combine RAG, SQL, web search, filesystem, and documentation tools in one workflow
- **Docker Support** — PostgreSQL + backend + frontend via docker-compose
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
│   │   ├── general.py      # General chat prompt
│   │   ├── rag.py          # RAG/staff prompt
│   │   ├── sql.py          # SQL planning, generation, retry prompts
│   │   ├── web.py          # Web search prompt
│   │   ├── documentation.py# Document generation prompt
│   │   ├── filesystem.py   # Filesystem agent prompt
│   │   └── memory.py       # Memory extraction prompt + VALID_CATEGORIES
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/
│   │   ├── llm.py          # LLM interface (Ollama), SQL retry logic
│   │   ├── embeddings.py   # Embedding service
│   │   ├── vector_store.py # ChromaDB vector store
│   │   ├── memory_store.py # ChromaDB-based user memory store
│   │   ├── sql_connector.py# SQLite/MySQL/PostgreSQL connector
│   │   ├── agent_orchestrator.py  # Multi-mode ReAct agent
│   │   ├── chat.py         # Chat service
│   │   ├── auth.py         # JWT authentication
│   │   ├── web_search.py   # Tavily web search
│   │   └── doc_agent.py    # Document processing agent
│   └── main.py             # FastAPI entry point
├── data/
│   ├── chroma/             # ChromaDB persistent vector store (TCET docs)
│   ├── chroma_user/        # ChromaDB user documents + memory store
│   ├── uploads/            # Uploaded user documents
│   └── tcet_docs/          # College-managed documents
├── frontend/
│   ├── src/
│   │   ├── components/     # React components (ChatPanel, Sidebar, Modals, Pages)
│   │   ├── context/        # Auth context provider
│   │   ├── services/       # HTTP API client
│   │   ├── App.jsx         # Layout shell
│   │   └── index.css       # Main stylesheet
│   ├── Dockerfile          # Frontend container (Nginx)
│   ├── nginx.conf          # Nginx config for SPA + API proxy
│   └── vite.config.js
├── config.json             # Global settings (Ollama URL, model, chunk params, DB, etc.)
├── docker-compose.yml      # PostgreSQL + Backend + Frontend containers
├── Dockerfile              # Backend container
├── latency_test.py         # Latency benchmark for all critical operations
├── streamlit_app.py        # Alternative Streamlit frontend
├── setup.bat               # Setup script
├── install_deps.bat        # Dependency installer
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

## SQL Database Connector

Query connected databases using natural language. The system:
1. Discovers tables and schemas from the database
2. Plans the query (tables, joins, filters)
3. Generates and executes SQL
4. Retries up to 2 times on error with automatic error analysis
5. Formats results as a clean markdown table

### Supported Databases
- PostgreSQL (via psycopg2)
- MySQL (via mysql-connector-python)
- SQLite

### Configuration
Add database connections in `config.json` under `sql_databases`:
```json
{
    "sql_databases": {
        "default": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5433,
            "user": "admin",
            "password": "admin123",
            "database": "tcet_tnp_db"
        }
    }
}
```

---

## User Memory System

The chatbot maintains long-term memory per user using a ChromaDB vector store.

### Memory Categories
| Category | Usage |
|---|---|
| User | Identity & role information |
| preferences | User preferences & settings |
| professional_info | Work/education details |
| likes | User interests & likes |
| dislikes | User dislikes & aversions |
| personal | Personal information |
| contact | Contact details |
| education | Educational background |
| skill | Skills & expertise |
| other | Miscellaneous facts |

### Available Tools (always active in multi-mode)
- `read_memory` — Search stored memories about the user
- `write_memory` — Store new facts in long-term memory
- `update_memory` — Update an existing memory
- `delete_memory` — Delete a memory by ID

Memories are automatically extracted from conversations and stored with confidence scores.

---

## MCP Filesystem Agent

The MCP agent uses `@modelcontextprotocol/server-filesystem` with a configurable recursion limit:

| Parameter | Default | Description |
|---|---|---|
| `recursion_limit` | 20 | Max tool-call + reasoning steps per query |
| `timeout` | 180s | Hard deadline for filesystem operations |

---

## Multi-Mode Agent Orchestrator

When multiple modes are toggled on, the system creates a LangGraph ReAct agent with access to all corresponding tools:
- **RAG mode** → `search_tcet_docs`, `search_user_docs`
- **SQL mode** → `get_table_schemas`, `query_database`
- **Web mode** → `web_search`
- **Filesystem mode** → `list_directory`, `read_file`, `write_file`, `search_files`, `get_file_info`
- **Documentation mode** → `generate_document`
- **Memory (always)** → `read_memory`, `write_memory`, `update_memory`, `delete_memory`

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
    "sql_max_iterations": 2,
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
- Docker (optional, for containerized deployment)

### Quick Setup

```bash
# Clone and setup
git clone <repo-url>
cd TCET-Chatbot
setup.bat

# Pull models
ollama pull gemma4:31b-cloud
ollama pull nomic-embed-text:latest
```

### Docker Deployment

```bash
docker-compose up -d
```
- PostgreSQL available on `localhost:5433`
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

---

## Running

### Full Stack (Bare Metal)
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
- **Database connection refused** — Ensure PostgreSQL/MySQL is running on the configured port
- **Memory not working** — Check `data/chroma_user/` directory exists and is writable
