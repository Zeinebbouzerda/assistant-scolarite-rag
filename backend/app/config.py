
from pathlib import Path

# Racine du projet
BASE_DIR = Path(__file__).resolve().parents[2]

# Dossier contenant les documents PDF
CORPUS_DIR = BASE_DIR / "data" / "corpus"

# Dossier de stockage de la base vectorielle
STORAGE_DIR = BASE_DIR / "storage"

# Paramètres de recherche
DEFAULT_TOP_K = 5
SIMILARITY_THRESHOLD = 0.35

# Modèle d'embeddings multilingue
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Créer les dossiers nécessaires s'ils n'existent pas
CORPUS_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
