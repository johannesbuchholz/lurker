import logging
from logging import Logger
from typing import Optional, Union


def new_logger(name: str, file: Optional[str] = None) -> Logger:
    logger: Logger = logging.getLogger("Lurker ({})".format(name))

    if file is not None:
        handler = logging.FileHandler(filename=file)
        logger.handlers = [handler]

    return logger


def init_global_config(global_level: Union[str, int], global_format: str = '[%(levelname)8s] %(name)s: %(message)s') -> None:
    if type(global_level) == str and global_level.isnumeric():
        global_level = int(global_level)
    logging.basicConfig(level=global_level, format=global_format)
