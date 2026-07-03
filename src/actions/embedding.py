import logging
from dataclasses import dataclass
from typing import TypeVar, cast

import numpy as np
import onnxruntime as ort
from numpy.typing import NDArray
from tokenizers import Tokenizer

from src import log
from src.actions.models import Describable

LOGGER = log.new_logger(__name__)

@dataclass(frozen=True, slots=True)
class Embedder:
    tokenizer: Tokenizer
    session: ort.InferenceSession

    def embed(self, text: str) -> NDArray[np.float32]:
        encoded = self.tokenizer.encode(text)

        input_ids = np.array([encoded.ids], dtype=np.int64)
        attention_mask = np.array([encoded.attention_mask], dtype=np.int64)

        inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }

        if "token_type_ids" in [i.name for i in self.session.get_inputs()]:
            inputs["token_type_ids"] = np.zeros_like(input_ids)

        token_embeddings = cast(NDArray[np.float32], self.session.run(None, inputs)[0])

        mask = attention_mask[..., None]
        embedding = (token_embeddings * mask).sum(axis=1) / mask.sum(axis=1)

        embedding /= np.linalg.norm(embedding, axis=1, keepdims=True)

        return embedding[0].astype(np.float32)


T = TypeVar("T", bound=Describable)


@dataclass(frozen=True, slots=True)
class _ScoredItem:
    """Mean embedding score and per-description scores for one item."""
    item: Describable
    mean: float
    per_description: list[tuple[str, float]]

    def format(self) -> str:
        phrases = ", ".join(f"{desc}: {s:.4f}" for desc, s in self.per_description)
        return f"{self.item.name}: {self.mean:.4f} [{phrases}]"


def best_match(
    items: list[T],
    embedder: Embedder,
    query: str,
    top_n: int = 1,
    threshold: float = 0.0,
) -> list[T]:
    if not items:
        return []

    query_emb = embedder.embed(" ".join(query.lower().split()))
    scored_items = [_score_item(item, embedder, query_emb) for item in items]

    if LOGGER.isEnabledFor(logging.DEBUG):
        ranked = sorted(scored_items, key=lambda s: s.mean, reverse=True)
        lines = [s.format() for s in ranked]
        LOGGER.debug("Light selection score summary:\n" + "\n".join(lines))

    above_threshold = [(s.item, s.mean) for s in scored_items if s.mean >= threshold]
    above_threshold.sort(key=lambda x: x[1], reverse=True)

    if top_n < 0:
        return [item for item, _ in above_threshold]
    return [item for item, _ in above_threshold[:top_n]]


def _score_item(item: Describable, embedder: Embedder, query_emb: NDArray[np.float32]) -> _ScoredItem:
    """Return the mean description score and per-description scores sorted descending."""
    desc_embs = [embedder.embed(desc) for desc in item.descriptions]
    scores = np.array([query_emb @ desc_emb for desc_emb in desc_embs], dtype=np.float32)
    per_desc = sorted(zip(item.descriptions, scores), key=lambda x: x[1], reverse=True)
    return _ScoredItem(
        item=item,
        mean=float(np.mean(scores)),
        per_description=[(desc, float(s)) for desc, s in per_desc],
    )
