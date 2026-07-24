import logging
from dataclasses import dataclass
from typing import TypeVar, Generic
from typing import cast

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
        # Convert text into model input tokens (IDs + attention mask)
        encoded = self.tokenizer.encode(text)

        input_ids = np.array([encoded.ids], dtype=np.int64)
        attention_mask = np.array([encoded.attention_mask], dtype=np.int64)

        inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }

        # Some ONNX exports require token_type_ids (segment IDs)
        if "token_type_ids" in [i.name for i in self.session.get_inputs()]:
            inputs["token_type_ids"] = np.zeros_like(input_ids)

        # Run the transformer model.
        # Output is one vector per token, not one vector for the whole sentence.
        token_embeddings = cast(NDArray[np.float32], self.session.run(None, inputs)[0])

        # Mean-pool token vectors into one sentence vector.
        # Attention mask ignores padding tokens.
        mask = attention_mask[..., None]
        embedding = (token_embeddings * mask).sum(axis=1) / mask.sum(axis=1)

        # Normalize vector length so cosine similarity works correctly.
        embedding /= np.linalg.norm(embedding, axis=1, keepdims=True)

        # Return the single sentence embedding (384 dimensions for e5-small)
        return embedding[0].astype(np.float32)


T = TypeVar("T", bound=Describable)


@dataclass(frozen=True, slots=True)
class Embedded(Generic[T]):
    item: T
    embeddings: tuple[NDArray[np.float32], ...]
    _embedder: Embedder

    def score_for(self, query_emb: NDArray[np.float32], include_top_ratio: float = 0.5) -> float:
        """Mean score across all top descriptions."""
        scores = np.array(
            [query_emb @ desc_emb for desc_emb in self.embeddings],
            dtype=np.float32,
        )

        top_k: int = max(1, int(len(scores) * np.clip(include_top_ratio, 0.0, 1.0)))

        if LOGGER.isEnabledFor(logging.DEBUG):
            scored = sorted(
                zip(self.item.descriptions, scores),
                key=lambda x: x[1],
                reverse=True,
            )
            lines = []
            for i, (desc, score) in enumerate(scored):
                marker = ">" if i < top_k else ""
                lines.append(f"{marker}'{desc}': {score:.4f}")
            joined_scores = "\n".join(lines)
            LOGGER.debug(f"scores for '{self.item}':\n{joined_scores}")

        top_k_scores = np.sort(scores)[-top_k:]

        return float(np.mean(top_k_scores))

    def __str__(self):
        return str(self.item)


def embed_items(embedder: Embedder, items: list[T]) -> list[Embedded[T]]:
    return [
        Embedded(
            item=item,
            embeddings=tuple(embedder.embed(description) for description in item.descriptions),
            _embedder=embedder,
        )
        for item in items
    ]


def best_match(items: list[Embedded[T]], query_emb: NDArray[np.float32], threshold: float = 0.5) -> T | None:
    scores: list[tuple[Embedded[T], float]] = [(e, e.score_for(query_emb)) for e in items]
    best_emb, best_score = max(scores, key=lambda x: x[1])
    if LOGGER.isEnabledFor(logging.DEBUG):
        sorted_scores = sorted(scores, reverse=True, key=lambda x: x[1])
        sorted_scores_s = "\n".join([f"{emb}: {score}" for emb, score in sorted_scores])
        LOGGER.debug(f"Best match (threshold={threshold}):\n{sorted_scores_s}")
    if best_score < threshold:
        return None
    return best_emb.item
