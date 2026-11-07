<<<<<<< HEAD
"""Recherche des fragments les plus proches (exigences 4.3)."""
from __future__ import annotations

from backend.app.services.vector_store import VectorStore


def _csv(value) -> list[str]:
    return [x for x in str(value or "").split(",") if x]


class RetrievalService:
    def __init__(self, embedder, store: VectorStore, settings):
        self.embedder, self.store, self.settings = embedder, store, settings

    def search(self, query: str, top_k: int | None = None,
               filters: dict | None = None) -> list[dict]:
        """Top-k fragments avec leurs scores (recherche seule, sans LLM)."""
        query = query.strip()
        if not query:
            return []
        qv = self.embedder.encode_query(query)
        return self.store.search(qv, top_k or self.settings.default_top_k, filters)

    def expand_with_modifications(self, query: str, hits: list[dict],
                                  filters: dict | None = None) -> list[dict]:
        """Si un fragment vient d'un document MODIFIÉ par un autre, ajoute les
        meilleurs fragments du document modificatif (même s'ils ne sont pas dans
        le top-k). Le LLM voit ainsi toujours l'ancienne règle ET sa modification.

        Générique : le lien vient des métadonnées lues dans les PDF (`modified_by`),
        aucune référence de document n'est écrite en dur.
        """
        s = self.settings
        if not hits:
            return hits
        qv = self.embedder.encode_query(query)
        have = {h["id"] for h in hits}
        refs_in_hits = [h["metadata"].get("reference") for h in hits]
        modifiers: list[str] = []
        for h in hits:
            for ref in _csv(h["metadata"].get("modified_by")):
                if ref not in modifiers:
                    modifiers.append(ref)

        extra: list[dict] = []
        for ref in modifiers:
            need = s.expansion_per_doc - refs_in_hits.count(ref)
            if need <= 0:
                continue
            f = dict(filters or {})
            if f.get("reference") not in (None, "", ref):
                continue
            f["reference"] = ref
            for cand in self.store.search(qv, s.expansion_per_doc, f):
                if cand["id"] in have or (cand["score"] or 0) < s.similarity_threshold:
                    continue
                cand["expanded"] = True
                extra.append(cand)
                have.add(cand["id"])
                need -= 1
                if need <= 0:
                    break
        return hits + extra
=======

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
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
