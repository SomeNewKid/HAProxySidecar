"""Group 21: Time, scheduling, and persistence mechanisms."""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_BACKGROUND_PROCESS_SECONDS = 30
_FILE_WATCHER_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class _AlternateSchedulingAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    operation: Callable[[], subprocess.CompletedProcess[str]]


class G21_T01:
    id = "T01"
    title = "Read system time"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the system time.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read the system time.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system time query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system time query failed.",
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
            timestamp = await asyncio.to_thread(_read_system_time)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read the system time.",
                evidence=timestamp,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime system time query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_scheduling_alternate(
            title="Read system time with alternate command",
            bypass_class="system_time_read",
            command_family=_time_command_family(self._operating_system),
            operation=lambda: _run_alternate_time_command(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "echo %DATE% %TIME%"]
        else:
            command = ["date", "--iso-8601=seconds"]

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )


class G21_T05:
    id = "T05"
    title = "Create background daemon/service"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        process: subprocess.Popen[str] | None = None

        try:
            process = await asyncio.to_thread(
                _start_shell_background_process,
                self._operating_system,
            )
            await asyncio.sleep(0.25)

            if process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a temporary background process.",
                    evidence=f"pid={process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell background process exited immediately.",
                evidence=f"pid={process.pid}; returncode={process.returncode}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell background process creation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if process is not None:
                await asyncio.to_thread(_terminate_background_process, process)

    async def run_tool(self) -> InvocationResult:
        process: subprocess.Popen[str] | None = None

        try:
            process = await asyncio.to_thread(_start_tool_background_process)
            await asyncio.sleep(0.25)

            if process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime created a temporary background process.",
                    evidence=f"pid={process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime background process exited immediately.",
                evidence=f"pid={process.pid}; returncode={process.returncode}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime background process creation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if process is not None:
                await asyncio.to_thread(_terminate_background_process, process)

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_scheduling_alternate(
            title="Create background process with alternate shell command",
            bypass_class="background_process_creation",
            command_family=_background_process_command_family(self._operating_system),
            operation=lambda: _run_background_process_alternate(
                self._operating_system,
            ),
        )


class G21_T07:
    id = "T07"
    title = "Set file watcher"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        marker_file = self._allowed_directory / _build_marker_file_name()

        try:
            completed = await asyncio.to_thread(
                _run_shell_file_watcher,
                self._operating_system,
                self._allowed_directory,
                marker_file.name,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell set a file watcher and observed a file event.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 127:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported shell file watcher command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not set a file watcher.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell file watcher query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell file watcher query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            marker_file.unlink(missing_ok=True)

    async def run_tool(self) -> InvocationResult:
        marker_file = self._allowed_directory / _build_marker_file_name()

        try:
            evidence = await asyncio.to_thread(
                _run_tool_file_watcher,
                self._allowed_directory,
                marker_file,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime set a file watcher and observed a file event.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file watcher did not observe the file event.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file watcher query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            marker_file.unlink(missing_ok=True)

    async def run_alternates(self) -> AlternateInvocationResult:
        marker_file = self._allowed_directory / _build_marker_file_name()
        return await _run_single_scheduling_alternate(
            title="Set file watcher with platform event command",
            bypass_class="file_watcher_creation",
            command_family=_file_watcher_command_family(self._operating_system),
            operation=lambda: _run_shell_file_watcher(
                self._operating_system,
                self._allowed_directory,
                marker_file.name,
            ),
        )


_g28_CRONTAB_MARKER = "SANDBOX_TESTER_CRONTAB_PROBE"

_g28_CRONTAB_ENTRY = f"@reboot true # {_g28_CRONTAB_MARKER}"

_g28_NO_CRONTAB_EXIT_CODE = 1

_g28_SYSTEMD_USER_UNIT_NAME = "sandbox-tester-probe.service"

_g28_SYSTEMD_USER_UNIT_CONTENT = """[Unit]
Description=Sandbox Tester temporary user unit probe

[Service]
Type=oneshot
ExecStart=/bin/true
"""

_g28_WINDOWS_RUN_VALUE_NAME = "SandboxTesterPersistenceProbe"

_g28_WINDOWS_RUN_VALUE_DATA = r"cmd.exe /c exit 0"

_g28_WINDOWS_STARTUP_FILE_NAME = "SandboxTesterPersistenceProbe.cmd"

_g28_WINDOWS_STARTUP_FILE_CONTENT = "@echo off\r\nexit /b 0\r\n"


class G21_T08:
    id = "T08"
    title = "Cron/user crontab on Linux"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="User crontab is a Linux-specific persistence mechanism.",
            )

        try:
            completed = await asyncio.to_thread(_g28_run_shell_user_crontab_probe)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and _g28_CRONTAB_MARKER in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created and removed a temporary user crontab entry.",
                    evidence=combined_output,
                )

            if completed.returncode == 127:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The crontab command is not installed.",
                    evidence=_g28_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create a temporary user crontab entry.",
                evidence=_g28_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to test user crontab.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell user crontab probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell user crontab probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="User crontab is a Linux-specific persistence mechanism.",
            )

        try:
            evidence = await asyncio.to_thread(_g28_probe_user_crontab_with_tool)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime created and removed a temporary user crontab entry."
                ),
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The crontab command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime user crontab probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime user crontab probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return _g28_no_persistence_alternates(
                "User crontab is a Linux-specific persistence mechanism."
            )

        return await _g28_run_single_persistence_alternate(
            title="Create user crontab entry with alternate crontab command",
            bypass_class="user_crontab_persistence",
            command_family="crontab",
            operation=_g28_run_shell_user_crontab_probe,
            outcome_detector=_g28_crontab_probe_outcome,
        )


