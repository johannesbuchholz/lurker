from dataclasses import dataclass

import numpy as np
import onnxruntime as ort
from numpy._typing import NDArray
from tokenizers import Tokenizer


@dataclass(frozen=True, slots=True)
class Embedder:
    tokenizer: Tokenizer
    session: ort.InferenceSession

    def embed_query(self, text: str):
        """Use when embedding a sentence used for querying something (the search input)."""
        return self._embed(f"query: {text}")

    def embed_passage(self, text: str):
        """Use when embedding a sentence that may be targeted by an input query (the potential search finding)."""
        return self._embed(f"passage: {text}")

    def _embed(self, text: str) -> NDArray[np.float32]:
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
        token_embeddings = self.session.run(None, inputs)[0]

        # Mean-pool token vectors into one sentence vector.
        # Attention mask ignores padding tokens.
        mask = attention_mask[..., None]
        embedding = (token_embeddings * mask).sum(axis=1) / mask.sum(axis=1)

        # Normalize vector length so cosine similarity works correctly.
        embedding /= np.linalg.norm(embedding, axis=1, keepdims=True)

        # Return the single sentence embedding (384 dimensions for e5-small)
        return embedding[0].astype(np.float32)
