"""Command-line interface for the application."""

from __future__ import annotations

import sys

from docker_sandbox.cli import main as docker_sandbox_main
from docker_sandbox.container_guard import (
    ensure_running_in_docker_sandbox,
    is_running_in_docker_sandbox,
)
from sandbox_agent.openai_agent import run_html_element_agent


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    args = sys.argv[1:] if argv is None else argv
    if not is_running_in_docker_sandbox():
        return docker_sandbox_main(args)

    if "--test-sandbox" in args:
        raise SystemExit("--test-sandbox must be used from the host.")

    ensure_running_in_docker_sandbox()

    print(run_html_element_agent())
    return 0
