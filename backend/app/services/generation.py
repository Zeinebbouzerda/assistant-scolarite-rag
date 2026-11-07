"""Génération de la réponse et contrôles côté code (exigences 4.4)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from backend.app.errors import LLMUnavailable
from backend.app.services.llm import LLMClient
from backend.app.services.prompts import REFUSAL, SYSTEM_PROMPT, build_user_prompt
from backend.app.services.retrieval import RetrievalService
from backend.app.services.vector_store import VectorStore

_CITATION_RE = re.compile(r"\[([\d\s,;]+)\]")


def extract_citations(answer: str) -> list[int]:
    """Numéros cités, dans l'ordre : « [1] », « [1][3] », « [1, 3] »."""
    nums: list[int] = []
    for m in _CITATION_RE.finditer(answer):
        nums += [int(n) for n in re.findall(r"\d+", m.group(1))]
    return nums


def check_citations(answer: str, n_passages: int) -> tuple[list[int], list[int]]:
    """Renvoie (numéros valides, numéros invalides). Un numéro est valide s'il
    correspond à l'un des fragments réellement fournis au modèle."""
    cited = extract_citations(answer)
    valid = sorted({n for n in cited if 1 <= n <= n_passages})
    invalid = sorted({n for n in cited if not 1 <= n <= n_passages})
    return valid, invalid


def is_refusal(answer: str) -> bool:
    """Vrai si le modèle a répondu (quasi) uniquement par la phrase de refus."""
    core = answer.strip().strip("«»\"' ").strip()
    return core.startswith(REFUSAL) and len(core) <= len(REFUSAL) + 5


@dataclass
class AskResult:
    answer: str
    found: bool
    passages: list[dict] = field(default_factory=list)
    invalid_citations: list[int] = field(default_factory=list)
    refused_by: str | None = None      # "threshold" | "llm" | "empty" | None
    best_score: float | None = None
    latency_ms: int = 0


class RagPipeline:
    """recherche top-k -> seuil -> (extension modificative) -> prompt -> LLM -> contrôles"""

    def __init__(self, retrieval: RetrievalService, store: VectorStore,
                 llm: LLMClient, settings):
        self.retrieval, self.store, self.llm, self.settings = retrieval, store, llm, settings

    def ask(self, question: str, top_k: int | None = None,
            filters: dict | None = None) -> AskResult:
        t0 = time.perf_counter()

        def done(**kw) -> AskResult:
            return AskResult(latency_ms=int((time.perf_counter() - t0) * 1000), **kw)

        hits = self.retrieval.search(question, top_k, filters)
        if not hits:
            return done(answer=REFUSAL, found=False, refused_by="empty")
        best = hits[0]["score"]

        # Contrôle 1 : seuil de score. En dessous, on refuse SANS appeler le LLM.
        if best is None or best < self.settings.similarity_threshold:
            return done(answer=REFUSAL, found=False, refused_by="threshold", best_score=best)

        passages = hits
        if self.settings.expand_modifications:
            passages = self.retrieval.expand_with_modifications(question, hits, filters)

        registry = {d["reference"]: d for d in self.store.documents()}
        prompt = build_user_prompt(question, passages, registry)
        answer = self.llm.generate(SYSTEM_PROMPT, prompt)      # peut lever LLMUnavailable
        if not answer or not answer.strip():
            raise LLMUnavailable("Le modèle a renvoyé une réponse vide.")
        answer = answer.strip()

        if is_refusal(answer):
            return done(answer=REFUSAL, found=False, refused_by="llm", best_score=best)

        # Contrôle 2 : chaque numéro cité doit correspondre à un fragment fourni.
        _, invalid = check_citations(answer, len(passages))
        return done(answer=answer, found=True, passages=passages,
                    invalid_citations=invalid, best_score=best)
