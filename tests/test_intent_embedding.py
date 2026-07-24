from onnxruntime import InferenceSession
from tokenizers import Tokenizer

from src.actions.embedding import Embedder, Embedded, embed_items, best_match
from src.actions.models import Intent, INTENTS

MODEL_PATH = "lurker/models/onnx/intfloat.multilingual-e5-small"


def _make_embedder() -> Embedder:
    return Embedder(
        tokenizer=Tokenizer.from_file(f"{MODEL_PATH}/tokenizer.json"),
        session=InferenceSession(f"{MODEL_PATH}/model_O4.onnx", providers=["CPUExecutionProvider"]),
    )


EMBEDDER = None


def _get_embedder() -> Embedder:
    global EMBEDDER
    if EMBEDDER is None:
        EMBEDDER = _make_embedder()
    return EMBEDDER


def _embed_intents() -> list[Embedded[Intent]]:
    return embed_items(_get_embedder(), INTENTS)


INTENT_QUERIES: dict[str, list[str]] = {
    "power": [
        "schalte alle lichter im flur aus",
        "mach das küchenlicht aus",
        "schalte das licht im wohnzimmern an",
        "schalte alle lichter aus",
        "mach die lampe auf dem nacht tisch an",

    ],
}


class TestIntentEmbedding:
    """Each Intent's descriptions should score highest for clearly intended instructions."""

    def test_power_queries_match_power_intent(self):
        embedded_intents = _embed_intents()
        for query in INTENT_QUERIES["power"]:
            emb = _get_embedder().embed(query)
            match = best_match(embedded_intents, emb, threshold=0.0)
            assert match is not None, f"No match for '{query}'"
            assert match.name == "power", f"Expected 'power' for '{query}', got '{match.name}'"
