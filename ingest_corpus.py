
import argparse

from backend.app.config import CORPUS_DIR
from backend.app.services.extraction import extract_corpus
from backend.app.services.chunking import (
    fixed_size_chunking,
    structural_chunking,
)
from backend.app.services.embeddings import EmbeddingService
from backend.app.services.vector_store import VectorStore


def main():
    parser = argparse.ArgumentParser(
        description="Indexer les PDF dans ChromaDB."
    )
    parser.add_argument(
        "--strategy",
        choices=["structural", "fixed"],
        default="structural",
        help="Stratégie de découpage à utiliser.",
    )
    args = parser.parse_args()

    print(f"Corpus : {CORPUS_DIR}")

    pages = extract_corpus(CORPUS_DIR)

    if not pages:
        raise RuntimeError(
            "Aucun PDF trouvé. Vérifie le dossier du corpus."
        )

    if args.strategy == "fixed":
        chunks = fixed_size_chunking(pages)
    else:
        chunks = structural_chunking(pages)

    if not chunks:
        raise RuntimeError("Aucun chunk créé à partir des PDF.")

    print(f"\nPages extraites : {len(pages)}")
    print(f"Chunks créés : {len(chunks)}")
    print("Calcul des embeddings...")

    embedding_service = EmbeddingService()
    embeddings = embedding_service.encode_documents(
        [chunk["text"] for chunk in chunks]
    )

    vector_store = VectorStore()
    collection = vector_store.collection

    # Indexer les nouveaux chunks.
    vector_store.upsert_chunks(chunks, embeddings)

    # Supprimer les anciens chunks qui ne font plus partie
    # du corpus courant ou de la stratégie sélectionnée.
    expected_ids = {chunk["chunk_id"] for chunk in chunks}
    existing_ids = collection.get()["ids"]
    stale_ids = [
        chunk_id
        for chunk_id in existing_ids
        if chunk_id not in expected_ids
    ]

    if stale_ids:
        collection.delete(ids=stale_ids)

    print("\nIndexation terminée avec succès.")
    print(f"Stratégie : {args.strategy}")
    print(f"Chunks indexés : {len(chunks)}")
    print(f"Chunks présents dans ChromaDB : {collection.count()}")


if __name__ == "__main__":
    main()
