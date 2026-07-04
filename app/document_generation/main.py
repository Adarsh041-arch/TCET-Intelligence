"""
Standalone document generation service.
Run with: uvicorn app.document_generation.main:app --host 0.0.0.0 --port 8001
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.document_generation.api.routes import router

app = FastAPI(
    title="Document Generation Service",
    version="1.0.0",
    description="AI Chatbot Document Generation Service - converts Markdown/HTML to DOCX, PDF, PPTX, XLSX",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "Document Generation Service",
        "version": "1.0.0",
        "status": "running",
        "formats": ["docx", "pdf", "pptx", "xlsx"],
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.document_generation.main:app", host="0.0.0.0", port=8001, reload=True)
