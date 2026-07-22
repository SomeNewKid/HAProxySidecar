"""Command-line interface for the code-execution sidecar."""

from __future__ import annotations

import argparse
import sys

from .server import run_server

_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8090


def main(argv: list[str] | None = None) -> int:
    """Run the code-execution sidecar HTTP server."""
    arguments = _parse_arguments(argv)
    run_server(host=arguments.host, port=arguments.port)
    return 0


def _parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    args = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Run the code-execution sidecar.")
    parser.add_argument(
        "--host",
        default=_DEFAULT_HOST,
        help=f"Host used by the HTTP server. Default: {_DEFAULT_HOST}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_PORT,
        help=f"Port used by the HTTP server. Default: {_DEFAULT_PORT}",
    )
    return parser.parse_args(args)
