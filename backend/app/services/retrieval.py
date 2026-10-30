
from backend.app.services.embeddings import EmbeddingService
from backend.app.services.vector_store import VectorStore


class RetrievalService:
    def __init__(self):
        self.embeddings = EmbeddingService()
        self.vector_store = VectorStore()

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        query = query.strip()

        if not query:
            return []

        query_embedding = self.embeddings.encode_query(query)

        return self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters,
        )
