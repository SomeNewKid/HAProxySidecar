"""Command-line interface for running Sandbox Tester."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .reporter import (
    CompositeReporter,
    ConsoleReporter,
    QuietReporter,
    StatusFileReporter,
    TestReporter,
)
from .runner import run_from_files


def main(arguments: list[str] | None = None) -> int:
    """Run Sandbox Tester from a serialized capability context."""
    parsed_arguments = _parse_arguments(arguments)
    config_path = parsed_arguments.config.expanduser().resolve()
    output_directory = _get_output_directory(config_path, parsed_arguments.output)
    reporter = _create_reporter(output_directory, parsed_arguments.verbose)

    asyncio.run(
        run_from_files(
            config_path,
            output_directory,
            reporter,
            serialize_evidence=parsed_arguments.serialize_evidence,
        )
    )
    print(f"Sandbox Tester report saved to: {output_directory / 'report.json'}")
    return 0


def _parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Sandbox Tester from a capability context JSON file."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the serialized CapabilityContext JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Directory where report.json, done.json, and status.ndjson are written. "
            "Defaults to output_directory from the config file."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress to stdout.",
    )
    parser.add_argument(
        "--serialize-evidence",
        action="store_true",
        help="Include captured evidence in report.json.",
    )
    return parser.parse_args(arguments)


def _get_output_directory(
    config_path: Path,
    output_directory: Path | None,
) -> Path:
    if output_directory is not None:
        return output_directory.expanduser().resolve()

    config = json.loads(config_path.read_text(encoding="utf-8"))
    configured_output_directory = config.get("output_directory")

    if not configured_output_directory:
        raise ValueError(
            "No --output directory was provided, and config.json does not include "
            "output_directory."
        )

    return Path(configured_output_directory)


def _create_reporter(output_directory: Path, verbose: bool) -> TestReporter:
    console_reporter = ConsoleReporter() if verbose else QuietReporter()
    status_path = output_directory / "status.ndjson"
    return CompositeReporter(
        [
            console_reporter,
            StatusFileReporter(status_path),
        ]
    )
