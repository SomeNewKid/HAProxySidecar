"""Group 06: Program and executable invocation."""

from __future__ import annotations

import asyncio
import ctypes
import importlib.util
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G06_T01:
    id = "T01"
    title = "Run harmless built-in command"

    _MESSAGE = "sandbox-tester"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran the harmless echo command.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran the harmless echo command.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_builtin_command_alternate_attempts(
                self._operating_system,
                self._MESSAGE,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "echo", self._MESSAGE]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "echo", self._MESSAGE]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_echoed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T02:
    id = "T02"
    title = "Run language interpreter"

    _MESSAGE = "sandbox-tester"
    _PYTHON_CODE = "print('sandbox-tester')"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran the Python language interpreter.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran the Python language interpreter.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_language_interpreter_alternate_attempts(
                self._operating_system,
                self._PYTHON_CODE,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_printed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T03:
    id = "T03"
    title = "Run shell command through shell"

    _MESSAGE = "sandbox-tester-shell"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran a command through the shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran a command through the shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_shell_command_alternate_attempts(
                self._operating_system,
                self._MESSAGE,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", f"echo {self._MESSAGE}"]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", f"echo {self._MESSAGE}"]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_echoed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T04:
    id = "T04"
    title = "Run command without shell"

    _MESSAGE = "sandbox-tester-direct"
    _PYTHON_CODE = "print('sandbox-tester-direct')"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invocation ran a command without a shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran a command without a shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_without_shell_alternate_attempts(
                self._operating_system,
                self._PYTHON_CODE,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )

    def _was_printed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T05:
    id = "T05"
    title = "Invoke package manager"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            return self._evaluate_result(completed, "Shell")
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
            return self._evaluate_result(completed, "Tool")
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
            _build_package_manager_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "pip", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "pip", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _evaluate_result(
        self,
        completed: subprocess.CompletedProcess[str],
        invocation_name: str,
    ) -> InvocationResult:
        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=f"{invocation_name} invocation ran the Python package manager.",
                evidence=completed.stdout.strip()[:500],
            )

        combined_output = f"{completed.stdout}\n{completed.stderr}"
        if "No module named pip" in combined_output:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The Python package manager is not installed.",
                evidence=combined_output.strip()[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{invocation_name} command failed.",
            evidence=combined_output.strip()[:500],
        )


class G06_T06:
    id = "T06"
    title = "Invoke compiler or build tool"

    _PYTHON_CODE = "print('sandbox-tester-compile')\n"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        source_file = self._create_source_file("shell")
        bytecode_file = self._get_bytecode_file(source_file)
        self._delete_existing_bytecode(bytecode_file)

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                source_file,
            )

            if bytecode_file.is_file():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invoked the Python compiler/build tool.",
                    evidence=str(bytecode_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but bytecode was not created.",
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

    async def run_tool(self) -> InvocationResult:
        source_file = self._create_source_file("tool")
        bytecode_file = self._get_bytecode_file(source_file)
        self._delete_existing_bytecode(bytecode_file)

        try:
            completed = await asyncio.to_thread(
                self._run_tool_command,
                source_file,
            )

            if bytecode_file.is_file():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation invoked the Python compiler/build tool.",
                    evidence=str(bytecode_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but bytecode was not created.",
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

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_compile_alternate_attempts(
                self._allowed_directory,
                self._PYTHON_CODE,
            ),
        )

    def _create_source_file(self, invocation_name: str) -> Path:
        unique_id = uuid.uuid4().hex
        source_file = (
            self._allowed_directory / f"g06_t06_{invocation_name}_{unique_id}.py"
        )
        source_file.write_text(self._PYTHON_CODE, encoding="utf-8")
        return source_file

    def _get_bytecode_file(self, source_file: Path) -> Path:
        bytecode_file_name = importlib.util.cache_from_source(str(source_file))
        return Path(bytecode_file_name)

    def _delete_existing_bytecode(self, bytecode_file: Path) -> None:
        if bytecode_file.exists():
            bytecode_file.unlink()

    def _run_shell_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "compileall", "-q", str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "compileall", "-q", str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G06_T07:
    id = "T07"
    title = "Invoke test runner"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            return self._evaluate_result(completed, "Shell")
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
            return self._evaluate_result(completed, "Tool")
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
            _build_test_runner_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "pytest", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "pytest", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _evaluate_result(
        self,
        completed: subprocess.CompletedProcess[str],
        invocation_name: str,
    ) -> InvocationResult:
        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=f"{invocation_name} invocation ran the pytest test runner.",
                evidence=completed.stdout.strip()[:500],
            )

        combined_output = f"{completed.stdout}\n{completed.stderr}"
        if "No module named pytest" in combined_output:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The pytest test runner is not installed.",
                evidence=combined_output.strip()[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{invocation_name} command failed.",
            evidence=combined_output.strip()[:500],
        )


