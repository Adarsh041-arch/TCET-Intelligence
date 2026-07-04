import os
import uuid
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas import DocumentUploadResponse, DocumentInfo
from app.services.auth import decode_token
from app.api.routes import get_current_user
from app.documents.processor import document_processor
from app.services.vector_store import vector_store
from app.models.database import db
from app.core.config import config


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


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".docx",
    ".xlsx",
    ".xls",
    ".csv",
    ".json",
    ".html",
}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...), current_user: dict = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided"
        )

    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
        )

    result = document_processor.process_file(
        file_content=content, filename=file.filename, user_id=current_user["user_id"]
    )

    if not result["success"]:
        return DocumentUploadResponse(
            success=False, message=result.get("message", "Upload failed")
        )

    return DocumentUploadResponse(
        success=True,
        doc_id=result["doc_id"],
        filename=result["filename"],
        chunks_created=result.get("chunks_created"),
        message="Document uploaded and indexed successfully",
    )


@router.get("/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    documents = db.get_all_documents()
    count = vector_store.get_document_count()
    return {
        "documents": [
            DocumentInfo(
                doc_id=doc["doc_id"],
                filename=doc["filename"],
                file_type=doc["file_type"],
                uploaded_by=doc["uploaded_by"],
                uploaded_at=str(doc["uploaded_at"]),
            )
            for doc in documents
        ],
        "total_chunks": count,
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_admin_user)):
    success = document_processor.delete_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return {"message": "Document deleted successfully"}


@router.delete("/documents")
async def clear_all_documents(current_user: dict = Depends(get_admin_user)):
    success = vector_store.clear_all()
    if success:
        return {"message": "All documents cleared successfully"}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to clear documents",
    )


# ── TCET Documents (Admin-Controlled Indexing) ─────────────

class IndexRequest(BaseModel):
    file_names: List[str]


TCET_DOCS_DIR = Path(config.tcet_docs_directory)


def _scan_tcet_directory():
    """Scan data/tcet_docs/ and return list of files with db status."""
    TCET_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files_on_disk = {}
    for fpath in TCET_DOCS_DIR.iterdir():
        if fpath.is_file():
            stat = fpath.stat()
            files_on_disk[fpath.name] = {
                "file_name": fpath.name,
                "file_path": str(fpath),
                "file_size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }

    db_records = {r["file_name"]: r for r in db.get_all_tcet_docs()}
    result = []
    for name, info in files_on_disk.items():
        db_rec = db_records.get(name)
        if db_rec:
            info["indexed"] = db_rec["indexed"]
            info["doc_id"] = db_rec["doc_id"]
            info["chunks_count"] = db_rec["chunks_count"]
            info["indexed_at"] = db_rec.get("indexed_at")
        else:
            info["indexed"] = False
            info["doc_id"] = None
            info["chunks_count"] = 0
            info["indexed_at"] = None
        result.append(info)

    return result


@router.get("/tcet-docs")
async def list_tcet_docs(current_user: dict = Depends(get_admin_user)):
    files = _scan_tcet_directory()
    indexed_count = sum(1 for f in files if f["indexed"])
    return {
        "files": files,
        "total": len(files),
        "indexed": indexed_count,
        "unindexed": len(files) - indexed_count,
    }


@router.post("/tcet-docs/index")
async def index_tcet_docs(
    request: IndexRequest, current_user: dict = Depends(get_admin_user)
):
    results = []
    for file_name in request.file_names:
        fpath = TCET_DOCS_DIR / file_name
        if not fpath.is_file():
            results.append({"file_name": file_name, "success": False, "message": "File not found"})
            continue

        try:
            content = fpath.read_bytes()
            if not content:
                results.append({"file_name": file_name, "success": False, "message": "Empty file"})
                continue

            file_hash = vector_store.compute_file_hash(content)
            db.upsert_tcet_doc(file_name, str(fpath), file_hash, len(content))

            result = document_processor.process_file(
                file_content=content, filename=file_name, user_id=current_user["user_id"],
                extra_metadata={"source": "tcet_managed"},
            )

            if result["success"]:
                db.mark_tcet_doc_indexed(str(fpath), result["doc_id"], result.get("chunks_created", 0))
                results.append({
                    "file_name": file_name,
                    "success": True,
                    "doc_id": result["doc_id"],
                    "chunks_created": result.get("chunks_created", 0),
                    "message": "Indexed successfully",
                })
            else:
                results.append({
                    "file_name": file_name,
                    "success": False,
                    "message": result.get("message", "Processing failed"),
                })
        except Exception as e:
            results.append({
                "file_name": file_name,
                "success": False,
                "message": str(e),
            })

    return {"results": results}

