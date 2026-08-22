"""Experiment: find optimal best_match parameters for room extraction.

Two monolingual test sets (English + German). Tests richer descriptions too.
Run: pytest tests/test_extract_room_experiment.py -v -s
"""
from pathlib import Path

import pytest

from src.actions.embedding import Embedder, best_match
from src.actions.models import Describable
from src.lurker import _resolve_embedding_model_path

MODEL_PATH = _resolve_embedding_model_path(str(Path(__file__).resolve().parents[1] / "lurker"))

EN_LIGHT_NAMES = [
    "Living Room Entry", "Living Room Couch", "Living Room Ceiling",
    "Living Room Table", "Living Room Desk", "Kitchen",
    "Floor 1", "Floor 2", "Bedroom Ceiling",
    "Bedroom Nightstand Alex", "Bedroom Nightstand Jenny",
]

EN_CASES = [
    ("dim the table light", {"Living Room Table"}),
    ("turn on the bedroom ceiling", {"Bedroom Ceiling"}),
    ("bedroom nightstand alex dim", {"Bedroom Nightstand Alex"}),
    ("floor lights on", {"Floor 1", "Floor 2"}),
    ("turn all lights off", None),
    ("make the light blue", None),
    ("what time is it", set()),
    ("living room couch", {"Living Room Couch"}),
    ("kitchen light off", {"Kitchen"}),
    ("turn on everything in the bedroom", {"Bedroom Ceiling", "Bedroom Nightstand Alex", "Bedroom Nightstand Jenny"}),
]

DE_LIGHT_NAMES = [
    "Wohnzimmereingang", "Wohnzimmercouch", "Wohnzimmerdecke",
    "Wohnzimmertisch", "Wohnzimmerarbeitsplatz", "Kueche",
    "Etage 1", "Etage 2", "Schlafzimmerdecke",
    "Nachttisch Alex", "Nachttisch Jenny",
]

DE_CASES = [
    ("dimm das licht am wohnzimmertisch", {"Wohnzimmertisch"}),
    ("schalte die schlafzimmerdecke an", {"Schlafzimmerdecke"}),
    ("nachttisch alex dimmen", {"Nachttisch Alex"}),
    ("lichter in etage 1 einschalten", {"Etage 1"}),
    ("alle lichter ausschalten", None),
    ("mache das licht an", None),
    ("wie spaet ist es", set()),
    ("wohnzimmercouch", {"Wohnzimmercouch"}),
    ("kueche licht aus", {"Kueche"}),
    ("schalte alles im schlafzimmer ein", {"Schlafzimmerdecke", "Nachttisch Alex", "Nachttisch Jenny"}),
]


def light_descriptions_simple(name: str) -> tuple[str, ...]:
    normalized = name.lower().strip()
    return tuple(dict.fromkeys([normalized, f"{normalized} light"]))


def light_descriptions_rich(name: str) -> tuple[str, ...]:
    normalized = name.lower().strip()
    descs = [normalized, f"{normalized} light"]
    parts = normalized.split()
    if len(parts) >= 2:
        descs.append(f"light in the {parts[0]}")
        descs.append(f"{parts[0]} {parts[-1]} light")
    return tuple(dict.fromkeys(descs))


DESCRIPTION_MODELS = {
    "simple": light_descriptions_simple,
    "rich": light_descriptions_rich,
}


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    from tokenizers import Tokenizer
    import onnxruntime as ort
    return Embedder(
        tokenizer=Tokenizer.from_file(f"{MODEL_PATH}/tokenizer.json"),
        session=ort.InferenceSession(f"{MODEL_PATH}/model_O4.onnx", providers=["CPUExecutionProvider"]),
    )


THRESHOLDS = [0.3, 0.4, 0.5, 0.55]
TOP_NS = [1, -1]


@pytest.mark.skip(reason="slow experiment — run with: pytest tests/test_extract_room_experiment.py -v -s --no-header -p no:cacheprovider -k test_experiment")
@pytest.mark.parametrize("threshold", THRESHOLDS)
@pytest.mark.parametrize("top_n", TOP_NS)
@pytest.mark.parametrize("desc_model", ["simple", "rich"])
@pytest.mark.parametrize("lang", ["en", "de"])
def test_experiment(threshold: float, top_n: int, desc_model: str, lang: str, embedder: Embedder) -> None:
    light_names = EN_LIGHT_NAMES if lang == "en" else DE_LIGHT_NAMES
    cases = EN_CASES if lang == "en" else DE_CASES
    desc_fn = DESCRIPTION_MODELS[desc_model]

    results = []
    for instruction, expected in cases:
        items = [Describable(name=n, descriptions=desc_fn(n)) for n in light_names]
        matches = best_match(items, embedder, instruction.lower(), top_n=top_n, threshold=threshold)
        names = tuple(m.name for m in matches)
        results.append((instruction, names, expected))

    print(f"\n=== {lang.upper()} | desc={desc_model} | threshold={threshold} | top_n={top_n} ===")
    print(f"{'Instruction':<45} {'Result':<40} {'Expected'}")
    print("-" * 120)
    for instruction, names, expected in results:
        display = ", ".join(names[:4])
        if len(names) > 4:
            display += f" (+{len(names)-4})"
        if not names:
            display = "(none)"
        exp_str = str(expected) if expected is not None else "ALL"
        match = "OK" if (expected is None and not names) or (expected == set() and not names) or (set(names) == expected) else "FAIL"
        print(f"{instruction:<45} {display:<40} {exp_str:<30} {match}")

    assert True
