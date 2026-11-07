"""Évaluation reproductible du système RAG (section 7 de l'énoncé).

    # 0. vérifier que chaque « gold » du jeu de test existe bien dans le corpus
    python eval/run_eval.py --check-gold

    # 1. recherche seule (rapide, sans LLM) : Hit@k, MRR, calibrage du seuil
    python eval/run_eval.py --configs fixed:500:100:3 fixed:500:100:8 structural:1000:100:3 structural:1000:100:8 --sweep

    # 2. avec génération (appelle le LLM du .env) : exactitude, fidélité, taux de refus
    python eval/run_eval.py --configs fixed:500:100:5 structural:1000:100:5 --generate

Format d'une configuration : strategie:taille:chevauchement:k
Les résultats sont écrits dans eval/results/<date>/ (report.md, summary.json,
details.jsonl, manual_grading.csv pour la notation manuelle 0-2).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings  # noqa: E402
from backend.app.services.chunking import chunk_document  # noqa: E402
from backend.app.services.container import build_container  # noqa: E402
from backend.app.services.embeddings import build_embedder  # noqa: E402
from backend.app.services.extraction import extract_corpus  # noqa: E402
from backend.app.services.generation import check_citations  # noqa: E402
from backend.app.services.ingestion import ingest_corpus  # noqa: E402

CATEGORIES = ["simple", "synthese", "version", "hors_corpus"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower().replace("’", "'").replace("\u00a0", " "))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def load_questions(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def parse_config(spec: str) -> dict:
    strategy, size, overlap, k = spec.split(":")
    return {"strategy": strategy, "size": int(size), "overlap": int(overlap), "k": int(k),
            "name": f"{strategy}-{size}-{overlap}-k{k}"}


# ------------------------------------------------------------------ gold
def chunk_matches(item: dict, meta: dict, text: str) -> bool:
    refs = item["reference"] if isinstance(item["reference"], list) else [item["reference"]]
    return meta.get("reference") in refs and all(norm(c) in norm(text) for c in item["contains"])


def check_gold(questions: list[dict], settings) -> int:
    docs = extract_corpus(settings.corpus_dir)
    bad = 0
    for strat, size, ov in (("fixed", 500, 100), ("structural", 1000, 100)):
        chunks = [c for d in docs for c in chunk_document(d, strat, size, ov)]
        for q in questions:
            for item in q["gold"]:
                if not any(chunk_matches(item, c.metadata, c.text) for c in chunks):
                    bad += 1
                    print(f"  ✗ {q['id']} [{strat}] introuvable : {item}")
    print("gold OK : tous les passages attendus existent dans le corpus." if not bad
          else f"{bad} élément(s) gold à corriger (le texte coupé entre deux fragments est normal "
               "en découpage fixe : voir le rapport).")
    return bad


# ------------------------------------------------------------- recherche
def retrieval_metrics(hits: list[dict], gold: list[dict], k: int) -> dict:
    ranks = []   # rang (1-based) du premier fragment pertinent pour chaque élément gold
    for item in gold:
        r = next((i for i, h in enumerate(hits, 1)
                  if chunk_matches(item, h["metadata"], h["text"])), None)
        ranks.append(r)
    found = [r for r in ranks if r]
    first = min(found) if found else None
    return {
        "first_rank": first,
        "hit@1": bool(first and first <= 1), "hit@3": bool(first and first <= 3),
        "hit@5": bool(first and first <= 5), "hit@k": bool(first and first <= k),
        "coverage@k": sum(1 for r in ranks if r and r <= k) / len(ranks),
        "rr": (1 / first) if first else 0.0,
    }


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


# ------------------------------------------------------------ génération
def exactness(answer: str, facts: list[str], found: bool) -> int:
    """0/1/2 automatique : 2 = tous les faits attendus, 1 = au moins la moitié, 0 sinon.
    Un fait « a|b » est satisfait par l'une de ses variantes."""
    if not found or not facts:
        return 0
    a = norm(answer)
    ok = sum(any(norm(v) in a for v in f.split("|")) for f in facts)
    return 2 if ok == len(facts) else (1 if ok / len(facts) >= 0.5 else 0)


def build_index(cfg: dict, settings, embedder, llm, storage: Path):
    c = build_container(settings, embedder=embedder, llm=llm,
                        collection_name=f"eval_{cfg['strategy']}_{cfg['size']}_{cfg['overlap']}",
                        storage_dir=storage)
    t = time.time()
    r = ingest_corpus(settings, c.store, embedder, cfg["strategy"], cfg["size"], cfg["overlap"])
    print(f"  index {cfg['strategy']} {cfg['size']}/{cfg['overlap']} : {r['chunks']} fragments "
          f"({time.time() - t:.0f}s)")
    return c, r["chunks"]


