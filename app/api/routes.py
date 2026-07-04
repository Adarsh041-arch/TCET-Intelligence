from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
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
    ApiKeySaveRequest,
    ApiKeyStatusResponse,
    DirectoryAddRequest,
    UserDirectoriesResponse,
    DirectoryInfo,
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
from app.core.config import config
from app.services.sql_connector import db_connector
from app.prompts.web import WEB_SEARCH_SYSTEM_PROMPT
from app.prompts.general import GENERAL_CHAT_PROMPT, RAG_FALLBACK_PROMPT
import uuid
import json
import time
import asyncio


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


@router.post("/auth/api-key")
async def save_api_key(
    request: ApiKeySaveRequest, current_user: dict = Depends(get_current_user)
):
    success = db.set_api_key(current_user["user_id"], request.provider, request.api_key)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save API key")
    return {"success": True}


@router.get("/auth/api-key", response_model=ApiKeyStatusResponse)
async def get_api_key_status(current_user: dict = Depends(get_current_user)):
    key = db.get_api_key(current_user["user_id"], "tavily")
    return ApiKeyStatusResponse(has_key=bool(key), provider="tavily")


@router.delete("/auth/api-key")
async def delete_api_key(current_user: dict = Depends(get_current_user)):
    db.delete_api_key(current_user["user_id"], "tavily")
    return {"success": True}


@router.get("/auth/directories", response_model=UserDirectoriesResponse)
async def get_user_directories(current_user: dict = Depends(get_current_user)):
    dirs = db.get_user_directory_list(current_user["user_id"])
    return UserDirectoriesResponse(directories=[DirectoryInfo(**d) for d in dirs])


@router.post("/auth/directories")
async def add_user_directory(
    request: DirectoryAddRequest, current_user: dict = Depends(get_current_user)
):
    success = db.add_user_directory(current_user["user_id"], request.directory_path)
    if not success:
        raise HTTPException(status_code=400, detail="Directory already exists or is invalid")
    return {"success": True}


@router.delete("/auth/directories")
async def delete_user_directory(
    request: DirectoryAddRequest, current_user: dict = Depends(get_current_user)
):
    success = db.delete_user_directory(current_user["user_id"], request.directory_path)
    if not success:
        raise HTTPException(status_code=404, detail="Directory not found")
    return {"success": True}


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


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    session = db.get_session(session_id)
    if not session or session["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    chat_service.delete_session(session_id)
    return {"success": True}


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
        response_time=result.get("response_time", 0.0),
        retrieved_docs=result.get("retrieved_docs", []),
    )


