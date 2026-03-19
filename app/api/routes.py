from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    SessionCreate,
    SessionResponse,
    MessageRequest,
    MessageResponse,
    HealthResponse,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    register_user,
    decode_token,
)
from app.services.llm import llm_service
from app.services.vector_store import vector_store
from app.services.chat import chat_service
from app.graphs.chat_graph import chat_agent
from app.models.database import db
import uuid


router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return {
        "user_id": payload["user_id"],
        "username": payload["username"],
        "role": payload["role"],
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        ollama_connected=llm_service.check_connection(),
        documents_count=vector_store.get_document_count(),
        version="1.0.0",
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}
    )

    return TokenResponse(
        access_token=access_token,
        user_id=user["user_id"],
        username=user["username"],
        role=user["role"],
    )


@router.post("/auth/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    if request.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'user' or 'admin'",
        )

    user_id = str(uuid.uuid4())
    success = register_user(user_id, request.username, request.password, request.role)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    access_token = create_access_token(
        {"user_id": user_id, "username": request.username, "role": request.role}
    )

    return TokenResponse(
        access_token=access_token,
        user_id=user_id,
        username=request.username,
        role=request.role,
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreate, current_user: dict = Depends(get_current_user)
):
    session = chat_service.create_session(
        user_id=current_user["user_id"], session_name=request.session_name
    )

    full_session = db.get_session(session["session_id"])

    return SessionResponse(
        session_id=session["session_id"],
        session_name=request.session_name,
        created_at=str(full_session["created_at"]) if full_session else "",
        updated_at=str(full_session["updated_at"]) if full_session else "",
    )


@router.get("/sessions")
async def get_sessions(current_user: dict = Depends(get_current_user)):
    sessions = chat_service.get_user_sessions(current_user["user_id"])
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    session = db.get_session(session_id)
    if not session or session["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    messages = chat_service.get_session_history(session_id)
    return {"session_id": session_id, "messages": messages}


@router.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest, current_user: dict = Depends(get_current_user)):
    result = chat_agent.process_query(
        user_id=current_user["user_id"],
        session_id=request.session_id,
        query=request.message,
    )

    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["error"]
        )

    return MessageResponse(
        response=result["response"],
        source=result["source"],
        retrieved_docs=result.get("retrieved_docs", []),
    )
