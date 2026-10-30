import json
from pathlib import Path

required_keys = {"chunk_id", "text", "metadata", "strategy"}

for path in [
    Path("data/processed/chunks_fixed.json"),
    Path("data/processed/chunks_structural.json"),
]:
    chunks = json.loads(path.read_text(encoding="utf-8"))

    invalid_chunks = []
    missing_source_page = []

    for i, chunk in enumerate(chunks):
        if not required_keys.issubset(chunk.keys()):
            invalid_chunks.append(i)

        metadata = chunk.get("metadata", {})
        if not metadata.get("source") or metadata.get("page") is None:
            missing_source_page.append(i)

    print(f"\n--- {path.name} ---")
    print("Nombre de fragments :", len(chunks))
    print("Fragments avec clés manquantes :", len(invalid_chunks))
    print("Fragments sans source ou page :", len(missing_source_page))
    print("JSON valide : oui")
    