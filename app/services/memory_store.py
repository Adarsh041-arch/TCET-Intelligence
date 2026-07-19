import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import chromadb
from chromadb.config import Settings

from app.core.config import config
from app.services.embeddings import embedding_service


class MemoryStore:
    _write_lock = threading.Lock()

    def __init__(
        self,
        persist_directory: str = "data/chroma_memory",
        collection_name: str = "user_memory",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._init_store()

    def _get_client(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            try:
                self._collection = client.get_collection(name=self.collection_name)
            except Exception:
                self._collection = client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                    get_or_create=True,
                )
        return self._collection

    def _init_store(self):
        self._get_collection()

    def add_memory(
        self,
        user_id: str,
        fact: str,
        category: str = "other",
        confidence: float = 0.8,
        source_message_id: str = "",
    ) -> str:
        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        metadata = {
            "user_id": user_id,
            "category": category,
            "confidence": confidence,
            "source_message_id": source_message_id,
            "created_at": now,
        }
        embedding = embedding_service.embed_text(fact)
        collection = self._get_collection()
        with self._write_lock:
            collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[fact],
            )
        return memory_id

    def add_memories_batch(
        self,
        user_id: str,
        facts: List[Dict[str, Any]],
        source_message_id: str = "",
    ) -> List[str]:
        if not facts:
            return []
        now = datetime.now(timezone.utc).isoformat()
        texts = [f["fact"] for f in facts]
        ids = [str(uuid.uuid4()) for _ in facts]
        embeddings = embedding_service.embed_texts(texts)
        metadatas = [
            {
                "user_id": user_id,
                "category": f.get("category", "other"),
                "confidence": f.get("confidence", 0.8),
                "source_message_id": source_message_id,
                "created_at": now,
            }
            for f in facts
        ]
        collection = self._get_collection()
        with self._write_lock:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts,
            )
        return ids

    def retrieve_memories(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection()
        embedding = embedding_service.embed_text(query)
        if category:
            where: Dict[str, Any] = {
                "$and": [{"user_id": user_id}, {"category": category}],
            }
        else:
            where: Dict[str, Any] = {"user_id": user_id}
        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
        )
        memories = []
        if results["ids"] and results["ids"][0]:
            for i, mem_id in enumerate(results["ids"][0]):
                meta = dict(results["metadatas"][0][i]) if results["metadatas"] else {}
                memories.append({
                    "memory_id": mem_id,
                    "fact": results["documents"][0][i],
                    "metadata": meta,
                    "similarity": 1 - results["distances"][0][i] if results.get("distances") else 1.0,
                })
        return memories

    def update_memory(
        self,
        memory_id: str,
        fact: Optional[str] = None,
        category: Optional[str] = None,
    ) -> bool:
        collection = self._get_collection()
        existing = collection.get(ids=[memory_id])
        if not existing["ids"]:
            return False
        meta = dict(existing["metadatas"][0]) if existing["metadatas"] else {}
        if category:
            meta["category"] = category
        if fact:
            meta["confidence"] = min(meta.get("confidence", 0.8) + 0.05, 1.0)
            embedding = embedding_service.embed_text(fact)
            collection.update(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[fact],
                metadatas=[meta],
            )
        else:
            collection.update(ids=[memory_id], metadatas=[meta])
        return True

    def delete_memory(self, memory_id: str) -> bool:
        collection = self._get_collection()
        existing = collection.get(ids=[memory_id])
        if not existing["ids"]:
            return False
        collection.delete(ids=[memory_id])
        return True

    def get_user_memories(
        self,
        user_id: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection()
        if category:
            where: Dict[str, Any] = {
                "$and": [{"user_id": user_id}, {"category": category}],
            }
        else:
            where: Dict[str, Any] = {"user_id": user_id}
        results = collection.get(where=where)
        memories = []
        if results["ids"]:
            for i, mem_id in enumerate(results["ids"]):
                memories.append({
                    "memory_id": mem_id,
                    "fact": results["documents"][i] if results["documents"] else "",
                    "metadata": dict(results["metadatas"][i]) if results["metadatas"] else {},
                })
        return memories

    def get_memory_count(self, user_id: Optional[str] = None) -> int:
        collection = self._get_collection()
        if user_id:
            results = collection.get(where={"user_id": user_id})
        else:
            results = collection.get()
        return len(results["ids"])


memory_store = MemoryStore()
