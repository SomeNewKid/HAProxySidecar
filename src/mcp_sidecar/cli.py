"""Command-line interface for the MCP sidecar server."""

from __future__ import annotations

import argparse
import sys

from .server import create_mcp_server

_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8000
_DEFAULT_TRANSPORT = "streamable-http"
_SUPPORTED_TRANSPORTS = ("stdio", "sse", "streamable-http")


def main(argv: list[str] | None = None) -> int:
    """Run the MCP sidecar server."""
    arguments = _parse_arguments(argv)
    server = create_mcp_server(host=arguments.host, port=arguments.port)
    server.run(transport=arguments.transport)
    return 0


def _parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    args = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Run the MCP sidecar server.")
    parser.add_argument(
        "--transport",
        choices=_SUPPORTED_TRANSPORTS,
        default=_DEFAULT_TRANSPORT,
        help=f"MCP transport to use. Default: {_DEFAULT_TRANSPORT}",
    )
    parser.add_argument(
        "--host",
        default=_DEFAULT_HOST,
        help=f"Host used by HTTP transports. Default: {_DEFAULT_HOST}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_PORT,
        help=f"Port used by HTTP transports. Default: {_DEFAULT_PORT}",
    )
    return parser.parse_args(args)
