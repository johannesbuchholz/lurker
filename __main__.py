import os
import sys

from src import log
from src import lurker

__version__ = "0.0.0-PLACEHOLDER"

LOGGER = log.new_logger(__name__)

# Big by Glenn Chappell 4/93 -- based on Standard
# Includes ISO Latin-1
# Greek characters by Bruce Jakeway <pbjakeway@neumann.uwaterloo.ca>
# figlet release 2.2 -- November 1996
# Permission is hereby given to modify this font, as long as the
# modifier's name is placed on a comment line.
#
# Modified by Paul Burton  12/96 to include new parameter
# supported by FIGlet and FIGWin.  May also be slightly modified for better use
# of new full-width/kern/smush alternatives, but default output is NOT changed.
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
    log.init_global_config("INFO", True)
    LOGGER.info(f"Welcome to\n{_TITLE}\n{__version__}\n")
    lurker_home = _determine_lurker_home()
    LOGGER.info(f"Determined lurker home: {lurker_home}")

    lurker.start(lurker_home=lurker_home)
