import os
import sys

from src import log
from src import lurker

LOGGER = log.new_logger(__name__)


def _determine_lurker_home() -> str:
    try:
        i = sys.argv.index("--lurker-home")
    except ValueError:
        i = None
    if i is not None and i + 1 < len(sys.argv):
        return os.path.abspath(sys.argv[i + 1])
    else:
        return os.getcwd() + "/lurker"


if __name__ == "__main__":
    lurker_home = _determine_lurker_home()
    LOGGER.info(f"Determined lurker home: {lurker_home}")

    lurker.start(lurker_home=lurker_home)