@router.post("/chat/stream")
async def chat_stream(
    request: MessageRequest, current_user: dict = Depends(get_current_user)
):
    async def generate():
        start_time = time.time()
        query = request.message
        session_id = request.session_id

        existing_messages = db.get_session_messages(session_id)
        history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in existing_messages[-10:]
        ]

        query_lower = query.lower()

        retrieved_docs = []
        web_images = []
        sql_result = None
        query_type = "general"
        source = "general"

        general_patterns = [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "how are you",
            "what's up",
            "bye",
            "goodbye",
            "thanks",
            "thank you",
            "who are you",
            "what are you",
            "tell me about yourself",
            "joke",
            "funny",
            "help",
            "what can you do",
            "capabilities",
            "weather",
            "news",
            "date",
            "time",
        ]
        sql_patterns = [
            "sql",
            "query",
            "database",
            "table",
            "select",
            "insert",
            "update",
            "delete",
            "count",
            "sum",
        ]
        rag_keywords = [
            "document",
            "file",
            "pdf",
            "excel",
            "sheet",
            "attendance",
            "marks",
            "student",
            "results",
            "report",
            "data",
            "record",
            "from the",
            "based on",
            "according to",
            "mentioned in",
            "summarize",
            "extract",
            "find",
            "search",
            "list all",
            "fees",
            "fee",
            "hostel",
            "hostel fees",
            "tcet fees",
            "tcet hostel",
            "fee structure",
        ]
        fs_patterns = [
            "file", "folder", "directory", "filesystem", "create", "write", "read", 
            "delete", "list contents", "contents", "make directory", "text file",
            "open", ".txt", ".csv", ".json"
        ]
        # Mode override from frontend toggles — normalise to list
        raw_mode = getattr(request, "mode", None)
        if isinstance(raw_mode, list):
            active_modes = raw_mode
        elif isinstance(raw_mode, str) and raw_mode:
            active_modes = [raw_mode]
        else:
            active_modes = []

        # ── Multi-mode orchestrator ───────────────────────────
        if len(active_modes) > 1:
            query_type = "multi"
        elif active_modes and active_modes[0] == "rag" or getattr(request, "attached_files", None):
            query_type = "rag"
        elif active_modes and active_modes[0] == "sql":
            query_type = "sql"
        elif active_modes and active_modes[0] == "filesystem":
            query_type = "filesystem"
        elif active_modes and active_modes[0] == "documentation":
            query_type = "documentation"
        elif active_modes and active_modes[0] == "web":
            query_type = "web"
        else:
            # "Else" mode (mode is "general" or None/nothing turned on)
            # Answer from parametric knowledge, but automatically use web search if it lacks detail
            has_web_key = False
            try:
                api_key = db.get_api_key(current_user["user_id"], "tavily")
                if api_key:
                    has_web_key = True
            except Exception:
                pass

            if has_web_key and llm_service.decide_web_search(query):
                query_type = "web"
            else:
                query_type = "general"

        single_mode = active_modes[0] if len(active_modes) == 1 else None

        if query_type == "rag" or getattr(request, "attached_files", None):
            if not retrieved_docs:
                try:
                    filter_dict = None
                    threshold = config.similarity_threshold

                    if getattr(request, "attached_files", None):
                        filter_dict = {"filename": {"$in": request.attached_files}}
                        threshold = 0.1
                    elif single_mode == "rag":
                        tcet_filenames = vector_store.get_all_filenames(where={"source": "tcet_managed"})
                        relevant = llm_service.select_relevant_tcet_docs(query, tcet_filenames)
                        if relevant and len(relevant) < len(tcet_filenames):
                            filter_dict = {"source": "tcet_managed", "filename": {"$in": relevant}}
                        else:
                            filter_dict = {"source": "tcet_managed"}
                    
                    retrieved_docs = vector_store.retrieve_similar(
                        query, top_k=config.top_k, threshold=threshold,
                        filter_dict=filter_dict
                    )
                except Exception as e:
                    print(f"Retrieval error: {e}")

        full_response = ""
        filesystem_handled = False

        if query_type == "multi":
            source = "multi"
            filesystem_handled = True
            try:
                from app.services.agent_orchestrator import stream_multi_agent
                deadline = time.monotonic() + 180.0
                async for event in stream_multi_agent(
                    query, history, active_modes, current_user["user_id"],
                ):
                    if time.monotonic() > deadline:
                        raise asyncio.TimeoutError()
                    if event["type"] == "thinking":
                        yield f"data: {json.dumps({'thinking': event['text'], 'done': False})}\n\n"
                    elif event["type"] == "milestone":
                        yield f"data: {json.dumps({'milestone': event['text'], 'done': False})}\n\n"
                    elif event["type"] == "token":
                        full_response += event["text"]
                        yield f"data: {json.dumps({'token': event['text'], 'done': False})}\n\n"
                    elif event["type"] == "final":
                        pass  # we handle final below
            except asyncio.TimeoutError:
                chunk = "Multi-agent operation timed out after 3 minutes."
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
            except Exception as e:
                chunk = f"Multi-agent error: {e}"
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
        elif query_type == "filesystem":
            source = "filesystem"
            filesystem_handled = True
            try:
                from app.services.mcp_agent import stream_mcp_agent
                deadline = time.monotonic() + 180.0
                async for event in stream_mcp_agent(query, history, current_user["user_id"]):
                    if time.monotonic() > deadline:
                        raise asyncio.TimeoutError()
                    if event["type"] == "thinking":
                        yield f"data: {json.dumps({'thinking': event['text'], 'done': False})}\n\n"
                    elif event["type"] == "final":
                        words = event["text"].split(" ")
                        for i, w in enumerate(words):
                            chunk = w + (" " if i < len(words) - 1 else "")
                            full_response += chunk
                            yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
            except asyncio.TimeoutError:
                chunk = "Filesystem operation timed out after 3 minutes."
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
            except Exception as e:
                chunk = f"Filesystem error: {e}"
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
        elif query_type == "documentation":
            source = "documentation"
            filesystem_handled = True
            try:
                from app.services.doc_agent import stream_documentation_agent
                deadline = time.monotonic() + 180.0
                async for event in stream_documentation_agent(
                    query, history,
                    attached_files=getattr(request, "attached_files", None),
                    user_id=current_user["user_id"],
                ):
                    if time.monotonic() > deadline:
                        raise asyncio.TimeoutError()
                    if event["type"] == "thinking":
                        yield f"data: {json.dumps({'thinking': event['text'], 'done': False})}\n\n"
                    elif event["type"] == "token":
                        full_response += event["text"]
                        yield f"data: {json.dumps({'token': event['text'], 'done': False})}\n\n"
                    elif event["type"] == "document":
                        doc_info = event
                        doc_info["done"] = False
                        yield f"data: {json.dumps(doc_info)}\n\n"
            except asyncio.TimeoutError:
                chunk = "Document generation timed out after 3 minutes."
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
            except Exception as e:
                chunk = f"Document generation error: {e}"
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
        elif query_type == "web":
            source = "web"
            try:
                api_key = db.get_api_key(current_user["user_id"], "tavily")
                if not api_key:
                    def stream_no_key():
                        yield "Web Search is not configured. Click the Web Search toggle and enter your Tavily API key to enable this feature."
                    gen = stream_no_key()
                else:
                    from app.services.web_search import web_search_service
                    search_res = web_search_service.search(query, api_key)
                    
                    # Map search results to retrieved_docs format for references display
                    for s in search_res.get("sources", []):
                        retrieved_docs.append({
                            "content": s.get("content", ""),
                            "filename": s.get("title", "Untitled"),
                            "similarity": 1.0,
                            "url": s.get("url", "")
                        })
                    
                    web_images = search_res.get("images", [])
                    context = f"Web search results for '{query}':\n\n{search_res.get('context', '')}"
                    web_sys_prompt = WEB_SEARCH_SYSTEM_PROMPT
                    gen = llm_service.generate_stream(query, context, history, system_prompt=web_sys_prompt)
            except Exception as e:
                def stream_err():
                    yield f"Web search error: {e}"
                gen = stream_err()
        elif query_type == "sql" and db_connector.current_connection:
            source = "sql"
            try:
                tables = db_connector.get_tables()
                if tables:
                    schema_parts = []
                    for table in tables:
                        schema = db_connector.get_table_schema(table)
                        if schema.get("columns"):
                            cols = ", ".join([f"{c['name']} ({c['type']})" for c in schema["columns"]])
                            schema_parts.append(f"{table}: {cols}")
                    table_info = "\n".join(schema_parts)
                    
                    sql_query = llm_service.generate_sql_query(query, table_info)
                    if sql_query and not sql_query.startswith("Error"):
                        sql_result = db_connector.execute_query(sql_query)
                        sql_resp = llm_service.generate_sql_response(query, sql_result)
                    else:
                        sql_resp = f"I failed to generate a valid SQL query for request. SQL query generated: {sql_query}"
                else:
                    sql_resp = "No tables found in the database."
            except Exception as e:
                sql_resp = f"Error executing database query: {e}"
            
            def stream_sql(text):
                words = text.split(" ")
                for i, w in enumerate(words):
                    yield w + (" " if i < len(words) - 1 else "")
            gen = stream_sql(sql_resp)
        elif (query_type == "rag" or getattr(request, "attached_files", None)) and retrieved_docs:
            source = "rag"
            filtered_docs = [d for d in retrieved_docs if d.get("similarity", 1) >= config.similarity_threshold]
            gen = llm_service.generate_rag_response_stream(
                query, filtered_docs, history
            )
        else:
            source = "general"
            if raw_mode == "rag" or (isinstance(raw_mode, list) and "rag" in raw_mode):
                sys_prompt = RAG_FALLBACK_PROMPT
            else:
                sys_prompt = GENERAL_CHAT_PROMPT
            gen = llm_service.generate_stream(query, None, history, system_prompt=sys_prompt)

        completed_normally = False
        try:
            if not filesystem_handled:
                for chunk in gen:
                    full_response += chunk
                    yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
            
            # If we completed normally and have web search images, append them to the response
            if query_type == "web" and web_images:
                image_markdown = "\n\n### Related Images:\n"
                for img_url in web_images[:3]:
                    image_markdown += f"![Search Image]({img_url})\n"
                full_response += image_markdown
                yield f"data: {json.dumps({'token': image_markdown, 'done': False})}\n\n"

            completed_normally = True
        except GeneratorExit:
            print("Stream generator caught GeneratorExit (client disconnected).")
            if full_response.strip():
                try:
                    db.add_message(session_id, "user", query)
                    db.add_message(session_id, "assistant", full_response + " ⏹️ [Generation Interrupted]")
                except Exception as e:
                    print(f"Memory update error on disconnect: {e}")
            raise

        if completed_normally:
            response_time = time.time() - start_time

            retrieved_for_response = (
                [
                    {
                        "content": doc["content"][:200] + "..."
                        if len(doc["content"]) > 200
                        else doc["content"],
                        "filename": doc["metadata"].get("filename", "Unknown") if doc.get("metadata") else doc.get("filename", "Source"),
                        "similarity": round(doc.get("similarity", 1.0), 3),
                        "url": doc.get("url") if doc.get("url") else None,
                    }
                    for doc in retrieved_docs
                ]
                if retrieved_docs
                else []
            )

            try:
                db.add_message(session_id, "user", query)
                db.add_message(session_id, "assistant", full_response)
            except Exception as e:
                print(f"Memory update error: {e}")

            yield f"data: {json.dumps({'done': True, 'source': source, 'response_time': round(response_time, 2), 'retrieved_docs': retrieved_for_response})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
