"""Indexation en ligne de commande (équivalent de POST /api/ingest).

    python ingest_corpus.py --strategy structural
    python ingest_corpus.py --strategy fixed --size 500 --overlap 100
"""
import argparse

from backend.app.config import get_settings
from backend.app.services.container import build_container
from backend.app.services.ingestion import ingest_corpus


def main() -> None:
    p = argparse.ArgumentParser(description="Indexer les PDF dans ChromaDB.")
    p.add_argument("--strategy", choices=["structural", "fixed"], default="structural")
    p.add_argument("--size", type=int, default=None, help="taille des fragments (caractères)")
    p.add_argument("--overlap", type=int, default=None, help="chevauchement (caractères)")
    a = p.parse_args()

    c = build_container(get_settings())
    print(f"Corpus : {c.settings.corpus_dir}")
    r = ingest_corpus(c.settings, c.store, c.embedder, a.strategy, a.size, a.overlap)
    for d in r["per_document"]:
        print(f"  {d['reference']:<22} {d['chunks']:>3} fragments")
    print(f"\n{r['documents']} documents, {r['chunks']} fragments "
          f"({r['strategy']}, taille {r['chunk_size']}, chevauchement {r['chunk_overlap']}) "
          f"en {r['duration_ms']} ms")
    print(f"Fragments présents dans ChromaDB : {c.store.count()}")


if __name__ == "__main__":
    main()
