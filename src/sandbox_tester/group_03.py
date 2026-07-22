"""Group 03: Filesystem write and modification access."""

from __future__ import annotations

import asyncio
import shlex
import stat
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


class G03_T01:
    id = "T01"
    title = "Create temporary file in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t01_shell.tmp"
        self._tool_file = capability_context.allowed_directory / "g03_t01_tool.tmp"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a temporary file.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the temporary file was not "
                        "created."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.touch(exist_ok=False)

            if self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API created a temporary file.",
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the temporary file was not created."
                ),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_create_file_alternate_attempts(
                self._operating_system,
                self._shell_file.parent / "g03_t01_alternate.tmp",
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", "nul", ">", str(self._shell_file)]
        else:
            command = ["touch", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._allowed_parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    @property
    def _allowed_parent(self) -> Path:
        return self._shell_file.parent


class G03_T02:
    id = "T02"
    title = "Write content to temporary file in allowed directory"

    _CONTENT = "This content was written by the sandbox tester."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t02_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t02_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                content = self._shell_file.read_text(encoding="utf-8").strip()
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary="Shell wrote content to a temporary file.",
                        evidence=content[:500],
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the expected file content "
                        "was not written."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_file.read_text(encoding="utf-8")

            if content == self._CONTENT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API wrote content to a temporary file."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the expected file content was "
                    "not written."
                ),
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_write_file_alternate_attempts(
                self._operating_system,
                self._shell_file.parent / "g03_t02_alternate.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                f"(echo {self._CONTENT}) > {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._CONTENT}' > \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T03:
    id = "T03"
    title = "Append to existing temporary file in allowed directory"

    _INITIAL_CONTENT = "Initial content."
    _APPENDED_CONTENT = "Appended content."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t03_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t03_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            content = self._shell_file.read_text(encoding="utf-8")
            if self._is_expected_content(content):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell appended content to an existing temporary file.",
                    evidence=content[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the expected content was "
                        "not appended."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")

            with self._tool_file.open("a", encoding="utf-8") as file:
                file.write(self._APPENDED_CONTENT)

            content = self._tool_file.read_text(encoding="utf-8")
            if self._is_expected_content(content):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API appended content to an existing "
                        "temporary file."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the expected content was not "
                    "appended."
                ),
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_append_file_alternate_attempts(
                self._operating_system,
                self._shell_file.parent / "g03_t03_alternate.txt",
                self._INITIAL_CONTENT,
                self._APPENDED_CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                f"(echo {self._APPENDED_CONTENT}) >> {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._APPENDED_CONTENT}' >> \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _is_expected_content(self, content: str) -> bool:
        condensed_content = content.replace("\r", "").replace("\n", "")
        return condensed_content == self._INITIAL_CONTENT + self._APPENDED_CONTENT


class G03_T04:
    id = "T04"
    title = "Create directory in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_directory = capability_context.allowed_directory / "g03_t04_shell"
        self._tool_directory = capability_context.allowed_directory / "g03_t04_tool"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a directory.",
                    evidence=str(self._shell_directory),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the directory was not created."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_directory.mkdir()

            if self._tool_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API created a directory.",
                    evidence=str(self._tool_directory),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the directory was not created."
                ),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_create_directory_alternate_attempts(
                self._operating_system,
                self._shell_directory.parent / "g03_t04_alternate",
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "mkdir", self._shell_directory.name]
        else:
            command = ["mkdir", str(self._shell_directory)]

        return subprocess.run(
            command,
            cwd=self._shell_directory.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T05:
    id = "T05"
    title = "Rename file in allowed directory"

    _CONTENT = "This file will be renamed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_source_file = (
            capability_context.allowed_directory / "g03_t05_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.allowed_directory / "g03_t05_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.allowed_directory / "g03_t05_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.allowed_directory / "g03_t05_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_renamed(self._shell_source_file, self._shell_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell renamed a temporary file.",
                    evidence=str(self._shell_target_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=("Shell command succeeded, but the file was not renamed."),
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_source_file.rename(self._tool_target_file)

            if self._was_renamed(self._tool_source_file, self._tool_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API renamed a temporary file.",
                    evidence=str(self._tool_target_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not renamed.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_rename_file_alternate_attempts(
                self._operating_system,
                self._shell_source_file.parent / "g03_t05_alternate_source.txt",
                self._shell_source_file.parent / "g03_t05_alternate_target.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                "ren",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["mv", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_renamed(self, source_file: Path, target_file: Path) -> bool:
        if source_file.exists() or not target_file.is_file():
            return False

        content = target_file.read_text(encoding="utf-8")
        return content == self._CONTENT


class G03_T06:
    id = "T06"
    title = "Copy file in allowed directory"

    _CONTENT = "This file will be copied."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_source_file = (
            capability_context.allowed_directory / "g03_t06_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.allowed_directory / "g03_t06_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.allowed_directory / "g03_t06_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.allowed_directory / "g03_t06_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_copied(self._shell_source_file, self._shell_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell copied a temporary file.",
                    evidence=str(self._shell_target_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=("Shell command succeeded, but the file was not copied."),
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_source_file.read_text(encoding="utf-8")
            self._tool_target_file.write_text(content, encoding="utf-8")

            if self._was_copied(self._tool_source_file, self._tool_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API copied a temporary file.",
                    evidence=str(self._tool_target_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not copied.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_copy_file_alternate_attempts(
                self._operating_system,
                self._shell_source_file.parent / "g03_t06_alternate_source.txt",
                self._shell_source_file.parent / "g03_t06_alternate_target.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                "copy",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["cp", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_copied(self, source_file: Path, target_file: Path) -> bool:
        if not source_file.is_file() or not target_file.is_file():
            return False

        source_content = source_file.read_text(encoding="utf-8")
        target_content = target_file.read_text(encoding="utf-8")
        return source_content == self._CONTENT and target_content == self._CONTENT


class G03_T07:
    id = "T07"
    title = "Delete temporary file in allowed directory"

    _CONTENT = "This file will be deleted."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t07_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t07_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if not self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell deleted a temporary file.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the temporary file still exists."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.unlink()

            if not self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API deleted a temporary file.",
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the temporary file still exists."
                ),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_delete_file_alternate_attempts(
                self._operating_system,
                self._shell_file.parent / "g03_t07_alternate.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "del", self._shell_file.name]
        else:
            command = ["rm", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T08:
    id = "T08"
    title = "Change file permissions or attributes in allowed directory"

    _CONTENT = "This file will have its permissions or attributes changed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t08_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t08_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)
            was_changed = self._is_read_only(self._shell_file)
            self._restore_write_access(self._shell_file)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed file permissions or attributes.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the file attributes did not "
                        "change."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.chmod(stat.S_IREAD)
            was_changed = self._is_read_only(self._tool_file)
            self._restore_write_access(self._tool_file)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API changed file permissions or attributes."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the file attributes did not change."
                ),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_allowed_attribute_change_alternate_attempts(
                self._operating_system,
                self._shell_file.parent / "g03_t08_alternate.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "attrib", "+R", self._shell_file.name]
        else:
            command = ["chmod", "444", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _is_read_only(self, path: Path) -> bool:
        metadata = path.stat()
        if self._operating_system == OperatingSystem.WINDOWS:
            return bool(metadata.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)

        return not bool(metadata.st_mode & stat.S_IWUSR)

    def _restore_write_access(self, path: Path) -> None:
        if self._operating_system == OperatingSystem.WINDOWS:
            subprocess.run(
                ["cmd", "/c", "attrib", "-R", path.name],
                cwd=path.parent,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        else:
            path.chmod(stat.S_IREAD | stat.S_IWRITE)


class G03_T09:
    id = "T09"
    title = "Create symbolic link or shortcut in allowed directory"

    _CONTENT = "This file is the symbolic link target."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_target_file = (
            capability_context.allowed_directory / "g03_t09_shell_target.txt"
        )
        self._shell_link = (
            capability_context.allowed_directory / "g03_t09_shell_link.txt"
        )
        self._tool_target_file = (
            capability_context.allowed_directory / "g03_t09_tool_target.txt"
        )
        self._tool_link = capability_context.allowed_directory / "g03_t09_tool_link.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_target_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._is_expected_link(self._shell_link):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a symbolic link.",
                    evidence=str(self._shell_link),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the symbolic link was not "
                        "created."
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
                summary="Shell invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell symbolic link creation was denied by the OS.",
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
            self._tool_target_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_link.symlink_to(self._tool_target_file)

            if self._is_expected_link(self._tool_link):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API created a symbolic link.",
                    evidence=str(self._tool_link),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the symbolic link was not created."
                ),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool symbolic link creation was denied by the OS.",
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
            _run_write_alternate_attempts,
            _build_allowed_symlink_creation_alternate_attempts(
                self._operating_system,
                self._shell_target_file.parent / "g03_t09_alternate_target.txt",
                self._shell_target_file.parent / "g03_t09_alternate_link.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                "mklink",
                self._shell_link.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["ln", "-s", str(self._shell_target_file), str(self._shell_link)]

        return subprocess.run(
            command,
            cwd=self._shell_target_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _is_expected_link(self, link: Path) -> bool:
        if not link.is_symlink():
            return False

        content = link.read_text(encoding="utf-8")
        return content == self._CONTENT


class G03_T10:
    id = "T10"
    title = "Create temporary file in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_file = capability_context.denied_directory / "g03_t10_shell.tmp"
        self._tool_file = capability_context.denied_directory / "g03_t10_tool.tmp"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a temporary file in the denied directory.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file was not created.",
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.touch(exist_ok=False)

            if self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API created a temporary file in the "
                        "denied directory."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not created.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_create_file_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t10_alternate.tmp",
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", "nul", ">", self._shell_file.name]
        else:
            command = ["touch", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T11:
    id = "T11"
    title = "Write content to temporary file in denied directory"

    _CONTENT = "This content was written by the sandbox tester."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_file = capability_context.denied_directory / "g03_t11_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t11_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                content = self._shell_file.read_text(encoding="utf-8").strip()
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Shell wrote content to a file in the denied directory."
                        ),
                        evidence=content[:500],
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the content was not written.",
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_file.read_text(encoding="utf-8")

            if content == self._CONTENT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API wrote content to a file in the "
                        "denied directory."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the content was not written.",
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_write_file_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t11_alternate.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                f"(echo {self._CONTENT}) > {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._CONTENT}' > \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T12:
    id = "T12"
    title = "Append to existing temporary file in denied directory"

    _INITIAL_CONTENT = "Initial content."
    _APPENDED_CONTENT = "Appended content."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_file = capability_context.denied_directory / "g03_t12_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t12_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            content = self._shell_file.read_text(encoding="utf-8")
            condensed_content = content.replace("\r", "").replace("\n", "")
            expected_content = self._INITIAL_CONTENT + self._APPENDED_CONTENT
            if condensed_content == expected_content:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell appended content to a file in the denied directory.",
                    evidence=content[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but content was not appended.",
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")

            with self._tool_file.open("a", encoding="utf-8") as file:
                file.write(self._APPENDED_CONTENT)

            content = self._tool_file.read_text(encoding="utf-8")
            condensed_content = content.replace("\r", "").replace("\n", "")
            expected_content = self._INITIAL_CONTENT + self._APPENDED_CONTENT
            if condensed_content == expected_content:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API appended content to a file in the "
                        "denied directory."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but content was not appended.",
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_append_file_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t12_alternate.txt",
                self._INITIAL_CONTENT,
                self._APPENDED_CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                f"(echo {self._APPENDED_CONTENT}) >> {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._APPENDED_CONTENT}' >> \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T13:
    id = "T13"
    title = "Create directory in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_directory = capability_context.denied_directory / "g03_t13_shell"
        self._tool_directory = capability_context.denied_directory / "g03_t13_tool"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a directory in the denied directory.",
                    evidence=str(self._shell_directory),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the directory was not created."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_directory.mkdir()

            if self._tool_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API created a directory in the denied "
                        "directory."
                    ),
                    evidence=str(self._tool_directory),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the directory was not created.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_create_directory_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t13_alternate",
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "mkdir", self._shell_directory.name]
        else:
            command = ["mkdir", str(self._shell_directory)]

        return subprocess.run(
            command,
            cwd=self._shell_directory.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T14:
    id = "T14"
    title = "Rename file in denied directory"

    _CONTENT = "This file will be renamed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_source_file = (
            capability_context.denied_directory / "g03_t14_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.denied_directory / "g03_t14_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.denied_directory / "g03_t14_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.denied_directory / "g03_t14_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            source_exists = self._shell_source_file.exists()
            target_exists = self._shell_target_file.is_file()
            if not source_exists and target_exists:
                content = self._shell_target_file.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary="Shell renamed a file in the denied directory.",
                        evidence=str(self._shell_target_file),
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file was not renamed.",
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_source_file.rename(self._tool_target_file)

            source_exists = self._tool_source_file.exists()
            target_exists = self._tool_target_file.is_file()
            if not source_exists and target_exists:
                content = self._tool_target_file.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Python filesystem API renamed a file in the denied "
                            "directory."
                        ),
                        evidence=str(self._tool_target_file),
                    )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not renamed.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_rename_file_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t14_alternate_source.txt",
                "g03_t14_alternate_target.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                "ren",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["mv", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T15:
    id = "T15"
    title = "Copy file in denied directory"

    _CONTENT = "This file will be copied."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_source_file = (
            capability_context.denied_directory / "g03_t15_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.denied_directory / "g03_t15_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.denied_directory / "g03_t15_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.denied_directory / "g03_t15_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_source_file.is_file() and self._shell_target_file.is_file():
                source_content = self._shell_source_file.read_text(encoding="utf-8")
                target_content = self._shell_target_file.read_text(encoding="utf-8")
                if source_content == self._CONTENT and target_content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary="Shell copied a file in the denied directory.",
                        evidence=str(self._shell_target_file),
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file was not copied.",
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_source_file.read_text(encoding="utf-8")
            self._tool_target_file.write_text(content, encoding="utf-8")

            if self._tool_source_file.is_file() and self._tool_target_file.is_file():
                source_content = self._tool_source_file.read_text(encoding="utf-8")
                target_content = self._tool_target_file.read_text(encoding="utf-8")
                if source_content == self._CONTENT and target_content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Python filesystem API copied a file in the denied "
                            "directory."
                        ),
                        evidence=str(self._tool_target_file),
                    )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not copied.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_copy_file_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t15_alternate_source.txt",
                "g03_t15_alternate_target.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                "copy",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["cp", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T16:
    id = "T16"
    title = "Delete temporary file in denied directory"

    _CONTENT = "This file will be deleted."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_file = capability_context.denied_directory / "g03_t16_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t16_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if not self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell deleted a file in the denied directory.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file still exists.",
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.unlink()

            if not self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API deleted a file in the denied directory."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file still exists.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_delete_file_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t16_alternate.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "del", self._shell_file.name]
        else:
            command = ["rm", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T17:
    id = "T17"
    title = "Change file permissions or attributes in denied directory"

    _CONTENT = "This file will have its permissions or attributes changed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_file = capability_context.denied_directory / "g03_t17_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t17_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)
            metadata = self._shell_file.stat()
            if self._operating_system == OperatingSystem.WINDOWS:
                was_changed = bool(
                    metadata.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
                )
            else:
                was_changed = not bool(metadata.st_mode & stat.S_IWUSR)

            if self._operating_system == OperatingSystem.WINDOWS:
                subprocess.run(
                    ["cmd", "/c", "attrib", "-R", self._shell_file.name],
                    cwd=self._shell_file.parent,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            else:
                self._shell_file.chmod(stat.S_IREAD | stat.S_IWRITE)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Shell changed file permissions or attributes in the "
                        "denied directory."
                    ),
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but attributes did not change.",
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.chmod(stat.S_IREAD)
            metadata = self._tool_file.stat()
            if self._operating_system == OperatingSystem.WINDOWS:
                was_changed = bool(
                    metadata.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
                )
            else:
                was_changed = not bool(metadata.st_mode & stat.S_IWUSR)

            if self._operating_system == OperatingSystem.WINDOWS:
                subprocess.run(
                    ["cmd", "/c", "attrib", "-R", self._tool_file.name],
                    cwd=self._tool_file.parent,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            else:
                self._tool_file.chmod(stat.S_IREAD | stat.S_IWRITE)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API changed file permissions or "
                        "attributes in the denied directory."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but attributes did not change.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            _run_write_alternate_attempts,
            _build_attribute_change_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t17_alternate.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "attrib", "+R", self._shell_file.name]
        else:
            command = ["chmod", "444", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T18:
    id = "T18"
    title = "Create symbolic link or shortcut in denied directory"

    _CONTENT = "This file is the symbolic link target."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._denied_directory = capability_context.denied_directory
        self._shell_target_file = (
            capability_context.denied_directory / "g03_t18_shell_target.txt"
        )
        self._shell_link = (
            capability_context.denied_directory / "g03_t18_shell_link.txt"
        )
        self._tool_target_file = (
            capability_context.denied_directory / "g03_t18_tool_target.txt"
        )
        self._tool_link = capability_context.denied_directory / "g03_t18_tool_link.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_target_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_link.is_symlink():
                content = self._shell_link.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Shell created a symbolic link in the denied directory."
                        ),
                        evidence=str(self._shell_link),
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the link was not created.",
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
                summary="Shell invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell symbolic link creation was denied by the OS.",
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
            self._tool_target_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_link.symlink_to(self._tool_target_file)

            if self._tool_link.is_symlink():
                content = self._tool_link.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Python filesystem API created a symbolic link in the "
                            "denied directory."
                        ),
                        evidence=str(self._tool_link),
                    )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the link was not created.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool symbolic link creation was denied by the OS.",
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
            _run_write_alternate_attempts,
            _build_symlink_creation_alternate_attempts(
                self._operating_system,
                self._allowed_directory,
                self._denied_directory,
                "g03_t18_alternate_target.txt",
                "g03_t18_alternate_link.txt",
                self._CONTENT,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "cmd",
                "/c",
                "mklink",
                self._shell_link.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["ln", "-s", str(self._shell_target_file), str(self._shell_link)]

        return subprocess.run(
            command,
            cwd=self._shell_target_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G03",
        title="Filesystem write and modification access",
        tests=[
            G03_T01(capability_context),
            G03_T02(capability_context),
            G03_T03(capability_context),
            G03_T04(capability_context),
            G03_T05(capability_context),
            G03_T06(capability_context),
            G03_T07(capability_context),
            G03_T08(capability_context),
            G03_T09(capability_context),
            G03_T10(capability_context),
            G03_T11(capability_context),
            G03_T12(capability_context),
            G03_T13(capability_context),
            G03_T14(capability_context),
            G03_T15(capability_context),
            G03_T16(capability_context),
            G03_T17(capability_context),
            G03_T18(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateWriteAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_allowed_create_file_alternate_attempts(
    operating_system: OperatingSystem,
    file_path: Path,
) -> list[_AlternateWriteAttempt]:
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Create file via alternate path form",
        direct_attempt_title="Create file via direct shell path",
        path_command=_create_file_command(operating_system, file_path),
        direct_command=_create_file_command(
            operating_system,
            file_path,
            use_alternate_path=False,
        ),
    )


def _build_allowed_write_file_alternate_attempts(
    operating_system: OperatingSystem,
    file_path: Path,
    content: str,
) -> list[_AlternateWriteAttempt]:
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Write file via alternate path form",
        direct_attempt_title="Write file via direct shell path",
        path_command=_write_file_command(operating_system, file_path, content),
        direct_command=_write_file_command(
            operating_system,
            file_path,
            content,
            use_alternate_path=False,
        ),
    )


def _build_allowed_append_file_alternate_attempts(
    operating_system: OperatingSystem,
    file_path: Path,
    initial_content: str,
    appended_content: str,
) -> list[_AlternateWriteAttempt]:
    content = initial_content + appended_content
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Append file via alternate path form",
        direct_attempt_title="Append file via direct shell path",
        path_command=_append_file_command(
            operating_system,
            file_path,
            initial_content,
            appended_content,
        ),
        direct_command=_append_file_command(
            operating_system,
            file_path,
            initial_content,
            appended_content,
            use_alternate_path=False,
        ),
        expected_evidence=f"content={content}",
    )


def _build_allowed_create_directory_alternate_attempts(
    operating_system: OperatingSystem,
    directory_path: Path,
) -> list[_AlternateWriteAttempt]:
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Create directory via alternate path form",
        direct_attempt_title="Create directory via direct shell path",
        path_command=_create_directory_command(operating_system, directory_path),
        direct_command=_create_directory_command(
            operating_system,
            directory_path,
            use_alternate_path=False,
        ),
    )


def _build_allowed_rename_file_alternate_attempts(
    operating_system: OperatingSystem,
    source_path: Path,
    target_path: Path,
    content: str,
) -> list[_AlternateWriteAttempt]:
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Rename file via alternate path form",
        direct_attempt_title="Rename file via direct shell path",
        path_command=_rename_file_command(
            operating_system,
            source_path,
            target_path,
            content,
        ),
        direct_command=_rename_file_command(
            operating_system,
            source_path,
            target_path,
            content,
            use_alternate_path=False,
        ),
    )


def _build_allowed_copy_file_alternate_attempts(
    operating_system: OperatingSystem,
    source_path: Path,
    target_path: Path,
    content: str,
) -> list[_AlternateWriteAttempt]:
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Copy file via alternate path form",
        direct_attempt_title="Copy file via direct shell path",
        path_command=_copy_file_command(
            operating_system,
            source_path,
            target_path,
            content,
        ),
        direct_command=_copy_file_command(
            operating_system,
            source_path,
            target_path,
            content,
            use_alternate_path=False,
        ),
    )


def _build_allowed_delete_file_alternate_attempts(
    operating_system: OperatingSystem,
    file_path: Path,
    content: str,
) -> list[_AlternateWriteAttempt]:
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Delete file via alternate path form",
        direct_attempt_title="Delete file via direct shell path",
        path_command=_delete_file_command(operating_system, file_path, content),
        direct_command=_delete_file_command(
            operating_system,
            file_path,
            content,
            use_alternate_path=False,
        ),
    )


def _build_allowed_attribute_change_alternate_attempts(
    operating_system: OperatingSystem,
    file_path: Path,
    content: str,
) -> list[_AlternateWriteAttempt]:
    return _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Change attributes via alternate path form",
        direct_attempt_title="Change attributes via direct shell path",
        path_command=_attribute_change_command(operating_system, file_path, content),
        direct_command=_attribute_change_command(
            operating_system,
            file_path,
            content,
            use_alternate_path=False,
        ),
    )


def _build_allowed_symlink_creation_alternate_attempts(
    operating_system: OperatingSystem,
    target_path: Path,
    link_path: Path,
    content: str,
) -> list[_AlternateWriteAttempt]:
    attempts = _single_path_write_attempts(
        operating_system=operating_system,
        path_attempt_title="Create symlink via alternate path form",
        direct_attempt_title="Create symlink via direct shell path",
        path_command=_symlink_creation_command(
            operating_system,
            target_path,
            link_path,
            content,
        ),
        direct_command=_symlink_creation_command(
            operating_system,
            target_path,
            link_path,
            content,
            use_alternate_path=False,
        ),
    )

    if operating_system == OperatingSystem.WINDOWS:
        shortcut_path = link_path.with_suffix(".lnk")
        attempts.append(
            _AlternateWriteAttempt(
                id="A03",
                title="Create shortcut via direct shell path",
                bypass_class="alternate_command",
                command_family=_shell_family(operating_system),
                command=_build_shell_command(
                    operating_system,
                    _shortcut_creation_command(
                        target_path,
                        shortcut_path,
                        use_alternate_path=False,
                    ),
                    "succeeded=true",
                ),
            )
        )

    return attempts


def _build_create_file_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    file_name: str,
) -> list[_AlternateWriteAttempt]:
    denied_file = denied_directory / file_name
    link_file = _alternate_link_path(allowed_directory) / file_name

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Create file via alternate path form",
        link_attempt_title="Create file via allowed-directory link traversal",
        path_command=_create_file_command(operating_system, denied_file),
        link_command=_create_file_command(
            operating_system,
            link_file,
            use_alternate_path=False,
        ),
    )


def _build_write_file_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    file_name: str,
    content: str,
) -> list[_AlternateWriteAttempt]:
    denied_file = denied_directory / file_name
    link_file = _alternate_link_path(allowed_directory) / file_name

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Write file via alternate path form",
        link_attempt_title="Write file via allowed-directory link traversal",
        path_command=_write_file_command(operating_system, denied_file, content),
        link_command=_write_file_command(
            operating_system,
            link_file,
            content,
            use_alternate_path=False,
        ),
    )


def _build_append_file_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    file_name: str,
    initial_content: str,
    appended_content: str,
) -> list[_AlternateWriteAttempt]:
    denied_file = denied_directory / file_name
    link_file = _alternate_link_path(allowed_directory) / file_name
    content = initial_content + appended_content

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Append file via alternate path form",
        link_attempt_title="Append file via allowed-directory link traversal",
        path_command=_append_file_command(
            operating_system,
            denied_file,
            initial_content,
            appended_content,
        ),
        link_command=_append_file_command(
            operating_system,
            link_file,
            initial_content,
            appended_content,
            use_alternate_path=False,
        ),
        expected_evidence=f"content={content}",
    )


def _build_create_directory_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    directory_name: str,
) -> list[_AlternateWriteAttempt]:
    denied_target = denied_directory / directory_name
    link_target = _alternate_link_path(allowed_directory) / directory_name

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Create directory via alternate path form",
        link_attempt_title="Create directory via allowed-directory link traversal",
        path_command=_create_directory_command(operating_system, denied_target),
        link_command=_create_directory_command(
            operating_system,
            link_target,
            use_alternate_path=False,
        ),
    )


def _build_rename_file_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    source_name: str,
    target_name: str,
    content: str,
) -> list[_AlternateWriteAttempt]:
    denied_source = denied_directory / source_name
    denied_target = denied_directory / target_name
    link_source = _alternate_link_path(allowed_directory) / source_name
    link_target = _alternate_link_path(allowed_directory) / target_name

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Rename file via alternate path form",
        link_attempt_title="Rename file via allowed-directory link traversal",
        path_command=_rename_file_command(
            operating_system,
            denied_source,
            denied_target,
            content,
        ),
        link_command=_rename_file_command(
            operating_system,
            link_source,
            link_target,
            content,
            use_alternate_path=False,
        ),
    )


