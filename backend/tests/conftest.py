"""Fixtures : base Chroma temporaire, embeddings lexicaux, faux LLM (aucun réseau)."""
import pytest
from fastapi.testclient import TestClient

from backend.app.api import container_dep
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.container import build_container
from backend.app.services.embeddings import HashEmbeddingService
from backend.app.services.llm import FakeLLM
from backend.app.services.ingestion import ingest_corpus

REFUSAL = "Je ne trouve pas cette information dans les documents de l'École."


@pytest.fixture(scope="session", autouse=True)
def cached_extraction():
    """L'extraction des 7 PDF est lente : on la fait une seule fois pour toute la session."""
    import backend.app.services.ingestion as ing
    real, cache = ing.extract_corpus, {}
    ing.extract_corpus = lambda d: cache.setdefault(str(d), real(d))
    yield
    ing.extract_corpus = real


@pytest.fixture
def settings(tmp_path):
    return Settings(storage_dir=tmp_path, embedding_backend="hash", llm_provider="fake",
                    similarity_threshold=0.15, _env_file=None)


@pytest.fixture
def container(settings):
    return build_container(settings, embedder=HashEmbeddingService(), llm=FakeLLM(),
                           collection_name="test", storage_dir=settings.storage_dir / "chroma")


@pytest.fixture
def client(container):
    app = create_app()
    app.dependency_overrides[container_dep] = lambda: container
    return TestClient(app)


@pytest.fixture
def indexed(container):
    ingest_corpus(container.settings, container.store, container.embedder, "structural")
    return container
