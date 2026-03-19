from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import config


class EmbeddingService:
    def __init__(self):
        self.model_name = config.embedding_model
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def get_embedding_dimension(self) -> int:
        sample_embedding = self.embed_text("sample")
        return len(sample_embedding)


embedding_service = EmbeddingService()
