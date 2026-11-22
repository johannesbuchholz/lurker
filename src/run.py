from __main__ import __version__
from src import bootstrap, log, lurker

LOGGER = log.new_logger(__name__)

_TITLE = r"""
  _                   _
 | |                 | |
 | |     _   _  _ __ | | __ ___  _ __
 | |    | | | || '__|| |/ // _ \| '__|
 | |____| |_| || |   |   <|  __/| |
 |______|\__,_||_|   |_|\_\\___||_|
 """

def main(argv: list[str]) -> int:
    startup = bootstrap.bootstrap(argv)
    LOGGER.info(_TITLE.strip() + " " + __version__)
    LOGGER.info(startup)
    lurker.get_new(startup).start_main_loop()
    return 0
