import logging
import os.path
from logging import Logger, handlers
from typing import Union


_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)8s] %(name)s: %(message)s")


class ExecInfoFilter(logging.Filter):

    def filter(self, record):
        record.exc_info = None
        return record


def new_logger(name: str) -> Logger:
    return logging.getLogger("Lurker ({})".format(name))


def init_global_config(global_level: Union[str, int], log_to_file: bool = False) -> None:
    if type(global_level) == str and global_level.isnumeric():
        global_level = int(global_level)

    logging.basicConfig(level=global_level, force=True)

    for handler in logging.root.handlers:
        handler.setFormatter(_FORMATTER)

    if log_to_file:
        # add rotating file handler
        log_file_name = os.getcwd() + "/lurker_log"
        handler = logging.handlers.RotatingFileHandler(filename=log_file_name, maxBytes=1000**2, backupCount=3)
        handler.setFormatter(_FORMATTER)
        logging.root.handlers.append(handler)

    if int(logging.root.level) > int(logging.DEBUG):
        # disable stack strace printing for log messages as the level is higher than DEBUG
        for handler in logging.root.handlers:
            handler.addFilter(ExecInfoFilter())