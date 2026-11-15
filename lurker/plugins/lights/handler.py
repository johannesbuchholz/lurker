from src.action_handler import ActionHandler, LurkerContext
from .action import ActionGenerator
from .backend import LightBackend
from .dummy import DummyBackend
from .embedding import resolve_embedding_model_path
from .hue import HueBackend
from .noop import NoopBackend

ACCEPT_KEYWORDS = (
    "light",
    "lights",
    "lamp",
    "lamps",
    "licht",
    "lichter",
    "lampe",
    "lampen",
)


class LightsHandler(ActionHandler):
    key = "lights"

    def __init__(
            self,
            context: LurkerContext,
            config: dict,
            *,
            backend: LightBackend | None = None,
            generator: ActionGenerator | None = None,
    ):
        super().__init__(context)
        self._backend = backend or self._create_backend(config)
        self._generator = generator

    def _create_backend(self, config: dict) -> LightBackend:
        backend = config.get("backend", "dummy")
        if backend == "dummy":
            return DummyBackend(self.context.language)
        if backend == "noop":
            return NoopBackend()
        if backend == "hue":
            host = config.get("host")
            user = config.get("user")
            if not host or not user:
                raise ValueError("hue backend requires both 'host' and 'user' config values")
            return HueBackend(host, user)
        raise ValueError(f"Unknown lights backend: {backend!r}")

    def ensure_resources(self) -> None:
        if not isinstance(self._backend, NoopBackend):
            resolve_embedding_model_path(self.context.lurker_home)

    def _ensure_generator(self) -> ActionGenerator:
        if self._generator is None:
            self._generator = ActionGenerator(
                model_path=resolve_embedding_model_path(self.context.lurker_home),
                initial_state=self._backend.get_state(),
            )
        return self._generator

    def accepts(self, instruction: str) -> bool:
        normalized = instruction.lower()
        return any(keyword in normalized for keyword in ACCEPT_KEYWORDS)

    def handle(self, instruction: str) -> int:
        if isinstance(self._backend, NoopBackend):
            self._logger.info(f"Lights disabled (backend=noop): '{instruction}'")
            return 0
        lights = self._ensure_generator().generate_lights(instruction, self._backend.get_state())
        if not lights:
            self._logger.info(f"No action for instruction '{instruction}'")
            return 1
        return self._backend.apply(lights)