class G06_T09:
    id = "T09"
    title = "Invoke system administration tool"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            return self._evaluate_result(completed, "Shell")
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The system administration tool is not installed.",
                evidence=repr(error),
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
            return self._evaluate_result(completed, "Tool")
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The system administration tool is not installed.",
                evidence=repr(error),
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
            _build_admin_tool_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = self._get_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = self._get_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _get_command(self) -> list[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            return ["sc.exe", "query"]

        return [
            "systemctl",
            "list-units",
            "--type=service",
            "--no-pager",
            "--plain",
        ]

    def _evaluate_result(
        self,
        completed: subprocess.CompletedProcess[str],
        invocation_name: str,
    ) -> InvocationResult:
        output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    f"{invocation_name} invocation ran a system administration tool."
                ),
                evidence=output[:500],
            )

        if self._is_tool_absent(output):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The system administration tool is not installed.",
                evidence=output[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{invocation_name} command failed.",
            evidence=output[:500],
        )

    def _is_tool_absent(self, output: str) -> bool:
        absent_markers = (
            "is not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in absent_markers)


class G06_T11:
    id = "T11"
    title = "Run newly created script"

    _MESSAGE = "sandbox-tester-script"
    _PYTHON_CODE = "print('sandbox-tester-script')\n"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        source_file = self._create_source_file("shell")

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                source_file,
            )

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran a newly created script.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        source_file = self._create_source_file("tool")

        try:
            completed = await asyncio.to_thread(
                self._run_tool_command,
                source_file,
            )

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran a newly created script.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_program_alternate_attempts,
            _build_new_script_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._PYTHON_CODE,
            ),
        )

    def _create_source_file(self, invocation_name: str) -> Path:
        unique_id = uuid.uuid4().hex
        source_file = (
            self._allowed_directory / f"g06_t11_{invocation_name}_{unique_id}.py"
        )
        source_file.write_text(self._PYTHON_CODE, encoding="utf-8")
        return source_file

    def _run_shell_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_printed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


_g27_RUNTIME_MODULE_SENTINEL = "sandbox-tester-runtime-import"


class G06_T12:
    id = "T12"
    title = "Load system native library"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g27_run_shell_native_library_load,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell loaded a system native library.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not load a system native library.",
                evidence=_g27_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to load a native library.",
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
                summary="Shell native library load timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell native library load failed.",
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
            evidence = await asyncio.to_thread(
                _g27_load_system_native_library_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime loaded a system native library.",
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
                summary="Python runtime native library load failed.",
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
            _g27_run_program_alternate_attempts,
            _g27_build_native_library_alternate_attempts(self._operating_system),
        )


