import os
import sys

from src import log
from src import lurker
from src.config import load_lurker_config, LurkerConfig

__version__ = "0.16.0"

LOGGER = log.new_logger(__name__)


_TITLE = r"""
  _                   _               
 | |                 | |              
 | |     _   _  _ __ | | __ ___  _ __ 
 | |    | | | || '__|| |/ // _ \| '__|
 | |____| |_| || |   |   <|  __/| |   
 |______|\__,_||_|   |_|\_\\___||_|                                         
"""

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
    lurker_config: LurkerConfig = load_lurker_config(lurker_home + "/config.json")
    log.init_global_config(lurker_config.LURKER_LOG_LEVEL, file_name=lurker_config.LURKER_LOG_FILE)
    LOGGER.info(f"{_TITLE}\n{__version__}\n")

    LOGGER.info(f"Determined lurker home: {lurker_home}")
    LOGGER.info(f"Loaded configuration:\n{lurker_config.to_pretty_str()}")

    lurker = lurker.get_new(lurker_home=lurker_home, lurker_config=lurker_config)
    lurker.start_main_loop(lurker_config.LURKER_KEYWORD, lurker_config.LURKER_ACTION_REFRESH_INTERVAL)
