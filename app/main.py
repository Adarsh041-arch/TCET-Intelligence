from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.api.admin import router as admin_router
from app.api.sql_routes import router as sql_router
from app.core.config import config
from app.services.llm import llm_service
from app.document_generation.api.routes import router as doc_gen_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {config.project_name} v{config.version}...")
    print(f"Warming up LLM model: {config.llm_model}")
    if llm_service.warmup():
        print("Model ready!")
    else:
        print("Warning: Model warmup failed, first request may be slow")
    yield
    print("Shutting down...")


app = FastAPI(
    title=config.project_name,
    version=config.version,
    description="Organizational chatbot with RAG capabilities",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(sql_router, prefix="/api/admin")
app.include_router(doc_gen_router)


@app.get("/")
async def root():
    return {"name": config.project_name, "version": config.version, "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
