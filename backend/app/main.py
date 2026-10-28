
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
