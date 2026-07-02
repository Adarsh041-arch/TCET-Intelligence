# 🏫 TCET Intelligence - Advanced RAG & Agentic Chatbot

A production-ready, highly modular enterprise chatbot platform built with **FastAPI**, **React + Vite**, and local LLM inference via **Ollama**. Features state-of-the-art document indexing, SQL database execution, local filesystem agents, and real-time internet search with structured source citations and inline image galleries.

---

## ⚡ Core Features

*   **🎨 Claude-Style Premium UI**: A highly refined, clean chat timeline column capped at `768px` for focused reading. Implements bubble-less left-aligned AI responses and right-aligned user text blocks.
*   **📱 Persistent Collapsible Sidebar**: Smooth slide transition animation with local preference storage (`localStorage`) and a floating toggle button.
*   **🔍 Clickable Web Search Sources**: Displays webpage reference citations in a dropdown drawer with clickable links to the original sources.
*   **🖼️ Related Image Gallery**: Fetches and renders relevant visual search result cards inline inside chat threads.
*   **🤖 Adaptive Query Router**: Automatically decides when to answer via the model's static knowledge and when it lacks detail, dynamically triggering web search only when necessary.
*   **🔗 Strict Tool Gating**: SQL querying and Filesystem operations are strictly isolated and execution is gated behind explicit user toggle switches.
*   **📄 High-Fidelity RAG Pipeline**: Index, parse, chunk, embed, and query PDF/TXT/DOCX files locally with ChromaDB.

---

## 🛠️ Tech Stack

*   **Frontend**: React (ES6), Lucide Icons, React Markdown (GFM), Vite Dev Server
*   **Backend**: FastAPI, Pydantic, SQLite (Message History)
*   **Vector Database**: ChromaDB (Local persistent storage)
*   **Inference Engine**: Ollama (supports `qwen2.5`, `mistral`, `gemma4` etc.)
*   **Search Provider**: Tavily API (Search Context + Image API)
*   **File Agent**: MCP Filesystem Server integration

---

## 📐 Project Structure

```
.
├── app/
│   ├── api/            # API endpoints (Auth, Chat, SQL, Admin)
│   ├── core/           # Configuration parsing & core settings
│   ├── documents/      # Text extraction and chunking
│   ├── graphs/         # Conversational agent graphs
│   ├── models/         # SQLite tables & database model wrapper
│   ├── schemas/        # Pydantic schemas for payload validation
│   ├── services/       # Business logic (auth, embeddings, LLM, MCP, web search, Chroma)
│   └── main.py         # FastAPI application entry point
├── data/
│   ├── chroma/         # Persistent Vector Embeddings
│   └── uploads/        # Uploaded source documents
├── frontend/
│   ├── public/         # Icons and SVG assets
│   ├── src/
│   │   ├── components/ # React components (ChatPanel, Sidebar, Modals, Pages)
│   │   ├── context/    # Authentication Context
│   │   ├── services/   # HTTP request layer
│   │   ├── App.jsx     # Layout and page shell
│   │   └── index.css   # Main CSS stylesheet
│   └── vite.config.js  # Vite server setup
├── config.json         # Global settings and DB settings
├── run_all.bat         # Single-click run script
└── requirements.txt    # Python backend requirements
```

---

## ⚙️ Configuration

System parameters can be adjusted inside the [config.json](file:///c:/Users/adars/OneDrive/Desktop/LOCAL%20CHATBOT%20FOR%20TCET/config.json) file:

```json
{
    "project_name": "TCET Chatbot",
    "version": "1.0.0",
    "ollama_base_url": "http://localhost:11434",
    "llm_model": "qwen2.5:3b",
    "embedding_model": "nomic-embed-text:latest",
    "chroma_persist_directory": "data/chroma",
    "upload_directory": "data/uploads",
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "top_k": 5,
    "similarity_threshold": 0.4,
    "admin_username": "admin",
    "admin_password": "admin123",
    "default_web_search_provider": "tavily"
}
```

---

## 🚀 Installation & Setup

### Prerequisites

1.  **Python 3.10+**
2.  **Node.js 18+** & **npm**
3.  **Ollama** installed and running

### Setup

1.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd Local-Chatbot-for-College
    ```

2.  **Initialize Environment & Dependencies**:
    Run the setup script:
    ```bash
    setup.bat
    ```

3.  **Pull Required Local Models**:
    Ensure Ollama is running and download the LLM and Embedding models:
    ```bash
    ollama pull qwen2.5:3b
    ollama pull nomic-embed-text:latest
    ```

---

## 🏃 Running the Application

### Option 1: Run All Services (Recommended)
Double-click the `run_all.bat` script in the root directory, or run:
```bash
.\run_all.bat
```

### Option 2: Start Services Separately
1.  **Backend Server**:
    ```bash
    .\run_backend.bat
    ```
    *   Backend API will run at: `http://localhost:8000`
    *   Interactive API Documentation: `http://localhost:8000/docs`

2.  **Frontend Server**:
    ```bash
    .\run_frontend.bat
    ```
    *   Vite Dev Server will host the client at: `http://localhost:5173`

---

## 🔑 Default Credentials

*   **Administrator Account**:
    *   **Username**: `admin`
    *   **Password**: `admin123`
*   *Note: Regular users can be registered directly using the Sign Up page in the UI.*

---

## 🛠️ Troubleshooting

### Ollama Model issues
If the LLM responds slowly or connections fail:
```bash
# Check running models
ollama list

# Ensure server is active
ollama serve
```

### Resetting Embeddings Database
To clear the vector store indices:
1.  Delete the `data/chroma/` directory.
2.  Re-run the backend server and upload files again.

---

## 📄 License
This project is licensed under the MIT License.
