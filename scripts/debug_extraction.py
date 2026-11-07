"""Affiche ce que l'extraction comprend de chaque PDF (titres, tableaux, métadonnées).

    python scripts/debug_extraction.py            # résumé
    python scripts/debug_extraction.py 07         # détail d'un document (préfixe du nom)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import get_settings  # noqa: E402
from backend.app.services.extraction import extract_corpus  # noqa: E402

docs = extract_corpus(get_settings().corpus_dir)
wanted = sys.argv[1] if len(sys.argv) > 1 else None
for d in docs:
    m = d.metadata
    print(f"{d.file}: {m['reference']} | {m['type']} | {m['date']} | v{m['version']} | "
          f"modifie {m['modifies']} | modifié par {m['modified_by']} | {len(d.blocks)} blocs")
    if wanted and d.file.startswith(wanted):
        for b in d.blocks:
            print(f"   p{b.page} {b.kind:<9} L{b.level} {b.text[:110]}")
