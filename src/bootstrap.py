import os
from dataclasses import dataclass

from src import log, plugins
from src.action_handler import ActionHandler, LurkerContext
from src.config import LurkerConfig, load_lurker_config

LOGGER = log.new_logger(__name__)


def _argument_value(argv: list[str], flag: str) -> str | None:
    try:
        index = argv.index(flag)
    except ValueError:
        return None
    if index + 1 < len(argv):
        return argv[index + 1]
    return None


def _plugin_root(lurker_home: str) -> str:
    return os.path.abspath(os.path.join(lurker_home, "plugins"))


@dataclass(frozen=True)
class Bootstrap:
    lurker_home: str
    overlay_home: str | None
    config: LurkerConfig

    @property
    def plugin_root(self) -> str:
        return _plugin_root(self.lurker_home)

    @property
    def overlay_plugin_root(self) -> str | None:
        return _plugin_root(self.overlay_home) if self.overlay_home is not None else None

    def context(self) -> LurkerContext:
        return LurkerContext(
            lurker_home=self.lurker_home,
            plugin_root_dir=self.plugin_root,
            log_level=self.config.LURKER_LOG_LEVEL,
            language=self.config.LURKER_LANGUAGE,
        )

    def load_handlers(self, *, strict: bool = False) -> list[ActionHandler]:
        return plugins.load_handlers(self.context(), self.overlay_plugin_root, raise_on_error=strict)


def bootstrap(argv: list[str]) -> Bootstrap:
    """Resolve homes and configuration, then configure logging."""
    lurker_home_argument = _argument_value(argv, "--lurker-home")
    lurker_home = (
        os.path.abspath(lurker_home_argument)
        if lurker_home_argument is not None
        else os.path.join(os.getcwd(), "lurker")
    )
    overlay_home_argument = _argument_value(argv, "--overlay-home")
    overlay_home = (
        os.path.abspath(overlay_home_argument) if overlay_home_argument is not None else None
    )

    overlay_config_path = (
        os.path.join(overlay_home, "config.json") if overlay_home is not None else None
    )
    config = load_lurker_config(os.path.join(lurker_home, "config.json"), overlay_config_path)
    log.init_global_config(
        config.LURKER_LOG_LEVEL,
        file_name=config.LURKER_LOG_FILE,
        lurker_home=lurker_home,
    )

    startup = Bootstrap(lurker_home=lurker_home, overlay_home=overlay_home, config=config)
    LOGGER.info(f"Determined lurker home: {startup.lurker_home}")
    LOGGER.info(f"Determined overlay home: {startup.overlay_home or 'none'}")
    LOGGER.info(f"Determined plugin root: {startup.plugin_root}")
    LOGGER.info(f"Determined overlay plugin root: {startup.overlay_plugin_root or 'none'}")
    LOGGER.info(f"Loaded configuration:\n{startup.config.to_pretty_str()}")

    return startup
