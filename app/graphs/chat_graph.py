from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.services.vector_store import vector_store
from app.services.llm import llm_service
from app.models.database import db
from app.core.config import config


class ChatState(TypedDict):
    user_id: str
    session_id: str
    current_query: str
    chat_history: List[Dict[str, str]]
    retrieved_docs: List[Dict[str, Any]]
    response_source: str
    final_response: str
    error: Optional[str]


class ChatAgent:
    def __init__(self):
        self.workflow = self._build_workflow()
        self.max_history = config.top_k * 5

    def _input_node(self, state: ChatState) -> ChatState:
        if not state.get("current_query"):
            state["error"] = "No query provided"
        return state

    def _retrieval_node(self, state: ChatState) -> ChatState:
        try:
            query = state["current_query"]
            retrieved = vector_store.retrieve_similar(
                query, top_k=config.top_k, threshold=config.similarity_threshold
            )
            state["retrieved_docs"] = retrieved
        except Exception as e:
            state["error"] = f"Retrieval error: {str(e)}"
            state["retrieved_docs"] = []
        return state

    def _decision_node(self, state: ChatState) -> str:
        if state.get("error"):
            return "error"
        if state["retrieved_docs"]:
            return "rag"
        return "general"

    def _rag_response_node(self, state: ChatState) -> ChatState:
        try:
            query = state["current_query"]
            chat_history = state.get("chat_history", [])[-self.max_history :]

            context = "\n\n".join(
                [
                    f"Document {i + 1} ({doc['metadata'].get('filename', 'Unknown')}):\n{doc['content']}"
                    for i, doc in enumerate(state["retrieved_docs"])
                ]
            )

            response = llm_service.generate_rag_response(
                query=query,
                retrieved_docs=state["retrieved_docs"],
                chat_history=chat_history,
            )

            state["final_response"] = response
            state["response_source"] = "rag"
        except Exception as e:
            state["error"] = f"RAG response error: {str(e)}"
        return state

    def _general_response_node(self, state: ChatState) -> ChatState:
        try:
            query = state["current_query"]
            chat_history = state.get("chat_history", [])[-self.max_history :]

            response = llm_service.generate_response(
                prompt=query, context=None, chat_history=chat_history
            )

            state["final_response"] = response
            state["response_source"] = "general"
        except Exception as e:
            state["error"] = f"General response error: {str(e)}"
        return state

    def _memory_update_node(self, state: ChatState) -> ChatState:
        try:
            if state.get("session_id") and state.get("final_response"):
                db.add_message(state["session_id"], "user", state["current_query"])
                db.add_message(
                    state["session_id"], "assistant", state["final_response"]
                )

                updated_history = state.get("chat_history", [])
                updated_history.append(
                    {"role": "user", "content": state["current_query"]}
                )
                updated_history.append(
                    {"role": "assistant", "content": state["final_response"]}
                )
                state["chat_history"] = updated_history[-self.max_history :]
        except Exception as e:
            state["error"] = f"Memory update error: {str(e)}"
        return state

    def _error_handler_node(self, state: ChatState) -> ChatState:
        state["final_response"] = (
            f"I apologize, but I encountered an error: {state.get('error', 'Unknown error')}"
        )
        state["response_source"] = "error"
        return state

    def _build_workflow(self):
        workflow = StateGraph(ChatState)

        workflow.add_node("input", self._input_node)
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("rag_response", self._rag_response_node)
        workflow.add_node("general_response", self._general_response_node)
        workflow.add_node("memory_update", self._memory_update_node)
        workflow.add_node("error_handler", self._error_handler_node)

        workflow.set_entry_point("input")

        workflow.add_edge("input", "retrieval")

        workflow.add_conditional_edges(
            "retrieval",
            self._decision_node,
            {
                "rag": "rag_response",
                "general": "general_response",
                "error": "error_handler",
            },
        )

        workflow.add_edge("rag_response", "memory_update")
        workflow.add_edge("general_response", "memory_update")
        workflow.add_edge("error_handler", END)
        workflow.add_edge("memory_update", END)

        return workflow.compile()

    def process_query(
        self,
        user_id: str,
        session_id: str,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        existing_messages = db.get_session_messages(session_id)
        history = chat_history or [
            {"role": msg["role"], "content": msg["content"]}
            for msg in existing_messages[-self.max_history :]
        ]

        initial_state: ChatState = {
            "user_id": user_id,
            "session_id": session_id,
            "current_query": query,
            "chat_history": history,
            "retrieved_docs": [],
            "response_source": "",
            "final_response": "",
            "error": None,
        }

        result = self.workflow.invoke(initial_state)

        return {
            "response": result["final_response"],
            "source": result["response_source"],
            "retrieved_docs": [
                {
                    "content": doc["content"][:200] + "..."
                    if len(doc["content"]) > 200
                    else doc["content"],
                    "filename": doc["metadata"].get("filename", "Unknown"),
                    "similarity": round(doc["similarity"], 3),
                }
                for doc in result.get("retrieved_docs", [])
            ],
            "error": result.get("error"),
        }


chat_agent = ChatAgent()
