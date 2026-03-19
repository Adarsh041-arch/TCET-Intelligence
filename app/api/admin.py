from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas import DocumentUploadResponse, DocumentInfo
from app.services.auth import decode_token
from app.documents.processor import document_processor
from app.services.vector_store import vector_store
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
    file: UploadFile = File(...), current_user: dict = Depends(get_admin_user)
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
async def list_documents(current_user: dict = Depends(get_admin_user)):
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
