import logging

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "allenai/scibert_scivocab_uncased"


class EmbeddingService:
    """
    Lazy-loads SciBERT once per process (class-level singleton).
    Falls back gracefully if the model can't be loaded so the crawler
    still works without the ML dependency present.
    """

    _tokenizer = None
    _model = None
    _available: bool | None = None  # None = not yet checked

    @classmethod
    def _load(cls) -> bool:
        if cls._available is not None:
            return cls._available
        try:
            from transformers import AutoModel, AutoTokenizer

            cls._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            cls._model = AutoModel.from_pretrained(MODEL_NAME)
            cls._model.eval()
            cls._available = True
            logger.info("SciBERT loaded from %s", MODEL_NAME)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SciBERT unavailable (%s) — similarity filtering disabled", exc)
            cls._available = False
        return cls._available

    def embed(self, text: str) -> np.ndarray | None:
        """
        Return a 1-D float32 embedding for *text*, or None if the model
        isn't available. Uses the [CLS] token from the last hidden state.
        """
        if not self._load():
            return None

        import torch

        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True,
        )
        with torch.no_grad():
            outputs = self._model(**inputs)

        # CLS token representation
        cls_vec = outputs.last_hidden_state[:, 0, :].squeeze(0).numpy()
        return cls_vec.astype(np.float32)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


def paper_text(title: str | None, abstract: str | None = None) -> str:
    """Combine title and abstract into a single string for embedding."""
    parts = [p for p in (title, abstract) if p and p.strip()]
    return ". ".join(parts)
