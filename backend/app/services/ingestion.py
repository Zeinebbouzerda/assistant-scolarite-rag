"""Chaîne d'ingestion : PDF -> extraction -> découpage -> embeddings -> base."""
from __future__ import annotations

import time

from backend.app.services.chunking import chunk_document, validate_params
from backend.app.services.extraction import extract_corpus


def ingest_corpus(settings, store, embedder, strategy: str | None = None,
                  chunk_size: int | None = None, chunk_overlap: int | None = None,
                  contextual_header: bool = True) -> dict:
    """(Ré)indexe le corpus. Idempotente : les fragments de chaque fichier sont
    remplacés (jamais ajoutés), donc l'exécuter deux fois donne le même résultat."""
    t0 = time.perf_counter()
    strategy = strategy or "structural"
    if chunk_size is None:
        chunk_size = (settings.fixed_chunk_size if strategy == "fixed"
                      else settings.structural_chunk_size)
    if chunk_overlap is None:
        chunk_overlap = (settings.fixed_chunk_overlap if strategy == "fixed"
                         else settings.structural_chunk_overlap)
    validate_params(strategy, chunk_size, chunk_overlap)

    docs = extract_corpus(settings.corpus_dir)
    if not docs:
        raise FileNotFoundError(f"Aucun PDF trouvé dans {settings.corpus_dir}")

    # on calcule tout AVANT de toucher à la base : une erreur d'embedding ne
    # laisse donc jamais l'index à moitié vidé
    prepared = []
    for doc in docs:
        chunks = chunk_document(doc, strategy, chunk_size, chunk_overlap, contextual_header)
        prepared.append((doc, chunks, embedder.encode_documents([c.embed_text for c in chunks])))

    removed = store.delete_sources_not_in({d.file for d in docs})
    per_doc = []
    for doc, chunks, vectors in prepared:
        store.replace_file(doc.file, chunks, vectors)
        per_doc.append({"file": doc.file, "reference": doc.metadata["reference"],
                        "chunks": len(chunks)})
    return {
        "documents": len(docs), "chunks": sum(d["chunks"] for d in per_doc),
        "strategy": strategy, "chunk_size": chunk_size, "chunk_overlap": chunk_overlap,
        "removed_documents": removed, "per_document": per_doc,
        "duration_ms": int((time.perf_counter() - t0) * 1000),
    }