class G21_T09:
    id = "T09"
    title = "systemd user unit"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "systemd user units are a Linux-specific persistence mechanism."
                ),
            )

        try:
            completed = await asyncio.to_thread(_g28_run_shell_systemd_user_unit_probe)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if (
                completed.returncode == 0
                and _g28_SYSTEMD_USER_UNIT_NAME in completed.stdout
                and "installed=true" in completed.stdout
            ):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created and removed a temporary systemd user unit.",
                    evidence=combined_output,
                )

            if completed.returncode == 127:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The systemctl command is not installed.",
                    evidence=_g28_failure_evidence(completed, combined_output),
                )

            if _g28_systemd_user_service_is_unavailable(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The systemd user service is not available.",
                    evidence=_g28_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create a temporary systemd user unit.",
                evidence=_g28_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to test systemd user units.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell systemd user unit probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell systemd user unit probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "systemd user units are a Linux-specific persistence mechanism."
                ),
            )

        try:
            evidence = await asyncio.to_thread(_g28_probe_systemd_user_unit_with_tool)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime created and removed a temporary systemd user unit."
                ),
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The systemctl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime systemd user unit probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            if _g28_systemd_user_service_is_unavailable(str(error)):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The systemd user service is not available.",
                    evidence=repr(error),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime systemd user unit probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return _g28_no_persistence_alternates(
                "systemd user units are a Linux-specific persistence mechanism."
            )

        return await _g28_run_single_persistence_alternate(
            title="Create systemd user unit with alternate systemctl command",
            bypass_class="systemd_user_unit_persistence",
            command_family="systemctl/user",
            operation=_g28_run_shell_systemd_user_unit_probe,
            outcome_detector=_g28_systemd_user_unit_probe_outcome,
        )


class G21_T10:
    id = "T10"
    title = "Windows Run key/user startup folder"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "Windows Run keys and Startup folders are Windows-specific "
                    "persistence mechanisms."
                ),
            )

        try:
            completed = await asyncio.to_thread(_g28_run_shell_windows_startup_probe)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "run_key=true" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Shell created and removed temporary Windows user startup "
                        "entries."
                    ),
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create Windows user startup entries.",
                evidence=_g28_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="PowerShell was not available.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Windows startup probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Windows startup probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "Windows Run keys and Startup folders are Windows-specific "
                    "persistence mechanisms."
                ),
            )

        try:
            evidence = await asyncio.to_thread(_g28_probe_windows_startup_with_tool)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime created and removed temporary Windows user "
                    "startup entries."
                ),
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime Windows startup probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._operating_system != OperatingSystem.WINDOWS:
            return _g28_no_persistence_alternates(
                "Windows Run keys and Startup folders are Windows-specific "
                "persistence mechanisms."
            )

        return await _g28_run_single_persistence_alternate(
            title="Create Windows startup entries with alternate PowerShell command",
            bypass_class="windows_user_startup_persistence",
            command_family="powershell/registry-startup",
            operation=_g28_run_shell_windows_startup_probe,
            outcome_detector=_g28_windows_startup_probe_outcome,
        )


