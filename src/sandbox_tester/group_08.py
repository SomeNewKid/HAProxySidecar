"""Group 08: Resource limits."""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G08_T01:
    id = "T01"
    title = "Query CPU count"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the CPU count.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            cpu_count = os.cpu_count()

            if cpu_count is None:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Python runtime could not determine CPU count.",
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the CPU count.",
                evidence=str(cpu_count),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_cpu_count_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "[Environment]::ProcessorCount",
            ]
        else:
            command = ["nproc"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G08",
        title="Resource limits",
        tests=[
            G08_T01(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateProgramAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_cpu_count_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="Query CPU count via cmd environment variable",
                bypass_class="resource_introspection",
                command_family="cmd/environment",
                command=["cmd", "/c", "echo %NUMBER_OF_PROCESSORS%"],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="Query CPU count via WMIC",
                bypass_class="resource_introspection",
                command_family="wmic",
                command=[
                    "wmic",
                    "cpu",
                    "get",
                    "NumberOfLogicalProcessors",
                    "/value",
                ],
            ),
        ]

    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Query CPU count via getconf",
            bypass_class="resource_introspection",
            command_family="getconf",
            command=["getconf", "_NPROCESSORS_ONLN"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Query CPU count via procfs",
            bypass_class="procfs",
            command_family="procfs",
            command=["sh", "-c", "grep -c '^processor' /proc/cpuinfo"],
        ),
        _AlternateProgramAttempt(
            id="A03",
            title="Query CPU count via lscpu",
            bypass_class="resource_introspection",
            command_family="lscpu",
            command=["sh", "-c", "lscpu | grep '^CPU(s):'"],
        ),
    ]


def _run_program_alternate_attempts(
    attempts: list[_AlternateProgramAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_program_alternate_attempt(attempt) for attempt in attempts]
    allowed_count = sum(
        1 for result in attempt_results if result.outcome == Outcome.ALLOWED
    )

    if allowed_count:
        outcome = Outcome.ALLOWED
        summary = (
            f"{allowed_count} of {len(attempt_results)} alternate shell attempts "
            "succeeded."
        )
    else:
        not_applicable_count = sum(
            1 for result in attempt_results if result.outcome == Outcome.NOT_APPLICABLE
        )
        if not_applicable_count == len(attempt_results):
            outcome = Outcome.NOT_APPLICABLE
            summary = "No alternate shell command was available."
        else:
            outcome = Outcome.DENIED
            summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _run_program_alternate_attempt(
    attempt: _AlternateProgramAttempt,
) -> AlternateAttemptResult:
    try:
        completed = subprocess.run(
            attempt.command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_alternate_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _alternate_exception_result(attempt, Outcome.ERROR, error)


def _alternate_exception_result(
    attempt: _AlternateProgramAttempt,
    outcome: Outcome,
    error: Exception,
) -> AlternateAttemptResult:
    return AlternateAttemptResult(
        id=attempt.id,
        title=attempt.title,
        outcome=outcome,
        bypass_class=attempt.bypass_class,
        command_family=attempt.command_family,
        evidence=repr(error),
    )


def _alternate_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
