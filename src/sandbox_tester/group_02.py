"""Group 02: Basic filesystem read access"""

from __future__ import annotations

import asyncio
import os
import shlex
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import (
    ALLOWED_CHILD_DIRECTORY,
    ALLOWED_FILE_NAME,
    DENIED_CHILD_DIRECTORY,
    DENIED_FILE_NAME,
    HIDDEN_FILE_NAME,
    CapabilityContext,
    CapabilityGroup,
    OperatingSystem,
)


class G02_T01:
    id = "T01"
    title = "Read a known file in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.allowed_directory
            / ALLOWED_CHILD_DIRECTORY
            / ALLOWED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the known allowed test file.",
                    evidence=_read_output_evidence(self._text_file, completed.stdout),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._text_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the known allowed test file.",
                evidence=_read_output_evidence(self._text_file, content),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_path_alternate_attempts,
            _build_file_read_alternate_attempts(
                self._operating_system,
                self._text_file,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", str(self._text_file)]
        else:
            command = ["cat", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T02:
    id = "T02"
    title = "List current directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._working_directory = capability_context.working_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the current directory,",
                    evidence=_directory_listing_evidence(
                        self._working_directory,
                        completed.stdout,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._working_directory.iterdir())

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the current directory.",
                evidence=_directory_entries_evidence(self._working_directory, entries),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_path_alternate_attempts,
            _build_directory_listing_alternate_attempts(
                self._operating_system,
                self._working_directory,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._working_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T03:
    id = "T03"
    title = "List parent directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._parent_directory = capability_context.working_directory.parent

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the parent directory.",
                    evidence=_directory_listing_evidence(
                        self._parent_directory,
                        completed.stdout,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._parent_directory.iterdir())

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the parent directory.",
                evidence=_directory_entries_evidence(self._parent_directory, entries),
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
            _run_path_alternate_attempts,
            _build_directory_listing_alternate_attempts(
                self._operating_system,
                self._parent_directory,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._parent_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T04:
    id = "T04"
    title = "Read file metadata in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.allowed_directory
            / ALLOWED_CHILD_DIRECTORY
            / ALLOWED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read metadata for the known test file.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            metadata = self._text_file.stat()
            evidence = (
                f"size={metadata.st_size}, "
                f"created={metadata.st_ctime}, "
                f"modified={metadata.st_mtime}, "
                f"mode={metadata.st_mode}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read metadata for the known test file.",
                evidence=evidence,
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
            _run_path_alternate_attempts,
            _build_metadata_read_alternate_attempts(
                self._operating_system,
                self._text_file,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir", str(self._text_file)]
        else:
            command = ["ls", "-l", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T05:
    id = "T05"
    title = "Read hidden/dot files in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._hidden_file = (
            capability_context.allowed_directory
            / ALLOWED_CHILD_DIRECTORY
            / HIDDEN_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the hidden dot file.",
                    evidence=_read_output_evidence(self._hidden_file, completed.stdout),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._hidden_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the hidden dot file.",
                evidence=_read_output_evidence(self._hidden_file, content),
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
            _run_path_alternate_attempts,
            _build_file_read_alternate_attempts(
                self._operating_system,
                self._hidden_file,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", str(self._hidden_file)]
        else:
            command = ["cat", str(self._hidden_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T06:
    id = "T06"
    title = "Read user home directory listing"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._runtime_user_directory = capability_context.runtime_user_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the runtime user directory.",
                    evidence=_directory_listing_evidence(
                        self._runtime_user_directory,
                        completed.stdout,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._runtime_user_directory.iterdir())

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the runtime user directory.",
                evidence=_directory_entries_evidence(
                    self._runtime_user_directory,
                    entries,
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
            _run_path_alternate_attempts,
            _build_directory_listing_alternate_attempts(
                self._operating_system,
                self._runtime_user_directory,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._runtime_user_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T07:
    id = "T07"
    title = "Read application config directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._config_file = capability_context.working_directory / "pyproject.toml"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the project application configuration file.",
                    evidence=_read_output_evidence(
                        self._config_file,
                        completed.stdout,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._config_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python filesystem API read the project application "
                    "configuration file."
                ),
                evidence=_read_output_evidence(self._config_file, content),
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
            _run_path_alternate_attempts,
            _build_file_read_alternate_attempts(
                self._operating_system,
                self._config_file,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", str(self._config_file)]
        else:
            command = ["cat", str(self._config_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T08:
    id = "T08"
    title = "Read temporary directory listing"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._runtime_temp_directory = capability_context.runtime_temp_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the runtime temporary directory.",
                    evidence=_directory_listing_evidence(
                        self._runtime_temp_directory,
                        completed.stdout,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._runtime_temp_directory.iterdir())

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the runtime temporary directory.",
                evidence=_directory_entries_evidence(
                    self._runtime_temp_directory,
                    entries,
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
            _run_path_alternate_attempts,
            _build_directory_listing_alternate_attempts(
                self._operating_system,
                self._runtime_temp_directory,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._runtime_temp_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T09:
    id = "T09"
    title = "Read mounted/shared directory listing"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._mounted_shared_directory = capability_context.mounted_shared_directory

    async def run_shell(self) -> InvocationResult:
        if self._mounted_shared_directory is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No mounted/shared directory was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the mounted/shared directory.",
                    evidence=_directory_listing_evidence(
                        self._mounted_shared_directory,
                        completed.stdout,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._mounted_shared_directory is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No mounted/shared directory was configured.",
            )

        try:
            entries = list(self._mounted_shared_directory.iterdir())

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the mounted/shared directory.",
                evidence=_directory_entries_evidence(
                    self._mounted_shared_directory,
                    entries,
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
        if self._mounted_shared_directory is None:
            return AlternateInvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No mounted/shared directory was configured.",
                attempts=[],
            )

        return await asyncio.to_thread(
            _run_path_alternate_attempts,
            _build_directory_listing_alternate_attempts(
                self._operating_system,
                self._mounted_shared_directory,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._mounted_shared_directory is None:
            raise RuntimeError("No mounted/shared directory was configured.")

        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._mounted_shared_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T10:
    id = "T10"
    title = "Read a known file in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.denied_directory
            / DENIED_CHILD_DIRECTORY
            / DENIED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the known denied test file.",
                    evidence=_read_output_evidence(self._text_file, completed.stdout),
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
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._text_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the known denied test file.",
                evidence=_read_output_evidence(self._text_file, content),
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
            _run_path_alternate_attempts,
            _build_file_read_alternate_attempts(
                self._operating_system,
                self._text_file,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", str(self._text_file)]
        else:
            command = ["cat", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T11:
    id = "T11"
    title = "Read file metadata in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.denied_directory
            / DENIED_CHILD_DIRECTORY
            / DENIED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read metadata for the known denied test file.",
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
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            metadata = self._text_file.stat()
            evidence = (
                f"size={metadata.st_size}, "
                f"created={metadata.st_ctime}, "
                f"modified={metadata.st_mtime}, "
                f"mode={metadata.st_mode}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read metadata for the denied test file.",
                evidence=evidence,
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
            _run_path_alternate_attempts,
            _build_metadata_read_alternate_attempts(
                self._operating_system,
                self._text_file,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir", str(self._text_file)]
        else:
            command = ["ls", "-l", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T12:
    id = "T12"
    title = "Read hidden/dot files in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._hidden_file = (
            capability_context.denied_directory
            / DENIED_CHILD_DIRECTORY
            / HIDDEN_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the hidden dot file in the denied directory.",
                    evidence=_read_output_evidence(self._hidden_file, completed.stdout),
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
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._hidden_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the denied directory hidden file.",
                evidence=_read_output_evidence(self._hidden_file, content),
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
            _run_path_alternate_attempts,
            _build_file_read_alternate_attempts(
                self._operating_system,
                self._hidden_file,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", str(self._hidden_file)]
        else:
            command = ["cat", str(self._hidden_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def _read_output_evidence(path: Path, content: str) -> str:
    return f"path={path}; bytes_read={len(content.encode('utf-8', errors='replace'))}"


def _directory_listing_evidence(path: Path, output: str) -> str:
    entries = [line for line in output.splitlines() if line.strip()]
    return f"path={path}; entry_count={len(entries)}"


def _directory_entries_evidence(path: Path, entries: list[Path]) -> str:
    return f"path={path}; entry_count={len(entries)}"


_g24_NO_SHELL_CANDIDATE_EXIT_CODE = 127

_g24_LINUX_SURFACE_DIRECTORIES = [
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/run"),
    Path("/mnt"),
    Path("/media"),
]

_g24_LINUX_SURFACE_DIRECTORIES_AS_TEXT = [
    str(path) for path in _g24_LINUX_SURFACE_DIRECTORIES
]

_g24_LINUX_PROCESS_NAMESPACE_DIRECTORY = Path("/proc/self/ns")

_g24_LINUX_SERVICE_ACCOUNT_PATHS = [
    Path("/var/run/secrets/kubernetes.io"),
    Path("/run/secrets/kubernetes.io"),
    Path("/run/secrets"),
    Path("/var/run/secrets"),
]

_g24_LINUX_MOUNTINFO_PATH = Path("/proc/self/mountinfo")

_g24_LINUX_CONTAINER_RUNTIME_SOCKET_PATHS = [
    Path("/run/containerd/containerd.sock"),
    Path("/var/run/containerd/containerd.sock"),
    Path("/run/crio/crio.sock"),
    Path("/var/run/crio/crio.sock"),
    Path("/run/podman/podman.sock"),
    Path("/var/run/podman/podman.sock"),
]


class G02_T13:
    id = "T13"
    title = "Read Linux namespace surface directories"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g24_run_shell_surface_directory_listing,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux namespace surface directories.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g24_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux namespace surface directories are not applicable.",
                    evidence=_g24_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read all Linux namespace surface directories.",
                evidence=_g24_failure_evidence(completed, combined_output),
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
                summary="Shell namespace surface directory listing timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell namespace surface directory listing failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux namespace surface directories are not applicable.",
            )

        try:
            all_readable, evidence = await asyncio.to_thread(
                _g24_read_surface_directories_with_python,
            )

            if all_readable:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime read Linux namespace surface directories.",
                    evidence=evidence,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not read all Linux namespace surface "
                    "directories."
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
                summary="Python runtime namespace surface directory listing failed.",
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
            _g24_run_namespace_alternate_attempts,
            _g24_build_surface_directory_alternate_attempts(self._operating_system),
        )


class G02_T14:
    id = "T14"
    title = "Read Linux service account secret files"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g24_run_shell_service_account_secret_read,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux service account secret file metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g24_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux service account secret files were not present.",
                    evidence=_g24_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux service account secret files.",
                evidence=_g24_failure_evidence(completed, combined_output),
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
                summary="Shell service account secret file read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell service account secret file read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux service account secret files were not present.",
            )

        try:
            result = await asyncio.to_thread(
                _g24_read_service_account_secret_metadata_with_python,
            )

            if result[0] == Outcome.ALLOWED:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime read Linux service account secret file "
                        "metadata."
                    ),
                    evidence=result[1],
                )

            if result[0] == Outcome.NOT_APPLICABLE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux service account secret files were not present.",
                    evidence=result[1],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not read Linux service account secret files."
                ),
                evidence=result[1],
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
                summary="Python runtime service account secret file read failed.",
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
            _g24_run_namespace_alternate_attempts,
            _g24_build_service_account_alternate_attempts(self._operating_system),
        )


class G02_T15:
    id = "T15"
    title = "Detect Linux mounted host paths and writable volumes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g24_run_shell_mount_surface_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected Linux mount and volume surfaces.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g24_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux mount and volume surfaces are not applicable.",
                    evidence=_g24_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not detect Linux mount and volume surfaces.",
                evidence=_g24_failure_evidence(completed, combined_output),
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
                summary="Shell mount surface detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell mount surface detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux mount and volume surfaces are not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g24_detect_mount_surfaces_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected Linux mount and volume surfaces.",
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
                summary="Python runtime mount surface detection failed.",
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
            _g24_run_namespace_alternate_attempts,
            _g24_build_mount_surface_alternate_attempts(self._operating_system),
        )


def _g24_run_shell_surface_directory_listing(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux namespace surface directories are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_surface_directory_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


@dataclass(frozen=True)
class _g24_AlternateNamespaceAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _g24_build_surface_directory_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    paths = " ".join(str(path) for path in _g24_LINUX_SURFACE_DIRECTORIES)
    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Read namespace surface directories via find",
            bypass_class="namespace_surface_directory_read",
            command_family="find",
            command=[
                "sh",
                "-c",
                (
                    f"for path in {paths}; do "
                    'printf "%s=" "$path"; '
                    'find "$path" -maxdepth 1 -mindepth 1 -print 2>/dev/null '
                    "| head -n 5 | paste -sd, -; "
                    "done"
                ),
            ],
        ),
        _g24_AlternateNamespaceAttempt(
            id="A02",
            title="Read namespace surface metadata via stat",
            bypass_class="namespace_surface_directory_read",
            command_family="stat",
            command=["stat", *_g24_LINUX_SURFACE_DIRECTORIES_AS_TEXT],
        ),
    ]


def _g24_build_process_namespace_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Read process namespace links via ls",
            bypass_class="process_namespace_link_read",
            command_family="ls/readlink",
            command=[
                "sh",
                "-c",
                (
                    "ls -l /proc/self/ns; "
                    "for namespace in /proc/self/ns/*; do "
                    'printf "%s=" "$(basename "$namespace")"; '
                    'readlink "$namespace"; '
                    "done"
                ),
            ],
        )
    ]


def _g24_build_service_account_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    paths = " ".join(str(path) for path in _g24_LINUX_SERVICE_ACCOUNT_PATHS)
    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Read service account secret metadata via find",
            bypass_class="service_account_secret_metadata_read",
            command_family="find/wc",
            command=[
                "sh",
                "-c",
                (
                    f"present=0; readable=0; for root in {paths}; do "
                    '[ -e "$root" ] || continue; present=1; '
                    'find "$root" -maxdepth 3 -type f 2>/dev/null | '
                    "while IFS= read -r file; do "
                    'size=$(wc -c < "$file" 2>/dev/null) '
                    "&& readable=$((readable + 1)) "
                    '&& printf "%s:size=%s;" "$file" "$size"; '
                    "done; "
                    "done; "
                    '[ "$present" -eq 1 ] || exit 127'
                ),
            ],
        )
    ]


def _g24_build_mount_surface_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Detect mount surfaces via findmnt",
            bypass_class="mount_surface_detection",
            command_family="findmnt",
            command=[
                "sh",
                "-c",
                (
                    "command -v findmnt >/dev/null 2>&1 || exit 127; "
                    "findmnt -R -o TARGET,SOURCE,FSTYPE,OPTIONS | head -n 30"
                ),
            ],
        ),
        _g24_AlternateNamespaceAttempt(
            id="A02",
            title="Detect mount surfaces via mount and df",
            bypass_class="mount_surface_detection",
            command_family="mount/df",
            command=["sh", "-c", "mount | head -n 30; df -T | head -n 30"],
        ),
    ]


def _g24_build_container_runtime_socket_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Access container runtime sockets via shell socket client",
            bypass_class="container_runtime_socket_access",
            command_family="socat/nc-unix",
            command=_g24_build_linux_container_runtime_socket_command(),
        )
    ]


def _g24_run_namespace_alternate_attempts(
    attempts: list[_g24_AlternateNamespaceAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _g24_run_namespace_alternate_attempt(attempt) for attempt in attempts
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


def _g24_run_namespace_alternate_attempt(
    attempt: _g24_AlternateNamespaceAttempt,
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
        elif completed.returncode == _g24_NO_SHELL_CANDIDATE_EXIT_CODE:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_g24_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g24_namespace_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.ERROR, error)


def _g24_namespace_alternate_exception_result(
    attempt: _g24_AlternateNamespaceAttempt,
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


def _g24_run_shell_process_namespace_link_read(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux process namespace links are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_process_namespace_link_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_run_shell_service_account_secret_read(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux service account secret files are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_service_account_secret_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_run_shell_mount_surface_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux mount and volume surfaces are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_mount_surface_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_run_shell_container_runtime_socket_access(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux container runtime Unix sockets are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_container_runtime_socket_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_build_linux_surface_directory_command() -> list[str]:
    paths = " ".join(str(path) for path in _g24_LINUX_SURFACE_DIRECTORIES)
    script = f"""
set -u
denied=0
evidence=""
for path in {paths}; do
    if [ ! -e "$path" ]; then
        evidence="${{evidence}}$path:missing;"
        continue
    fi
    if [ ! -d "$path" ]; then
        evidence="${{evidence}}$path:not_directory;"
        denied=1
        continue
    fi
    entry_count=$(ls -A "$path" 2>/dev/null | wc -l)
    status=$?
    if [ "$status" -eq 0 ]; then
        evidence="${{evidence}}$path:readable:entry_count=$entry_count;"
    else
        evidence="${{evidence}}$path:denied;"
        denied=1
    fi
done
printf '%s\\n' "$evidence"
exit "$denied"
"""
    return ["sh", "-c", script]


def _g24_build_linux_container_runtime_socket_command() -> list[str]:
    paths = " ".join(str(path) for path in _g24_linux_container_runtime_socket_paths())
    script = f"""
set -u
present=0
connected=0
denied=0
evidence=""
if command -v socat >/dev/null 2>&1; then
    client=socat
elif command -v nc >/dev/null 2>&1; then
    client=nc
else
    client=""
fi
for path in {paths}; do
    if [ ! -e "$path" ]; then
        continue
    fi
    if [ ! -S "$path" ]; then
        evidence="${{evidence}}$path:not_socket;"
        present=1
        denied=$((denied + 1))
        continue
    fi
    present=1
    if [ -z "$client" ]; then
        evidence="${{evidence}}$path:present:no_shell_socket_client;"
        continue
    fi
    if [ "$client" = "socat" ]; then
        timeout 2 sh -c "printf '' | socat - UNIX-CONNECT:'$path'" \
            >/dev/null 2>&1
        status=$?
    else
        timeout 2 nc -U -z "$path" >/dev/null 2>&1
        status=$?
    fi
    if [ "$status" -eq 0 ]; then
        connected=$((connected + 1))
        evidence="${{evidence}}$path:connected;"
    else
        denied=$((denied + 1))
        evidence="${{evidence}}$path:denied_or_unreachable:status=$status;"
    fi
done
if [ "$present" -eq 0 ]; then
    echo "present=False"
    exit 127
fi
printf 'present=True; connected_count=%s; denied_count=%s; sockets=[%s]\\n' \
    "$connected" \
    "$denied" \
    "$evidence"
if [ "$connected" -gt 0 ]; then
    exit 0
fi
if [ -z "$client" ]; then
    exit 127
fi
exit 1
"""
    return ["sh", "-c", script]


def _g24_build_linux_mount_surface_command() -> list[str]:
    script = """
set -u
if [ ! -r /proc/self/mountinfo ]; then
    echo '/proc/self/mountinfo:unreadable'
    exit 1
fi
mount_count=$(wc -l < /proc/self/mountinfo)
rw_count=$(
    awk '{
        split($6, options, ",")
        for (i in options) {
            if (options[i] == "rw") {
                count += 1
                break
            }
        }
    } END { print count + 0 }' /proc/self/mountinfo
)
bind_like_count=$(
    awk '$0 ~ / - (overlay|9p|virtiofs|fuse|fuse\\.|nfs|cifs|drvfs|vboxsf|vmhgfs) / {
        count += 1
    } END { print count + 0 }' /proc/self/mountinfo
)
printf 'mount_count=%s; rw_option_count=%s; bind_like_count=%s\\n' \
    "$mount_count" \
    "$rw_count" \
    "$bind_like_count"
"""
    return ["sh", "-c", script]


def _g24_build_linux_service_account_secret_command() -> list[str]:
    paths = " ".join(str(path) for path in _g24_LINUX_SERVICE_ACCOUNT_PATHS)
    script = f"""
set -u
present=0
readable=0
denied=0
evidence=""
for root in {paths}; do
    if [ ! -e "$root" ]; then
        continue
    fi
    present=1
    if [ -f "$root" ]; then
        size=$(wc -c < "$root" 2>/dev/null || true)
        if [ -n "$size" ]; then
            readable=$((readable + 1))
            evidence="${{evidence}}file:readable;"
        else
            denied=$((denied + 1))
            evidence="${{evidence}}file:denied;"
        fi
        continue
    fi
    if [ -d "$root" ]; then
        while IFS= read -r file; do
            [ -n "$file" ] || continue
            size=$(wc -c < "$file" 2>/dev/null || true)
            if [ -n "$size" ]; then
                readable=$((readable + 1))
                evidence="${{evidence}}file:readable;"
            else
                denied=$((denied + 1))
                evidence="${{evidence}}file:denied;"
            fi
        done <<EOF
$(find "$root" -maxdepth 3 -type f 2>/dev/null)
EOF
    fi
done
if [ "$present" -eq 0 ]; then
    echo "present=False"
    exit 127
fi
printf 'present=True; readable_count=%s; denied_count=%s; files=[%s]\\n' \\
    "$readable" \\
    "$denied" \\
    "$evidence"
if [ "$readable" -gt 0 ]; then
    exit 0
fi
exit 1
"""
    return ["sh", "-c", script]


def _g24_build_linux_process_namespace_link_command() -> list[str]:
    script = """
set -u
if [ ! -d /proc/self/ns ]; then
    echo '/proc/self/ns:missing'
    exit 1
fi
evidence=""
for namespace in /proc/self/ns/*; do
    name=$(basename "$namespace")
    target=$(readlink "$namespace" 2>/dev/null || true)
    if [ -n "$target" ]; then
        evidence="${evidence}${name}:${target},"
    else
        evidence="${evidence}${name}:denied,"
        exit_code=1
    fi
done
printf '%s\\n' "$evidence"
exit "${exit_code:-0}"
"""
    return ["sh", "-c", script]


def _g24_read_surface_directories_with_python() -> tuple[bool, str]:
    all_readable = True
    entries: list[str] = []

    for path in _g24_LINUX_SURFACE_DIRECTORIES:
        if not path.exists():
            entries.append(f"{path}:missing")
            continue

        if not path.is_dir():
            entries.append(f"{path}:not_directory")
            all_readable = False
            continue

        try:
            entry_count = sum(1 for _ in path.iterdir())
            entries.append(f"{path}:readable:entry_count={entry_count}")
        except PermissionError:
            entries.append(f"{path}:denied")
            all_readable = False

    return all_readable, ";".join(entries)


def _g24_read_process_namespace_links_with_python() -> str:
    if not _g24_LINUX_PROCESS_NAMESPACE_DIRECTORY.exists():
        raise FileNotFoundError(_g24_LINUX_PROCESS_NAMESPACE_DIRECTORY)

    entries: list[str] = []

    for path in sorted(_g24_LINUX_PROCESS_NAMESPACE_DIRECTORY.iterdir()):
        target = path.readlink()
        entries.append(f"{path.name}:{target}")

    return ",".join(entries)


def _g24_read_service_account_secret_metadata_with_python() -> tuple[Outcome, str]:
    candidates = _g24_collect_service_account_secret_files()

    if not candidates:
        return Outcome.NOT_APPLICABLE, "present=False"

    readable_count = 0
    denied_count = 0
    entries: list[str] = []

    for path in candidates:
        try:
            path.stat()
            readable_count += 1
            entries.append("file:readable")
        except PermissionError:
            denied_count += 1
            entries.append("file:denied")

    evidence = (
        "present=True; "
        f"readable_count={readable_count}; "
        f"denied_count={denied_count}; "
        f"files=[{';'.join(entries)}]"
    )

    if readable_count > 0:
        return Outcome.ALLOWED, evidence

    return Outcome.DENIED, evidence


def _g24_detect_mount_surfaces_with_python() -> str:
    mounts = _g24_read_linux_mountinfo()
    rw_option_count = 0
    writable_mountpoint_count = 0
    bind_like_mounts: list[dict[str, str]] = []

    for mount in mounts:
        options = mount["options"].split(",")

        if "rw" in options:
            rw_option_count += 1

        if os.access(mount["mount_point"], os.W_OK):
            writable_mountpoint_count += 1

        if _g24_is_bind_like_mount(mount):
            bind_like_mounts.append(mount)

    return (
        f"mount_count={len(mounts)}; "
        f"rw_option_count={rw_option_count}; "
        f"writable_mountpoint_count={writable_mountpoint_count}; "
        f"bind_like_count={len(bind_like_mounts)}"
    )


def _g24_read_linux_mountinfo() -> list[dict[str, str]]:
    mounts: list[dict[str, str]] = []

    with _g24_LINUX_MOUNTINFO_PATH.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        for line in file:
            fields = line.strip().split()

            if "-" not in fields:
                continue

            separator_index = fields.index("-")

            if separator_index + 3 > len(fields):
                continue

            mount = {
                "mount_point": _g24_decode_mountinfo_field(fields[4]),
                "options": fields[5],
                "filesystem_type": fields[separator_index + 1],
                "mount_source": _g24_decode_mountinfo_field(
                    fields[separator_index + 2]
                ),
            }
            mounts.append(mount)

    return mounts


def _g24_decode_mountinfo_field(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _g24_is_bind_like_mount(mount: dict[str, str]) -> bool:
    filesystem_type = mount["filesystem_type"]
    mount_source = mount["mount_source"]
    mount_point = mount["mount_point"]
    bind_like_filesystems = {
        "9p",
        "cifs",
        "drvfs",
        "fuse",
        "fuse.vmhgfs-fuse",
        "nfs",
        "overlay",
        "virtiofs",
        "vboxsf",
        "vmhgfs",
    }

    if filesystem_type in bind_like_filesystems:
        return True

    return (
        mount_source.startswith("/")
        and not mount_point.startswith("/proc")
        and not mount_point.startswith("/sys")
        and not mount_point.startswith("/dev")
    )


def _g24_access_container_runtime_sockets_with_python() -> tuple[Outcome, str]:
    candidates = [
        path for path in _g24_linux_container_runtime_socket_paths() if path.exists()
    ]

    if not candidates:
        return Outcome.NOT_APPLICABLE, "present=False"

    connected_count = 0
    denied_count = 0
    entries: list[str] = []

    for path in candidates:
        if not path.is_socket():
            denied_count += 1
            entries.append(f"{path}:not_socket")
            continue

        try:
            unix_socket_family = socket.AF_UNIX  # type: ignore[attr-defined]

            with socket.socket(unix_socket_family, socket.SOCK_STREAM) as client:
                client.settimeout(2)
                client.connect(str(path))

            connected_count += 1
            entries.append(f"{path}:connected")
        except OSError as error:
            denied_count += 1
            entries.append(f"{path}:denied_or_unreachable:{error.__class__.__name__}")

    evidence = (
        "present=True; "
        f"connected_count={connected_count}; "
        f"denied_count={denied_count}; "
        f"sockets=[{';'.join(entries)}]"
    )

    if connected_count > 0:
        return Outcome.ALLOWED, evidence

    return Outcome.DENIED, evidence


def _g24_linux_container_runtime_socket_paths() -> list[Path]:
    paths = list(_g24_LINUX_CONTAINER_RUNTIME_SOCKET_PATHS)
    runtime_directory = os.environ.get("XDG_RUNTIME_DIR")

    if runtime_directory:
        paths.append(Path(runtime_directory) / "podman" / "podman.sock")
    else:
        getuid = os.getuid  # type: ignore[attr-defined]
        paths.append(Path("/run/user") / str(getuid()) / "podman/podman.sock")

    return paths


def _g24_collect_service_account_secret_files() -> list[Path]:
    files: list[Path] = []

    for path in _g24_LINUX_SERVICE_ACCOUNT_PATHS:
        if not path.exists():
            continue

        if path.is_file():
            files.append(path)
            continue

        if path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file())

    return sorted(set(files))


def _g24_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G02",
        title="Basic filesystem read access",
        tests=[
            G02_T01(capability_context),
            G02_T02(capability_context),
            G02_T03(capability_context),
            G02_T04(capability_context),
            G02_T05(capability_context),
            G02_T06(capability_context),
            G02_T07(capability_context),
            G02_T08(capability_context),
            G02_T09(capability_context),
            G02_T10(capability_context),
            G02_T11(capability_context),
            G02_T12(capability_context),
            G02_T13(capability_context),
            G02_T14(capability_context),
            G02_T15(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternatePathAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]
    target_path: Path
    evidence_kind: str


def _build_file_read_alternate_attempts(
    operating_system: OperatingSystem,
    path: Path,
) -> list[_AlternatePathAttempt]:
    attempts: list[_AlternatePathAttempt] = []

    if operating_system == OperatingSystem.WINDOWS:
        attempts.append(
            _AlternatePathAttempt(
                id="A01",
                title="Read via Windows extended-length path",
                bypass_class="alternate_path",
                command_family="cmd/type",
                command=["cmd", "/c", "type", _windows_extended_path(path)],
                target_path=path,
                evidence_kind="file_read",
            )
        )
        attempts.append(
            _AlternatePathAttempt(
                id="A02",
                title="Read via PowerShell Get-Content",
                bypass_class="alternate_command",
                command_family="powershell/get-content",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    f"Get-Content -LiteralPath {_quote_powershell_string(str(path))}",
                ],
                target_path=path,
                evidence_kind="file_read",
            )
        )
        return attempts

    attempts.append(
        _AlternatePathAttempt(
            id="A01",
            title="Read via /proc/self/root alternate path",
            bypass_class="alternate_path",
            command_family="cat",
            command=["cat", _linux_proc_root_path(path)],
            target_path=path,
            evidence_kind="file_read",
        )
    )
    attempts.append(
        _AlternatePathAttempt(
            id="A02",
            title="Read via inherited file descriptor",
            bypass_class="inherited_descriptor",
            command_family="sh/procfs",
            command=[
                "sh",
                "-c",
                (f"exec 3< {shlex.quote(str(path))} && cat /proc/$$/fd/3"),
            ],
            target_path=path,
            evidence_kind="file_read",
        )
    )
    attempts.append(
        _AlternatePathAttempt(
            id="A03",
            title="Read via sed",
            bypass_class="alternate_command",
            command_family="sed",
            command=["sed", "-n", "1,200p", str(path)],
            target_path=path,
            evidence_kind="file_read",
        )
    )
    return attempts


def _build_metadata_read_alternate_attempts(
    operating_system: OperatingSystem,
    path: Path,
) -> list[_AlternatePathAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternatePathAttempt(
                id="A01",
                title="Read metadata via Windows extended-length path",
                bypass_class="alternate_path",
                command_family="cmd/dir",
                command=["cmd", "/c", "dir", _windows_extended_path(path)],
                target_path=path,
                evidence_kind="metadata",
            ),
            _AlternatePathAttempt(
                id="A02",
                title="Read metadata via PowerShell Get-Item",
                bypass_class="alternate_command",
                command_family="powershell/get-item",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$item = Get-Item -LiteralPath "
                        f"{_quote_powershell_string(str(path))}; "
                        "$item | Select-Object FullName,Length,CreationTime,"
                        "LastWriteTime,Attributes"
                    ),
                ],
                target_path=path,
                evidence_kind="metadata",
            ),
        ]

    return [
        _AlternatePathAttempt(
            id="A01",
            title="Read metadata via /proc/self/root alternate path",
            bypass_class="alternate_path",
            command_family="ls",
            command=["ls", "-l", _linux_proc_root_path(path)],
            target_path=path,
            evidence_kind="metadata",
        ),
        _AlternatePathAttempt(
            id="A02",
            title="Read metadata via stat",
            bypass_class="alternate_command",
            command_family="stat",
            command=["stat", str(path)],
            target_path=path,
            evidence_kind="metadata",
        ),
    ]


def _build_directory_listing_alternate_attempts(
    operating_system: OperatingSystem,
    path: Path,
) -> list[_AlternatePathAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternatePathAttempt(
                id="A01",
                title="List directory via Windows extended-length path",
                bypass_class="alternate_path",
                command_family="cmd/dir",
                command=["cmd", "/c", "dir", _windows_extended_path(path)],
                target_path=path,
                evidence_kind="directory_listing",
            ),
            _AlternatePathAttempt(
                id="A02",
                title="List directory via PowerShell Get-ChildItem",
                bypass_class="alternate_command",
                command_family="powershell/get-childitem",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "Get-ChildItem -Force -LiteralPath "
                        f"{_quote_powershell_string(str(path))}"
                    ),
                ],
                target_path=path,
                evidence_kind="directory_listing",
            ),
        ]

    return [
        _AlternatePathAttempt(
            id="A01",
            title="List directory via /proc/self/root alternate path",
            bypass_class="alternate_path",
            command_family="ls",
            command=["ls", _linux_proc_root_path(path)],
            target_path=path,
            evidence_kind="directory_listing",
        ),
        _AlternatePathAttempt(
            id="A02",
            title="List directory via find",
            bypass_class="alternate_command",
            command_family="find",
            command=["find", str(path), "-maxdepth", "1", "-mindepth", "1", "-print"],
            target_path=path,
            evidence_kind="directory_listing",
        ),
    ]


def _run_path_alternate_attempts(
    attempts: list[_AlternatePathAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_path_alternate_attempt(attempt) for attempt in attempts]
    allowed_count = sum(
        1 for result in attempt_results if result.outcome == Outcome.ALLOWED
    )

    if allowed_count > 0:
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


def _run_path_alternate_attempt(
    attempt: _AlternatePathAttempt,
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
            evidence=_alternate_evidence(attempt, completed, combined_output),
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
    attempt: _AlternatePathAttempt,
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
    attempt: _AlternatePathAttempt,
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if completed.returncode == 0:
        if attempt.evidence_kind == "file_read":
            return _read_output_evidence(attempt.target_path, completed.stdout)

        if attempt.evidence_kind == "directory_listing":
            return _directory_listing_evidence(attempt.target_path, completed.stdout)

        if attempt.evidence_kind == "metadata":
            return f"path={attempt.target_path}; metadata_read=True"

    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def _windows_extended_path(path: Path) -> str:
    path_text = str(path.resolve())
    if path_text.startswith("\\\\?\\"):
        return path_text
    if path_text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path_text.lstrip("\\")

    return "\\\\?\\" + path_text


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _linux_proc_root_path(path: Path) -> str:
    path_text = str(path.resolve())
    return "/proc/self/root/" + path_text.lstrip("/")
