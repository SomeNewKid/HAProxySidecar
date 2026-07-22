"""Bootstrap the command-line application."""

from . import cli


def main() -> None:
    """Run the command-line application."""
    raise SystemExit(cli.main())


if __name__ == "__main__":
    main()
