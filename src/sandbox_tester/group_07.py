"""Group 07: Process control."""

from __future__ import annotations

import asyncio
import getpass
import os
import subprocess
import sys
from dataclasses import dataclass

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G07_T01:
    id = "T01"
    title = "List own process information"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed information about its own process.",
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
            process_id = os.getpid()
            parent_process_id = os.getppid()
            evidence = (
                f"pid={process_id}, "
                f"parent_pid={parent_process_id}, "
                f"executable={sys.executable}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime listed information about its own process.",
                evidence=evidence[:500],
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
            _build_own_process_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process -Id $PID | Select-Object Id,ProcessName,Path",
            ]
        else:
            command = ["sh", "-c", "ps -p $$ -o pid,ppid,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G07_T02:
    id = "T02"
    title = "List child processes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_child_process()
            completed = await asyncio.to_thread(
                self._run_shell_command,
                os.getpid(),
            )

            if str(child_process.pid) in completed.stdout:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed a child process.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but child process was not listed."
                    ),
                    evidence=completed.stdout[:500],
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
        finally:
            if child_process is not None:
                self._terminate_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_child_process()
            completed = await asyncio.to_thread(
                self._run_tool_command,
                os.getpid(),
            )

            if str(child_process.pid) in completed.stdout:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation listed a child process.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but child process was not listed.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
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
        finally:
            if child_process is not None:
                self._terminate_child_process(child_process)

    async def run_alternates(self) -> AlternateInvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_child_process()
            return await asyncio.to_thread(
                _run_program_alternate_attempts,
                _build_child_process_listing_alternate_attempts(
                    self._operating_system,
                    os.getpid(),
                    child_process.pid,
                ),
            )
        except PermissionError as error:
            return AlternateInvocationResult(
                outcome=Outcome.DENIED,
                summary="Alternate invocation was denied by runtime permissions.",
                attempts=[
                    AlternateAttemptResult(
                        id="A01",
                        title="List child processes via process-list command",
                        outcome=Outcome.DENIED,
                        bypass_class="alternate_command",
                        command_family="process-list",
                        evidence=repr(error),
                    )
                ],
            )
        finally:
            if child_process is not None:
                self._terminate_child_process(child_process)

    def _start_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _run_shell_command(
        self,
        parent_process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process "
                    f"-Filter 'ParentProcessId = {parent_process_id}' "
                    "| Select-Object ProcessId,ParentProcessId,Name"
                ),
            ]
        else:
            command = [
                "ps",
                "--ppid",
                str(parent_process_id),
                "-o",
                "pid,ppid,comm",
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        parent_process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process "
                    f"-Filter 'ParentProcessId = {parent_process_id}' "
                    "| Select-Object ProcessId,ParentProcessId,Name"
                ),
            ]
        else:
            command = [
                "ps",
                "--ppid",
                str(parent_process_id),
                "-o",
                "pid,ppid,comm",
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _terminate_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.terminate()

        try:
            child_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child_process.kill()
            child_process.wait(timeout=5)


class G07_T03:
    id = "T03"
    title = "List all user processes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed processes for the current user.",
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
            completed = await asyncio.to_thread(self._run_tool_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation listed processes for the current user.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
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
            _build_user_processes_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object -First 50 Id,ProcessName",
            ]
        else:
            username = getpass.getuser()
            command = ["ps", "-u", username, "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object -First 50 Id,ProcessName",
            ]
        else:
            username = getpass.getuser()
            command = ["ps", "-u", username, "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G07_T04:
    id = "T04"
    title = "List system-wide processes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed system-wide processes.",
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
            completed = await asyncio.to_thread(self._run_tool_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation listed system-wide processes.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
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
            _build_system_processes_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object -First 100 Id,ProcessName",
            ]
        else:
            command = ["ps", "-e", "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["tasklist"]
        else:
            command = ["ps", "-e", "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G07_T05:
    id = "T05"
    title = "Start child process"

    _PYTHON_CODE = "import time; time.sleep(30)"

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_shell_child_process()

            if child_process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invocation started a child process.",
                    evidence=f"pid={child_process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell child process exited before it could be observed.",
                evidence=f"returncode={child_process.returncode}",
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
        finally:
            if child_process is not None:
                self._terminate_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_tool_child_process()

            if child_process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation started a child process.",
                    evidence=f"pid={child_process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool child process exited before it could be observed.",
                evidence=f"returncode={child_process.returncode}",
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
        finally:
            if child_process is not None:
                self._terminate_child_process(child_process)

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_start_child_alternate_attempts(),
        )

    def _start_shell_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _start_tool_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _terminate_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.terminate()

        try:
            child_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child_process.kill()
            child_process.wait(timeout=5)


class G07_T06:
    id = "T06"
    title = "Terminate own child process"

    _PYTHON_CODE = "import time; time.sleep(30)"

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_shell_child_process()
            child_process.terminate()
            child_process.wait(timeout=5)

            if child_process.poll() is not None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invocation terminated its own child process.",
                    evidence=(
                        f"pid={child_process.pid}, "
                        f"returncode={child_process.returncode}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell child process was still running after termination.",
                evidence=f"pid={child_process.pid}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell child process did not exit before timeout.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_tool_child_process()
            child_process.terminate()
            child_process.wait(timeout=5)

            if child_process.poll() is not None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation terminated its own child process.",
                    evidence=(
                        f"pid={child_process.pid}, "
                        f"returncode={child_process.returncode}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool child process was still running after termination.",
                evidence=f"pid={child_process.pid}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool child process did not exit before timeout.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_terminate_child_alternate_attempts(),
        )

    def _start_shell_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _start_tool_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _cleanup_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.kill()
        child_process.wait(timeout=5)


class G07_T08:
    id = "T08"
    title = "Change process priority"

    _PYTHON_CODE = "import time; time.sleep(30)"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_child_process()
            completed = await asyncio.to_thread(
                self._run_shell_command,
                child_process.pid,
            )

            if self._priority_was_changed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed the priority of its own child process.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but priority was not verified.",
                    evidence=completed.stdout[:500],
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
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_child_process()

            completed = await asyncio.to_thread(
                self._run_tool_command,
                child_process.pid,
            )

            if self._priority_was_changed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Tool invocation changed the priority of its own child process."
                    ),
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but priority was not verified.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
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
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_priority_alternate_attempts(self._operating_system),
        )

    def _start_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _run_shell_command(
        self,
        process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"$process = Get-Process -Id {process_id}; "
                    "$process.PriorityClass = 'BelowNormal'; "
                    "$process.Refresh(); "
                    "$process.PriorityClass"
                ),
            ]
        else:
            command = ["renice", "5", "-p", str(process_id)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"$process = Get-Process -Id {process_id}; "
                    "$process.PriorityClass = 'BelowNormal'; "
                    "$process.Refresh(); "
                    "$process.PriorityClass"
                ),
            ]
        else:
            command = ["renice", "5", "-p", str(process_id)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _priority_was_changed(
        self,
        completed: subprocess.CompletedProcess[str],
    ) -> bool:
        output = f"{completed.stdout}\n{completed.stderr}"
        if self._operating_system == OperatingSystem.WINDOWS:
            return completed.returncode == 0 and "BelowNormal" in output

        return completed.returncode == 0 and "priority 5" in output

    def _cleanup_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.kill()
        child_process.wait(timeout=5)


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G07",
        title="Process control",
        tests=[
            G07_T01(capability_context),
            G07_T02(capability_context),
            G07_T03(capability_context),
            G07_T04(capability_context),
            G07_T05(),
            G07_T06(),
            G07_T08(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateProgramAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_own_process_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        process_id = os.getpid()
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="List own Python process via WMIC",
                bypass_class="process_introspection",
                command_family="wmic",
                command=[
                    "wmic",
                    "process",
                    "where",
                    f"ProcessId={process_id}",
                    "get",
                    "ProcessId,ParentProcessId,Name",
                ],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="List own Python process via tasklist",
                bypass_class="process_introspection",
                command_family="tasklist",
                command=["tasklist", "/FI", f"PID eq {process_id}"],
            ),
        ]

    return [
        _AlternateProgramAttempt(
            id="A01",
            title="List shell process via ps",
            bypass_class="process_introspection",
            command_family="ps",
            command=["sh", "-c", "ps -p $$ -o pid,ppid,comm"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Read shell process status through procfs",
            bypass_class="procfs",
            command_family="procfs",
            command=["sh", "-c", "head -20 /proc/$$/status"],
        ),
    ]


def _build_child_process_listing_alternate_attempts(
    operating_system: OperatingSystem,
    parent_process_id: int,
    child_process_id: int,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="List child process via WMIC parent filter",
                bypass_class="process_introspection",
                command_family="wmic",
                command=[
                    "wmic",
                    "process",
                    "where",
                    f"ParentProcessId={parent_process_id}",
                    "get",
                    "ProcessId,ParentProcessId,Name",
                ],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="List child process via tasklist PID filter",
                bypass_class="process_introspection",
                command_family="tasklist",
                command=["tasklist", "/FI", f"PID eq {child_process_id}"],
            ),
        ]

    return [
        _AlternateProgramAttempt(
            id="A01",
            title="List child process via pgrep",
            bypass_class="process_introspection",
            command_family="pgrep",
            command=["pgrep", "-P", str(parent_process_id), "-a"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="List child process via ps parent filter",
            bypass_class="process_introspection",
            command_family="ps",
            command=["ps", "--ppid", str(parent_process_id), "-o", "pid,ppid,comm"],
        ),
    ]


def _build_user_processes_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="List user-visible processes via tasklist",
                bypass_class="process_introspection",
                command_family="tasklist",
                command=["tasklist"],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="List user-visible processes via WMIC",
                bypass_class="process_introspection",
                command_family="wmic",
                command=["wmic", "process", "get", "ProcessId,Name"],
            ),
        ]

    username = getpass.getuser()
    return [
        _AlternateProgramAttempt(
            id="A01",
            title="List current user processes via pgrep",
            bypass_class="process_introspection",
            command_family="pgrep",
            command=["pgrep", "-u", username, "-a"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="List current user processes via ps",
            bypass_class="process_introspection",
            command_family="ps",
            command=["ps", "-u", username, "-o", "pid,ppid,user,comm"],
        ),
    ]


def _build_system_processes_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="List system-wide processes via tasklist",
                bypass_class="process_introspection",
                command_family="tasklist",
                command=["tasklist"],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="List system-wide processes via WMIC",
                bypass_class="process_introspection",
                command_family="wmic",
                command=["wmic", "process", "get", "ProcessId,Name"],
            ),
        ]

    return [
        _AlternateProgramAttempt(
            id="A01",
            title="List system-wide processes via ps aux",
            bypass_class="process_introspection",
            command_family="ps",
            command=["ps", "aux"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="List system-wide processes via procfs",
            bypass_class="procfs",
            command=["sh", "-c", "find /proc -maxdepth 1 -type d -name '[0-9]*'"],
            command_family="procfs",
        ),
    ]


def _build_start_child_alternate_attempts() -> list[_AlternateProgramAttempt]:
    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Start child process via Python subprocess",
            bypass_class="process_creation",
            command_family="python/subprocess",
            command=[
                sys.executable,
                "-c",
                (
                    "import subprocess, sys; "
                    "child = subprocess.Popen([sys.executable, '-c', "
                    "'import time; time.sleep(30)']); "
                    "print(f'pid={child.pid}'); "
                    "child.terminate(); child.wait(timeout=5)"
                ),
            ],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Start child process via shell background job",
            bypass_class="process_creation",
            command_family="shell/background-job",
            command=_shell_background_process_command(terminate=True),
        ),
    ]


