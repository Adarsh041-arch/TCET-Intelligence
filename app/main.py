import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router, _bg_tasks
from app.api.admin import router as admin_router
from app.api.sql_routes import router as sql_router
from app.core.config import config
from app.services.llm import llm_service
from app.services.sql_connector import db_connector
from app.document_generation.api.routes import router as doc_gen_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {config.project_name} v{config.version}...")
    print(f"Warming up LLM model: {config.llm_model}")
    if llm_service.warmup():
        print("Model ready!")
    else:
        print("Warning: Model warmup failed, first request may be slow")

    try:
        with open("config.json", "r") as f:
            raw_config = json.load(f)
        sql_databases = raw_config.get("sql_databases", {})
        default_db = sql_databases.get("default")
        if default_db:
            db_type = default_db.get("type", default_db.get("db_type", ""))
            if db_type == "sqlite":
                db_path = default_db.get("path", "data/institution.db")
                if db_connector.connect_sqlite(db_path):
                    print(f"Auto-connected to SQLite database: {db_path}")
                else:
                    print(f"Warning: Failed to auto-connect to SQLite database: {db_path}")
            elif db_type == "postgresql":
                if db_connector.connect_postgresql(
                    host=default_db.get("host", "localhost"),
                    port=int(default_db.get("port", 5432)),
                    user=default_db.get("user", "postgres"),
                    password=default_db.get("password", ""),
                    database=default_db.get("database", ""),
                ):
                    print(f"Auto-connected to PostgreSQL database: {default_db.get('database', '')}")
                else:
                    print(f"Warning: Failed to auto-connect to PostgreSQL database: {default_db.get('database', '')}")
            elif db_type == "mysql":
                if db_connector.connect_mysql(
                    host=default_db.get("host", "localhost"),
                    port=int(default_db.get("port", 3306)),
                    user=default_db.get("user", "root"),
                    password=default_db.get("password", ""),
                    database=default_db.get("database", ""),
                ):
                    print(f"Auto-connected to MySQL database: {default_db.get('database', '')}")
                else:
                    print(f"Warning: Failed to auto-connect to MySQL database: {default_db.get('database', '')}")
    except Exception as e:
        print(f"Warning: Could not auto-connect to default database: {e}")

    yield

    # ── Drain background memory extraction tasks ──
    pending = [t for t in _bg_tasks if not t.done()]
    if pending:
        print(f"Draining {len(pending)} background memory task(s)...")
        done, _ = await asyncio.wait(pending, timeout=5.0)
        if len(done) < len(pending):
            print(f"Warning: {len(pending) - len(done)} background task(s) did not complete within timeout")
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
