# TCET Chatbot - Organizational RAG System

A production-ready multi-user chatbot platform with RAG capabilities, built using LangChain, LangGraph, and local LLM inference via Ollama.

## Features

- **Role-Based Access**: Admin and User roles with different capabilities
- **RAG Pipeline**: Document upload, chunking, embedding, and retrieval
- **LangGraph Workflow**: Stateful multi-user conversations with conditional branching
- **Persistent Storage**: SQLite for chat history, ChromaDB for vector embeddings
- **Local LLM**: Runs entirely on Ollama (qwen2.5:3b)
- **Multi-Session Support**: Users can create, view, and resume chat sessions

## Tech Stack

- **LLM**: Ollama (qwen2.5:3b)
- **Embeddings**: SentenceTransformer (BAAI/bge-m3)
- **Vector DB**: Chroma (persistent)
- **Framework**: LangChain + LangGraph
- **Backend**: FastAPI
- **Frontend**: Streamlit
- **Database**: SQLite

## Project Structure

```
.
├── app/
│   ├── api/           # API routes (auth, chat, admin)
│   ├── core/          # Configuration
│   ├── documents/     # Document processing
│   ├── graphs/        # LangGraph workflow
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── services/     # Business logic (auth, embeddings, llm, vector store)
│   └── main.py        # FastAPI application
├── data/
│   ├── chroma/       # ChromaDB persistent storage
│   └── uploads/       # Uploaded documents
├── config.json        # Configuration file
├── streamlit_app.py   # Streamlit frontend
└── *.bat             # Run scripts
```

## Installation

### Prerequisites

1. **Python 3.10+**
2. **Ollama** installed and running
3. **Ollama model**: qwen2.5:3b

### Setup

1. Clone the repository
2. Run the setup script:
```bash
setup.bat
```

3. Pull the Ollama model:
```bash
ollama pull qwen2.5:3b
```

### Running the Application

**Option 1: Run All Services**
```bash
run_all.bat
```

**Option 2: Run Individually**
```bash
# Terminal 1 - Backend
run_backend.bat

# Terminal 2 - Frontend
run_frontend.bat
```

## Access Points

- **Frontend (Streamlit)**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Default Credentials

- **Admin**: `admin` / `admin123`
- **New users** can be registered via the UI

## Usage

### Admin Features

1. **Login** with admin credentials
2. **Upload Documents**: Upload PDF, TXT, or DOCX files
3. **Manage Documents**: View and delete indexed documents
4. **Chat**: Use RAG-enabled chat with uploaded documents

### User Features

1. **Login/Register** as a regular user
2. **Create Sessions**: Start new chat sessions
3. **Chat**: Ask questions (uses RAG if documents available, otherwise general LLM)
4. **View History**: Resume previous conversations

## RAG Pipeline

1. **Document Upload**: Admin uploads PDF/TXT/DOCX
2. **Text Extraction**: Extract text from documents
3. **Chunking**: Split text using RecursiveCharacterTextSplitter
4. **Embedding**: Generate embeddings using BAAI/bge-m3
5. **Storage**: Store in ChromaDB with metadata
6. **Retrieval**: Top-k similarity search with threshold filtering
7. **Response**: Generate response using context + LLM

## LangGraph Workflow

```
Input Node → Retrieval Node → Decision Node
                                  ↓
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
              RAG Response              General Response
                    ↓                           ↓
              Memory Update ←────────── Memory Update
                    ↓
                   END
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register

### Chat
- `POST /api/sessions` - Create session
- `GET /api/sessions` - List sessions
- `GET /api/sessions/{id}/history` - Get session history
- `POST /api/chat` - Send message

### Admin
- `POST /api/admin/documents/upload` - Upload document
- `GET /api/admin/documents` - List documents
- `DELETE /api/admin/documents/{id}` - Delete document
- `DELETE /api/admin/documents` - Clear all documents

## Configuration

Edit `config.json` to customize:

```json
{
    "ollama_base_url": "http://localhost:11434",
    "llm_model": "qwen2.5:3b",
    "embedding_model": "BAAI/bge-m3",
    "chroma_persist_directory": "data/chroma",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 3,
    "similarity_threshold": 0.5,
    "admin_username": "admin",
    "admin_password": "admin123"
}
```

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
ollama list

# Start Ollama
ollama serve

# Pull model if missing
ollama pull qwen2.5:3b
```

### ChromaDB Issues
- Delete `data/chroma/` directory to reset vector store
- Ensure sufficient disk space for embeddings

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

## Performance Tips

1. **GPU Acceleration**: Ollama uses GPU automatically if available
2. **Batch Processing**: Upload multiple documents at once
3. **Session Management**: Use multiple sessions to organize conversations
4. **Chunk Size**: Adjust in config.json based on document type

## License

MIT License