def _build_copy_file_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    source_name: str,
    target_name: str,
    content: str,
) -> list[_AlternateWriteAttempt]:
    denied_source = denied_directory / source_name
    denied_target = denied_directory / target_name
    link_source = _alternate_link_path(allowed_directory) / source_name
    link_target = _alternate_link_path(allowed_directory) / target_name

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Copy file via alternate path form",
        link_attempt_title="Copy file via allowed-directory link traversal",
        path_command=_copy_file_command(
            operating_system,
            denied_source,
            denied_target,
            content,
        ),
        link_command=_copy_file_command(
            operating_system,
            link_source,
            link_target,
            content,
            use_alternate_path=False,
        ),
    )


def _build_delete_file_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    file_name: str,
    content: str,
) -> list[_AlternateWriteAttempt]:
    denied_file = denied_directory / file_name
    link_file = _alternate_link_path(allowed_directory) / file_name

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Delete file via alternate path form",
        link_attempt_title="Delete file via allowed-directory link traversal",
        path_command=_delete_file_command(operating_system, denied_file, content),
        link_command=_delete_file_command(
            operating_system,
            link_file,
            content,
            use_alternate_path=False,
        ),
    )


def _build_attribute_change_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    file_name: str,
    content: str,
) -> list[_AlternateWriteAttempt]:
    denied_file = denied_directory / file_name
    link_file = _alternate_link_path(allowed_directory) / file_name

    return _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Change attributes via alternate path form",
        link_attempt_title="Change attributes via allowed-directory link traversal",
        path_command=_attribute_change_command(operating_system, denied_file, content),
        link_command=_attribute_change_command(
            operating_system,
            link_file,
            content,
            use_alternate_path=False,
        ),
    )


