import abc
from dataclasses import dataclass
from typing import ClassVar

from src import log


@dataclass(frozen=True, slots=True)
class LurkerContext:
    lurker_home: str
    """Base lurker home. Models, config and the shipped plugins live here."""

    plugin_root_dir: str
    """Base plugin root. Defaults to ``<lurker_home>/plugins``."""

    log_level: int | str
    """Log level configured for this lurker instance."""

    language: str
    """Language used for speech recognition and plugin defaults."""


class ActionHandler(abc.ABC):
    key: ClassVar[str]

    def __init__(self, context: LurkerContext, config: dict) -> None:
        self.context = context
        self.config = config
        self._logger = log.new_logger(type(self).__name__)

    @abc.abstractmethod
    def accepts(self, instruction: str) -> bool:
        """Return True if this handler wants to act on the instruction."""

    @abc.abstractmethod
    def handle(self, instruction: str) -> int:
        """Act on the instruction. Returns 0 iff it was handled successfully."""

    def ensure_resources(self) -> None:
        """Idempotent resource provisioning (models, caches). Default: nothing to do.

        Called by the loader after construction, on every start, and by ``setup``. Must
        return fast when resources are present (plain existence checks); may raise, which
        makes the loader skip this plugin. The constructor must not depend on these
        resources, so construction never triggers a download.
        """
