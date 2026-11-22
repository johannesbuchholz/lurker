import sys

__version__ = "0.21.0"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _usage()

    command, remaining_args = args[0], args[1:]
    match command:
        case "run":
            from src.run import main as run
            return run(remaining_args)
        case "setup":
            from src.setup import main as setup
            return setup(remaining_args)
        case "version", "--version":
            print(__version__)
            return 0
        case _:
            return _usage()


def _usage() -> int:
    print("usage: python . <command> [options]", file=sys.stderr)
    print(f"commands: run, setup, version", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
