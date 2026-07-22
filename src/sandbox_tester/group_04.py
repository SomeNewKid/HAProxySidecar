"""Group 04: Filesystem persistence."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G04_T08:
    id = "T08"
    title = "Detect available disk space"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._working_directory = capability_context.working_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected available disk space.",
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
            disk_usage = shutil.disk_usage(self._working_directory)
            evidence = (
                f"total={disk_usage.total}, "
                f"used={disk_usage.used}, "
                f"free={disk_usage.free}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected available disk space.",
                evidence=evidence,
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
            _run_disk_space_alternate_attempts,
            _build_disk_space_alternate_attempts(
                self._operating_system,
                self._working_directory,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            drive_name = self._working_directory.drive.rstrip(":")
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"Get-PSDrive -Name '{drive_name}' | "
                    "Select-Object Name,Used,Free | Format-List"
                ),
            ]
        else:
            command = ["df", "-k", str(self._working_directory)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G04",
        title="Filesystem persistence",
        tests=[
            G04_T08(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateDiskSpaceAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_disk_space_alternate_attempts(
    operating_system: OperatingSystem,
    working_directory: Path,
) -> list[_AlternateDiskSpaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        drive_letter = working_directory.drive.rstrip(":")
        drive_id = f"{drive_letter}:"
        return [
            _AlternateDiskSpaceAttempt(
                id="A01",
                title="Detect disk space via WMIC logicaldisk",
                bypass_class="alternate_command",
                command_family="wmic",
                command=[
                    "wmic",
                    "logicaldisk",
                    "where",
                    f"DeviceID='{drive_id}'",
                    "get",
                    "DeviceID,FreeSpace,Size",
                ],
            ),
            _AlternateDiskSpaceAttempt(
                id="A02",
                title="Detect disk space via fsutil volume diskfree",
                bypass_class="alternate_command",
                command_family="fsutil",
                command=["fsutil", "volume", "diskfree", drive_id],
            ),
        ]

    return [
        _AlternateDiskSpaceAttempt(
            id="A01",
            title="Detect disk space via stat filesystem",
            bypass_class="alternate_command",
            command_family="stat",
            command=["stat", "-f", str(working_directory)],
        ),
        _AlternateDiskSpaceAttempt(
            id="A02",
            title="Detect disk space via POSIX df",
            bypass_class="alternate_command",
            command_family="df",
            command=["df", "-P", str(working_directory)],
        ),
    ]


def _run_disk_space_alternate_attempts(
    attempts: list[_AlternateDiskSpaceAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _run_disk_space_alternate_attempt(attempt) for attempt in attempts
    ]
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


def _run_disk_space_alternate_attempt(
    attempt: _AlternateDiskSpaceAttempt,
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
    attempt: _AlternateDiskSpaceAttempt,
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
