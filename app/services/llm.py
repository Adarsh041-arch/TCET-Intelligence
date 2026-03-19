import os
from typing import Optional, List, Dict, Any, Generator
import ollama
from app.core.config import config


os.environ["OLLAMA_HOST"] = config.ollama_base_url


class LLMService:
    def __init__(self):
        self.model = config.llm_model

    def check_connection(self) -> bool:
        try:
            ollama.list()
            return True
        except Exception:
            return False

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        try:
            if context:
                system_prompt = """You are a helpful AI assistant. Use the provided context to answer questions accurately. 
                If the context doesn't contain relevant information, say so and provide a general answer based on your knowledge."""
                user_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
            else:
                system_prompt = "You are a helpful AI assistant. Provide accurate and helpful responses."
                user_prompt = prompt

            messages = [{"role": "system", "content": system_prompt}]
            if chat_history:
                for msg in chat_history[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_prompt})

            response = ollama.chat(model=self.model, messages=messages)
            return response["message"]["content"]
        except Exception as e:
            print(f"LLM generation error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def generate_rag_response(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if retrieved_docs:
            context = "\n\n".join(
                [
                    f"Document {i + 1}:\n{doc['content']}"
                    for i, doc in enumerate(retrieved_docs)
                ]
            )
        else:
            context = None
        return self.generate_response(query, context, chat_history)


llm_service = LLMService()