def run_config(cfg, questions, settings, embedder, llm, storage, generate, sleep):
    c, n_chunks = build_index(cfg, settings, embedder, llm, storage)
    rows = []
    for q in questions:
        hits = c.retrieval.search(q["question"], max(cfg["k"], 10))
        row = {"id": q["id"], "category": q["category"], "question": q["question"],
               "best_score": hits[0]["score"] if hits else None, "config": cfg["name"]}
        if q["in_corpus"]:
            row.update(retrieval_metrics(hits, q["gold"], cfg["k"]))
        if generate:
            if sleep:
                time.sleep(sleep)
            res = c.rag.ask(q["question"], cfg["k"])
            refs = {p["metadata"]["reference"] for p in res.passages}
            _, invalid = check_citations(res.answer, len(res.passages)) if res.found else ([], [])
            cited = bool(re.search(r"\[\d+", res.answer)) if res.found else False
            row.update({
                "answer": res.answer, "found": res.found, "refused_by": res.refused_by,
                "invalid_citations": invalid, "has_citation": cited,
                "exactitude_auto": exactness(res.answer, q["expected_facts"], res.found)
                if q["in_corpus"] else (2 if not res.found else 0),
                "latency_ms": res.latency_ms,
                "sources": sorted(refs),
                "uses_latest": (q.get("newer_ref") in refs) if q.get("newer_ref") else None,
            })
        rows.append(row)
    return rows, n_chunks


def summarize(rows: list[dict], generate: bool) -> dict:
    inc = [r for r in rows if r["category"] != "hors_corpus"]
    out = [r for r in rows if r["category"] == "hors_corpus"]
    s = {"n_questions": len(rows),
         "retrieval": {m: mean(r[m] for r in inc) for m in
                       ("hit@1", "hit@3", "hit@5", "hit@k", "coverage@k", "rr")}}
    s["retrieval"]["MRR"] = s["retrieval"].pop("rr")
    s["retrieval_by_category"] = {
        cat: {"hit@k": mean(r["hit@k"] for r in inc if r["category"] == cat),
              "MRR": mean(r["rr"] for r in inc if r["category"] == cat)}
        for cat in CATEGORIES[:3]}
    if generate:
        found = [r for r in inc if r["found"]]
        s["generation"] = {
            "exactitude_moy_/2": mean(r["exactitude_auto"] for r in inc),
            "fidelite_auto": mean(r["has_citation"] and not r["invalid_citations"] for r in found),
            "taux_refus_correct": mean(not r["found"] for r in out),
            "taux_refus_a_tort": mean(not r["found"] for r in inc),
            "version_utilise_la_plus_recente": mean(
                r["uses_latest"] for r in rows if r.get("uses_latest") is not None),
            "latence_moy_ms": mean(r["latency_ms"] for r in rows),
        }
    return s


def fmt(x):
    return "—" if x is None or x != x else f"{x:.2f}"


def sweep(rows_by_cfg: dict):
    """Calibrage du seuil : meilleur score de chaque question, dans/hors corpus."""
    name, rows = next(iter(rows_by_cfg.items()))
    ins = sorted(r["best_score"] for r in rows if r["category"] != "hors_corpus")
    outs = sorted(r["best_score"] for r in rows if r["category"] == "hors_corpus")
    print(f"\nCalibrage du seuil ({name})")
    print(f"  meilleur score, questions DANS le corpus : min {ins[0]:.3f} · médiane {ins[len(ins)//2]:.3f}")
    print(f"  meilleur score, questions HORS corpus    : médiane {outs[len(outs)//2]:.3f} · max {outs[-1]:.3f}")
    print("  seuil | refus à tort (dans corpus) | refus correct (hors corpus)")
    best = 0.0
    for i in range(0, 21):
        th = i * 0.05
        fr = mean(s < th for s in ins)
        cr = mean(s < th for s in outs)
        if fr == 0:
            best = th
        print(f"  {th:.2f}  |        {fr:6.0%}              |        {cr:6.0%}")
    print(f"  -> plus grand seuil sans refus à tort : {best:.2f} "
          "(à reporter dans SIMILARITY_THRESHOLD du .env)")
    print("  Le seuil sert de garde-fou grossier ; les cas ambigus sont traités par le prompt (refus du LLM).")