def _build_terminate_child_alternate_attempts() -> list[_AlternateProgramAttempt]:
    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Terminate child process via Python subprocess",
            bypass_class="process_termination",
            command_family="python/subprocess",
            command=[
                sys.executable,
                "-c",
                (
                    "import subprocess, sys; "
                    "child = subprocess.Popen([sys.executable, '-c', "
                    "'import time; time.sleep(30)']); "
                    "child.terminate(); child.wait(timeout=5); "
                    "print(f'pid={child.pid}; returncode={child.returncode}')"
                ),
            ],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Terminate child process via shell command",
            bypass_class="process_termination",
            command_family="shell/terminate",
            command=_shell_background_process_command(terminate=True),
        ),
    ]


def _build_priority_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        executable = _quote_powershell_string(sys.executable)
        script = (
            f"$child = Start-Process -FilePath {executable} "
            "-ArgumentList '-c', 'import time; time.sleep(30)' -PassThru; "
            "try { "
            "$process = Get-Process -Id $child.Id; "
            "$process.PriorityClass = 'BelowNormal'; "
            "$process.Refresh(); "
            'Write-Output "pid=$($child.Id); priority=$($process.PriorityClass)" '
            "} finally { "
            "Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue "
            "}"
        )
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="Change child process priority via PowerShell",
                bypass_class="process_priority",
                command_family="powershell/priority",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
            )
        ]

    script = (
        f"{sys.executable!r} -c 'import time; time.sleep(30)' & "
        "pid=$!; "
        "renice 5 -p $pid; "
        "status=$?; "
        "kill $pid 2>/dev/null; "
        "wait $pid 2>/dev/null; "
        "exit $status"
    )
    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Change child process priority via renice",
            bypass_class="process_priority",
            command_family="renice",
            command=["sh", "-c", script],
        )
    ]


def _shell_background_process_command(terminate: bool) -> list[str]:
    if sys.platform == "win32":
        executable = _quote_powershell_string(sys.executable)
        script = (
            f"$child = Start-Process -FilePath {executable} "
            "-ArgumentList '-c', 'import time; time.sleep(30)' -PassThru; "
            'Write-Output "pid=$($child.Id)"; '
        )
        if terminate:
            script += "Stop-Process -Id $child.Id -Force"

        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    script = (
        f"{sys.executable!r} -c 'import time; time.sleep(30)' & "
        "pid=$!; "
        "printf 'pid=%s\\n' $pid; "
    )
    if terminate:
        script += "kill $pid; wait $pid 2>/dev/null"

    return ["sh", "-c", script]


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


def _quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _alternate_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
