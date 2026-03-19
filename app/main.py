from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.api.admin import router as admin_router
from app.core.config import config


app = FastAPI(
    title=config.project_name,
    version=config.version,
    description="Organizational chatbot with RAG capabilities",
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


@app.get("/")
async def root():
    return {"name": config.project_name, "version": config.version, "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
