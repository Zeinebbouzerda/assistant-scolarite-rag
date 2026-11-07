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
