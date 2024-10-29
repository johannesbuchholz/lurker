import logging
import os.path
from logging import Logger, handlers
from typing import Union


_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)8s] %(name)s: %(message)s")

def new_logger(name: str) -> Logger:
    return logging.getLogger("Lurker ({})".format(name))


def init_global_config(global_level: Union[str, int], log_to_file: bool = False) -> None:
    if type(global_level) == str and global_level.isnumeric():
        global_level = int(global_level)

    logging.basicConfig(level=global_level, force=True)

    if log_to_file:
        log_file_name = os.getcwd() + "/lurker_log"
        handler = logging.handlers.RotatingFileHandler(filename=log_file_name, maxBytes=1000**2, backupCount=3)
        logging.root.handlers.append(handler)

    for handler in logging.root.handlers:
        handler.setFormatter(_FORMATTER)