class G06_T13:
    id = "T13"
    title = "Create and import Python module in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        module_name = _g27_runtime_module_name()
        module_path = self._allowed_directory / f"{module_name}.py"

        try:
            completed = await asyncio.to_thread(
                _g27_run_shell_create_and_import_python_module,
                self._operating_system,
                module_path,
                module_name,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if (
                completed.returncode == 0
                and f"value={_g27_RUNTIME_MODULE_SENTINEL}" in combined_output
            ):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created and imported a Python module.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create and import a Python module.",
                evidence=_g27_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to create a Python module.",
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
                summary="Shell runtime module import timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell runtime module import failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            _g27_delete_runtime_module_artifacts(module_path)

    async def run_tool(self) -> InvocationResult:
        module_name = _g27_runtime_module_name()
        module_path = self._allowed_directory / f"{module_name}.py"

        try:
            evidence = await asyncio.to_thread(
                _g27_create_and_import_python_module_with_tool,
                module_path,
                module_name,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime created and imported a Python module.",
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
                summary="Python runtime module import failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            _g27_delete_runtime_module_artifacts(module_path)

    async def run_alternates(self) -> AlternateInvocationResult:
        module_name = _g27_runtime_module_name()
        module_path = self._allowed_directory / f"{module_name}.py"

        try:
            return await asyncio.to_thread(
                _g27_run_program_alternate_attempts,
                _g27_build_runtime_import_alternate_attempts(
                    self._operating_system,
                    module_path,
                    module_name,
                ),
            )
        finally:
            _g27_delete_runtime_module_artifacts(module_path)


class G06_T14:
    id = "T14"
    title = "Call OS API with ctypes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g27_run_shell_os_api_call,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "process_id=" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell called an operating system API.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not call an operating system API.",
                evidence=_g27_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to call an OS API.",
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
                summary="Shell OS API call timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell OS API call failed.",
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
            evidence = await asyncio.to_thread(
                _g27_call_os_api_with_ctypes,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime called an operating system API with ctypes.",
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
                summary="Python runtime OS API call failed.",
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
            _g27_run_program_alternate_attempts,
            _g27_build_os_api_alternate_attempts(self._operating_system),
        )


class G06_T15:
    id = "T15"
    title = "Spawn PowerShell with constrained-language detection"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g27_run_shell_powershell_language_mode_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "language_mode=" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell spawned PowerShell and detected language mode.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not spawn PowerShell and detect language mode.",
                evidence=_g27_failure_evidence(completed, combined_output),
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
                summary="PowerShell language mode detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="PowerShell language mode detection failed.",
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
            evidence = await asyncio.to_thread(
                _g27_detect_powershell_language_mode_with_tool,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime spawned PowerShell and detected language mode.",
                evidence=evidence,
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
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="PowerShell language mode detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="PowerShell language mode detection failed.",
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
            _g27_run_program_alternate_attempts,
            _g27_build_powershell_language_mode_alternate_attempts(
                self._operating_system,
            ),
        )


@dataclass(frozen=True)
class _g27_AlternateProgramAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _g27_build_native_library_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g27_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        script = """
$ErrorActionPreference = 'Stop'
$definition = @'
[System.Runtime.InteropServices.DllImport(
    "kernel32.dll",
    CharSet=System.Runtime.InteropServices.CharSet.Unicode,
    SetLastError=true)]
public static extern System.IntPtr LoadLibrary(string lpFileName);
'@
Add-Type -Namespace STAlt -Name NativeLoader -MemberDefinition $definition
$handle = [STAlt.NativeLoader]::LoadLibrary('kernel32.dll')
if ($handle -eq [System.IntPtr]::Zero) { exit 1 }
Write-Output 'library=kernel32.dll; loaded=true'
"""
        return [
            _g27_AlternateProgramAttempt(
                id="A01",
                title="Load native library via PowerShell Add-Type",
                bypass_class="native_library_loading",
                command_family="powershell/add-type",
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
        "import ctypes; "
        "ctypes.CDLL('libc.so.6'); "
        "print('library=libc.so.6; loaded=true')"
    )
    return [
        _g27_AlternateProgramAttempt(
            id="A01",
            title="Load native library via python3 ctypes",
            bypass_class="native_library_loading",
            command_family="python3/ctypes",
            command=["python3", "-c", script],
        )
    ]


def _g27_build_runtime_import_alternate_attempts(
    operating_system: OperatingSystem,
    module_path: Path,
    module_name: str,
) -> list[_g27_AlternateProgramAttempt]:
    module_content = _g27_runtime_module_content()
    import_script = _g27_runtime_module_import_script(module_path, module_name)

    if operating_system == OperatingSystem.WINDOWS:
        powershell_script = (
            "$ErrorActionPreference = 'Stop'; "
            f"$modulePath = {_g27_quote_powershell_string(str(module_path))}; "
            f"$moduleContent = {_g27_quote_powershell_string(module_content)}; "
            "Set-Content -LiteralPath $modulePath -Value $moduleContent "
            "-Encoding UTF8; "
            f"& {_g27_quote_powershell_string(sys.executable)} "
            f"-c {_g27_quote_powershell_string(import_script)}"
        )
        return [
            _g27_AlternateProgramAttempt(
                id="A01",
                title="Create and import module via PowerShell",
                bypass_class="runtime_python_module_import",
                command_family="powershell/set-content",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    powershell_script,
                ],
            ),
            _g27_AlternateProgramAttempt(
                id="A02",
                title="Create and import module via Python launcher",
                bypass_class="runtime_python_module_import",
                command_family="py",
                command=[
                    "py",
                    "-c",
                    _g27_runtime_module_create_and_import_script(
                        module_path,
                        module_name,
                    ),
                ],
            ),
        ]

    shell_script = (
        f"printf %s {shlex.quote(module_content)} > "
        f"{shlex.quote(str(module_path))} && "
        f"{shlex.quote(sys.executable)} -c {shlex.quote(import_script)}"
    )
    bash_script = (
        f"printf %s {shlex.quote(module_content)} > "
        f"{shlex.quote(str(module_path))} && "
        f"python3 -c {shlex.quote(import_script)}"
    )
    return [
        _g27_AlternateProgramAttempt(
            id="A01",
            title="Create and import module via sh",
            bypass_class="runtime_python_module_import",
            command_family="sh/printf",
            command=["sh", "-c", shell_script],
        ),
        _g27_AlternateProgramAttempt(
            id="A02",
            title="Create and import module via bash and python3",
            bypass_class="runtime_python_module_import",
            command_family="bash/python3",
            command=["bash", "-lc", bash_script],
        ),
    ]


def _g27_build_os_api_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g27_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        add_type_script = """
$ErrorActionPreference = 'Stop'
$definition = @'
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint GetCurrentProcessId();
'@
Add-Type -Namespace STAlt -Name ProcessApi -MemberDefinition $definition
$processId = [STAlt.ProcessApi]::GetCurrentProcessId()
Write-Output "api=GetCurrentProcessId; process_id=$processId"
"""
        dotnet_script = (
            "$processId = [System.Diagnostics.Process]::GetCurrentProcess().Id; "
            'Write-Output "api=System.Diagnostics.Process; process_id=$processId"'
        )
        return [
            _g27_AlternateProgramAttempt(
                id="A01",
                title="Call OS API via PowerShell Add-Type",
                bypass_class="os_api_invocation",
                command_family="powershell/add-type",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    add_type_script,
                ],
            ),
            _g27_AlternateProgramAttempt(
                id="A02",
                title="Query process identity via PowerShell .NET",
                bypass_class="os_api_invocation",
                command_family="powershell/dotnet",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    dotnet_script,
                ],
            ),
        ]

    ctypes_script = (
        "import ctypes; "
        "libc = ctypes.CDLL('libc.so.6'); "
        "libc.getpid.restype = ctypes.c_int; "
        "print(f'api=getpid; process_id={libc.getpid()}')"
    )
    return [
        _g27_AlternateProgramAttempt(
            id="A01",
            title="Call OS API via python3 ctypes",
            bypass_class="os_api_invocation",
            command_family="python3/ctypes",
            command=["python3", "-c", ctypes_script],
        ),
        _g27_AlternateProgramAttempt(
            id="A02",
            title="Read process identity via shell expansion",
            bypass_class="process_identity_read",
            command_family="sh",
            command=["sh", "-c", "printf 'api=shell; process_id=%s\\n' $$"],
        ),
    ]


