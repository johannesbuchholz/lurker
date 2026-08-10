from pathlib import Path

from onnxruntime import InferenceSession
from tokenizers import Tokenizer

from src.actions.action import resolve_llm_model_path
from src.actions.embedding import Embedder, best_match, normalize_query
from src.actions.models import SCENES, Describable, light_descriptions

MODEL_PATH = resolve_llm_model_path(str(Path(__file__).resolve().parents[1] / "lurker"))

LIGHT_NAMES = [
    "Living Room Entry",
    "Living Room Couch",
    "Living Room Ceiling",
    "Living Room Table",
    "Living Room Desk",
    "Kitchen",
    "Floor 1",
    "Floor 2",
    "Bedroom Ceiling",
    "Bedroom Nightstand Alex",
    "Bedroom Nightstand Jenny",
]


def _make_embedder() -> Embedder:
    return Embedder(
        tokenizer=Tokenizer.from_file(f"{MODEL_PATH}/tokenizer.json"),
        session=InferenceSession(f"{MODEL_PATH}/model_O4.onnx", providers=["CPUExecutionProvider"]),
    )


EMBEDDER: Embedder = _make_embedder()


def _light_items() -> list[Describable]:
    return [Describable(name=name, descriptions=light_descriptions(name)) for name in LIGHT_NAMES]


class TestBestMatch:
    def test_top_n_single(self) -> None:
        matches = best_match(_light_items(), EMBEDDER, "Turn the kitchen light off", top_n=1)
        assert [item.name for item in matches] == ["Kitchen"]

    def test_top_n_negative_returns_all_above_threshold(self) -> None:
        matches = best_match(_light_items(), EMBEDDER, "All lights on in the living room", top_n=-1, threshold=0.55)
        names = [item.name for item in matches]
        assert set(names) == {name for name in LIGHT_NAMES if name.startswith("Living Room")}

    def test_threshold_rejects_unrelated(self) -> None:
        matches = best_match(_light_items(), EMBEDDER, "What time is it", top_n=-1, threshold=0.55)
        assert matches == []

    def test_top_n_respects_order(self) -> None:
        matches = best_match(_light_items(), EMBEDDER, "Dim the desk lamp", top_n=2)
        names = [item.name for item in matches]
        assert names[0] == "Living Room Desk"
        assert len(names) == 2

    def test_empty_items(self) -> None:
        assert best_match([], EMBEDDER, "any query") == []


class TestSceneSelection:
    def test_movie_night(self) -> None:
        matches = best_match(SCENES, EMBEDDER, "Movie night", top_n=1)
        assert matches[0].name == "movie_night"

    def test_unrelated_rejected_by_threshold(self) -> None:
        candidates = [scene for scene in SCENES if scene.pattern.search("That movie was great")]
        assert [scene.name for scene in candidates] == ["movie_night"]
        assert best_match(candidates, EMBEDDER, "That movie was great", top_n=1, threshold=0.4) == []


class TestNormalizeQuery:
    def test_lowercases(self) -> None:
        assert normalize_query("Turn the Kitchen Light OFF") == "turn the kitchen light off"

    def test_collapses_whitespace(self) -> None:
        assert normalize_query("  dim   the desk  lamp ") == "dim the desk lamp"


class TestLightDescriptions:
    def test_lowercases_name(self) -> None:
        assert light_descriptions("Kitchen") == ("kitchen", "kitchen light")

    def test_multiple_words(self) -> None:
        assert light_descriptions("Desk Lamp") == ("desk lamp", "desk lamp light")
