"""Run the sandbox tester from serialized input files."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from .manager import run_all_groups
from .models import CapabilityGroupResult
from .reporter import TestReporter
from .testing import read_capability_context

_REMOVED_EVIDENCE = "[REMOVED]"


async def run_from_files(
    context_path: Path,
    output_directory: Path,
    reporter: TestReporter,
    serialize_evidence: bool = False,
) -> list[CapabilityGroupResult]:
    """Run tests from a serialized capability context and write output files."""
    output_directory.mkdir(parents=True, exist_ok=True)
    context = read_capability_context(context_path)
    if context.output_directory != output_directory:
        context = dataclasses.replace(context, output_directory=output_directory)

    results = await run_all_groups(context, reporter)

    report_path = output_directory / "report.json"
    done_path = output_directory / "done.json"
    report_data = _results_to_json_data(results, serialize_evidence)
    _write_json_atomically(report_path, report_data)
    _write_json_atomically(
        done_path,
        {
            "outcome": "completed",
            "report_path": str(report_path),
        },
    )

    return results


def _results_to_json_data(
    results: list[CapabilityGroupResult],
    serialize_evidence: bool = False,
) -> list[dict[str, object]]:
    data = [dataclasses.asdict(result) for result in results]
    if serialize_evidence:
        return data

    return [_remove_serialized_evidence(result) for result in data]


def _remove_serialized_evidence(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _REMOVED_EVIDENCE
            if key == "evidence"
            else _remove_serialized_evidence(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_remove_serialized_evidence(item) for item in value]

    return value


def _write_json_atomically(path: Path, data: object) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    json_text = json.dumps(data, indent=2, default=str)
    temporary_path.write_text(f"{json_text}\n", encoding="utf-8")
    temporary_path.replace(path)