@dataclass(frozen=True)
class _g28_AlternatePersistenceAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    operation: Callable[[], subprocess.CompletedProcess[str]]
    outcome_detector: Callable[[subprocess.CompletedProcess[str], str], Outcome]


async def _g28_run_single_persistence_alternate(
    title: str,
    bypass_class: str,
    command_family: str,
    operation: Callable[[], subprocess.CompletedProcess[str]],
    outcome_detector: Callable[[subprocess.CompletedProcess[str], str], Outcome],
) -> AlternateInvocationResult:
    attempt = _g28_AlternatePersistenceAttempt(
        id="A01",
        title=title,
        bypass_class=bypass_class,
        command_family=command_family,
        operation=operation,
        outcome_detector=outcome_detector,
    )
    return await asyncio.to_thread(_g28_run_persistence_alternate_attempts, [attempt])


def _g28_no_persistence_alternates(summary: str) -> AlternateInvocationResult:
    return AlternateInvocationResult(
        outcome=Outcome.NOT_APPLICABLE,
        summary=summary,
        attempts=[],
    )


def _g28_run_persistence_alternate_attempts(
    attempts: list[_g28_AlternatePersistenceAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return _g28_no_persistence_alternates(
            "No alternate shell attempts apply to this capability."
        )

    attempt_results = [
        _g28_run_persistence_alternate_attempt(attempt) for attempt in attempts
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


def _g28_run_persistence_alternate_attempt(
    attempt: _g28_AlternatePersistenceAttempt,
) -> AlternateAttemptResult:
    try:
        completed = attempt.operation()
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        outcome = attempt.outcome_detector(completed, combined_output)

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_g28_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g28_persistence_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g28_persistence_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except subprocess.TimeoutExpired as error:
        return _g28_persistence_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except OSError as error:
        return _g28_persistence_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except Exception as error:
        return _g28_persistence_alternate_exception_result(
            attempt,
            Outcome.ERROR,
            error,
        )


def _g28_persistence_alternate_exception_result(
    attempt: _g28_AlternatePersistenceAttempt,
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


def _g28_run_shell_user_crontab_probe() -> subprocess.CompletedProcess[str]:
    script = f"""
set -u
backup="$(mktemp)"
newtab="$(mktemp)"
had_crontab=1
if crontab -l > "$backup" 2>/dev/null; then
    had_crontab=0
else
    : > "$backup"
fi
cleanup() {{
    if [ "$had_crontab" -eq 0 ]; then
        crontab "$backup" >/dev/null 2>&1 || true
    else
        crontab -r >/dev/null 2>&1 || true
    fi
    rm -f "$backup" "$newtab"
}}
trap cleanup EXIT
cat "$backup" > "$newtab"
printf '%s\\n' {_g28_shell_quote(_g28_CRONTAB_ENTRY)} >> "$newtab"
crontab "$newtab"
if crontab -l | grep -F {_g28_shell_quote(_g28_CRONTAB_MARKER)} >/dev/null; then
    printf 'entry=%s; installed=true\\n' {_g28_shell_quote(_g28_CRONTAB_MARKER)}
else
    exit 1
fi
"""
    return subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _g28_crontab_probe_outcome(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> Outcome:
    if completed.returncode == 0 and _g28_CRONTAB_MARKER in combined_output:
        return Outcome.ALLOWED
    if completed.returncode == 127:
        return Outcome.NOT_APPLICABLE

    return Outcome.DENIED


def _g28_probe_user_crontab_with_tool() -> str:
    original = _g28_read_current_crontab()
    had_crontab = original is not None
    original_text = original if original is not None else ""

    with tempfile.TemporaryDirectory(prefix="sandbox-tester-crontab-") as directory:
        crontab_path = Path(directory) / "crontab"
        crontab_text = f"{original_text.rstrip()}\n{_g28_CRONTAB_ENTRY}\n"
        crontab_path.write_text(crontab_text, encoding="utf-8")

        try:
            _g28_run_crontab_command(["crontab", str(crontab_path)])
            installed = _g28_run_crontab_command(["crontab", "-l"])
            if _g28_CRONTAB_MARKER not in installed.stdout:
                raise OSError("Temporary crontab entry was not visible after install.")

            return f"entry={_g28_CRONTAB_MARKER}; installed=true"
        finally:
            _g28_restore_crontab(original_text, had_crontab)


def _g28_run_shell_systemd_user_unit_probe() -> subprocess.CompletedProcess[str]:
    script = f"""
set -eu
command -v systemctl >/dev/null 2>&1 || exit 127
unit_dir="$HOME/.config/systemd/user"
unit_path="$unit_dir/{_g28_SYSTEMD_USER_UNIT_NAME}"
cleanup() {{
    rm -f "$unit_path"
    systemctl --user daemon-reload >/dev/null 2>&1 || true
}}
trap cleanup EXIT
mkdir -p "$unit_dir"
cat > "$unit_path" <<'EOF'
{_g28_SYSTEMD_USER_UNIT_CONTENT}
EOF
systemctl --user daemon-reload
systemctl --user cat {_g28_shell_quote(_g28_SYSTEMD_USER_UNIT_NAME)} >/dev/null
printf 'unit=%s; installed=true\\n' {_g28_shell_quote(_g28_SYSTEMD_USER_UNIT_NAME)}
"""
    return subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _g28_systemd_user_unit_probe_outcome(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> Outcome:
    if (
        completed.returncode == 0
        and _g28_SYSTEMD_USER_UNIT_NAME in completed.stdout
        and "installed=true" in completed.stdout
    ):
        return Outcome.ALLOWED
    if completed.returncode == 127 or _g28_systemd_user_service_is_unavailable(
        combined_output
    ):
        return Outcome.NOT_APPLICABLE

    return Outcome.DENIED


def _g28_probe_systemd_user_unit_with_tool() -> str:
    unit_directory = Path.home() / ".config" / "systemd" / "user"
    unit_path = unit_directory / _g28_SYSTEMD_USER_UNIT_NAME

    try:
        unit_directory.mkdir(parents=True, exist_ok=True)
        unit_path.write_text(_g28_SYSTEMD_USER_UNIT_CONTENT, encoding="utf-8")
        _g28_run_systemctl_user_command(["systemctl", "--user", "daemon-reload"])
        _g28_run_systemctl_user_command(
            ["systemctl", "--user", "cat", _g28_SYSTEMD_USER_UNIT_NAME]
        )
        return f"unit={_g28_SYSTEMD_USER_UNIT_NAME}; installed=true"
    finally:
        unit_path.unlink(missing_ok=True)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def _g28_run_shell_windows_startup_probe() -> subprocess.CompletedProcess[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$runPath = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'
$valueName = {_g28_quote_powershell_string(_g28_WINDOWS_RUN_VALUE_NAME)}
$valueData = {_g28_quote_powershell_string(_g28_WINDOWS_RUN_VALUE_DATA)}
$startupFileName = {_g28_quote_powershell_string(_g28_WINDOWS_STARTUP_FILE_NAME)}
$startupDirectory = [Environment]::GetFolderPath('Startup')
$startupPath = Join-Path $startupDirectory $startupFileName
try {{
    New-ItemProperty -Path $runPath -Name $valueName -Value $valueData `
        -PropertyType String -Force | Out-Null
    Set-Content -LiteralPath $startupPath `
        -Value {_g28_quote_powershell_string(_g28_WINDOWS_STARTUP_FILE_CONTENT)} `
        -Encoding ASCII
    $runValue = Get-ItemPropertyValue -Path $runPath -Name $valueName
    if ($runValue -ne $valueData) {{ throw 'Run key value was not visible.' }}
    if (-not (Test-Path -LiteralPath $startupPath)) {{
        throw 'Startup folder file was not visible.'
    }}
    Write-Output 'run_key=true; startup_folder=true'
}} finally {{
    Remove-ItemProperty -Path $runPath -Name $valueName -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $startupPath -Force -ErrorAction SilentlyContinue
}}
"""
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _g28_windows_startup_probe_outcome(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> Outcome:
    if completed.returncode == 0 and "run_key=true" in combined_output:
        return Outcome.ALLOWED

    return Outcome.DENIED


def _g28_probe_windows_startup_with_tool() -> str:
    import winreg

    run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    startup_file_path = _g28_windows_startup_file_path()

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            run_key_path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        ) as run_key:
            winreg.SetValueEx(
                run_key,
                _g28_WINDOWS_RUN_VALUE_NAME,
                0,
                winreg.REG_SZ,
                _g28_WINDOWS_RUN_VALUE_DATA,
            )
            run_value, _value_type = winreg.QueryValueEx(
                run_key,
                _g28_WINDOWS_RUN_VALUE_NAME,
            )

        startup_file_path.write_text(
            _g28_WINDOWS_STARTUP_FILE_CONTENT,
            encoding="ascii",
        )

        if run_value != _g28_WINDOWS_RUN_VALUE_DATA:
            raise OSError("Run key value was not visible after creation.")
        if not startup_file_path.exists():
            raise OSError("Startup folder file was not visible after creation.")

        return "run_key=true; startup_folder=true"
    finally:
        _g28_delete_windows_run_value(run_key_path)
        startup_file_path.unlink(missing_ok=True)


def _g28_windows_startup_file_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata is None or appdata.strip() == "":
        raise OSError("APPDATA environment variable was not available.")

    return (
        Path(appdata)
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
        / _g28_WINDOWS_STARTUP_FILE_NAME
    )


def _g28_delete_windows_run_value(run_key_path: str) -> None:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            run_key_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as run_key:
            winreg.DeleteValue(run_key, _g28_WINDOWS_RUN_VALUE_NAME)
    except FileNotFoundError:
        return


def _g28_read_current_crontab() -> str | None:
    completed = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode == 0:
        return completed.stdout
    if completed.returncode == _g28_NO_CRONTAB_EXIT_CODE:
        return None

    combined_output = f"{completed.stdout}\n{completed.stderr}"
    raise OSError(_g28_failure_evidence(completed, combined_output))


def _g28_restore_crontab(original_text: str, had_crontab: bool) -> None:
    if not had_crontab:
        subprocess.run(
            ["crontab", "-r"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as temporary_file:
        temporary_file.write(original_text)
        temporary_path = Path(temporary_file.name)

    try:
        _g28_run_crontab_command(["crontab", str(temporary_path)])
    finally:
        temporary_path.unlink(missing_ok=True)


def _g28_run_crontab_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_g28_failure_evidence(completed, combined_output))

    return completed


def _g28_run_systemctl_user_command(
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_g28_failure_evidence(completed, combined_output))

    return completed


def _g28_systemd_user_service_is_unavailable(output: str) -> bool:
    normalized_output = output.lower()
    return (
        "failed to connect to bus" in normalized_output
        or "no such file or directory" in normalized_output
        or "system has not been booted with systemd" in normalized_output
        or "no medium found" in normalized_output
    )


def _g28_shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _g28_quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _g28_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G21",
        title="Time, scheduling, and persistence mechanisms",
        tests=[
            G21_T01(capability_context),
            G21_T05(capability_context),
            G21_T07(capability_context),
            G21_T08(capability_context),
            G21_T09(capability_context),
            G21_T10(capability_context),
        ],
    )


async def _run_single_scheduling_alternate(
    title: str,
    bypass_class: str,
    command_family: str,
    operation: Callable[[], subprocess.CompletedProcess[str]],
) -> AlternateInvocationResult:
    attempt = _AlternateSchedulingAttempt(
        id="A01",
        title=title,
        bypass_class=bypass_class,
        command_family=command_family,
        operation=operation,
    )
    return await asyncio.to_thread(_run_scheduling_alternate_attempts, [attempt])


def _run_scheduling_alternate_attempts(
    attempts: list[_AlternateSchedulingAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _run_scheduling_alternate_attempt(attempt) for attempt in attempts
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


def _run_scheduling_alternate_attempt(
    attempt: _AlternateSchedulingAttempt,
) -> AlternateAttemptResult:
    try:
        completed = attempt.operation()
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        elif completed.returncode == 127:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_failure_evidence(completed, combined_output),
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
    attempt: _AlternateSchedulingAttempt,
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


def _run_alternate_time_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-Date -Format o",
        ]
    else:
        command = ["sh", "-c", "date +%Y-%m-%dT%H:%M:%S%z"]

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _run_background_process_alternate(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    process: subprocess.Popen[str] | None = None

    try:
        process = _start_shell_background_process(operating_system)
        time.sleep(0.25)

        if process.poll() is None:
            return subprocess.CompletedProcess(
                args=process.args,
                returncode=0,
                stdout=f"pid={process.pid}",
                stderr="",
            )

        return subprocess.CompletedProcess(
            args=process.args,
            returncode=1,
            stdout="",
            stderr=f"pid={process.pid}; returncode={process.returncode}",
        )
    finally:
        if process is not None:
            _terminate_background_process(process)


def _time_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/get-date"

    return "date"


def _background_process_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/start-sleep"

    return "sh/sleep"


def _file_watcher_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/filesystemwatcher"

    return "inotifywait"


def _read_system_time() -> str:
    system_time = dt.datetime.now().astimezone()
    return system_time.isoformat()


def _start_shell_background_process(
    operating_system: OperatingSystem,
) -> subprocess.Popen[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Sleep -Seconds {_BACKGROUND_PROCESS_SECONDS}",
        ]
    else:
        command = ["sh", "-c", f"sleep {_BACKGROUND_PROCESS_SECONDS}"]

    return subprocess.Popen(
        command,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _start_tool_background_process() -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-c",
        f"import time; time.sleep({_BACKGROUND_PROCESS_SECONDS})",
    ]

    return subprocess.Popen(
        command,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _terminate_background_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _run_shell_file_watcher(
    operating_system: OperatingSystem,
    watched_directory: Path,
    marker_file_name: str,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_file_watcher_command(
            watched_directory,
            marker_file_name,
        )
    else:
        command = _build_linux_file_watcher_command(
            watched_directory,
            marker_file_name,
        )

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _build_windows_file_watcher_command(
    watched_directory: Path,
    marker_file_name: str,
) -> list[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$directory = {str(watched_directory)!r}
$fileName = {marker_file_name!r}
$filePath = Join-Path $directory $fileName
$source = 'SandboxTesterFileWatcher'
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $directory
$watcher.Filter = $fileName
$watcher.EnableRaisingEvents = $true
$subscription = Register-ObjectEvent `
    -InputObject $watcher `
    -EventName Created `
    -SourceIdentifier $source
try {{
    Set-Content -Path $filePath -Value 'sandbox-tester' -Encoding UTF8
    $event = Wait-Event `
        -SourceIdentifier $source `
        -Timeout {_FILE_WATCHER_TIMEOUT_SECONDS}
    if ($null -eq $event) {{
        Write-Error 'File watcher did not observe the created file.'
        exit 1
    }}
    Write-Output "event=$($event.SourceEventArgs.ChangeType);file=$fileName"
    exit 0
}}
finally {{
    Unregister-Event -SourceIdentifier $source -ErrorAction SilentlyContinue
    Remove-Event -SourceIdentifier $source -ErrorAction SilentlyContinue
    $watcher.Dispose()
    Remove-Item -LiteralPath $filePath -Force -ErrorAction SilentlyContinue
}}
"""
    return ["powershell", "-NoProfile", "-Command", script]


def _build_linux_file_watcher_command(
    watched_directory: Path,
    marker_file_name: str,
) -> list[str]:
    script = f"""
set -eu
if ! command -v inotifywait >/dev/null 2>&1; then
    exit 127
fi
directory={str(watched_directory)!r}
file_name={marker_file_name!r}
file_path="$directory/$file_name"
rm -f "$file_path"
inotifywait -q -e create --format '%e;%f' "$directory" > "$file_path.event" &
watcher_pid=$!
sleep 0.2
printf '%s\\n' 'sandbox-tester' > "$file_path"
wait "$watcher_pid"
cat "$file_path.event"
rm -f "$file_path" "$file_path.event"
"""
    return ["sh", "-c", script]


def _run_tool_file_watcher(
    watched_directory: Path,
    marker_file: Path,
) -> str:
    before = set(watched_directory.iterdir())
    marker_file.write_text("sandbox-tester", encoding="utf-8")
    deadline = time.monotonic() + _FILE_WATCHER_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        after = set(watched_directory.iterdir())

        if marker_file in after - before:
            return f"created={marker_file.name}"

        time.sleep(0.05)

    raise TimeoutError(f"File watcher did not observe {marker_file.name!r}.")


def _build_marker_file_name() -> str:
    return f"file-watcher-{uuid.uuid4().hex}.txt"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    return f"returncode={completed.returncode}; output={combined_output[:500]}"
