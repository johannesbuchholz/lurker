import logging
import sys
from logging import Logger
from typing import List, Optional

_LOGGERS: List[Logger] = []


def new_logger(name: str, file: Optional[str] = None) -> Logger:
    logger: Logger = logging.getLogger("Lurker ({})".format(name))

    logger.setLevel("INFO")
    logger.propagate = False

    if file is None:
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(filename=file)

    formatter = logging.Formatter('[%(levelname)8s] %(name)s: %(message)s')
    handler.setLevel(logger.level)
    handler.setFormatter(formatter)

    # make logger only use this one handler
    logger.handlers = [handler]
    _LOGGERS.append(logger)
    return logger


def set_all_levels(level: str) -> None:
    for logger in _LOGGERS:
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