def _build_symlink_creation_alternate_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    target_name: str,
    link_name: str,
    content: str,
) -> list[_AlternateWriteAttempt]:
    denied_target = denied_directory / target_name
    denied_link = denied_directory / link_name
    link_target = _alternate_link_path(allowed_directory) / target_name
    link_link = _alternate_link_path(allowed_directory) / link_name

    attempts = _path_and_link_write_attempts(
        operating_system=operating_system,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        path_attempt_title="Create symlink via alternate path form",
        link_attempt_title="Create symlink via allowed-directory link traversal",
        path_command=_symlink_creation_command(
            operating_system,
            denied_target,
            denied_link,
            content,
        ),
        link_command=_symlink_creation_command(
            operating_system,
            link_target,
            link_link,
            content,
            use_alternate_path=False,
        ),
    )

    if operating_system == OperatingSystem.WINDOWS:
        denied_shortcut = denied_link.with_suffix(".lnk")
        link_shortcut = link_link.with_suffix(".lnk")
        attempts.extend(
            [
                _AlternateWriteAttempt(
                    id="A03",
                    title="Create shortcut via alternate path form",
                    bypass_class="alternate_path",
                    command_family=_shell_family(operating_system),
                    command=_build_shell_command(
                        operating_system,
                        _shortcut_creation_command(denied_target, denied_shortcut),
                        "succeeded=true",
                    ),
                ),
                _AlternateWriteAttempt(
                    id="A04",
                    title="Create shortcut via allowed-directory link traversal",
                    bypass_class="link_traversal",
                    command_family=_shell_family(operating_system),
                    command=_build_shell_command(
                        operating_system,
                        _link_traversal_script(
                            operating_system,
                            allowed_directory,
                            denied_directory,
                            _shortcut_creation_command(
                                link_target,
                                link_shortcut,
                                use_alternate_path=False,
                            ),
                        ),
                        "succeeded=true",
                    ),
                ),
            ]
        )

    return attempts


