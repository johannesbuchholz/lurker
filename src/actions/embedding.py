import logging
from dataclasses import dataclass
from typing import cast

import numpy as np
import onnxruntime as ort
from numpy.typing import NDArray
from tokenizers import Tokenizer

from src import log
from src.actions.models import Describable, Intent

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


def best_match(items: list[Describable], embedder: Embedder, query: str, threshold: float = 0.5) -> Describable | None:
    normalized = query.lower().strip()

    for item in items:
        if isinstance(item, Intent) and item.pattern and item.pattern.search(normalized):
            if item.nested:
                return best_match(list(item.nested), embedder, query, threshold)
            return item

    if not items:
        return None

    query_emb = embedder.embed(query)
    return _best_by_embedding(items, embedder, query_emb, threshold)


def _best_by_embedding(items: list[Describable], embedder: Embedder, query_emb: NDArray[np.float32], threshold: float) -> Describable | None:
    scores = [
        (item, _score_item(item, embedder, query_emb))
        for item in items
    ]
    best_item, best_score = max(scores, key=lambda x: x[1])

    if LOGGER.isEnabledFor(logging.DEBUG):
        sorted_scores = sorted(scores, reverse=True, key=lambda x: x[1])
        sorted_s = "\n".join([f"{item}: {score:.4f}" for item, score in sorted_scores])
        LOGGER.debug(f"Embedding scores:\n{sorted_s}")

    if best_score < threshold:
        return None
    return best_item


def _score_item(item: Describable, embedder: Embedder, query_emb: NDArray[np.float32]) -> float:
    desc_embs = [embedder.embed(desc) for desc in item.descriptions]
    scores = np.array([query_emb @ desc_emb for desc_emb in desc_embs], dtype=np.float32)

    if LOGGER.isEnabledFor(logging.DEBUG):
        scored = sorted(
            zip(item.descriptions, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        lines = [f"  '{desc}': {s:.4f}" for desc, s in scored]
        LOGGER.debug(f"scores for '{item.name}':\n" + "\n".join(lines))

    return float(np.mean(scores))
