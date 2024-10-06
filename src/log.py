import logging
from logging import Logger
from typing import Optional


def new_logger(name: str, file: Optional[str] = None) -> Logger:
    logger: Logger = logging.getLogger("Lurker ({})".format(name))

    if file is not None:
        handler = logging.FileHandler(filename=file)
        logger.handlers = [handler]

    return logger


def init_global_config(global_level: str | int, global_format: str = '[%(levelname)8s] %(name)s: %(message)s') -> None:
    logging.basicConfig(level=global_level, format=global_format)
