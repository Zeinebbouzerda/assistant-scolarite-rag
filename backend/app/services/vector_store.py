
import chromadb

from backend.app.config import STORAGE_DIR


class VectorStore:
    def __init__(self):
        """Initialise la base de données vectorielle ChromaDB."""
        chroma_path = STORAGE_DIR / "chroma"
        chroma_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(chroma_path)
        )

        self.collection = self.client.get_or_create_collection(
            name="assistant_scolarite",
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        """Ajoute les chunks ou met à jour ceux qui existent déjà."""
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Le nombre de chunks doit être égal au nombre d'embeddings."
            )

        ids = [str(chunk["id"]) for chunk in chunks]
        documents = [str(chunk["text"]) for chunk in chunks]

        metadatas = []
        for chunk in chunks:
            metadata = {
                **chunk.get("metadata", {}),
                "strategy": chunk.get("strategy", "structural"),
            }

            # ChromaDB n'accepte pas les valeurs None dans les métadonnées.
            metadata = {
                key: value
                for key, value in metadata.items()
                if value is not None
            }

            metadatas.append(metadata)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        """Recherche les chunks les plus proches de la question."""
        if top_k < 1:
            return []

        count = self.collection.count()
        if count == 0:
            return []

        query_args = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, count),
            "include": ["documents", "metadatas", "distances"],
        }

        # Exemple : {"type": "faq"}
        if filters:
            query_args["where"] = filters

        results = self.collection.query(**query_args)

        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]
        distances = results.get("distances") or [[]]
        ids = results.get("ids") or [[]]

        found_documents = documents[0] if documents else []
        found_metadatas = metadatas[0] if metadatas else []
        found_distances = distances[0] if distances else []
        found_ids = ids[0] if ids else []

        items = []

        for index, document in enumerate(found_documents):
            metadata = (
                found_metadatas[index]
                if index < len(found_metadatas) and found_metadatas[index]
                else {}
            )

            distance = (
                float(found_distances[index])
                if index < len(found_distances)
                and found_distances[index] is not None
                else None
            )

            # Avec la distance cosinus de ChromaDB :
            # score = 1 - distance.
            score = 1.0 - distance if distance is not None else None

            items.append(
                {
                    "id": found_ids[index] if index < len(found_ids) else "",
                    "text": document or "",
                    "metadata": metadata,
                    "distance": distance,
                    "score": score,
                }
            )

        return items
