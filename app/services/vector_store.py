import hashlib
import uuid
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from app.core.config import config
from app.services.embeddings import embedding_service


class VectorStore:
    def __init__(self):
        self.persist_directory = config.chroma_persist_directory
        self.collection_name = "documents"
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(name=self.collection_name)
            except Exception:
                self._collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                    get_or_create=True,
                )
        return self._collection

    def compute_file_hash(self, file_content: bytes) -> str:
        return hashlib.sha256(file_content).hexdigest()

    def add_documents(
        self, texts: List[str], metadatas: List[Dict[str, Any]], doc_id: str
    ) -> bool:
        try:
            embeddings = embedding_service.embed_texts(texts)
            ids = [f"{doc_id}_{i}" for i in range(len(texts))]
            self.collection.add(
                embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids
            )
            return True
        except Exception as e:
            print(f"Error adding documents: {e}")
            return False

    def retrieve_similar(
        self, query: str, top_k: Optional[int] = None, threshold: Optional[float] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            k = top_k or config.top_k
            sim_threshold = threshold or config.similarity_threshold

            query_embedding = embedding_service.embed_text(query)

            kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"],
            }
            if filter_dict:
                kwargs["where"] = filter_dict
                
            results = self.collection.query(**kwargs)

            docs = []
            if results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results["distances"] else 0
                    similarity = 1 - distance

                    if similarity >= sim_threshold:
                        docs.append(
                            {
                                "content": doc,
                                "metadata": results["metadatas"][0][i]
                                if results["metadatas"]
                                else {},
                                "similarity": similarity,
                            }
                        )

            return docs
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []

    def get_document_count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0

    def delete_document(self, doc_id: str) -> bool:
        try:
            all_ids = self.collection.get()["ids"]
            ids_to_delete = [id for id in all_ids if id.startswith(f"{doc_id}_")]
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    def clear_all(self) -> bool:
        try:
            self.client.delete_collection(name=self.collection_name)
            self._collection = None
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False


vector_store = VectorStore()