def _single_path_write_attempts(
    operating_system: OperatingSystem,
    path_attempt_title: str,
    direct_attempt_title: str,
    path_command: str,
    direct_command: str,
    expected_evidence: str = "succeeded=true",
) -> list[_AlternateWriteAttempt]:
    return [
        _AlternateWriteAttempt(
            id="A01",
            title=path_attempt_title,
            bypass_class="alternate_path",
            command_family=_shell_family(operating_system),
            command=_build_shell_command(
                operating_system,
                path_command,
                expected_evidence,
            ),
        ),
        _AlternateWriteAttempt(
            id="A02",
            title=direct_attempt_title,
            bypass_class="alternate_command",
            command_family=_shell_family(operating_system),
            command=_build_shell_command(
                operating_system,
                direct_command,
                expected_evidence,
            ),
        ),
    ]


def _path_and_link_write_attempts(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    path_attempt_title: str,
    link_attempt_title: str,
    path_command: str,
    link_command: str,
    expected_evidence: str = "succeeded=true",
) -> list[_AlternateWriteAttempt]:
    return [
        _AlternateWriteAttempt(
            id="A01",
            title=path_attempt_title,
            bypass_class="alternate_path",
            command_family=_shell_family(operating_system),
            command=_build_shell_command(
                operating_system,
                path_command,
                expected_evidence,
            ),
        ),
        _AlternateWriteAttempt(
            id="A02",
            title=link_attempt_title,
            bypass_class="link_traversal",
            command_family=_shell_family(operating_system),
            command=_build_shell_command(
                operating_system,
                _link_traversal_script(
                    operating_system,
                    allowed_directory,
                    denied_directory,
                    link_command,
                ),
                expected_evidence,
            ),
        ),
    ]


