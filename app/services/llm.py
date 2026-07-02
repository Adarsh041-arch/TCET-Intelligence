import os
import hashlib
import time
from typing import Optional, List, Dict, Any, Generator
import ollama
from app.core.config import config


os.environ["OLLAMA_HOST"] = config.ollama_base_url

MAX_HISTORY = 5
CACHE_TTL = 300


class LLMService:
    def __init__(self):
        self.model = config.llm_model
        self._response_cache: Dict[str, tuple[str, float]] = {}

    def check_connection(self) -> bool:
        try:
            ollama.list()
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
            ollama.generate(
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
            sys = (
                "You are an AI assistant for TCET (Thakur College of Engineering and Technology). "
                "Provide accurate information about courses, attendance, results, college procedures, "
                "faculty, campus facilities, and general educational queries. "
                "Use the provided context to answer questions accurately. "
                "If the context doesn't contain relevant information, say so."
            )
        else:
            sys = (
                "You are an AI assistant for TCET (Thakur College of Engineering and Technology). "
                "Help students with questions about courses, attendance, results, college procedures, "
                "faculty, campus facilities, syllabus, exams, and general educational queries. "
                "Provide accurate and helpful responses."
            )

        messages = [{"role": "system", "content": sys}]

        if chat_history:
            for msg in chat_history[-MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        user_prefix = f"[SYSTEM INSTRUCTION: {sys}]\n\n"

        if context:
            messages.append(
                {
                    "role": "user",
                    "content": f"{user_prefix}Context:\n{context}\n\nQuestion: {prompt}",
                }
            )
        else:
            messages.append({"role": "user", "content": f"{user_prefix}{prompt}"})

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
            response = ollama.chat(model=self.model, messages=messages)
            result = response["message"]["content"]
            self._cache_response(cache_key, result)
            return result
        except Exception as e:
            print(f"LLM generation error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        try:
            messages = self._build_messages(prompt, context, chat_history, system_prompt)
            stream = ollama.chat(model=self.model, messages=messages, stream=True)
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
    ) -> Generator[str, None, None]:
        if retrieved_docs:
            docs_to_use = retrieved_docs[:3]
            context = "\n\n".join(
                [
                    f"Document {i + 1}:\n{doc['content']}"
                    for i, doc in enumerate(docs_to_use)
                ]
            )
        else:
            context = None

        system_prompt = (
            "You are an AI assistant for TCET (Thakur College of Engineering and Technology). "
            "Use the provided document context to answer questions accurately. "
            "Reference specific information from the documents when available."
        )

        messages = [{"role": "system", "content": system_prompt}]
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
            stream = ollama.chat(model=self.model, messages=messages, stream=True)
            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            yield f"I apologize, but I encountered an error: {str(e)}"

    def generate_sql_query(self, question: str, table_info: str) -> str:
        prompt = f"""Given the following database schema, convert this natural language question into a SQL query.
Only return the SQL query, nothing else.

Schema:
{table_info}

Question: {question}

SQL Query:"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a SQL expert. Return ONLY the SQL query, no explanation.",
                },
                {"role": "user", "content": prompt},
            ]
            response = ollama.chat(model=self.model, messages=messages)
            return response["message"]["content"].strip()
        except Exception as e:
            return f"Error generating query: {e}"

    def generate_sql_response(self, question: str, query_result: Dict[str, Any]) -> str:
        if not query_result.get("success"):
            return f"I couldn't execute that query. Error: {query_result.get('error', 'Unknown error')}"

        if query_result["type"] == "select":
            columns = query_result.get("columns", [])
            rows = query_result.get("rows", [])

            if not rows:
                return "No results found for your query."

            result_text = f"Found {len(rows)} results:\n\n"
            result_text += " | ".join(columns) + "\n"
            result_text += "-" * len(result_text)

            for row in rows[:50]:
                result_text += "\n" + " | ".join([str(val) for val in row])

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
    ) -> str:
        if retrieved_docs:
            docs_to_use = retrieved_docs[:3]
            context = "\n\n".join(
                [
                    f"Document {i + 1}:\n{doc['content']}"
                    for i, doc in enumerate(docs_to_use)
                ]
            )
        else:
            context = None
        return self.generate_response(query, context, chat_history)

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

        prompt = (
            "Task: Decide if answering the user's query requires current real-time information, news, local weather, sports scores, or specific factual details that might be missing from your static knowledge.\n"
            "Examples:\n"
            '- "latest news about Apple" -> YES\n'
            '- "price of BTC today" -> YES\n'
            '- "who is the prime minister of India" -> YES\n'
            '- "how to write a binary search in python" -> NO\n'
            '- "what is the capital of France" -> NO\n'
            '- "tell me a story" -> NO\n\n'
            f'User Query: "{query}"\n\n'
            "Require web search? (YES/NO):"
        )
        try:
            response = ollama.generate(
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


llm_service = LLMService()
