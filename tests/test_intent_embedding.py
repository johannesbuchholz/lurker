import pytest
from onnxruntime import InferenceSession
from tokenizers import Tokenizer

from src.actions.embedding import Embedder, best_match
from src.actions.models import INTENTS

MODEL_PATH = "lurker/models/onnx/intfloat.multilingual-e5-small"


def _make_embedder() -> Embedder:
    return Embedder(
        tokenizer=Tokenizer.from_file(f"{MODEL_PATH}/tokenizer.json"),
        session=InferenceSession(f"{MODEL_PATH}/model_O4.onnx", providers=["CPUExecutionProvider"]),
    )


EMBEDDER: Embedder = _make_embedder()

OFF_QUERIES: list[str] = [
    "turn the lights off",
    "light off",
    "turn everything off",
    "deactivate all lights",
    "schalte alle lichter im flur aus",
    "mach das küchenlicht aus",
    "schalte alle lichter aus",
    "switch off all lights",
    "mach das licht aus",
]

ON_QUERIES: list[str] = [
    "switch on all lights",
    "schalte das licht im wohnzimmern an",
    "mach die lampe auf dem nacht tisch an",
    "turn on the lights",
    "schalte die lichter ein",
    "activate all lights",
]


@pytest.mark.parametrize("query", OFF_QUERIES, ids=OFF_QUERIES)
def test_off_intent_matches(query: str) -> None:
    match = best_match(INTENTS, EMBEDDER, query, threshold=0.0)
    assert match is not None, f"No match for '{query}'"
    assert match.name == "off"


@pytest.mark.parametrize("query", ON_QUERIES, ids=ON_QUERIES)
def test_on_intent_matches(query: str) -> None:
    match = best_match(INTENTS, EMBEDDER, query, threshold=0.0)
    assert match is not None, f"No match for '{query}'"
    assert match.name in ("on", "brightness", "color", "scene")


class TestOffPattern:
    @pytest.mark.parametrize("query", OFF_QUERIES, ids=OFF_QUERIES)
    def test_off_regex(self, query: str) -> None:
        assert INTENTS[0].pattern.search(query.lower())

    @pytest.mark.parametrize("query", ON_QUERIES, ids=ON_QUERIES)
    def test_on_regex(self, query: str) -> None:
        assert INTENTS[1].pattern.search(query.lower())
