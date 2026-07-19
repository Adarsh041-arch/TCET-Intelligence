import json
import os
import hashlib
import re
import time
from collections import Counter
from typing import Optional, List, Dict, Any, Generator
import ollama
from app.core.config import config
from app.prompts.general import SYSTEM_CONTEXT_PROMPT, SYSTEM_NO_CONTEXT_PROMPT
from app.prompts.rag import RAG_STAFF_PROMPT, DOCUMENT_QUERY_DECISION_PROMPT, DOCUMENT_RELEVANCE_PROMPT
from app.services.vector_store import vector_store, user_vector_store
from app.prompts.sql import SQL_SYSTEM_PROMPT, SQL_QUERY_TEMPLATE, SQL_PLANNING_PROMPT, SQL_RETRY_PROMPT
from app.prompts.web import WEB_SEARCH_DECISION_PROMPT


# Set environment variable just in case other langchain code needs it
os.environ["OLLAMA_HOST"] = config.ollama_base_url

MAX_HISTORY = 30
CACHE_TTL = 300


class LLMService:
    def __init__(self):
        self.model = config.llm_model
        self.client = ollama.Client(host=config.ollama_base_url)
        self._response_cache: Dict[str, tuple[str, float]] = {}

    def check_connection(self) -> bool:
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def _get_cache_key(
        self, prompt: str, context: Optional[str], history_hash: str
    ) -> str:
        key_data = f"{prompt}|{context or ''}|{history_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_history_hash(self, chat_history: Optional[List[Dict[str, str]]]) -> str:
        if not chat_history:
            return "none"
        recent = chat_history[-MAX_HISTORY:]
        return hashlib.md5(str(recent).encode()).hexdigest()[:8]

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        if cache_key in self._response_cache:
            response, timestamp = self._response_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                return response
            else:
                del self._response_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: str) -> None:
        self._response_cache[cache_key] = (response, time.time())
        if len(self._response_cache) > 100:
            oldest_keys = sorted(self._response_cache.items(), key=lambda x: x[1][1])[
                :10
            ]
            for key in oldest_keys:
                del self._response_cache[key[0]]

    def warmup(self) -> bool:
        try:
            self.client.generate(
                model=self.model, prompt="Hello", options={"num_predict": 5}
            )
            return True
        except Exception as e:
            print(f"Warmup error: {e}")
            return False

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        if system_prompt:
            sys = system_prompt
        elif context:
            sys = SYSTEM_CONTEXT_PROMPT
        else:
            sys = SYSTEM_NO_CONTEXT_PROMPT

        messages = [{"role": "system", "content": sys}]

        if chat_history:
            for msg in chat_history[-MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        if context:
            messages.append(
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {prompt}",
                }
            )
        else:
            messages.append({"role": "user", "content": prompt})

        return messages

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        cache_key = self._get_cache_key(
            prompt, context, self._get_history_hash(chat_history)
        )
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached

        try:
            messages = self._build_messages(prompt, context, chat_history, system_prompt)
            response = self.client.chat(
                model=self.model, messages=messages,
                options={"num_predict": 2048, "num_ctx": 4096}
            )
            result = response["message"]["content"]
            self._cache_response(cache_key, result)
            return result
        except Exception as e:
            print(f"LLM generation error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def chat(self, messages: List[Dict[str, str]], options: Optional[Dict] = None) -> str:
        """Send pre-built messages list to Ollama and return the response text."""
        try:
            opts = {"num_predict": 2048, "num_ctx": 4096, "temperature": 0.7}
            if options:
                opts.update(options)
            response = self.client.chat(model=self.model, messages=messages, options=opts)
            return response["message"]["content"]
        except Exception as e:
            print(f"LLM chat error: {e}")
            return f"Error: {e}"

    def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        try:
            messages = self._build_messages(prompt, context, chat_history, system_prompt)
            stream = self.client.chat(
                model=self.model, messages=messages, stream=True,
                options={"num_predict": 2048, "num_ctx": 4096, "temperature": 0.7}
            )
            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            yield f"I apologize, but I encountered an error: {str(e)}"

    def generate_rag_response_stream(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        similarity_threshold: Optional[float] = None,
    ) -> Generator[str, None, None]:
        threshold = similarity_threshold if similarity_threshold is not None else config.similarity_threshold
        if retrieved_docs:
            is_doc_query = self._is_document_query(query)
            if is_doc_query:
                filename = self._identify_document(retrieved_docs)
                if filename:
                    all_chunks = user_vector_store.get_all_chunks_by_filename(filename)
                    if not all_chunks:
                        all_chunks = vector_store.get_all_chunks_by_filename(filename)
                    if all_chunks:
                        docs_to_use = all_chunks
                    else:
                        docs_to_use = [d for d in retrieved_docs if d.get("similarity", 0) >= threshold][:config.top_k]
                else:
                    docs_to_use = [d for d in retrieved_docs if d.get("similarity", 0) >= threshold][:config.top_k]
            else:
                docs_to_use = [d for d in retrieved_docs if d.get("similarity", 0) >= threshold][:config.top_k]
            context = "\n\n".join(
                [
                    f"Document {i + 1}:\n{doc['content']}"
                    for i, doc in enumerate(docs_to_use)
                ]
            ) if docs_to_use else None
        else:
            context = None

        messages = [{"role": "system", "content": RAG_STAFF_PROMPT}]
        if chat_history:
            for msg in chat_history[-MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        if context:
            messages.append(
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            )
        else:
            messages.append({"role": "user", "content": query})

        try:
            stream = self.client.chat(
                model=self.model, messages=messages, stream=True,
                options={"num_predict": 2048, "num_ctx": 4096, "temperature": 0.7}
            )
            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            yield f"I apologize, but I encountered an error: {str(e)}"

    def _format_sql_history(self, chat_history: Optional[List[Dict[str, str]]]) -> str:
        """Format last 10 chat messages for SQL context."""
        history_text = ""
        if chat_history:
            for msg in chat_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]
                history_text += f"{role.capitalize()}: {content}\n"
        return history_text or "(No previous conversation)"

    def _extract_sql(self, raw: str) -> str:
        """Strip markdown/noise and return the bare SQL statement."""
        query = raw.strip()
        match = re.search(r'```(?:sql)?\s*(.*?)```', query, re.DOTALL | re.IGNORECASE)
        if match:
            query = match.group(1).strip()
        if "text\nCopy\n" in query:
            query = query.replace("text\nCopy\n", "")

        keywords = ["SELECT ", "UPDATE ", "DELETE ", "INSERT ", "WITH "]
        first_idx = len(query)
        found = False
        upper_query = query.upper()
        for kw in keywords:
            idx = upper_query.find(kw)
            if idx != -1 and idx < first_idx:
                first_idx = idx
                found = True
        if found:
            query = query[first_idx:]
        return query.strip()

    def plan_sql_query(self, question: str, table_info: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Produce a short reasoning plan (tables, joins, filters) before writing SQL."""
        prompt = SQL_PLANNING_PROMPT.format(
            table_info=table_info,
            chat_history=self._format_sql_history(chat_history),
            question=question,
        )
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 512, "temperature": 0.2},
            )
            return response["message"]["content"].strip()
        except Exception as e:
            print(f"SQL planning error: {e}")
            return "(No plan available)"

    def generate_sql_query(
        self,
        question: str,
        table_info: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        plan: Optional[str] = None,
    ) -> str:
        prompt = SQL_QUERY_TEMPLATE.format(
            table_info=table_info,
            chat_history=self._format_sql_history(chat_history),
            plan=plan or "(No plan provided)",
            question=question,
        )
        try:
            messages = [
                {"role": "system", "content": SQL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = self.client.chat(model=self.model, messages=messages)
            return self._extract_sql(response["message"]["content"])
        except Exception as e:
            return f"Error generating query: {e}"

    def regenerate_sql_query(
        self,
        question: str,
        table_info: str,
        previous_query: str,
        error: str,
        plan: Optional[str] = None,
    ) -> str:
        """Reason over a failed query's error and produce a corrected SQL query."""
        prompt = SQL_RETRY_PROMPT.format(
            table_info=table_info,
            plan=plan or "(No plan provided)",
            question=question,
            previous_query=previous_query,
            error=error,
        )
        try:
            messages = [
                {"role": "system", "content": SQL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = self.client.chat(model=self.model, messages=messages)
            return self._extract_sql(response["message"]["content"])
        except Exception as e:
            return f"Error generating query: {e}"

    def execute_sql_with_retry(
        self,
        question: str,
        table_info: str,
        connector,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Plan, generate, execute a SQL query. On failure, reason over the error and retry
        up to max_iterations. Returns the final query result dict plus metadata."""
        limit = max_iterations if max_iterations is not None else config.sql_max_iterations

        # Step 1: plan (tables, joins, filters)
        plan = self.plan_sql_query(question, table_info, chat_history)

        attempts = []
        sql_query = self.generate_sql_query(question, table_info, chat_history, plan=plan)
        last_result: Dict[str, Any] = {}

        for iteration in range(1, limit + 1):
            if not sql_query or sql_query.startswith("Error"):
                error = sql_query or "Empty query"
                attempts.append({"query": sql_query, "error": error})
                sql_query = self.regenerate_sql_query(question, table_info, sql_query, error, plan=plan)
                continue

            last_result = connector.execute_query(sql_query)
            attempts.append({"query": sql_query, "error": last_result.get("error")})

            if last_result.get("success"):
                return {
                    "success": True,
                    "result": last_result,
                    "query": sql_query,
                    "plan": plan,
                    "iterations": iteration,
                    "attempts": attempts,
                }

            # Failed: reason over error and retry (unless out of iterations)
            if iteration < limit:
                sql_query = self.regenerate_sql_query(
                    question, table_info, sql_query,
                    last_result.get("error", "Unknown error"), plan=plan,
                )

        return {
            "success": False,
            "result": last_result,
            "query": sql_query,
            "plan": plan,
            "iterations": limit,
            "attempts": attempts,
        }

    def generate_sql_response(self, question: str, query_result: Dict[str, Any]) -> str:
        from app.prompts.sql import SQL_RESPONSE_PROMPT

        if not query_result.get("success"):
            return f"I couldn't execute that query. Error: {query_result.get('error', 'Unknown error')}"

        if query_result["type"] == "select":
            columns = query_result.get("columns", [])
            rows = query_result.get("rows", [])

            if not rows:
                return "No results found for your query."

            # Build structured result for LLM formatting
            result_data = {
                "columns": columns,
                "row_count": len(rows),
                "rows": rows[:50],  # Send first 50 rows
                "has_more": len(rows) > 50,
                "additional_rows": len(rows) - 50 if len(rows) > 50 else 0
            }

            result_json = json.dumps(result_data, indent=2, default=str)
            prompt = SQL_RESPONSE_PROMPT.format(query_result=result_json)

            try:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant that formats database results into clean markdown tables."},
                    {"role": "user", "content": prompt},
                ]
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={"num_predict": 2048, "temperature": 0.3}
                )
                return response["message"]["content"].strip()
            except Exception as e:
                # Fallback to basic formatting
                result_text = f"Found {len(rows)} results:\n\n"
                result_text += " | ".join(columns) + "\n"
                result_text += "-" * 50 + "\n"
                for row in rows[:50]:
                    result_text += " | ".join([str(val) for val in row]) + "\n"
                if len(rows) > 50:
                    result_text += f"\n... and {len(rows) - 50} more rows"
                return result_text
        else:
            return f"Query executed successfully. {query_result.get('affected_rows', 0)} rows affected."

    def generate_rag_response(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        similarity_threshold: Optional[float] = None,
    ) -> str:
        threshold = similarity_threshold if similarity_threshold is not None else config.similarity_threshold
        if retrieved_docs:
            is_doc_query = self._is_document_query(query)
            if is_doc_query:
                filename = self._identify_document(retrieved_docs)
                if filename:
                    all_chunks = user_vector_store.get_all_chunks_by_filename(filename)
                    if not all_chunks:
                        all_chunks = vector_store.get_all_chunks_by_filename(filename)
                    if all_chunks:
                        docs_to_use = all_chunks
                    else:
                        docs_to_use = [d for d in retrieved_docs if d.get("similarity", 0) >= threshold][:config.top_k]
                else:
                    docs_to_use = [d for d in retrieved_docs if d.get("similarity", 0) >= threshold][:config.top_k]
            else:
                docs_to_use = [d for d in retrieved_docs if d.get("similarity", 0) >= threshold][:config.top_k]
            context = "\n\n".join(
                [
                    f"Document {i + 1}:\n{doc['content']}"
                    for i, doc in enumerate(docs_to_use)
                ]
            ) if docs_to_use else None
        else:
            context = None

        return self.generate_response(query, context, chat_history, system_prompt=RAG_STAFF_PROMPT)

    def _is_document_query(self, query: str) -> bool:
        query_lower = query.lower().strip()
        doc_indicators = [
            "show me", "display", "read me", "what does it say",
            "full document", "full content", "what is written",
            "show the file", "open the", "give me the document",
            "tell me what's in", "what's in the", "entire document",
            "whole document", "print the", "get the content of",
            "show content", "show all", "load all", "read the file",
            "give me everything in", "show full", "display full",
            "show the syllabus", "read the syllabus",
            "show fees structure", "fee document",
            "admission document", "read admission policy",
            "attendance document", "read notice",
            "show timetable", "read the policy",
        ]
        for indicator in doc_indicators:
            if indicator in query_lower:
                return True

        filenames = vector_store.get_all_filenames() + user_vector_store.get_all_filenames()
        filenames_str = "\n".join(f"- {f}" for f in filenames) if filenames else "No documents available."
        prompt = DOCUMENT_QUERY_DECISION_PROMPT.format(filenames=filenames_str, query=query)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"num_predict": 5, "temperature": 0.0},
            )
            text = response.get("response", "").strip().upper()
            return "DOCUMENT" in text
        except Exception:
            return False

    def _identify_document(self, retrieved_docs: List[Dict[str, Any]]) -> Optional[str]:
        filenames = [d["metadata"].get("filename") for d in retrieved_docs if d.get("metadata") and d["metadata"].get("filename")]
        if not filenames:
            return None
        most_common = Counter(filenames).most_common(1)
        return most_common[0][0] if most_common else None

    def select_relevant_tcet_docs(self, query: str, filenames: List[str]) -> List[str]:
        if not filenames:
            return []
        filenames_str = "\n".join(f"- {f}" for f in filenames)
        prompt = DOCUMENT_RELEVANCE_PROMPT.format(filenames=filenames_str, query=query)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"num_predict": 128, "temperature": 0.0},
            )
            text = response.get("response", "").strip()
            if text.upper() == "NONE" or not text:
                return []
            text = text.replace("\n", ",").replace("- ", "").replace("* ", "")
            selected = [f.strip().strip('"\'') for f in text.split(",") if f.strip()]
            exact = [f for f in selected if f in filenames]
            partial = [f for f in filenames if any(s.lower() in f.lower() for s in selected)] if not exact else exact
            return exact if exact else partial[:5]
        except Exception as e:
            print(f"Error selecting relevant docs: {e}")
            return []

    def decide_web_search(self, query: str) -> bool:
        query_lower = query.lower()
        
        # Obvious non-web conversational queries
        conversational = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "how are you", "who are you", "what are you", "thank you", "thanks", "bye", "goodbye"]
        if any(w == query_lower.strip().rstrip("?.!") for w in conversational):
            return False

        # Obvious coding queries
        coding = ["write a python", "write a function", "write code", "how to write a", "regex", "sql query", "merge lists", "javascript function"]
        if any(w in query_lower for w in coding):
            return False

        prompt = WEB_SEARCH_DECISION_PROMPT.format(query=query)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "num_predict": 5,
                    "temperature": 0.0
                }
            )
            text = response.get("response", "").strip().upper()
            return "YES" in text
        except Exception as e:
            print(f"Error deciding web search: {e}")
            return False

    def extract_memories(
        self,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        from app.prompts.memory import MEMORY_EXTRACTION_PROMPT, VALID_CATEGORIES

        categories_str = ", ".join(VALID_CATEGORIES)
        prompt = MEMORY_EXTRACTION_PROMPT.format(
            categories=categories_str, message=message
        )
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"num_predict": 1024, "temperature": 0.0},
            )
            text = response.get("response", "").strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
            if not text or text == "[]":
                return []
            facts = json.loads(text)
            if isinstance(facts, list):
                valid = []
                for f in facts:
                    if isinstance(f, dict) and "fact" in f and "category" in f:
                        f.setdefault("confidence", 0.8)
                        if f["category"] not in VALID_CATEGORIES:
                            f["category"] = "other"
                        valid.append(f)
                return valid
            return []
        except Exception as e:
            print(f"Memory extraction error: {e}")
            return []


llm_service = LLMService()
