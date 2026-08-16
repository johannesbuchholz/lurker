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
    scores = [
        (item, _score_item(item, embedder, query_emb))
        for item in items
    ]

    if LOGGER.isEnabledFor(logging.DEBUG):
        sorted_scores = sorted(scores, reverse=True, key=lambda x: x[1])
        sorted_s = "\n".join([f"{item}: {score:.4f}" for item, score in sorted_scores])
        LOGGER.debug(f"Embedding scores:\n{sorted_s}")

    above_threshold = [(item, score) for item, score in scores if score >= threshold]
    above_threshold.sort(key=lambda x: x[1], reverse=True)

    if top_n < 0:
        return [item for item, _ in above_threshold]
    return [item for item, _ in above_threshold[:top_n]]


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
