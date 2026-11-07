<<<<<<< HEAD
"""Point d'entrée : uvicorn backend.app.main:app --reload"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import router
from backend.app.config import get_settings
from backend.app.errors import LLMUnavailable, VectorStoreUnavailable


def create_app() -> FastAPI:
    app = FastAPI(
        title="Assistant Scolarité RAG — EIH",
        description="Répond aux questions des étudiants à partir des documents officiels "
                    "de l'École d'Ingénieurs Hélianthe, en citant ses sources.",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=get_settings().cors_origin_list,
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(LLMUnavailable)
    async def _llm(_: Request, exc: LLMUnavailable):
        return JSONResponse({"detail": f"Le modèle de langage ne répond pas. {exc}"}, 502)

    @app.exception_handler(VectorStoreUnavailable)
    async def _db(_: Request, exc: VectorStoreUnavailable):
        return JSONResponse({"detail": f"Base vectorielle indisponible. {exc}"}, 503)

    app.include_router(router)
    return app


app = create_app()
=======

from fastapi import FastAPI, HTTPException

from backend.app.models import SearchRequest, SearchResponse, SourceItem
from backend.app.services.retrieval import RetrievalService

app = FastAPI(
    title="Assistant Scolarité RAG",
    description="Assistant documentaire de l'École.",
    version="0.1.0",
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def search_documents(request: SearchRequest):
    try:
        retrieval = RetrievalService()

        results = retrieval.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )

        sources = [
            SourceItem(
                source=item["metadata"].get("source", "Inconnu"),
                page=int(item["metadata"].get("page", 1)),
                text=item["text"],
                score=(
                    float(item["score"])
                    if item["score"] is not None
                    else None
                ),
                metadata=item["metadata"],
            )
            for item in results
        ]

        return SearchResponse(
            query=request.query,
            results=sources,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur pendant la recherche : {exc}",
        ) from exc
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
