import re
from typing import Any, Collection

import onnxruntime as ort
from tokenizers.tokenizers import Tokenizer

from src import log
from . import intents
from .embedding import Embedder, best_match
from .light import Light
from .models import Describable, light_descriptions

LIGHT_MATCH_THRESHOLD = 0.55

ALL_LIGHTS_PATTERN = re.compile(
    r"\ballen?\s+lichter?\b"
    r"|\balle[sn]?\s+(?:licht(?:er)?|lampe|lampen)?\s*(?:ein|aus|an)\b"
    r"|\ball\s+lights?\b|\ball(?:s|es)?\b|\beverything\b",
    re.IGNORECASE,
)
NAME_STOP_WORDS = {
    "light", "lights", "lamp", "lamps", "licht", "lichter", "lampe", "lampen", "room", "zimmer",
    "on", "in", "the", "a", "an", "of", "at", "to", "for", "with", "by",
    "ein", "eine", "einem", "einen", "der", "die", "das", "den", "dem", "des",
    "an", "auf", "in", "mit", "von", "zu", "bei", "nach", "über", "unter",
}


def _name_tokens(name: str) -> list[str]:
    """Split a light name into significant lowercase tokens."""
    return [
        word
        for word in re.split(r"\W+", name.lower())
        if word and (len(word) >= 2 or word.isdigit()) and word not in NAME_STOP_WORDS
    ]


def _try_room_filtering(instruction: str, available_lights: Collection[str]) -> Collection[str]:
    instruction_words = set(instruction.split())
    scores: list[tuple[int, str]] = []
    for name in available_lights:
        tokens = _name_tokens(name)
        hits = sum(1 for t in tokens if t in instruction_words)
        if hits > 0:
            scores.append((hits, name))
    if not scores:
        return []
    max_hits = max(h for h, _ in scores)
    return [name for h, name in scores if h == max_hits]


class ActionGenerator:
    _logger = log.new_logger(__qualname__)

    def __init__(self, model_path: str, initial_state: dict[str, Any]):
        self._logger = log.new_logger(self.__class__.__name__)
        if len(initial_state) < 1:
            self._logger.warning("No state given ActionGenerator!")
        self._embedder: Embedder = Embedder(
            tokenizer=Tokenizer.from_file(f"{model_path}/tokenizer.json"),
            session=ort.InferenceSession(f"{model_path}/model_O4.onnx", providers=["CPUExecutionProvider"])
        )

    def generate_lights(self, instruction: str, state: dict[str, Any]) -> Collection[Light]:
        lights = [v for v in state.values() if isinstance(v, Light)]
        names = self.guess_lights(instruction, [light.name for light in lights])
        affected = [light for light in lights if light.name in names]
        if not affected:
            affected = lights
        new_lights = intents.guess_intent_and_apply(instruction, affected, self._embedder)
        if new_lights is None:
            self._logger.info(f"No intent matched for instruction: '{instruction}'")
            return []
        return list(new_lights)

    def guess_lights(self, instruction: str, available_lights: Collection[str]) -> Collection[str]:
        """
        NOTE: _extract_room relies on light name tokens appearing literally in the instruction text.
        This only works when light names and the instruction share the same language;
        cross-language room qualifiers (e.g. German "küche" vs English light name "Kitchen") will not be detected.
        """
        normalized = instruction.lower()
        room_lights = _try_room_filtering(normalized, available_lights)
        if room_lights:
            return room_lights
        if ALL_LIGHTS_PATTERN.search(normalized):
            return list(available_lights)
        # no room specified and no "all"-quantifier detected: Apply embeddings as fallback
        items = [Describable(name=name, descriptions=light_descriptions(name)) for name in available_lights]
        matches = best_match(items, self._embedder, instruction, top_n=-1, threshold=LIGHT_MATCH_THRESHOLD)
        return [item.name for item in matches]
