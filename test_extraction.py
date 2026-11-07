
from backend.app.config import CORPUS_DIR
from backend.app.services.extraction import extract_corpus
from backend.app.services.chunking import (
    fixed_size_chunking,
    structural_chunking,
)


def main():
    pages = extract_corpus(CORPUS_DIR)

    if not pages:
        print("Aucune page extraite. Vérifie que les PDF sont présents.")
        return

    print(f"\nNombre de pages extraites : {len(pages)}")

    for page in pages[:3]:
        print(f"\nDocument : {page['source']}")
        print(f"Page : {page['page']}")
        print(f"Texte : {page['text'][:200]}")

    fixed_chunks = fixed_size_chunking(pages)
    structural_chunks = structural_chunking(pages)

    print(f"\nChunks à taille fixe : {len(fixed_chunks)}")
    print(f"Chunks structurels : {len(structural_chunks)}")


if __name__ == "__main__":
    main()
