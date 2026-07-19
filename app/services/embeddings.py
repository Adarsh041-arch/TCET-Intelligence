from typing import List
import ollama
from app.core.config import config


class EmbeddingService:
    def __init__(self):
        self.model_name = config.embedding_model
        self.client = ollama.Client(host=config.ollama_base_url)

    def embed_text(self, text: str) -> List[float]:
        response = self.client.embeddings(model=self.model_name, prompt=text)
        return response["embedding"]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

    def get_embedding_dimension(self) -> int:
        return len(self.embed_text("sample"))


embedding_service = EmbeddingService()
