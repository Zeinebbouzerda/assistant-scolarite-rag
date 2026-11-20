"""Séance 1 : exporte les fragments et leurs métadonnées en JSON (sans embeddings).

    python export_chunks_json.py
"""
import json

from backend.app.config import BASE_DIR, get_settings
from backend.app.services.chunking import chunk_document
from backend.app.services.extraction import extract_corpus

OUTPUT_DIR = BASE_DIR / "data" / "processed"
CONFIGS = {"chunks_fixed.json": ("fixed", 500, 100),
           "chunks_structural.json": ("structural", 1000, 100)}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    docs = extract_corpus(get_settings().corpus_dir)
    print(f"Documents extraits : {len(docs)}")
    for filename, (strategy, size, overlap) in CONFIGS.items():
        chunks = [c.to_dict() for d in docs for c in chunk_document(d, strategy, size, overlap)]
        (OUTPUT_DIR / filename).write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{filename}: {len(chunks)} fragments ({strategy}, {size}/{overlap})")


if __name__ == "__main__":
    main()
