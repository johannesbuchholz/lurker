import logging
import os.path
from logging import Logger, handlers
from typing import Union, Optional

_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)8s] %(name)s: %(message)s")

def new_logger(name: str) -> Logger:
    return logging.getLogger("Lurker ({})".format(name))


def init_global_config(global_level: Union[str, int], file_name: Optional[str] = None) -> None:
    if type(global_level) == str and global_level.isnumeric():
        global_level = int(global_level)

    logging.basicConfig(level=global_level, force=True)
    logging.raiseExceptions = False  # Dismiss all errors regarding logging

    if file_name is not None and (len(file_name) > 0):
        log_file_path = f"{os.getcwd()}/{file_name}"
        handler = logging.handlers.RotatingFileHandler(filename=log_file_path, maxBytes=1000**2, backupCount=3)
        logging.root.handlers.append(handler)

    for handler in logging.root.handlers:
        handler.setFormatter(_FORMATTER)