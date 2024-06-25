import logging
from logging import Logger


def new_logger(name: str, level: str = "INFO") -> Logger:
    logger: Logger = logging.getLogger(name)

    logger.setLevel(level)
    logger.propagate = False

    # create formatter
    formatter = logging.Formatter('[%(levelname)8s] %(name)s: %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(logger.level)
    ch.setFormatter(formatter)

    # make logger only use this one handler
    logger.handlers = [ch]
    return logger
