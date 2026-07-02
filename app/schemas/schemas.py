from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    role: str = Field(default="user")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class SessionCreate(BaseModel):
    session_name: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    session_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)
    attached_files: Optional[List[str]] = []
    mode: Optional[str] = None


class MessageResponse(BaseModel):
    response: str
    source: str
    response_time: Optional[float] = 0.0
    retrieved_docs: List[dict] = []


class DocumentUploadResponse(BaseModel):
    success: bool
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    chunks_created: Optional[int] = None
    message: str


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    uploaded_by: str
    uploaded_at: str


class ChatHistoryItem(BaseModel):
    message_id: int
    role: str
    content: str
    created_at: str


class ApiKeySaveRequest(BaseModel):
    api_key: str = Field(..., min_length=1)
    provider: str = Field(default="tavily")

class ApiKeyStatusResponse(BaseModel):
    has_key: bool
    provider: str = "tavily"

class DirectoryAddRequest(BaseModel):
    directory_path: str = Field(..., min_length=1)

class DirectoryInfo(BaseModel):
    id: int
    directory_path: str
    created_at: Optional[str] = None

class UserDirectoriesResponse(BaseModel):
    directories: List[DirectoryInfo] = []

class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    documents_count: int
    version: str
