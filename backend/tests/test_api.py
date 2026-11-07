import pytest

from backend.app.errors import LLMUnavailable
from backend.app.services.llm import FakeLLM

REFUSAL = "Je ne trouve pas cette information dans les documents de l'École."


def test_ingest_is_idempotent(client, container):
    first = client.post("/api/ingest", json={"strategy": "structural"}).json()
    n1 = container.store.count()
    second = client.post("/api/ingest", json={"strategy": "structural"}).json()
    assert n1 == container.store.count() == first["chunks"] == second["chunks"]
    # changer de stratégie REMPLACE les fragments au lieu de les ajouter
    fixed = client.post("/api/ingest", json={"strategy": "fixed", "chunk_size": 500,
                                             "chunk_overlap": 100}).json()
    assert container.store.count() == fixed["chunks"]


@pytest.mark.parametrize("body", [
    {"strategy": "magic"}, {"strategy": "fixed", "chunk_size": 200, "chunk_overlap": 200},
    {"chunk_size": 10},
])
def test_ingest_rejects_invalid_params_with_422(client, body):
    assert client.post("/api/ingest", json=body).status_code == 422


def test_health_and_documents(client, indexed):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["chunks"] == indexed.store.count() > 0
    docs = client.get("/api/documents").json()
    assert len(docs) == 7 and all(d["chunks"] > 0 for d in docs)
    ns = next(d for d in docs if d["reference"] == "EIH-DE-NS-2026-14")
    assert ns["modifies"] == ["EIH-SRE-GUIDE-2026"]


def test_health_returns_503_when_store_is_down(client, container, monkeypatch):
    monkeypatch.setattr(container.store, "count", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    assert client.get("/api/health").status_code == 503


def test_empty_question_is_rejected_with_422(client, indexed):
    assert client.post("/api/search", json={"question": "   "}).status_code == 422
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.post("/api/ask", json={"question": "ok", "top_k": 0}).status_code == 422


def test_search_returns_scored_fragments_and_filters_by_type(client, indexed):
    r = client.post("/api/search", json={"question": "durée minimale du PFE", "top_k": 3}).json()
    assert len(r["results"]) == 3
    scores = [x["score"] for x in r["results"]]
    assert scores == sorted(scores, reverse=True)
    only_faq = client.post("/api/search", json={
        "question": "durée minimale du PFE", "top_k": 5,
        "filters": {"type": "FAQ (questions-réponses)"}}).json()["results"]
    assert only_faq and {x["type"] for x in only_faq} == {"FAQ (questions-réponses)"}


def test_out_of_corpus_question_is_refused_without_calling_the_llm(client, indexed):
    indexed.settings.similarity_threshold = 0.99          # tout est « hors corpus »
    llm = indexed.llm
    r = client.post("/api/ask", json={"question": "Quel est le prix d'un repas ?"}).json()
    assert r["found"] is False and r["answer"] == REFUSAL and r["sources"] == []
    assert llm.calls == 0


def test_llm_refusal_is_normalised(client, indexed):
    indexed.llm.reply = f"« {REFUSAL} »"
    r = client.post("/api/ask", json={"question": "Le stage d'initiation est-il rémunéré ?"}).json()
    assert r["found"] is False and r["answer"] == REFUSAL and r["sources"] == []
    assert indexed.llm.calls == 1


def test_citations_are_checked_against_provided_fragments(client, indexed):
    indexed.llm.reply = "La durée est de 18 semaines [1][2]. Autre fait [99]."
    r = client.post("/api/ask", json={"question": "durée minimale du PFE", "top_k": 3}).json()
    assert r["found"] is True and r["invalid_citations"] == [99]
    assert [s["id"] for s in r["sources"]][:3] == [1, 2, 3]
    assert {"chunk_id", "file", "reference", "date", "page", "section", "excerpt", "score"} <= set(r["sources"][0])


def test_modifying_document_is_always_added_to_the_context(client, indexed):
    """La note de service (plus récente) accompagne le guide qu'elle modifie."""
    indexed.llm.reply = lambda system, prompt: "ok [1]"
    r = client.post("/api/ask", json={"question": "durée minimale du PFE en février 2027",
                                      "top_k": 3}).json()
    refs = {s["reference"] for s in r["sources"]}
    assert "EIH-DE-NS-2026-14" in refs
    assert "CE DOCUMENT A ÉTÉ MODIFIÉ PAR EIH-DE-NS-2026-14" in indexed.llm.last_prompt


def test_llm_failure_returns_502(client, indexed):
    def boom(system, prompt):
        raise LLMUnavailable("panne")
    indexed.llm.reply = boom
    assert client.post("/api/ask", json={"question": "durée minimale du PFE"}).status_code == 502
