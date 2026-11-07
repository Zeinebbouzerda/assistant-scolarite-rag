<<<<<<< HEAD
"""Configuration centrale de l'application.

Toutes les valeurs peuvent être surchargées par des variables d'environnement
ou par le fichier `.env` placé à la racine du projet (jamais versionné).
Les noms GEMINI_API_KEY et GEMINI_MODEL sont ceux déjà utilisés dans le projet.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du projet (le dossier qui contient backend/, data/, eval/, frontend/)
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Données -----------------------------------------------------------
    corpus_dir: Path = BASE_DIR / "data" / "corpus"
    storage_dir: Path = BASE_DIR / "storage"
    collection_name: str = "assistant_scolarite"

    # --- Embeddings --------------------------------------------------------
    # "sentence-transformers" : modèle réel (production)
    # "hash"                  : embeddings lexicaux déterministes, SANS
    #                           téléchargement, réservés aux tests automatiques
    embedding_backend: Literal["sentence-transformers", "hash"] = "sentence-transformers"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # MiniLM est entraîné sur 128 tokens, mais nos fragments en font ~250 :
    # sans ce réglage, la fin de chaque fragment serait ignorée à l'encodage.
    embedding_max_seq_length: int = 384

    # --- LLM ---------------------------------------------------------------
    llm_provider: Literal["gemini", "ollama", "fake"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    llm_timeout_s: float = 60.0

    # --- Recherche / génération ---------------------------------------------
    default_top_k: int = 5
    # Score cosinus minimal du meilleur fragment ; en dessous, l'API refuse
    # SANS appeler le LLM. À calibrer avec eval/run_eval.py --sweep.
    similarity_threshold: float = 0.35
    # Si un fragment provient d'un document modifié par un autre, on ajoute
    # automatiquement les meilleurs fragments du document modificatif.
    expand_modifications: bool = True
    expansion_per_doc: int = 2

    # --- Découpage par défaut (surchargeable via POST /api/ingest) ---------
    fixed_chunk_size: int = 500
    fixed_chunk_overlap: int = 100
    structural_chunk_size: int = 1000
    structural_chunk_overlap: int = 100

    # --- Web ---------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
=======

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
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
