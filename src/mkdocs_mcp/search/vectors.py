"""Optional semantic layer (self-hosted embeddings).

Disabled by default. Enabled via ``MKDOCS_MCP_EMBEDDINGS_ENABLED=true`` + the
``vectors`` extra (sentence-transformers). Self-hosted on purpose so no external
embedding API is required; the default model is multilingual.

Both embedding and similarity search use sentence-transformers' own utilities
(``SentenceTransformer.encode`` + ``util.semantic_search``) rather than any
hand-written vector math. Imported lazily so the core server never pays for the
heavy dependency.
"""

from __future__ import annotations

from ..obs.logging import get_logger

log = get_logger(__name__)


class VectorIndex:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        self._embeddings = None  # torch.Tensor [n, dim], normalized
        self._util = None

    @property
    def enabled(self) -> bool:
        return self._embeddings is not None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer, util  # noqa: PLC0415

        self._util = util
        log.info("loading_embedding_model", model=self.model_name)
        self._model = SentenceTransformer(self.model_name)

    def build(self, texts: list[str]) -> None:
        if not texts:
            return
        try:
            self._ensure_model()
        except Exception as exc:  # noqa: BLE001 - missing extra / model
            log.warning("vectors_disabled", error=str(exc))
            self._embeddings = None
            return
        self._embeddings = self._model.encode(
            texts, normalize_embeddings=True, convert_to_tensor=True, show_progress_bar=False
        )

    def search(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        if not self.enabled:
            return []
        q = self._model.encode([query], normalize_embeddings=True, convert_to_tensor=True)
        hits = self._util.semantic_search(q, self._embeddings, top_k=top_k)[0]
        return [(h["corpus_id"], float(h["score"])) for h in hits]
