import uuid
from typing import List, Dict, Any, Optional
from app.models.database import db
from app.services.vector_store import vector_store
from app.services.llm import llm_service


class ChatService:
    def __init__(self):
        self.max_history = 10  # was 50

    def create_session(self, user_id: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        db.create_session(session_id, user_id, session_name)
        return {"session_id": session_id, "message": "Session created successfully"}

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        return db.get_user_sessions(user_id)

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        return db.get_session_messages(session_id)

    def process_message(self, session_id: str, user_id: str, message: str) -> Dict[str, Any]:
        session = db.get_session(session_id)
        if not session or session["user_id"] != user_id:
            return {"error": "Session not found or access denied"}

        chat_history = self.get_session_history(session_id)
        chat_history_formatted = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chat_history[-self.max_history:]
        ]

        retrieved_docs = vector_store.retrieve_similar(message)

        if retrieved_docs:
            response = llm_service.generate_rag_response(
                query=message,
                retrieved_docs=retrieved_docs[:3],
                chat_history=chat_history_formatted,
            )
            source = "rag"
        else:
            response = llm_service.generate_response(
                prompt=message, context=None, chat_history=chat_history_formatted
            )
            source = "general"
            retrieved_docs = []

        db.add_message(session_id, "user", message)
        db.add_message(session_id, "assistant", response)

        return {
            "response": response,
            "source": source,
            "retrieved_docs": [
                {
                    "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                    "filename": doc["metadata"].get("filename", "Unknown"),
                    "similarity": round(doc["similarity"], 3),
                }
                for doc in retrieved_docs
            ],
        }

    def process_message_stream(self, session_id: str, user_id: str, message: str):
        session = db.get_session(session_id)
        if not session or session["user_id"] != user_id:
            yield {"error": "Session not found or access denied"}
            return

        chat_history = self.get_session_history(session_id)
        chat_history_formatted = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chat_history[-self.max_history:]
        ]

        retrieved_docs = vector_store.retrieve_similar(message)
        full_response = ""

        if retrieved_docs:
            source = "rag"
            for chunk in llm_service.generate_rag_response_stream(
                query=message,
                retrieved_docs=retrieved_docs[:3],
                chat_history=chat_history_formatted,
            ):
                full_response += chunk
                yield {"chunk": chunk, "source": source}
        else:
            source = "general"
            for chunk in llm_service.generate_stream(
                prompt=message, context=None, chat_history=chat_history_formatted
            ):
                full_response += chunk
                yield {"chunk": chunk, "source": source}

        db.add_message(session_id, "user", message)
        db.add_message(session_id, "assistant", full_response)


chat_service = ChatService()