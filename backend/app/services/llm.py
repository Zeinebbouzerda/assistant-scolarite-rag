"""Clients LLM. Toute panne est convertie en LLMUnavailable (-> HTTP 502).

Les clés viennent de l'environnement (.env) : jamais dans le dépôt, jamais
côté navigateur.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable

import httpx

from backend.app.errors import LLMUnavailable


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system: str, prompt: str) -> str: ...


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str, timeout_s: float = 60, retries: int = 2):
        self.api_key, self.model = api_key, model
        self.timeout_s, self.retries = timeout_s, retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=int(self.timeout_s * 1000)),
            )
        return self._client

    def generate(self, system: str, prompt: str) -> str:
        if not self.api_key:
            raise LLMUnavailable("GEMINI_API_KEY est absente du fichier .env.")
        from google.genai import types
        config = types.GenerateContentConfig(system_instruction=system, temperature=0.0)
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = self._get_client().models.generate_content(
                    model=self.model, contents=prompt, config=config)
                text = (resp.text or "").strip()
                if text:
                    return text
                last = RuntimeError("réponse vide")
            except Exception as exc:          # quota 429, réseau, 5xx...
                last = exc
            time.sleep(1.5 * (attempt + 1))
        raise LLMUnavailable(f"Gemini ne répond pas : {last}")


class OllamaClient(LLMClient):
    def __init__(self, url: str, model: str, timeout_s: float = 120):
        self.url, self.model, self.timeout_s = url.rstrip("/"), model, timeout_s

    def generate(self, system: str, prompt: str) -> str:
        body = {"model": self.model, "stream": False, "options": {"temperature": 0},
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": prompt}]}
        try:
            r = httpx.post(f"{self.url}/api/chat", json=body, timeout=self.timeout_s)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        except Exception as exc:
            raise LLMUnavailable(f"Ollama ne répond pas : {exc}") from exc


class FakeLLM(LLMClient):
    """LLM de test : renvoie une réponse fixe (ou calculée) et compte les appels."""

    def __init__(self, reply: str | Callable[[str, str], str] = "Réponse de test [1]."):
        self.reply, self.calls, self.last_prompt = reply, 0, ""

    def generate(self, system: str, prompt: str) -> str:
        self.calls += 1
        self.last_prompt = prompt
        return self.reply(system, prompt) if callable(self.reply) else self.reply


def build_llm(settings) -> LLMClient:
    if settings.llm_provider == "gemini":
        return GeminiClient(settings.gemini_api_key, settings.gemini_model,
                            settings.llm_timeout_s)
    if settings.llm_provider == "ollama":
        return OllamaClient(settings.ollama_url, settings.ollama_model,
                            settings.llm_timeout_s)
    return FakeLLM()
