import sys

__version__ = "0.19.6"

_TITLE = r"""
  _                   _
 | |                 | |
 | |     _   _  _ __ | | __ ___  _ __
 | |    | | | || '__|| |/ // _ \| '__|
 | |____| |_| || |   |   <|  __/| |
 |______|\__,_||_|   |_|\_\\___||_|
"""

_COMMANDS = ("run", "setup", "version")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _usage()

    command, remaining_args = args[0], args[1:]
    match command:
        case "run":
            from src.run import main as run
            print(_TITLE)
            print(__version__)
            return run(remaining_args)
        case "setup":
            print(f"Setting up lurker... ({__version__})")
            from src.setup import main as setup
            return setup(remaining_args)
        case "version":
            print(__version__)
            return 0
        case _:
            return _usage()


def _usage() -> int:
    print("usage: python . <command> [options]", file=sys.stderr)
    print(f"commands: {', '.join(_COMMANDS)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
