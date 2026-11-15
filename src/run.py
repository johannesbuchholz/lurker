from src import bootstrap, log, lurker

LOGGER = log.new_logger(__name__)


def main(argv: list[str], banner: str) -> int:
    startup = bootstrap.bootstrap(argv)
    LOGGER.info(banner)
    lurker.get_new(startup).start_main_loop()
    return 0
