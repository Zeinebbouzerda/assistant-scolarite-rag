"""Base vectorielle ChromaDB (persistance sur disque, similarité cosinus)."""
from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings


def _csv(value) -> list[str]:
    return [x for x in str(value or "").split(",") if x]


def build_where(filters: dict | None) -> dict | None:
    """{"type": "FAQ", "reference": None} -> clause `where` de Chroma."""
    conds = [{k: v} for k, v in (filters or {}).items() if v not in (None, "")]
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


class VectorStore:
    def __init__(self, persist_dir: Path, collection_name: str):
        persist_dir = Path(persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------ écriture
    def replace_file(self, source: str, chunks, embeddings: list[list[float]]) -> None:
        """Remplace TOUS les fragments d'un fichier : relancer l'ingestion ne
        crée donc jamais de doublon, même si les paramètres de découpage changent."""
        if len(chunks) != len(embeddings):
            raise ValueError("Autant de fragments que d'embeddings sont attendus.")
        self.collection.delete(where={"source": source})
        if not chunks:
            return
        self.collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[{k: v for k, v in c.metadata.items() if v is not None}
                       for c in chunks],
        )

    def delete_sources_not_in(self, sources: set[str]) -> int:
        stale = [s for s in {m["source"] for m in self.all_metadatas()} if s not in sources]
        for s in stale:
            self.collection.delete(where={"source": s})
        return len(stale)

    # ------------------------------------------------------------- lecture
    def count(self) -> int:
        return self.collection.count()

    def all_metadatas(self) -> list[dict]:
        return self.collection.get(include=["metadatas"])["metadatas"] or []

    def documents(self) -> list[dict]:
        """Un enregistrement par document indexé (agrégé depuis les fragments)."""
        docs: dict[str, dict] = {}
        for m in self.all_metadatas():
            d = docs.setdefault(m["source"], {
                "file": m["source"], "reference": m.get("reference", ""),
                "title": m.get("title", ""), "type": m.get("type", ""),
                "date": m.get("date", ""), "version": m.get("version", ""),
                "status": m.get("status", ""),
                "modifies": _csv(m.get("modifies")),
                "modified_by": _csv(m.get("modified_by")),
                "chunks": 0, "pages": 0,
            })
            d["chunks"] += 1
            d["pages"] = max(d["pages"], int(m.get("page", 1)))
        return sorted(docs.values(), key=lambda d: d["file"])

    def search(self, query_embedding: list[float], top_k: int = 5,
               filters: dict | None = None) -> list[dict]:
        count = self.count()
        if top_k < 1 or count == 0:
            return []
        args = {"query_embeddings": [query_embedding], "n_results": min(top_k, count),
                "include": ["documents", "metadatas", "distances"]}
        where = build_where(filters)
        if where:
            args["where"] = where
        res = self.collection.query(**args)
        items = []
        for i, doc in enumerate((res.get("documents") or [[]])[0]):
            dist = (res["distances"][0][i]) if res.get("distances") else None
            items.append({
                "id": res["ids"][0][i], "text": doc or "",
                "metadata": res["metadatas"][0][i] or {},
                "distance": dist,
                # distance cosinus de Chroma -> score de similarité
                "score": None if dist is None else round(1.0 - float(dist), 4),
            })
        return items