def write_report(outdir: Path, summaries: dict, all_rows: list[dict], generate: bool):
    L = ["# Rapport d'évaluation", f"\nDate : {datetime.now():%Y-%m-%d %H:%M}\n",
         "## Recherche (questions dans le corpus)\n",
         "| Configuration | Fragments | Hit@1 | Hit@3 | Hit@5 | Hit@k | Couverture@k | MRR |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, (s, n) in summaries.items():
        r = s["retrieval"]
        L.append(f"| {name} | {n} | {fmt(r['hit@1'])} | {fmt(r['hit@3'])} | {fmt(r['hit@5'])} | "
                 f"{fmt(r['hit@k'])} | {fmt(r['coverage@k'])} | {fmt(r['MRR'])} |")
    L += ["\n### Hit@k par catégorie\n", "| Configuration | simple | synthèse | version |", "|---|---:|---:|---:|"]
    for name, (s, _) in summaries.items():
        b = s["retrieval_by_category"]
        L.append(f"| {name} | " + " | ".join(fmt(b[c]["hit@k"]) for c in CATEGORIES[:3]) + " |")
    if generate:
        L += ["\n## Génération\n",
              "| Configuration | Exactitude moy. (/2) | Fidélité | Refus correct | Refus à tort | Version récente | Latence (ms) |",
              "|---|---:|---:|---:|---:|---:|---:|"]
        for name, (s, _) in summaries.items():
            g = s["generation"]
            L.append(f"| {name} | {fmt(g['exactitude_moy_/2'])} | {fmt(g['fidelite_auto'])} | "
                     f"{fmt(g['taux_refus_correct'])} | {fmt(g['taux_refus_a_tort'])} | "
                     f"{fmt(g['version_utilise_la_plus_recente'])} | {g['latence_moy_ms']:.0f} |")
    L.append("\n## Échecs de recherche (à expliquer dans le rapport)\n")
    for r in all_rows:
        if r["category"] != "hors_corpus" and not r["hit@k"]:
            L.append(f"- **{r['config']}** · {r['id']} : « {r['question']} » — premier fragment "
                     f"pertinent au rang {r['first_rank'] or 'absent'}")
    (outdir / "report.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--questions", default=str(ROOT / "eval" / "questions.jsonl"))
    ap.add_argument("--configs", nargs="+", default=["structural:1000:100:5"])
    ap.add_argument("--generate", action="store_true", help="appelle aussi le LLM")
    ap.add_argument("--sweep", action="store_true", help="calibrage du seuil de score")
    ap.add_argument("--check-gold", action="store_true")
    ap.add_argument("--sleep", type=float, default=None,
                    help="pause entre appels LLM (défaut 4 s avec Gemini, quota gratuit)")
    a = ap.parse_args()

    settings = get_settings()
    questions = load_questions(Path(a.questions))
    if a.check_gold:
        sys.exit(1 if check_gold(questions, settings) else 0)

    sleep = a.sleep if a.sleep is not None else (4.0 if settings.llm_provider == "gemini" else 0)
    embedder = build_embedder(settings)
    from backend.app.services.llm import build_llm
    llm = build_llm(settings) if a.generate else None
    storage = settings.storage_dir / "eval_chroma"

    summaries, all_rows, by_cfg = {}, [], {}
    print(f"{len(questions)} questions · embeddings : {getattr(embedder, 'model_name', '?')}"
          + (f" · LLM : {settings.llm_provider}" if a.generate else " · recherche seule"))
    for spec in a.configs:
        cfg = parse_config(spec)
        rows, n = run_config(cfg, questions, settings, embedder, llm, storage, a.generate, sleep)
        summaries[cfg["name"]] = (summarize(rows, a.generate), n)
        by_cfg[cfg["name"]] = rows
        all_rows += rows

    outdir = ROOT / "eval" / "results" / datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir.mkdir(parents=True, exist_ok=True)
    write_report(outdir, summaries, all_rows, a.generate)
    (outdir / "summary.json").write_text(json.dumps(
        {k: {"chunks": n, **s} for k, (s, n) in summaries.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    with (outdir / "details.jsonl").open("w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if a.generate:
        with (outdir / "manual_grading.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["config", "id", "question", "reponse", "exactitude_auto",
                        "exactitude_manuelle_0-2", "fidelite_manuelle_0-2", "commentaire"])
            for r in all_rows:
                w.writerow([r["config"], r["id"], r["question"], r.get("answer", ""),
                            r.get("exactitude_auto", ""), "", "", ""])
    print("\n" + (outdir / "report.md").read_text(encoding="utf-8"))
    if a.sweep:
        sweep(by_cfg)
    print(f"\nRésultats écrits dans {outdir}")


if __name__ == "__main__":
    main()
