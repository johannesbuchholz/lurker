import logging
from logging import Logger

from src.utils import Constants


def new_logger(name: str) -> Logger:
    logger: Logger = logging.getLogger(name)

    logger.setLevel(Constants.LURKER_LOG_LEVEL)
    logger.propagate = False

    # create formatter
    formatter = logging.Formatter('[%(levelname)8s] %(name)s: %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(logger.level)
    ch.setFormatter(formatter)

    # make logger only use this one handler
    logger.handlers = [ch]
    return logger