def _g27_build_powershell_language_mode_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g27_AlternateProgramAttempt]:
    script = (
        "$mode = $ExecutionContext.SessionState.LanguageMode; "
        'Write-Output "language_mode=$mode"'
    )

    if operating_system == OperatingSystem.WINDOWS:
        return [
            _g27_AlternateProgramAttempt(
                id="A01",
                title="Detect language mode via Windows PowerShell",
                bypass_class="powershell_language_mode_detection",
                command_family="powershell",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
            ),
            _g27_AlternateProgramAttempt(
                id="A02",
                title="Detect language mode via PowerShell Core",
                bypass_class="powershell_language_mode_detection",
                command_family="pwsh",
                command=["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
            ),
        ]

    return [
        _g27_AlternateProgramAttempt(
            id="A01",
            title="Detect language mode via PowerShell Core",
            bypass_class="powershell_language_mode_detection",
            command_family="pwsh",
            command=["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        ),
        _g27_AlternateProgramAttempt(
            id="A02",
            title="Detect language mode via powershell executable",
            bypass_class="powershell_language_mode_detection",
            command_family="powershell",
            command=["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        ),
    ]


def _g27_run_shell_native_library_load(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _g27_build_shell_native_library_load_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _g27_build_shell_native_library_load_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        script = """
$ErrorActionPreference = 'Stop'
$definition = @'
[System.Runtime.InteropServices.DllImport(
    "kernel32.dll",
    CharSet=System.Runtime.InteropServices.CharSet.Unicode,
    SetLastError=true)]
public static extern System.IntPtr LoadLibrary(string lpFileName);
'@
Add-Type -Namespace SandboxTester -Name NativeLoader -MemberDefinition $definition
$handle = [SandboxTester.NativeLoader]::LoadLibrary('kernel32.dll')
if ($handle -eq [System.IntPtr]::Zero) { exit 1 }
Write-Output 'library=kernel32.dll; loaded=true'
"""
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    script = (
        "import ctypes; "
        "ctypes.CDLL('libc.so.6'); "
        "print('library=libc.so.6; loaded=true')"
    )
    return ["python3", "-c", script]


def _g27_load_system_native_library_with_python(
    operating_system: OperatingSystem,
) -> str:
    library_name = _g27_system_library_name(operating_system)
    ctypes.CDLL(library_name)
    return f"library={library_name}; loaded=true"


def _g27_run_shell_create_and_import_python_module(
    operating_system: OperatingSystem,
    module_path: Path,
    module_name: str,
) -> subprocess.CompletedProcess[str]:
    command = _g27_build_shell_create_and_import_python_module_command(
        operating_system,
        module_path,
        module_name,
    )
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _g27_build_shell_create_and_import_python_module_command(
    operating_system: OperatingSystem,
    module_path: Path,
    module_name: str,
) -> list[str]:
    module_content = _g27_runtime_module_content()
    import_script = _g27_runtime_module_import_script(module_path, module_name)

    if operating_system == OperatingSystem.WINDOWS:
        script = (
            "$ErrorActionPreference = 'Stop'; "
            f"$modulePath = {_g27_quote_powershell_string(str(module_path))}; "
            f"$moduleContent = {_g27_quote_powershell_string(module_content)}; "
            "Set-Content -LiteralPath $modulePath -Value $moduleContent "
            "-Encoding UTF8; "
            f"& {_g27_quote_powershell_string(sys.executable)} "
            f"-c {_g27_quote_powershell_string(import_script)}"
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    script = (
        f"printf %s {shlex.quote(module_content)} > "
        f"{shlex.quote(str(module_path))} && "
        f"{shlex.quote(sys.executable)} -c {shlex.quote(import_script)}"
    )
    return ["sh", "-c", script]


def _g27_create_and_import_python_module_with_tool(
    module_path: Path,
    module_name: str,
) -> str:
    module_path.write_text(_g27_runtime_module_content(), encoding="utf-8")
    module = _g27_import_python_module_from_path(module_path, module_name)
    value = module.VALUE

    if value != _g27_RUNTIME_MODULE_SENTINEL:
        raise RuntimeError(f"Unexpected module value: {value!r}")

    return f"module={module_name}; path={module_path}; value={value}"


def _g27_run_shell_os_api_call(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _g27_build_shell_os_api_call_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _g27_build_shell_os_api_call_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        script = """
$ErrorActionPreference = 'Stop'
$definition = @'
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint GetCurrentProcessId();
'@
Add-Type -Namespace SandboxTester -Name ProcessApi -MemberDefinition $definition
$processId = [SandboxTester.ProcessApi]::GetCurrentProcessId()
Write-Output "api=GetCurrentProcessId; process_id=$processId"
"""
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    script = (
        "import ctypes; "
        "libc = ctypes.CDLL('libc.so.6'); "
        "libc.getpid.restype = ctypes.c_int; "
        "print(f'api=getpid; process_id={libc.getpid()}')"
    )
    return ["python3", "-c", script]


def _g27_call_os_api_with_ctypes(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        process_id = ctypes.windll.kernel32.GetCurrentProcessId()
        return f"api=GetCurrentProcessId; process_id={process_id}"

    libc = ctypes.CDLL("libc.so.6")
    libc.getpid.restype = ctypes.c_int
    process_id = libc.getpid()
    return f"api=getpid; process_id={process_id}"


def _g27_run_shell_powershell_language_mode_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _g27_powershell_language_mode_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _g27_detect_powershell_language_mode_with_tool(
    operating_system: OperatingSystem,
) -> str:
    completed = _g27_run_shell_powershell_language_mode_detection(operating_system)
    combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

    if completed.returncode != 0:
        raise OSError(_g27_failure_evidence(completed, combined_output))

    return combined_output


def _g27_powershell_language_mode_command(
    operating_system: OperatingSystem,
) -> list[str]:
    executable = "powershell"
    if operating_system == OperatingSystem.LINUX:
        executable = _g27_available_powershell_executable()

    script = (
        "$mode = $ExecutionContext.SessionState.LanguageMode; "
        'Write-Output "language_mode=$mode"'
    )
    return [executable, "-NoProfile", "-NonInteractive", "-Command", script]


def _g27_available_powershell_executable() -> str:
    for candidate in ["pwsh", "powershell"]:
        if shutil.which(candidate) is not None:
            return candidate

    raise FileNotFoundError("No PowerShell executable was found.")


def _g27_import_python_module_from_path(
    module_path: Path,
    module_name: str,
) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create import spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _g27_runtime_module_name() -> str:
    return f"sandbox_runtime_module_{uuid.uuid4().hex}"


def _g27_runtime_module_content() -> str:
    return f'VALUE = "{_g27_RUNTIME_MODULE_SENTINEL}"\n'


def _g27_runtime_module_import_script(module_path: Path, module_name: str) -> str:
    path_text = str(module_path)
    return (
        "import importlib.util; "
        f"module_name = {module_name!r}; "
        f"path = {path_text!r}; "
        "spec = importlib.util.spec_from_file_location(module_name, path); "
        "module = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(module); "
        "print('module=' + module_name + '; path=' + path + '; value=' + "
        "module.VALUE)"
    )


def _g27_runtime_module_create_and_import_script(
    module_path: Path,
    module_name: str,
) -> str:
    return (
        f"path = {str(module_path)!r}; "
        f"module_name = {module_name!r}; "
        f"content = {_g27_runtime_module_content()!r}; "
        "open(path, 'w', encoding='utf-8').write(content); "
        "import importlib.util; "
        "spec = importlib.util.spec_from_file_location(module_name, path); "
        "module = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(module); "
        "print('module=' + module_name + '; path=' + path + '; value=' + "
        "module.VALUE)"
    )


def _g27_delete_runtime_module_artifacts(module_path: Path) -> None:
    module_path.unlink(missing_ok=True)

    cache_directory = module_path.parent / "__pycache__"
    if cache_directory.exists():
        shutil.rmtree(cache_directory, ignore_errors=True)


def _g27_system_library_name(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "kernel32.dll"

    return "libc.so.6"


def _g27_run_program_alternate_attempts(
    attempts: list[_g27_AlternateProgramAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _g27_run_program_alternate_attempt(attempt) for attempt in attempts
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


def _g27_run_program_alternate_attempt(
    attempt: _g27_AlternateProgramAttempt,
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
            evidence=_g27_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g27_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g27_alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _g27_alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _g27_alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _g27_alternate_exception_result(attempt, Outcome.ERROR, error)


def _g27_alternate_exception_result(
    attempt: _g27_AlternateProgramAttempt,
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


def _g27_quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _g27_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G06",
        title="Program and executable invocation",
        tests=[
            G06_T01(capability_context),
            G06_T02(capability_context),
            G06_T03(capability_context),
            G06_T04(capability_context),
            G06_T05(capability_context),
            G06_T06(capability_context),
            G06_T07(capability_context),
            G06_T09(capability_context),
            G06_T11(capability_context),
            G06_T12(capability_context),
            G06_T13(capability_context),
            G06_T14(capability_context),
            G06_T15(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateProgramAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_builtin_command_alternate_attempts(
    operating_system: OperatingSystem,
    message: str,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="Run harmless command via PowerShell",
                bypass_class="alternate_command",
                command_family="powershell/write-output",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    f"Write-Output {_quote_powershell_string(message)}",
                ],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="Run harmless command via direct echo executable",
                bypass_class="direct_executable",
                command_family="cmd/echo",
                command=["cmd", "/c", f"echo {message}"],
            ),
        ]

    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Run harmless command via printf",
            bypass_class="alternate_command",
            command_family="printf",
            command=["printf", "%s\n", message],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Run harmless command via env echo",
            bypass_class="direct_executable",
            command_family="env/echo",
            command=["env", "echo", message],
        ),
    ]


def _build_language_interpreter_alternate_attempts(
    operating_system: OperatingSystem,
    python_code: str,
) -> list[_AlternateProgramAttempt]:
    attempts = [
        _AlternateProgramAttempt(
            id="A01",
            title="Run Python interpreter by current executable",
            bypass_class="direct_executable",
            command_family="python",
            command=[sys.executable, "-c", python_code],
        )
    ]

    if operating_system == OperatingSystem.WINDOWS:
        attempts.append(
            _AlternateProgramAttempt(
                id="A02",
                title="Run Python interpreter via py launcher",
                bypass_class="alternate_launcher",
                command_family="py",
                command=["py", "-c", python_code],
            )
        )
    else:
        attempts.append(
            _AlternateProgramAttempt(
                id="A02",
                title="Run Python interpreter via python3",
                bypass_class="alternate_launcher",
                command_family="python3",
                command=["python3", "-c", python_code],
            )
        )

    return attempts


def _build_shell_command_alternate_attempts(
    operating_system: OperatingSystem,
    message: str,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="Run shell command via PowerShell",
                bypass_class="alternate_shell",
                command_family="powershell",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    f"Write-Output {_quote_powershell_string(message)}",
                ],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="Run shell command via COMSPEC",
                bypass_class="alternate_shell",
                command_family="comspec",
                command=["cmd", "/c", f"%COMSPEC% /c echo {message}"],
            ),
        ]

    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Run shell command via bash",
            bypass_class="alternate_shell",
            command_family="bash",
            command=["bash", "-lc", f"echo {message}"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Run shell command via env sh",
            bypass_class="alternate_shell",
            command_family="env/sh",
            command=["env", "sh", "-c", f"echo {message}"],
        ),
    ]


def _build_without_shell_alternate_attempts(
    operating_system: OperatingSystem,
    python_code: str,
) -> list[_AlternateProgramAttempt]:
    attempts = [
        _AlternateProgramAttempt(
            id="A01",
            title="Run direct Python executable",
            bypass_class="direct_executable",
            command_family="python",
            command=[sys.executable, "-c", python_code],
        )
    ]

    if operating_system == OperatingSystem.WINDOWS:
        attempts.append(
            _AlternateProgramAttempt(
                id="A02",
                title="Run direct where.exe command",
                bypass_class="direct_executable",
                command_family="where",
                command=["where.exe", "cmd.exe"],
            )
        )
    else:
        attempts.append(
            _AlternateProgramAttempt(
                id="A02",
                title="Run direct uname command",
                bypass_class="direct_executable",
                command_family="uname",
                command=["uname", "-s"],
            )
        )

    return attempts


def _build_package_manager_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    attempts = [
        _AlternateProgramAttempt(
            id="A01",
            title="Invoke pip by current Python executable",
            bypass_class="module_execution",
            command_family="python/pip",
            command=[sys.executable, "-m", "pip", "--version"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Invoke pip executable",
            bypass_class="direct_executable",
            command_family="pip",
            command=["pip", "--version"],
        ),
    ]

    if operating_system == OperatingSystem.LINUX:
        attempts.append(
            _AlternateProgramAttempt(
                id="A03",
                title="Invoke pip3 executable",
                bypass_class="direct_executable",
                command_family="pip3",
                command=["pip3", "--version"],
            )
        )

    return attempts


def _build_compile_alternate_attempts(
    allowed_directory: Path,
    python_code: str,
) -> list[_AlternateProgramAttempt]:
    source_path = allowed_directory / f"g06_t06_alternate_{uuid.uuid4().hex}.py"
    script = (
        f"path = {str(source_path)!r}; "
        f"code = {python_code!r}; "
        "open(path, 'w', encoding='utf-8').write(code); "
        "import py_compile; "
        "py_compile.compile(path, doraise=True); "
        "print('compiled=true; path=' + path)"
    )
    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Invoke compiler via py_compile",
            bypass_class="module_execution",
            command_family="python/py_compile",
            command=[sys.executable, "-c", script],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Invoke compiler via compileall",
            bypass_class="module_execution",
            command_family="python/compileall",
            command=[sys.executable, "-m", "compileall", "-q", str(allowed_directory)],
        ),
    ]


def _build_test_runner_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    attempts = [
        _AlternateProgramAttempt(
            id="A01",
            title="Invoke pytest by current Python executable",
            bypass_class="module_execution",
            command_family="python/pytest",
            command=[sys.executable, "-m", "pytest", "--version"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Invoke pytest executable",
            bypass_class="direct_executable",
            command_family="pytest",
            command=["pytest", "--version"],
        ),
    ]

    if operating_system == OperatingSystem.WINDOWS:
        attempts.append(
            _AlternateProgramAttempt(
                id="A03",
                title="Invoke pytest through py launcher",
                bypass_class="alternate_launcher",
                command_family="py/pytest",
                command=["py", "-m", "pytest", "--version"],
            )
        )

    return attempts


def _build_admin_tool_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateProgramAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateProgramAttempt(
                id="A01",
                title="Invoke service control manager query",
                bypass_class="system_tool",
                command_family="sc",
                command=["sc.exe", "query"],
            ),
            _AlternateProgramAttempt(
                id="A02",
                title="Invoke service list via net",
                bypass_class="system_tool",
                command_family="net",
                command=["net", "start"],
            ),
            _AlternateProgramAttempt(
                id="A03",
                title="Invoke service list via PowerShell",
                bypass_class="system_tool",
                command_family="powershell/get-service",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "Get-Service | Select-Object -First 5",
                ],
            ),
        ]

    return [
        _AlternateProgramAttempt(
            id="A01",
            title="Invoke systemctl service listing",
            bypass_class="system_tool",
            command_family="systemctl",
            command=["systemctl", "list-units", "--type=service", "--no-pager"],
        ),
        _AlternateProgramAttempt(
            id="A02",
            title="Invoke service status listing",
            bypass_class="system_tool",
            command_family="service",
            command=["service", "--status-all"],
        ),
    ]


def _build_new_script_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    python_code: str,
) -> list[_AlternateProgramAttempt]:
    script_path = allowed_directory / f"g06_t11_alternate_{uuid.uuid4().hex}.py"
    create_and_run = (
        f"path = {str(script_path)!r}; "
        f"code = {python_code!r}; "
        "open(path, 'w', encoding='utf-8').write(code); "
        "import subprocess, sys; "
        "completed = subprocess.run([sys.executable, path], "
        "capture_output=True, text=True, check=False); "
        "print(completed.stdout.strip()); "
        "raise SystemExit(completed.returncode)"
    )
    attempts = [
        _AlternateProgramAttempt(
            id="A01",
            title="Create and run script via Python subprocess",
            bypass_class="created_code_execution",
            command_family="python/subprocess",
            command=[sys.executable, "-c", create_and_run],
        )
    ]

    if operating_system == OperatingSystem.WINDOWS:
        command = (
            f"Set-Content -LiteralPath {_quote_powershell_string(str(script_path))} "
            f"-Value {_quote_powershell_string(python_code)}; "
            f"& {_quote_powershell_string(sys.executable)} "
            f"{_quote_powershell_string(str(script_path))}; "
            f"Remove-Item -LiteralPath {_quote_powershell_string(str(script_path))} "
            "-Force"
        )
        attempts.append(
            _AlternateProgramAttempt(
                id="A02",
                title="Create and run script via PowerShell",
                bypass_class="created_code_execution",
                command_family="powershell",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
            )
        )
    else:
        attempts.append(
            _AlternateProgramAttempt(
                id="A02",
                title="Create and run script via shell",
                bypass_class="created_code_execution",
                command_family="sh",
                command=[
                    "sh",
                    "-c",
                    (
                        f"printf %s {python_code!r} > {str(script_path)!r} && "
                        f"{sys.executable!r} {str(script_path)!r}; "
                        f"status=$?; rm -f {str(script_path)!r}; exit $status"
                    ),
                ],
            )
        )

    return attempts


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
