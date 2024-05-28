import logging
import os
from logging import Logger

GLOBAL_LOG_LEVEL = os.environ["LURKER_LOG_LEVEL"].upper() if "LURKER_LOG_LEVEL" in os.environ else "DEBUG"


def new_logger(name: str) -> Logger:
    logger: Logger = logging.getLogger(name)

    logger.setLevel(GLOBAL_LOG_LEVEL)
    logger.propagate = False

    # create formatter
    formatter = logging.Formatter('[%(levelname)8s] %(name)s: %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(logger.level)
    ch.setFormatter(formatter)

    # make logger only use this one handler
    logger.handlers = [ch]
    return logger
