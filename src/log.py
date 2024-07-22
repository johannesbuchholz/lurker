import logging
from logging import Logger
from typing import List

_LOGGERS: List[Logger] = []


def new_logger(name: str) -> Logger:
    logger: Logger = logging.getLogger("Lurker ({})".format(name))

    logger.setLevel("INFO")
    logger.propagate = False

    handler = logging.StreamHandler()
    handler.setLevel(logger.level)
    formatter = logging.Formatter('[%(levelname)8s] %(name)s: %(message)s')
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
