from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.services.vector_store import vector_store
from app.services.llm import llm_service
from app.services.sql_connector import db_connector
from app.models.database import db
from app.core.config import config
from app.services.mcp_agent import run_mcp_filesystem_agent


class ChatState(TypedDict):
    user_id: str
    session_id: str
    current_query: str
    chat_history: List[Dict[str, str]]
    retrieved_docs: List[Dict[str, Any]]
    sql_result: Optional[Dict[str, Any]]
    response_source: str
    final_response: str
    error: Optional[str]
    response_time: Optional[float]
    query_type: Optional[str]


class ChatAgent:
    def __init__(self):
        self.workflow = self._build_workflow()
        self.max_history = 5

    def _input_node(self, state: ChatState) -> ChatState:
        if not state.get("current_query"):
            state["error"] = "No query provided"
        return state

    def _classify_query_node(self, state: ChatState) -> ChatState:
        query = state["current_query"].lower()

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
            "delete from",
            "count",
            "sum",
            "average",
            "max",
            "min",
            "total",
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
            "in the document",
            "in this file",
            "what does it say",
            "summarize",
            "extract",
            "find",
            "search",
            "list all",
            "syllabus",
            "exam",
            "faculty",
            "subject",
            "department",
            "fees",
            "admission",
            "campus",
            "placement",
            "event",
            "notice",
            "timetable",
            "schedule",
        ]

        fs_patterns = [
            "file",
            "folder",
            "directory",
            "filesystem",
            "create",
            "write",
            "read",
            "delete",
            "list contents",
            "contents",
            "make directory",
            "text file",
            "open",
            ".txt",
            ".csv",
            ".json",
        ]

        general_count = sum(1 for p in general_patterns if p in query)
        sql_count = sum(1 for p in sql_patterns if p in query)
        rag_count = sum(1 for p in rag_keywords if p in query)
        fs_count = sum(1 for p in fs_patterns if p in query)

        if fs_count > 0 and (fs_count >= rag_count and fs_count >= sql_count):
            state["query_type"] = "filesystem"
        elif sql_count > 0:
            state["query_type"] = "sql"
        else:
            state["query_type"] = "rag"

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

    def _sql_node(self, state: ChatState) -> ChatState:
        if not db_connector.current_connection:
            state["sql_result"] = None
            return state

        try:
            tables = db_connector.get_tables()
            if not tables:
                state["sql_result"] = None
                return state

            schema_parts = []
            for table in tables:
                schema = db_connector.get_table_schema(table)
                if schema.get("columns"):
                    cols = ", ".join(
                        [f"{c['name']} ({c['type']})" for c in schema["columns"]]
                    )
                    schema_parts.append(f"{table}: {cols}")

            table_info = "\n".join(schema_parts)
            sql_query = llm_service.generate_sql_query(
                state["current_query"], table_info
            )

            if sql_query and not sql_query.startswith("Error"):
                result = db_connector.execute_query(sql_query)
                state["sql_result"] = result
            else:
                state["sql_result"] = None
        except Exception as e:
            print(f"SQL error: {e}")
            state["sql_result"] = None
        return state

    def _decision_node(self, state: ChatState) -> str:
        if state.get("error"):
            return "error"
        if state.get("query_type") == "sql" and state.get("sql_result"):
            return "sql"
        if state.get("query_type") == "general":
            return "general"
        if state["retrieved_docs"]:
            return "rag"
        return "general"

    def _sql_response_node(self, state: ChatState) -> ChatState:
        try:
            query = state["current_query"]
            sql_result = state.get("sql_result") or {}
            response = llm_service.generate_sql_response(query, sql_result)
            state["final_response"] = response
            state["response_source"] = "sql"
        except Exception as e:
            state["error"] = f"SQL response error: {str(e)}"
        return state

    def _rag_response_node(self, state: ChatState) -> ChatState:
        try:
            query = state["current_query"]
            chat_history = state.get("chat_history", [])[-self.max_history :]
            relevant_docs = [d for d in state["retrieved_docs"] if d.get("similarity", 0) >= config.similarity_threshold]
            response = llm_service.generate_rag_response(
                query=query,
                retrieved_docs=relevant_docs[:3],
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

    def _filesystem_node(self, state: ChatState) -> ChatState:
        try:
            query = state["current_query"]
            chat_history = state.get("chat_history", [])[-self.max_history :]

            response = run_mcp_filesystem_agent(query, chat_history)

            state["final_response"] = response
            state["response_source"] = "filesystem"
        except Exception as e:
            state["error"] = f"Filesystem agent error: {str(e)}"
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

    def _route_after_classify(self, state: ChatState) -> str:
        if state.get("query_type") == "sql":
            return "sql"
        elif state.get("query_type") == "rag":
            return "retrieval"
        elif state.get("query_type") == "filesystem":
            return "filesystem"
        else:
            return "general"

    def _build_workflow(self):
        workflow = StateGraph(ChatState)

        workflow.add_node("input", self._input_node)
        workflow.add_node("classify_query", self._classify_query_node)
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("sql", self._sql_node)
        workflow.add_node("sql_response", self._sql_response_node)
        workflow.add_node("rag_response", self._rag_response_node)
        workflow.add_node("general_response", self._general_response_node)
        workflow.add_node("filesystem", self._filesystem_node)
        workflow.add_node("memory_update", self._memory_update_node)
        workflow.add_node("error_handler", self._error_handler_node)

        workflow.set_entry_point("input")
        workflow.add_edge("input", "classify_query")

        workflow.add_conditional_edges(
            "classify_query",
            self._route_after_classify,
            {
                "sql": "sql",
                "retrieval": "retrieval",
                "filesystem": "filesystem",
                "general": "general_response",
            },
        )

        workflow.add_conditional_edges(
            "sql",
            self._decision_node,
            {
                "sql": "sql_response",
                "general": "general_response",
                "rag": "retrieval",
                "error": "error_handler",
            },
        )

        workflow.add_conditional_edges(
            "retrieval",
            lambda state: "rag" if state.get("retrieved_docs") else "general",
            {
                "rag": "rag_response",
                "general": "general_response",
            },
        )

        workflow.add_edge("sql_response", "memory_update")
        workflow.add_edge("rag_response", "memory_update")
        workflow.add_edge("general_response", "memory_update")
        workflow.add_edge("filesystem", "memory_update")
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
        import time

        start_time = time.time()

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
            "sql_result": None,
            "response_source": "",
            "final_response": "",
            "error": None,
            "response_time": None,
            "query_type": None,
        }

        result = self.workflow.invoke(initial_state)
        response_time = time.time() - start_time

        return {
            "response": result["final_response"],
            "source": result["response_source"],
            "response_time": response_time,
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
