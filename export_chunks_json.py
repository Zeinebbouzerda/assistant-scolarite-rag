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