from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.core.config import Settings
from app.core.resilience import CircuitBreaker


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = SentenceTransformer(settings.embedding_model_name)
        self.circuit = CircuitBreaker(
            failure_threshold=max(settings.circuit_failure_threshold, 1),
            recovery_seconds=max(settings.circuit_recovery_seconds, 1),
        )

    def embed_text(self, text: str) -> list[float]:
        if not self.circuit.allow():
            raise RuntimeError("Embedding circuit breaker open")
        try:
            vector = self.model.encode(text, normalize_embeddings=True)
            self.circuit.record_success()
            return vector.tolist()
        except Exception:
            self.circuit.record_failure()
            raise

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        if not self.circuit.allow():
            raise RuntimeError("Embedding circuit breaker open")
        try:
            vectors = self.model.encode(chunks, normalize_embeddings=True)
            self.circuit.record_success()
            return [v.tolist() for v in vectors]
        except Exception:
            self.circuit.record_failure()
            raise
