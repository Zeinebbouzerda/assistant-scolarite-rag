<<<<<<< HEAD
"""Calcul des embeddings.

* EmbeddingService      : modèle sentence-transformers réel (multilingue).
                          Le modèle n'est chargé qu'au premier appel, pour que
                          le démarrage de l'API et /api/health restent rapides.
* HashEmbeddingService  : embeddings lexicaux déterministes, sans réseau ni
                          modèle. Réservé aux TESTS AUTOMATIQUES : il ne
                          comprend pas le sens, seulement les mots communs.
"""
from __future__ import annotations

import math
import re
import unicodedata
import zlib


class EmbeddingService:
    def __init__(self, model_name: str, max_seq_length: int | None = None):
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        self._model = None
        # Les modèles E5 attendent des préfixes « query: » / « passage: ».
        self._is_e5 = "e5" in model_name.lower()

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            if self.max_seq_length:
                self._model.max_seq_length = self.max_seq_length
        return self._model

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        if self._is_e5:
            texts = [f"passage: {t}" for t in texts]
        vectors = self._load().encode(
            texts, normalize_embeddings=True, batch_size=32,
            show_progress_bar=len(texts) > 20,
=======

from sentence_transformers import SentenceTransformer

from backend.app.config import EMBEDDING_MODEL


class EmbeddingService:
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model = SentenceTransformer(model_name)

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
        )
        return vectors.tolist()

    def encode_query(self, query: str) -> list[float]:
<<<<<<< HEAD
        if self._is_e5:
            query = f"query: {query}"
        return self._load().encode([query], normalize_embeddings=True,
                                   show_progress_bar=False)[0].tolist()


_STOP = set("""a au aux avec ce ces cette dans de des du elle en et il ils je la le les leur lui
ma mais me mon ne ni nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te
tes toi ton tu un une vos votre vous est sont etre faut doit peut y c d l n s t""".split())


def _tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in _STOP]


class HashEmbeddingService:
    model_name = "hash-lexical-test"

    def __init__(self, dim: int = 2048):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        toks = [w[:5] for w in _tokens(text)]      # « racinisation » grossière
        counts: dict[int, float] = {}
        for i, w in enumerate(toks):
            h = zlib.crc32(w.encode()) % self.dim
            counts[h] = counts.get(h, 0) + 1
            if i:
                hb = zlib.crc32(f"{toks[i - 1]}_{w}".encode()) % self.dim
                counts[hb] = counts.get(hb, 0) + 0.6
        vec = [0.0] * self.dim
        for h, c in counts.items():
            vec[h] = 1 + math.log(c) if c >= 1 else c
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def encode_query(self, query: str) -> list[float]:
        return self._vec(query)


def build_embedder(settings):
    if settings.embedding_backend == "hash":
        return HashEmbeddingService()
    return EmbeddingService(settings.embedding_model, settings.embedding_max_seq_length)
=======
        vector = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector[0].tolist()
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
