from src import bootstrap, log, lurker

LOGGER = log.new_logger(__name__)


def main(argv: list[str]) -> int:
    startup = bootstrap.bootstrap(argv)
    LOGGER.info(startup)
    lurker.get_new(startup).start_main_loop()
    return 0
