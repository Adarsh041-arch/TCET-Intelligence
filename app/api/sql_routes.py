from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.services.auth import decode_token
from app.services.sql_connector import db_connector
from app.models.database import db


router = APIRouter()
security = HTTPBearer()


async def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    if payload["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return {
        "user_id": payload["user_id"],
        "username": payload["username"],
        "role": payload["role"],
    }


class SQLConnectRequest(BaseModel):
    db_type: str
    host: Optional[str] = "localhost"
    port: Optional[int] = 3306
    user: Optional[str] = "root"
    password: Optional[str] = ""
    database: Optional[str] = ""
    path: Optional[str] = ""


@router.get("/sql/status")
async def sql_status(current_user: dict = Depends(get_admin_user)):
    return {
        "connected": db_connector.current_connection is not None,
        "db_type": db_connector.db_type,
    }


@router.post("/sql/connect")
async def sql_connect(
    request: SQLConnectRequest, current_user: dict = Depends(get_admin_user)
):
    if request.db_type == "sqlite":
        if not request.path:
            return {"success": False, "error": "Path is required for SQLite"}
        success = db_connector.connect_sqlite(request.path)
    elif request.db_type == "mysql":
        success = db_connector.connect_mysql(
            host=request.host or "localhost",
            port=request.port or 3306,
            user=request.user or "root",
            password=request.password or "",
            database=request.database or "",
        )
    elif request.db_type == "postgresql":
        success = db_connector.connect_postgresql(
            host=request.host or "localhost",
            port=request.port or 5432,
            user=request.user or "postgres",
            password=request.password or "",
            database=request.database or "",
        )
    else:
        return {"success": False, "error": "Unsupported database type"}

    if success:
        return {"success": True, "message": f"Connected to {request.db_type}"}
    return {"success": False, "error": "Failed to connect"}


@router.post("/sql/disconnect")
async def sql_disconnect(current_user: dict = Depends(get_admin_user)):
    db_connector.disconnect()
    return {"success": True, "message": "Disconnected"}


@router.get("/sql/tables")
async def sql_tables(current_user: dict = Depends(get_admin_user)):
    if not db_connector.current_connection:
        return {"success": False, "tables": []}
    import traceback
    try:
        tables = db_connector.get_tables()
        return {"success": True, "tables": tables}
    except Exception as e:
        return {"success": False, "tables": [], "error": str(e), "traceback": traceback.format_exc()}


@router.get("/sql/schema/{table_name}")
async def sql_schema(table_name: str, current_user: dict = Depends(get_admin_user)):
    if not db_connector.current_connection:
        return {"success": False, "error": "Not connected"}
    schema = db_connector.get_table_schema(table_name)
    return {"success": True, "schema": schema}


@router.post("/sql/query")
async def sql_query(query: str, current_user: dict = Depends(get_admin_user)):
    if not db_connector.current_connection:
        return {"success": False, "error": "Not connected to any database"}
    result = db_connector.execute_query(query)
    return result


# ── Exposed Database Management (Admin) ─────────────────────

class ExposeDBRequest(BaseModel):
    db_type: str
    host: Optional[str] = "localhost"
    port: Optional[int] = 5432
    user: Optional[str] = "postgres"
    password: Optional[str] = ""
    database_name: Optional[str] = ""
    path: Optional[str] = ""
    label: str


@router.post("/sql/expose")
async def expose_database(
    request: ExposeDBRequest,
    current_user: dict = Depends(get_admin_user),
):
    data = request.model_dump()
    data["db_user"] = data.pop("user", "")
    db_id = db.expose_database(data, current_user["user_id"])
    if db_id:
        return {"success": True, "id": db_id, "message": f"Database '{request.label}' exposed to users"}
    return {"success": False, "error": "Failed to expose database"}


@router.get("/sql/exposed")
async def list_exposed_databases(current_user: dict = Depends(get_admin_user)):
    databases = db.get_exposed_databases()
    return {"success": True, "databases": databases}


@router.delete("/sql/exposed/{db_id}")
async def delete_exposed_database(
    db_id: int,
    current_user: dict = Depends(get_admin_user),
):
    if db.delete_exposed_database(db_id):
        return {"success": True, "message": "Exposed database removed"}
    return {"success": False, "error": "Not found"}