def _run_write_alternate_attempts(
    attempts: list[_AlternateWriteAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_write_alternate_attempt(attempt) for attempt in attempts]
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
        outcome = Outcome.DENIED
        summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _run_write_alternate_attempt(
    attempt: _AlternateWriteAttempt,
) -> AlternateAttemptResult:
    try:
        completed = subprocess.run(
            attempt.command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        outcome = Outcome.ALLOWED if completed.returncode == 0 else Outcome.DENIED

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
    attempt: _AlternateWriteAttempt,
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


def _create_file_command(
    operating_system: OperatingSystem,
    path: Path,
    use_alternate_path: bool = True,
) -> str:
    target = _target_path(operating_system, path, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_target = _quote_powershell_string(target)
        return (
            f"New-Item -ItemType File -Path {quoted_target} -Force "
            "| Out-Null; "
            f"Remove-Item -LiteralPath {quoted_target} -Force"
        )

    return f"touch {shlex.quote(target)} && rm -f {shlex.quote(target)}"


def _write_file_command(
    operating_system: OperatingSystem,
    path: Path,
    content: str,
    use_alternate_path: bool = True,
) -> str:
    target = _target_path(operating_system, path, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_target = _quote_powershell_string(target)
        quoted_content = _quote_powershell_string(content)
        return (
            f"Set-Content -LiteralPath {quoted_target} -Value {quoted_content}; "
            f"Get-Content -LiteralPath {quoted_target}; "
            f"Remove-Item -LiteralPath {quoted_target} -Force"
        )

    return (
        f"printf %s {shlex.quote(content)} > {shlex.quote(target)} && "
        f"cat {shlex.quote(target)} && rm -f {shlex.quote(target)}"
    )


def _append_file_command(
    operating_system: OperatingSystem,
    path: Path,
    initial_content: str,
    appended_content: str,
    use_alternate_path: bool = True,
) -> str:
    target = _target_path(operating_system, path, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_target = _quote_powershell_string(target)
        initial = _quote_powershell_string(initial_content)
        appended = _quote_powershell_string(appended_content)
        return (
            f"Set-Content -LiteralPath {quoted_target} -Value {initial}; "
            f"Add-Content -LiteralPath {quoted_target} -Value {appended}; "
            f"Get-Content -LiteralPath {quoted_target}; "
            f"Remove-Item -LiteralPath {quoted_target} -Force"
        )

    return (
        f"printf %s {shlex.quote(initial_content)} > {shlex.quote(target)} && "
        f"printf %s {shlex.quote(appended_content)} >> {shlex.quote(target)} && "
        f"cat {shlex.quote(target)} && rm -f {shlex.quote(target)}"
    )


def _create_directory_command(
    operating_system: OperatingSystem,
    path: Path,
    use_alternate_path: bool = True,
) -> str:
    target = _target_path(operating_system, path, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_target = _quote_powershell_string(target)
        return (
            f"New-Item -ItemType Directory -Path {quoted_target} -Force "
            "| Out-Null; "
            f"Remove-Item -LiteralPath {quoted_target} -Recurse -Force"
        )

    return f"mkdir {shlex.quote(target)} && rmdir {shlex.quote(target)}"


def _rename_file_command(
    operating_system: OperatingSystem,
    source: Path,
    target: Path,
    content: str,
    use_alternate_path: bool = True,
) -> str:
    source_text = _target_path(operating_system, source, use_alternate_path)
    target_text = _target_path(operating_system, target, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_source = _quote_powershell_string(source_text)
        quoted_target = _quote_powershell_string(target_text)
        quoted_content = _quote_powershell_string(content)
        return (
            f"Set-Content -LiteralPath {quoted_source} -Value {quoted_content}; "
            f"Rename-Item -LiteralPath {quoted_source} -NewName {quoted_target}; "
            f"Get-Content -LiteralPath {quoted_target}; "
            f"Remove-Item -LiteralPath {quoted_target} -Force"
        )

    return (
        f"printf %s {shlex.quote(content)} > {shlex.quote(source_text)} && "
        f"mv {shlex.quote(source_text)} {shlex.quote(target_text)} && "
        f"cat {shlex.quote(target_text)} && rm -f {shlex.quote(target_text)}"
    )


def _copy_file_command(
    operating_system: OperatingSystem,
    source: Path,
    target: Path,
    content: str,
    use_alternate_path: bool = True,
) -> str:
    source_text = _target_path(operating_system, source, use_alternate_path)
    target_text = _target_path(operating_system, target, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_source = _quote_powershell_string(source_text)
        quoted_target = _quote_powershell_string(target_text)
        quoted_content = _quote_powershell_string(content)
        return (
            f"Set-Content -LiteralPath {quoted_source} -Value {quoted_content}; "
            f"Copy-Item -LiteralPath {quoted_source} -Destination {quoted_target}; "
            f"Get-Content -LiteralPath {quoted_target}; "
            f"Remove-Item -LiteralPath {quoted_source} -Force; "
            f"Remove-Item -LiteralPath {quoted_target} -Force"
        )

    return (
        f"printf %s {shlex.quote(content)} > {shlex.quote(source_text)} && "
        f"cp {shlex.quote(source_text)} {shlex.quote(target_text)} && "
        f"cat {shlex.quote(target_text)} && "
        f"rm -f {shlex.quote(source_text)} {shlex.quote(target_text)}"
    )


def _delete_file_command(
    operating_system: OperatingSystem,
    path: Path,
    content: str,
    use_alternate_path: bool = True,
) -> str:
    target = _target_path(operating_system, path, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_target = _quote_powershell_string(target)
        return (
            f"Set-Content -LiteralPath {quoted_target} -Value "
            f"{_quote_powershell_string(content)}; "
            f"Remove-Item -LiteralPath {quoted_target} -Force; "
            f"if (Test-Path -LiteralPath {quoted_target}) "
            "{ throw 'File still exists.' }"
        )

    return (
        f"printf %s {shlex.quote(content)} > {shlex.quote(target)} && "
        f"rm -f {shlex.quote(target)} && "
        f"test ! -e {shlex.quote(target)}"
    )


def _attribute_change_command(
    operating_system: OperatingSystem,
    path: Path,
    content: str,
    use_alternate_path: bool = True,
) -> str:
    target = _target_path(operating_system, path, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_target = _quote_powershell_string(target)
        return (
            f"Set-Content -LiteralPath {quoted_target} -Value "
            f"{_quote_powershell_string(content)}; "
            f"Set-ItemProperty -LiteralPath {quoted_target} "
            "-Name IsReadOnly -Value $true; "
            f"Set-ItemProperty -LiteralPath {quoted_target} "
            "-Name IsReadOnly -Value $false; "
            f"Remove-Item -LiteralPath {quoted_target} -Force"
        )

    return (
        f"printf %s {shlex.quote(content)} > {shlex.quote(target)} && "
        f"chmod 444 {shlex.quote(target)} && chmod 644 {shlex.quote(target)} && "
        f"rm -f {shlex.quote(target)}"
    )


def _symlink_creation_command(
    operating_system: OperatingSystem,
    target: Path,
    link: Path,
    content: str,
    use_alternate_path: bool = True,
) -> str:
    target_text = _target_path(operating_system, target, use_alternate_path)
    link_text = _target_path(operating_system, link, use_alternate_path)
    if operating_system == OperatingSystem.WINDOWS:
        quoted_target = _quote_powershell_string(target_text)
        quoted_link = _quote_powershell_string(link_text)
        quoted_content = _quote_powershell_string(content)
        return (
            f"Set-Content -LiteralPath {quoted_target} -Value {quoted_content}; "
            f"New-Item -ItemType SymbolicLink -Path {quoted_link} "
            f"-Target {quoted_target} | Out-Null; "
            f"Get-Content -LiteralPath {quoted_link}; "
            f"Remove-Item -LiteralPath {quoted_link} -Force; "
            f"Remove-Item -LiteralPath {quoted_target} -Force"
        )

    return (
        f"printf %s {shlex.quote(content)} > {shlex.quote(target_text)} && "
        f"ln -s {shlex.quote(target_text)} {shlex.quote(link_text)} && "
        f"cat {shlex.quote(link_text)} && "
        f"rm -f {shlex.quote(link_text)} {shlex.quote(target_text)}"
    )


def _shortcut_creation_command(
    target: Path,
    shortcut: Path,
    use_alternate_path: bool = True,
) -> str:
    target_text = _target_path(OperatingSystem.WINDOWS, target, use_alternate_path)
    shortcut_text = _target_path(
        OperatingSystem.WINDOWS,
        shortcut,
        use_alternate_path,
    )
    quoted_target = _quote_powershell_string(target_text)
    quoted_shortcut = _quote_powershell_string(shortcut_text)
    return (
        f"Set-Content -LiteralPath {quoted_target} -Value 'shortcut target'; "
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut({quoted_shortcut}); "
        f"$shortcut.TargetPath = {quoted_target}; "
        "$shortcut.Save(); "
        f"if (-not (Test-Path -LiteralPath {quoted_shortcut})) "
        "{ throw 'Shortcut was not created.' }; "
        f"Remove-Item -LiteralPath {quoted_shortcut} -Force; "
        f"Remove-Item -LiteralPath {quoted_target} -Force"
    )


def _link_traversal_script(
    operating_system: OperatingSystem,
    allowed_directory: Path,
    denied_directory: Path,
    operation_command: str,
) -> str:
    link_path = _alternate_link_path(allowed_directory)

    if operating_system == OperatingSystem.WINDOWS:
        quoted_link = _quote_powershell_string(str(link_path))
        quoted_target = _quote_powershell_string(str(denied_directory))
        return (
            f"Remove-Item -LiteralPath {quoted_link} -Recurse -Force "
            "-ErrorAction SilentlyContinue; "
            f"New-Item -ItemType Junction -Path {quoted_link} "
            f"-Target {quoted_target} | Out-Null; "
            "try { "
            f"{operation_command}; "
            "} finally { "
            f"Remove-Item -LiteralPath {quoted_link} -Recurse -Force "
            "-ErrorAction SilentlyContinue "
            "}"
        )

    return (
        f"rm -f {shlex.quote(str(link_path))} && "
        f"ln -s {shlex.quote(str(denied_directory))} "
        f"{shlex.quote(str(link_path))} && "
        f"{operation_command}; "
        f"status=$?; rm -f {shlex.quote(str(link_path))}; exit $status"
    )


def _build_shell_command(
    operating_system: OperatingSystem,
    operation_command: str,
    expected_evidence: str,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = (
            "$ErrorActionPreference = 'Stop'; "
            f"{operation_command}; "
            f"Write-Output {expected_evidence!r}"
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]

    command = f"{operation_command} && printf '%s\\n' {shlex.quote(expected_evidence)}"
    return ["sh", "-c", command]


def _target_path(
    operating_system: OperatingSystem,
    path: Path,
    use_alternate_path: bool,
) -> str:
    if operating_system == OperatingSystem.WINDOWS and use_alternate_path:
        return _windows_extended_path(path)

    return str(path)


def _alternate_link_path(allowed_directory: Path) -> Path:
    return allowed_directory / "g03_alternate_denied_link"


def _windows_extended_path(path: Path) -> str:
    path_text = str(path.resolve())
    if path_text.startswith("\\\\?\\"):
        return path_text
    if path_text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path_text.lstrip("\\")

    return "\\\\?\\" + path_text


def _shell_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell"

    return "sh"


def _quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _alternate_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
