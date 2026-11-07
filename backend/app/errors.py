"""Exceptions métier, converties en codes HTTP dans main.py."""


class LLMUnavailable(RuntimeError):
    """Le modèle de langage ne répond pas (clé absente, réseau, quota...) -> HTTP 502."""


class VectorStoreUnavailable(RuntimeError):
    """La base vectorielle est inaccessible -> HTTP 503."""
