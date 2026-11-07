<<<<<<< HEAD
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
=======
import json
from pathlib import Path
from backend.app.config import CORPUS_DIR

from backend.app.services.extraction import extract_corpus
from backend.app.services.chunking import (
    fixed_size_chunking,
    structural_chunking,
)

# Dossier du projet
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "data" / "processed"

# Créer le dossier de sortie s'il n'existe pas
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_json(chunks: list[dict], filename: str) -> None:
    """Enregistre les fragments et leurs métadonnées dans un fichier JSON."""
    output_path = OUTPUT_DIR / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            chunks,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Fichier créé : {output_path}")
    print(f"Nombre de fragments : {len(chunks)}")


def main() -> None:
    # 1. Extraire le texte des PDF
    pages = extract_corpus(CORPUS_DIR)
    print(f"Nombre de pages extraites : {len(pages)}")

    # 2. Découper le texte selon les deux stratégies
    chunks_structural = structural_chunking(pages)
    chunks_fixed = fixed_size_chunking(
        pages,
        chunk_size=800,
        overlap=150,
    )

    # 3. Exporter les fragments au format JSON
    save_json(chunks_structural, "chunks_structural.json")
    save_json(chunks_fixed, "chunks_fixed.json")


if __name__ == "__main__":
    main()
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
