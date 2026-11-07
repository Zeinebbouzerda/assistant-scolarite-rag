"""Assemble les services une seule fois (le modèle d'embeddings est lourd :
on ne le recharge pas à chaque requête, contrairement à l'ancien RetrievalService)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from backend.app.config import Settings, get_settings
from backend.app.services.embeddings import build_embedder
from backend.app.services.generation import RagPipeline
from backend.app.services.llm import LLMClient, build_llm
from backend.app.services.retrieval import RetrievalService
from backend.app.services.vector_store import VectorStore


@dataclass
class Container:
    settings: Settings
    embedder: object
    store: VectorStore
    retrieval: RetrievalService
    llm: LLMClient
    rag: RagPipeline


def build_container(settings: Settings, embedder=None, llm: LLMClient | None = None,
                    collection_name: str | None = None,
                    storage_dir=None) -> Container:
    embedder = embedder or build_embedder(settings)
    store = VectorStore(storage_dir or settings.storage_dir / "chroma",
                        collection_name or settings.collection_name)
    llm = llm or build_llm(settings)
    retrieval = RetrievalService(embedder, store, settings)
    return Container(settings, embedder, store, retrieval, llm,
                     RagPipeline(retrieval, store, llm, settings))


@lru_cache
def get_container() -> Container:
    return build_container(get_settings())
