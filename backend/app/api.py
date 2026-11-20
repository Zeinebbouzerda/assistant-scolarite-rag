"""Routes de l'API REST, toutes préfixées par /api (documentation interactive : /docs)."""
from fastapi import APIRouter, Depends, HTTPException

from backend.app import models as m
from backend.app.errors import LLMUnavailable, VectorStoreUnavailable
from backend.app.services.container import Container, get_container
from backend.app.services.ingestion import ingest_corpus

router = APIRouter(prefix="/api")


def container_dep() -> Container:
    """Fournit le conteneur de services injecté par FastAPI (surchargeable en test)."""
    return get_container()


def _hit_fields(h: dict) -> dict:
    """Extrait les champs communs d'un fragment retourné par la base vectorielle."""
    md = h["metadata"]
    return dict(
        chunk_id=h["id"],
        file=md.get("source", ""),
        reference=md.get("reference", ""),
        date=md.get("date") or None,
        page=int(md.get("page", 1)),
        section=md.get("section", ""),
        score=float(h["score"] or 0.0),
    )


@router.get("/health", response_model=m.HealthResponse, summary="État du service")
def health(c: Container = Depends(container_dep)):
    """Vérifie la disponibilité de ChromaDB et renvoie la configuration active."""
    try:
        n = c.store.count()
    except Exception as exc:
        raise HTTPException(503, f"Base vectorielle indisponible : {exc}") from exc
    return m.HealthResponse(
        status="ok",
        chunks=n,
        embedding_model=getattr(c.embedder, "model_name", "?"),
        llm_provider=c.settings.llm_provider,
        similarity_threshold=c.settings.similarity_threshold,
    )


@router.post("/ingest", response_model=m.IngestResponse, summary="(Ré)indexer le corpus")
def ingest(req: m.IngestRequest, c: Container = Depends(container_dep)):
    """Extrait, découpe, encode et indexe les PDF du corpus de manière idempotente."""
    try:
        report = ingest_corpus(
            c.settings,
            c.store,
            c.embedder,
            req.strategy,
            req.chunk_size,
            req.chunk_overlap,
            req.contextual_header,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise VectorStoreUnavailable(str(exc)) from exc
    return report


@router.get("/documents", response_model=list[m.DocumentInfo], summary="Documents indexés")
def documents(c: Container = Depends(container_dep)):
    """Liste les documents présents dans ChromaDB avec leurs métadonnées et liens de version."""
    try:
        return c.store.documents()
    except Exception as exc:
        raise VectorStoreUnavailable(str(exc)) from exc


@router.post(
    "/search",
    response_model=m.SearchResponse,
    summary="Recherche seule (sans LLM) : fragments et scores",
)
def search(req: m.SearchRequest, c: Container = Depends(container_dep)):
    """Exécute uniquement la recherche vectorielle top-k, sans appel au LLM."""
    try:
        hits = c.retrieval.search(req.question, req.top_k, req.filter_dict())
    except Exception as exc:
        raise VectorStoreUnavailable(str(exc)) from exc
    return m.SearchResponse(
        question=req.question,
        results=[
            m.SearchHit(id=i, type=h["metadata"].get("type", ""), text=h["text"], **_hit_fields(h))
            for i, h in enumerate(hits, 1)
        ],
    )


@router.post("/ask", response_model=m.AskResponse, summary="Question -> réponse citée")
def ask(req: m.AskRequest, c: Container = Depends(container_dep)):
    """Exécute le pipeline RAG complet : recherche, seuil, extension modificative, génération et vérification."""
    try:
        res = c.rag.ask(req.question, req.top_k, req.filter_dict())
    except LLMUnavailable:
        # Converti en HTTP 502 par le gestionnaire d'exceptions de main.py
        raise
    except Exception as exc:
        raise VectorStoreUnavailable(str(exc)) from exc
    sources = (
        []
        if not res.found
        else [
            m.Source(
                id=i,
                excerpt=(p["text"][:400] + ("…" if len(p["text"]) > 400 else "")),
                **_hit_fields(p),
            )
            for i, p in enumerate(res.passages, 1)
        ]
    )
    return m.AskResponse(
        answer=res.answer,
        found=res.found,
        sources=sources,
        invalid_citations=res.invalid_citations,
        latency_ms=res.latency_ms,
    )
