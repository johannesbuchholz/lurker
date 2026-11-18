from src import bootstrap, log
from src.plugins import PluginError

LOGGER = log.new_logger(__name__)


def main(argv: list[str]) -> int:
    startup = bootstrap.bootstrap(argv)
    try:
        handlers = startup.load_handlers(strict=True)
    except PluginError as error:
        LOGGER.error(f"Setup failed: {type(error)} {error}")
        return 1
    for handler in handlers:
        LOGGER.info(f"Plugin handler ready: {handler.key}")
    return 0
