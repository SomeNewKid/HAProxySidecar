"""Group 01: Runtime identity and execution context."""

from __future__ import annotations

import asyncio
import getpass
import os
import platform
import socket
import subprocess
import sys
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


class G01_T01:
    id = "T01"
    title = "Identify current working directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                current_directory = completed.stdout.strip()
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the current working directory.",
                    evidence=current_directory,
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
            current_directory = Path.cwd()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python filesystem API identified the current working directory."
                ),
                evidence=str(current_directory),
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
            _run_runtime_alternate_attempts,
            _build_working_directory_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "cd"]
        else:
            command = ["pwd"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T02:
    id = "T02"
    title = "Identify current user/account name"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the current user/account name.",
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
            username = getpass.getuser()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the current user/account name.",
                evidence=username,
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
            _run_runtime_alternate_attempts,
            _build_current_user_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["whoami"]
        else:
            command = ["id", "-un"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T03:
    id = "T03"
    title = "Identify process ID"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified a process ID for its invocation.",
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

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the current process ID.",
                evidence=str(process_id),
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
            _run_runtime_alternate_attempts,
            _build_process_id_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["powershell", "-NoProfile", "-Command", "$PID"]
        else:
            command = ["sh", "-c", "echo $$"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T04:
    id = "T04"
    title = "Identify operating system family"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the operating system family.",
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
            system_name = platform.system()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the operating system family.",
                evidence=system_name,
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
            _run_runtime_alternate_attempts,
            _build_operating_system_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "ver"]
        else:
            command = ["uname", "-s"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T05:
    id = "T05"
    title = "Identify CPU architecture"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the CPU architecture.",
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
            architecture = platform.machine()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the CPU architecture.",
                evidence=architecture,
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
            _run_runtime_alternate_attempts,
            _build_cpu_architecture_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "echo", "%PROCESSOR_ARCHITECTURE%"]
        else:
            command = ["uname", "-m"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T06:
    id = "T06"
    title = "Identify hostname or machine name"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the hostname or machine name.",
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
            hostname = socket.gethostname()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the hostname or machine name.",
                evidence=hostname,
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
            _run_runtime_alternate_attempts,
            _build_hostname_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = ["hostname"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T07:
    id = "T07"
    title = "Identify container/VM indicators"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                evidence = completed.stdout.strip()
                if not evidence:
                    evidence = "No common container/VM indicators found."

                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell checked for common container/VM indicators.",
                    evidence=evidence[:500],
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
            indicators: list[str] = []

            if Path("/.dockerenv").exists():
                indicators.append("/.dockerenv exists")
            if os.environ.get("container"):
                indicators.append("container environment variable is set")
            if os.environ.get("KUBERNETES_SERVICE_HOST"):
                indicators.append("KUBERNETES_SERVICE_HOST is set")
            if os.environ.get("WSL_INTEROP"):
                indicators.append("WSL_INTEROP is set")

            evidence = ", ".join(indicators)
            if not evidence:
                evidence = "No common container/VM indicators found."

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime checked for common container/VM indicators.",
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
            _run_runtime_alternate_attempts,
            _build_container_vm_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "$items = @(); "
                    "if ($env:container) { $items += 'container env var is set' }; "
                    "if ($env:KUBERNETES_SERVICE_HOST) { "
                    "$items += 'KUBERNETES_SERVICE_HOST is set' }; "
                    "if ($env:WSL_INTEROP) { $items += 'WSL_INTEROP is set' }; "
                    "$items -join ', '"
                ),
            ]
        else:
            command = [
                "sh",
                "-c",
                (
                    "items=''; "
                    '[ -f /.dockerenv ] && items="$items/.dockerenv exists, "; '
                    '[ -n "$container" ] && '
                    'items="$items container env var is set, "; '
                    '[ -n "$KUBERNETES_SERVICE_HOST" ] && '
                    'items="$items KUBERNETES_SERVICE_HOST is set, "; '
                    "printf '%s' \"$items\""
                ),
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T08:
    id = "T08"
    title = "Read command-line arguments"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read command-line arguments for its invocation.",
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
            command_line_arguments = " ".join(sys.argv)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read its command-line arguments.",
                evidence=command_line_arguments[:500],
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
            _run_runtime_alternate_attempts,
            _build_command_line_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "[Environment]::CommandLine",
            ]
        else:
            command = ["sh", "-c", "tr '\\0' ' ' < /proc/$$/cmdline"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T09:
    id = "T09"
    title = "Read process environment summary"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                names = self._summarize_environment_names(completed.stdout)
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read a summary of process environment names.",
                    evidence=names,
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
            environment_names = sorted(os.environ)
            displayed_names = ", ".join(environment_names[:20])
            evidence = f"count={len(environment_names)}; names={displayed_names}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read a summary of process environment names.",
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
            _run_runtime_alternate_attempts,
            _build_environment_summary_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-ChildItem Env: | Select-Object -ExpandProperty Name",
            ]
        else:
            command = ["sh", "-c", "env | cut -d= -f1"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _summarize_environment_names(self, output: str) -> str:
        environment_names = sorted(
            line.strip() for line in output.splitlines() if line.strip()
        )
        displayed_names = ", ".join(environment_names[:20])
        return f"count={len(environment_names)}; names={displayed_names}"[:500]


_g23_LINUX_CONTAINER_MARKERS = [
    Path("/.dockerenv"),
    Path("/run/.containerenv"),
]

_g23_LINUX_CGROUP_PATH = Path("/proc/1/cgroup")

_g23_LINUX_SELF_CGROUP_PATH = Path("/proc/self/cgroup")

_g23_LINUX_SELF_STATUS_PATH = Path("/proc/self/status")

_g23_LINUX_SELF_NAMESPACE_DIRECTORY = Path("/proc/self/ns")

_g23_LINUX_APPARMOR_CURRENT_PATH = Path("/proc/self/attr/current")

_g23_LINUX_SELINUX_ENFORCE_PATH = Path("/sys/fs/selinux/enforce")

_g23_LINUX_PRODUCT_NAME_PATH = Path("/sys/class/dmi/id/product_name")

_g23_LINUX_PRODUCT_VERSION_PATH = Path("/sys/class/dmi/id/product_version")

_g23_LINUX_MACHINE_ID_PATHS = [
    Path("/etc/machine-id"),
    Path("/var/lib/dbus/machine-id"),
]

_g23_LINUX_DOMAIN_PATHS = [
    Path("/etc/resolv.conf"),
    Path("/etc/krb5.conf"),
    Path("/etc/sssd/sssd.conf"),
    Path("/etc/samba/smb.conf"),
]

_g23_NO_SHELL_CANDIDATE_EXIT_CODE = 127

_g23_LINUX_CAPABILITY_NAMES = {
    0: "CAP_CHOWN",
    1: "CAP_DAC_OVERRIDE",
    2: "CAP_DAC_READ_SEARCH",
    3: "CAP_FOWNER",
    4: "CAP_FSETID",
    5: "CAP_KILL",
    6: "CAP_SETGID",
    7: "CAP_SETUID",
    8: "CAP_SETPCAP",
    9: "CAP_LINUX_IMMUTABLE",
    10: "CAP_NET_BIND_SERVICE",
    11: "CAP_NET_BROADCAST",
    12: "CAP_NET_ADMIN",
    13: "CAP_NET_RAW",
    14: "CAP_IPC_LOCK",
    15: "CAP_IPC_OWNER",
    16: "CAP_SYS_MODULE",
    17: "CAP_SYS_RAWIO",
    18: "CAP_SYS_CHROOT",
    19: "CAP_SYS_PTRACE",
    20: "CAP_SYS_PACCT",
    21: "CAP_SYS_ADMIN",
    22: "CAP_SYS_BOOT",
    23: "CAP_SYS_NICE",
    24: "CAP_SYS_RESOURCE",
    25: "CAP_SYS_TIME",
    26: "CAP_SYS_TTY_CONFIG",
    27: "CAP_MKNOD",
    28: "CAP_LEASE",
    29: "CAP_AUDIT_WRITE",
    30: "CAP_AUDIT_CONTROL",
    31: "CAP_SETFCAP",
    32: "CAP_MAC_OVERRIDE",
    33: "CAP_MAC_ADMIN",
    34: "CAP_SYSLOG",
    35: "CAP_WAKE_ALARM",
    36: "CAP_BLOCK_SUSPEND",
    37: "CAP_AUDIT_READ",
    38: "CAP_PERFMON",
    39: "CAP_BPF",
    40: "CAP_CHECKPOINT_RESTORE",
}

_g23_CLOUD_ENVIRONMENT_PREFIXES = [
    "AWS_",
    "AZURE_",
    "GOOGLE_CLOUD_",
    "GCP_",
]

_g23_CLOUD_ENVIRONMENT_NAMES = [
    "CLOUD_RUN_JOB",
    "CLOUD_RUN_SERVICE",
    "FUNCTIONS_WORKER_RUNTIME",
    "KUBERNETES_SERVICE_HOST",
    "WEBSITE_SITE_NAME",
]


class G01_T10:
    id = "T10"
    title = "Detect container / VM / cloud runtime markers"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g23_run_shell_runtime_marker_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected sandbox identity runtime markers.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not detect sandbox identity runtime markers.",
                evidence=_g23_failure_evidence(completed, combined_output),
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
                summary="Shell sandbox identity marker detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell sandbox identity marker detection failed.",
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
                _g23_detect_runtime_markers_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected sandbox identity runtime markers.",
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
                summary="Python runtime sandbox identity marker detection failed.",
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
            _g23_run_identity_alternate_attempts,
            _g23_build_runtime_marker_alternate_attempts(self._operating_system),
        )


class G01_T11:
    id = "T11"
    title = "Read Linux cgroup and namespace status"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g23_run_shell_cgroup_namespace_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux cgroup and namespace status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g23_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux cgroup and namespace status is not applicable.",
                    evidence=_g23_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux cgroup and namespace status.",
                evidence=_g23_failure_evidence(completed, combined_output),
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
                summary="Shell cgroup and namespace detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell cgroup and namespace detection failed.",
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
                summary="Linux cgroup and namespace status is not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g23_detect_cgroup_namespace_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read Linux cgroup and namespace status.",
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
                summary="Python runtime cgroup and namespace detection failed.",
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
            _g23_run_identity_alternate_attempts,
            _g23_build_cgroup_namespace_alternate_attempts(self._operating_system),
        )


class G01_T12:
    id = "T12"
    title = "Read Linux confinement status"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g23_run_shell_confinement_status_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux confinement status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g23_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux confinement status is not applicable.",
                    evidence=_g23_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux confinement status.",
                evidence=_g23_failure_evidence(completed, combined_output),
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
                summary="Shell confinement status detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell confinement status detection failed.",
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
                summary="Linux confinement status is not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(_g23_detect_confinement_with_python)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read Linux confinement status.",
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
                summary="Python runtime confinement status detection failed.",
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
            _g23_run_identity_alternate_attempts,
            _g23_build_confinement_status_alternate_attempts(self._operating_system),
        )


class G01_T13:
    id = "T13"
    title = "Detect effective Linux capabilities"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g23_run_shell_linux_capability_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected effective Linux capabilities.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g23_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Effective Linux capabilities are not applicable.",
                    evidence=_g23_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not detect effective Linux capabilities.",
                evidence=_g23_failure_evidence(completed, combined_output),
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
                summary="Shell Linux capability detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Linux capability detection failed.",
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
                summary="Effective Linux capabilities are not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g23_detect_linux_capabilities_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected effective Linux capabilities.",
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
                summary="Python runtime Linux capability detection failed.",
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
            _g23_run_identity_alternate_attempts,
            _g23_build_linux_capability_alternate_attempts(self._operating_system),
        )


class G01_T14:
    id = "T14"
    title = "Detect Windows integrity and containment status"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g23_run_shell_windows_identity_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected Windows integrity and containment status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g23_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary=(
                        "Windows integrity and containment status is not applicable."
                    ),
                    evidence=_g23_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not detect Windows integrity and containment status."
                ),
                evidence=_g23_failure_evidence(completed, combined_output),
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
                summary="Shell Windows identity detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Windows identity detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=("Windows integrity and containment status is not applicable."),
            )

        try:
            evidence = await asyncio.to_thread(
                _g23_detect_windows_identity_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime detected Windows integrity and containment status."
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
                summary="Python runtime Windows identity detection failed.",
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
            _g23_run_identity_alternate_attempts,
            _g23_build_windows_identity_alternate_attempts(self._operating_system),
        )


class G01_T15:
    id = "T15"
    title = "Detect host identity and domain visibility"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g23_run_shell_host_identity_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected host identity and domain visibility.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=("Shell could not detect host identity and domain visibility."),
                evidence=_g23_failure_evidence(completed, combined_output),
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
                summary="Shell host identity detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell host identity detection failed.",
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
                _g23_detect_host_identity_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime detected host identity and domain visibility."
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
                summary="Python runtime host identity detection failed.",
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
            _g23_run_identity_alternate_attempts,
            _g23_build_host_identity_alternate_attempts(self._operating_system),
        )


@dataclass(frozen=True)
class _g23_AlternateIdentityAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _g23_build_runtime_marker_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g23_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _g23_AlternateIdentityAttempt(
                id="A01",
                title="Detect runtime markers via systeminfo",
                bypass_class="runtime_marker_detection",
                command_family="systeminfo",
                command=["systeminfo"],
            ),
            _g23_AlternateIdentityAttempt(
                id="A02",
                title="Detect runtime markers via environment",
                bypass_class="runtime_marker_detection",
                command_family="cmd/set",
                command=[
                    "cmd",
                    "/c",
                    (
                        "set AWS_ & set AZURE_ & set GOOGLE_CLOUD_ & set GCP_ "
                        "& exit /b 0"
                    ),
                ],
            ),
        ]

    return [
        _g23_AlternateIdentityAttempt(
            id="A01",
            title="Detect runtime markers via proc and sysfs",
            bypass_class="runtime_marker_detection",
            command_family="cat/proc/sysfs",
            command=[
                "sh",
                "-c",
                (
                    "for path in /.dockerenv /run/.containerenv "
                    "/proc/1/cgroup /sys/class/dmi/id/product_name "
                    "/sys/class/dmi/id/product_version; do "
                    '[ -r "$path" ] && printf "%s=" "$path" && '
                    'head -n 5 "$path" | tr "\\n" "|"; '
                    "done"
                ),
            ],
        ),
        _g23_AlternateIdentityAttempt(
            id="A02",
            title="Detect virtualization via systemd-detect-virt",
            bypass_class="runtime_marker_detection",
            command_family="systemd-detect-virt",
            command=[
                "sh",
                "-c",
                (
                    "command -v systemd-detect-virt >/dev/null 2>&1 "
                    f"|| exit {_g23_NO_SHELL_CANDIDATE_EXIT_CODE}; "
                    "systemd-detect-virt --vm --container"
                ),
            ],
        ),
    ]


def _g23_build_cgroup_namespace_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g23_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g23_AlternateIdentityAttempt(
            id="A01",
            title="Read cgroup and namespace links via cat and ls",
            bypass_class="cgroup_namespace_read",
            command_family="cat/ls",
            command=[
                "sh",
                "-c",
                ("cat /proc/self/cgroup; ls -l /proc/self/ns"),
            ],
        )
    ]


def _g23_build_confinement_status_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g23_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g23_AlternateIdentityAttempt(
            id="A01",
            title="Read confinement status via proc attributes",
            bypass_class="linux_confinement_status_read",
            command_family="cat/awk",
            command=[
                "sh",
                "-c",
                (
                    "[ -r /proc/self/attr/current ] "
                    "&& printf 'apparmor=' "
                    "&& head -n 1 /proc/self/attr/current; "
                    "[ -r /sys/fs/selinux/enforce ] "
                    "&& printf 'selinux=' "
                    "&& head -n 1 /sys/fs/selinux/enforce; "
                    "awk '/^Seccomp:|^Seccomp_filters:/ {print}' "
                    "/proc/self/status"
                ),
            ],
        )
    ]


def _g23_build_linux_capability_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g23_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g23_AlternateIdentityAttempt(
            id="A01",
            title="Read effective capabilities via proc status",
            bypass_class="linux_capability_detection",
            command_family="awk/proc",
            command=["awk", "/^CapEff:/ {print}", "/proc/self/status"],
        ),
        _g23_AlternateIdentityAttempt(
            id="A02",
            title="Decode effective capabilities via capsh",
            bypass_class="linux_capability_detection",
            command_family="capsh",
            command=[
                "sh",
                "-c",
                (
                    "command -v capsh >/dev/null 2>&1 "
                    f"|| exit {_g23_NO_SHELL_CANDIDATE_EXIT_CODE}; "
                    "cap_eff=$(awk '/^CapEff:/ {print $2}' /proc/self/status); "
                    'capsh --decode="$cap_eff"'
                ),
            ],
        ),
    ]


def _g23_build_windows_identity_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g23_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.LINUX:
        return []

    return [
        _g23_AlternateIdentityAttempt(
            id="A01",
            title="Detect integrity level via whoami groups",
            bypass_class="windows_integrity_detection",
            command_family="whoami",
            command=["whoami", "/groups"],
        ),
        _g23_AlternateIdentityAttempt(
            id="A02",
            title="Detect PowerShell constrained language mode",
            bypass_class="windows_language_mode_detection",
            command_family="powershell",
            command=[
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$ExecutionContext.SessionState.LanguageMode",
            ],
        ),
    ]


def _g23_build_host_identity_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g23_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _g23_AlternateIdentityAttempt(
                id="A01",
                title="Detect host identity via hostname and whoami",
                bypass_class="host_identity_detection",
                command_family="hostname/whoami",
                command=[
                    "cmd",
                    "/c",
                    "hostname & whoami /user & whoami /fqdn & exit /b 0",
                ],
            ),
            _g23_AlternateIdentityAttempt(
                id="A02",
                title="Detect domain visibility via wmic",
                bypass_class="domain_workgroup_visibility",
                command_family="wmic",
                command=[
                    "wmic",
                    "computersystem",
                    "get",
                    "domain,name,partofdomain,workgroup",
                ],
            ),
        ]

    return [
        _g23_AlternateIdentityAttempt(
            id="A01",
            title="Detect host identity via hostname commands",
            bypass_class="host_identity_detection",
            command_family="hostname/uname",
            command=["sh", "-c", "hostname; hostname -f 2>/dev/null; uname -n"],
        ),
        _g23_AlternateIdentityAttempt(
            id="A02",
            title="Detect machine and domain config files",
            bypass_class="machine_domain_config_read",
            command_family="cat/ls",
            command=[
                "sh",
                "-c",
                (
                    "for path in /etc/machine-id /var/lib/dbus/machine-id "
                    "/etc/resolv.conf /etc/krb5.conf /etc/sssd/sssd.conf "
                    "/etc/samba/smb.conf; do "
                    '[ -r "$path" ] && printf "%s:readable;" "$path"; '
                    "done"
                ),
            ],
        ),
    ]


def _g23_run_identity_alternate_attempts(
    attempts: list[_g23_AlternateIdentityAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _g23_run_identity_alternate_attempt(attempt) for attempt in attempts
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


def _g23_run_identity_alternate_attempt(
    attempt: _g23_AlternateIdentityAttempt,
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
        elif completed.returncode == _g23_NO_SHELL_CANDIDATE_EXIT_CODE:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_g23_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g23_identity_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g23_identity_alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _g23_identity_alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _g23_identity_alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _g23_identity_alternate_exception_result(attempt, Outcome.ERROR, error)


def _g23_identity_alternate_exception_result(
    attempt: _g23_AlternateIdentityAttempt,
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


def _g23_run_shell_runtime_marker_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _g23_build_windows_runtime_marker_command()
    else:
        command = _g23_build_linux_runtime_marker_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g23_run_shell_cgroup_namespace_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g23_not_applicable_completed_process(
            "Linux cgroup and namespace status is not applicable."
        )

    return subprocess.run(
        _g23_build_linux_cgroup_namespace_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g23_run_shell_confinement_status_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g23_not_applicable_completed_process(
            "Linux confinement status is not applicable."
        )

    return subprocess.run(
        _g23_build_linux_confinement_status_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g23_run_shell_linux_capability_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g23_not_applicable_completed_process(
            "Effective Linux capabilities are not applicable."
        )

    return subprocess.run(
        _g23_build_linux_capability_detection_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g23_run_shell_windows_identity_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.LINUX:
        return _g23_not_applicable_completed_process(
            "Windows integrity and containment status is not applicable."
        )

    return subprocess.run(
        _g23_build_windows_identity_detection_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g23_run_shell_host_identity_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _g23_build_windows_host_identity_command()
    else:
        command = _g23_build_linux_host_identity_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g23_build_windows_runtime_marker_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$computer = Get-CimInstance Win32_ComputerSystem
$bios = Get-CimInstance Win32_BIOS
$cloudNames = @(
    'AWS_',
    'AZURE_',
    'GOOGLE_CLOUD_',
    'GCP_',
    'CLOUD_RUN_JOB',
    'CLOUD_RUN_SERVICE',
    'FUNCTIONS_WORKER_RUNTIME',
    'KUBERNETES_SERVICE_HOST',
    'WEBSITE_SITE_NAME'
)
$cloudMarkers = @()
foreach ($name in [Environment]::GetEnvironmentVariables().Keys) {
    foreach ($candidate in $cloudNames) {
        if ($name -eq $candidate -or $name.StartsWith($candidate)) {
            $cloudMarkers += $name
        }
    }
}
$parts = @(
    "manufacturer=$($computer.Manufacturer)",
    "model=$($computer.Model)",
    "bios_serial_present=$([bool]$bios.SerialNumber)",
    "cloud_env_count=$($cloudMarkers.Count)",
    "cloud_env=[$($cloudMarkers -join ',')]"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g23_build_windows_host_identity_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$computer = Get-CimInstance Win32_ComputerSystem
$machineGuid = ''
$machineGuidPresent = $false
try {
    $machineGuid = (
        Get-ItemProperty `
            -Path 'HKLM:\\SOFTWARE\\Microsoft\\Cryptography' `
            -Name MachineGuid `
            -ErrorAction Stop
    ).MachineGuid
    $machineGuidPresent = [bool]$machineGuid
}
catch {
    $machineGuidPresent = $false
}
$parts = @(
    "hostname=$env:COMPUTERNAME",
    "dns_hostname=$($computer.DNSHostName)",
    "domain=$($computer.Domain)",
    "workgroup=$($computer.Workgroup)",
    "part_of_domain=$($computer.PartOfDomain)",
    "machine_guid_present=$machineGuidPresent"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g23_build_windows_identity_detection_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$languageMode = $ExecutionContext.SessionState.LanguageMode
$mandatoryLabel = whoami /groups |
    Select-String 'Mandatory Label' |
    Select-Object -First 1
$integrity = ''
if ($null -ne $mandatoryLabel) {
    $integrity = ($mandatoryLabel.Line -replace '^\\s+', '')
}
$source = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

public static class SandboxTesterToken {
    [DllImport("advapi32.dll", SetLastError=true)]
    private static extern bool OpenProcessToken(
        IntPtr ProcessHandle,
        UInt32 DesiredAccess,
        out IntPtr TokenHandle);

    [DllImport("advapi32.dll", SetLastError=true)]
    private static extern bool GetTokenInformation(
        IntPtr TokenHandle,
        int TokenInformationClass,
        out int TokenInformation,
        int TokenInformationLength,
        out int ReturnLength);

    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool CloseHandle(IntPtr handle);

    public static bool IsAppContainer() {
        const UInt32 TOKEN_QUERY = 0x0008;
        const int TokenIsAppContainer = 29;
        IntPtr tokenHandle;
        if (!OpenProcessToken(
            Process.GetCurrentProcess().Handle,
            TOKEN_QUERY,
            out tokenHandle)) {
            throw new System.ComponentModel.Win32Exception();
        }

        try {
            int isAppContainer;
            int returnLength;
            if (!GetTokenInformation(
                tokenHandle,
                TokenIsAppContainer,
                out isAppContainer,
                sizeof(int),
                out returnLength)) {
                throw new System.ComponentModel.Win32Exception();
            }

            return isAppContainer != 0;
        }
        finally {
            CloseHandle(tokenHandle);
        }
    }
}
'@
Add-Type -TypeDefinition $source
$isAppContainer = [SandboxTesterToken]::IsAppContainer()
$parts = @(
    "integrity=$integrity",
    "app_container=$isAppContainer",
    "powershell_language_mode=$languageMode"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g23_build_linux_runtime_marker_command() -> list[str]:
    cloud_pattern = (
        "^(AWS_|AZURE_|GOOGLE_CLOUD_|GCP_|CLOUD_RUN_JOB|"
        "CLOUD_RUN_SERVICE|FUNCTIONS_WORKER_RUNTIME|"
        "KUBERNETES_SERVICE_HOST|WEBSITE_SITE_NAME)"
    )
    printf_format = (
        "container_markers=[%s]; cgroup=%s; product_name=%s; "
        "product_version=%s; virt=%s; cloud_env_count=%s; cloud_env=[%s]\\n"
    )
    script = """
set -u
markers=""
for marker in /.dockerenv /run/.containerenv; do
    if [ -e "$marker" ]; then
        markers="${markers}${marker},"
    fi
done
cgroup=""
if [ -r /proc/1/cgroup ]; then
    cgroup=$(head -n 5 /proc/1/cgroup | tr '\\n' '|' | cut -c 1-200)
fi
product_name=""
if [ -r /sys/class/dmi/id/product_name ]; then
    product_name=$(head -n 1 /sys/class/dmi/id/product_name)
fi
product_version=""
if [ -r /sys/class/dmi/id/product_version ]; then
    product_version=$(head -n 1 /sys/class/dmi/id/product_version)
fi
virt=""
if command -v systemd-detect-virt >/dev/null 2>&1; then
    virt=$(systemd-detect-virt 2>/dev/null || true)
fi
cloud_env=$(env | cut -d= -f1 | grep -E __CLOUD_PATTERN__ | paste -sd, -)
cloud_count=0
if [ -n "$cloud_env" ]; then
    cloud_count=$(printf '%s' "$cloud_env" | tr ',' '\\n' | wc -l)
fi
printf __PRINTF_FORMAT__ \
    "$markers" \
    "$cgroup" \
    "$product_name" \
    "$product_version" \
    "$virt" \
    "$cloud_count" \
    "$cloud_env"
"""
    script = script.replace("__CLOUD_PATTERN__", repr(cloud_pattern))
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _g23_build_linux_host_identity_command() -> list[str]:
    printf_format = (
        "hostname=%s; fqdn=%s; machine_id_present=%s; domain_config_present=[%s]\\n"
    )
    script = """
set -u
hostname_value=$(hostname 2>/dev/null || true)
fqdn_value=$(hostname -f 2>/dev/null || true)
machine_id_present=False
if [ -r /etc/machine-id ] || [ -r /var/lib/dbus/machine-id ]; then
    machine_id_present=True
fi
domain_config=""
for path in /etc/resolv.conf /etc/krb5.conf /etc/sssd/sssd.conf /etc/samba/smb.conf; do
    if [ -r "$path" ]; then
        domain_config="${domain_config}${path},"
    fi
done
printf __PRINTF_FORMAT__ \
    "$hostname_value" \
    "$fqdn_value" \
    "$machine_id_present" \
    "$domain_config"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _g23_build_linux_capability_detection_command() -> list[str]:
    printf_format = (
        "cap_eff=%s; decoded=%s; capsh_available=%s; "
        "cap_sys_admin_present=%s; cap_net_raw_present=%s\\n"
    )
    script = """
set -u
if [ ! -r /proc/self/status ]; then
    exit 1
fi
cap_eff=$(awk '/^CapEff:/ {print $2}' /proc/self/status)
decoded=""
capsh_available=False
cap_sys_admin_present=unknown
cap_net_raw_present=unknown
if command -v capsh >/dev/null 2>&1; then
    capsh_available=True
    decoded=$(capsh --decode="$cap_eff" 2>/dev/null || true)
    case "$decoded" in
        *cap_sys_admin*) cap_sys_admin_present=True ;;
        *) cap_sys_admin_present=False ;;
    esac
    case "$decoded" in
        *cap_net_raw*) cap_net_raw_present=True ;;
        *) cap_net_raw_present=False ;;
    esac
fi
printf __PRINTF_FORMAT__ \
    "$cap_eff" \
    "$decoded" \
    "$capsh_available" \
    "$cap_sys_admin_present" \
    "$cap_net_raw_present"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _g23_build_linux_cgroup_namespace_command() -> list[str]:
    printf_format = "cgroup=%s; namespaces=[%s]\\n"
    script = """
set -u
cgroup=""
if [ -r /proc/self/cgroup ]; then
    cgroup=$(head -n 10 /proc/self/cgroup | tr '\\n' '|' | cut -c 1-300)
fi
namespaces=""
if [ -d /proc/self/ns ]; then
    for namespace in /proc/self/ns/*; do
        name=$(basename "$namespace")
        target=$(readlink "$namespace" 2>/dev/null || true)
        namespaces="${namespaces}${name}:${target},"
    done
fi
printf __PRINTF_FORMAT__ "$cgroup" "$namespaces"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _g23_build_linux_confinement_status_command() -> list[str]:
    printf_format = (
        "apparmor=%s; selinux_enforce=%s; seccomp=%s; "
        "seccomp_filters=%s; jail=not_applicable\\n"
    )
    script = """
set -u
apparmor=""
if [ -r /proc/self/attr/current ]; then
    apparmor=$(head -n 1 /proc/self/attr/current)
fi
selinux_enforce=""
if [ -r /sys/fs/selinux/enforce ]; then
    selinux_enforce=$(head -n 1 /sys/fs/selinux/enforce)
fi
seccomp=""
seccomp_filters=""
if [ -r /proc/self/status ]; then
    seccomp=$(awk '/^Seccomp:/ {print $2}' /proc/self/status)
    seccomp_filters=$(awk '/^Seccomp_filters:/ {print $2}' /proc/self/status)
fi
printf __PRINTF_FORMAT__ \
    "$apparmor" \
    "$selinux_enforce" \
    "$seccomp" \
    "$seccomp_filters"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _g23_detect_runtime_markers_with_python(
    operating_system: OperatingSystem,
) -> str:
    cloud_environment_names = _g23_detect_cloud_environment_names()

    if operating_system == OperatingSystem.WINDOWS:
        return _g23_detect_windows_runtime_markers(cloud_environment_names)

    return _g23_detect_linux_runtime_markers(cloud_environment_names)


def _g23_detect_windows_runtime_markers(cloud_environment_names: list[str]) -> str:
    computer_name = os.environ.get("COMPUTERNAME", "")
    processor_identifier = os.environ.get("PROCESSOR_IDENTIFIER", "")

    return (
        f"computer_name_present={bool(computer_name)}; "
        f"processor_identifier_present={bool(processor_identifier)}; "
        f"cloud_env_count={len(cloud_environment_names)}; "
        f"cloud_env=[{','.join(cloud_environment_names)}]"
    )


def _g23_detect_linux_runtime_markers(cloud_environment_names: list[str]) -> str:
    container_markers = [
        str(path) for path in _g23_LINUX_CONTAINER_MARKERS if path.exists()
    ]
    cgroup_sample = _g23_read_text_sample(_g23_LINUX_CGROUP_PATH)
    product_name = _g23_read_text_sample(_g23_LINUX_PRODUCT_NAME_PATH)
    product_version = _g23_read_text_sample(_g23_LINUX_PRODUCT_VERSION_PATH)

    return (
        f"container_markers=[{','.join(container_markers)}]; "
        f"cgroup={cgroup_sample}; "
        f"product_name={product_name}; "
        f"product_version={product_version}; "
        f"cloud_env_count={len(cloud_environment_names)}; "
        f"cloud_env=[{','.join(cloud_environment_names)}]"
    )


def _g23_detect_cgroup_namespace_with_python() -> str:
    cgroup_sample = _g23_read_text_sample(_g23_LINUX_SELF_CGROUP_PATH)
    namespaces = _g23_read_linux_namespaces()
    namespace_evidence = ",".join(
        f"{name}:{target}" for name, target in namespaces.items()
    )

    return f"cgroup={cgroup_sample}; namespaces=[{namespace_evidence}]"


def _g23_detect_confinement_with_python() -> str:
    apparmor = _g23_read_text_sample(_g23_LINUX_APPARMOR_CURRENT_PATH).strip()
    selinux_enforce = _g23_read_text_sample(_g23_LINUX_SELINUX_ENFORCE_PATH).strip()
    status_values = _g23_read_linux_status_values(
        ["Seccomp", "Seccomp_filters"],
    )
    seccomp = status_values.get("Seccomp", "")
    seccomp_filters = status_values.get("Seccomp_filters", "")

    return (
        f"apparmor={apparmor}; "
        f"selinux_enforce={selinux_enforce}; "
        f"seccomp={seccomp}; "
        f"seccomp_filters={seccomp_filters}; "
        "jail=not_applicable"
    )


def _g23_detect_linux_capabilities_with_python() -> str:
    status_values = _g23_read_linux_status_values(["CapEff"])
    cap_eff = status_values.get("CapEff", "")

    if cap_eff == "":
        raise RuntimeError("Could not read CapEff from /proc/self/status.")

    capability_names = _g23_decode_linux_capabilities(cap_eff)
    capability_set = set(capability_names)

    return (
        f"cap_eff={cap_eff}; "
        f"capability_count={len(capability_names)}; "
        f"cap_sys_admin_present={'CAP_SYS_ADMIN' in capability_set}; "
        f"cap_net_raw_present={'CAP_NET_RAW' in capability_set}; "
        f"capabilities=[{','.join(capability_names)}]"
    )


def _g23_detect_windows_identity_with_python() -> str:
    token = _g23_open_current_process_token()

    try:
        integrity_rid = _g23_read_windows_integrity_rid(token)
        integrity_level = _g23_map_windows_integrity_level(integrity_rid)
        app_container = _g23_read_windows_app_container_status(token)
    finally:
        _g23_close_windows_handle(token)

    return (
        f"integrity={integrity_level}; "
        f"integrity_rid={integrity_rid}; "
        f"app_container={app_container}; "
        "powershell_language_mode=not_applicable_to_python"
    )


def _g23_open_current_process_token() -> int:
    import ctypes

    token_query = 0x0008
    token = ctypes.c_void_p()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    advapi32.OpenProcessToken.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.OpenProcessToken.restype = ctypes.c_bool
    process_handle = kernel32.GetCurrentProcess()
    opened = advapi32.OpenProcessToken(
        process_handle,
        token_query,
        ctypes.byref(token),
    )

    if not opened:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "OpenProcessToken failed")

    if token.value is None:
        raise OSError("OpenProcessToken returned an empty token handle.")

    return int(token.value)


def _g23_read_windows_integrity_rid(token: int) -> int:
    import ctypes

    token_integrity_level = 25
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi32.GetTokenInformation.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    advapi32.GetTokenInformation.restype = ctypes.c_bool
    return_length = ctypes.c_uint32()
    advapi32.GetTokenInformation(
        ctypes.c_void_p(token),
        token_integrity_level,
        None,
        0,
        ctypes.byref(return_length),
    )
    buffer = ctypes.create_string_buffer(return_length.value)
    succeeded = advapi32.GetTokenInformation(
        ctypes.c_void_p(token),
        token_integrity_level,
        buffer,
        return_length,
        ctypes.byref(return_length),
    )

    if not succeeded:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GetTokenInformation(TokenIntegrityLevel) failed")

    class _SidAndAttributes(ctypes.Structure):
        _fields_ = [
            ("sid", ctypes.c_void_p),
            ("attributes", ctypes.c_uint32),
        ]

    class _TokenMandatoryLabel(ctypes.Structure):
        _fields_ = [("label", _SidAndAttributes)]

    token_label = ctypes.cast(
        buffer,
        ctypes.POINTER(_TokenMandatoryLabel),
    ).contents
    sid = token_label.label.sid
    advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
    advapi32.GetSidSubAuthority.restype = ctypes.POINTER(ctypes.c_uint32)
    advapi32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    sub_authority_count = advapi32.GetSidSubAuthorityCount(sid).contents.value
    integrity_rid = advapi32.GetSidSubAuthority(
        sid,
        sub_authority_count - 1,
    ).contents.value

    return int(integrity_rid)


def _g23_read_windows_app_container_status(token: int) -> bool:
    import ctypes

    token_is_app_container = 29
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi32.GetTokenInformation.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    advapi32.GetTokenInformation.restype = ctypes.c_bool
    is_app_container = ctypes.c_uint32()
    return_length = ctypes.c_uint32()
    succeeded = advapi32.GetTokenInformation(
        ctypes.c_void_p(token),
        token_is_app_container,
        ctypes.byref(is_app_container),
        ctypes.sizeof(is_app_container),
        ctypes.byref(return_length),
    )

    if not succeeded:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GetTokenInformation(TokenIsAppContainer) failed")

    return is_app_container.value != 0


def _g23_close_windows_handle(handle: int) -> None:
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool
    kernel32.CloseHandle(ctypes.c_void_p(handle))


def _g23_map_windows_integrity_level(integrity_rid: int) -> str:
    if integrity_rid >= 0x5000:
        return "protected"
    if integrity_rid >= 0x4000:
        return "system"
    if integrity_rid >= 0x3000:
        return "high"
    if integrity_rid >= 0x2000:
        return "medium"
    if integrity_rid >= 0x1000:
        return "low"

    return "untrusted"


def _g23_detect_host_identity_with_python(
    operating_system: OperatingSystem,
) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _g23_detect_windows_host_identity_with_python()

    return _g23_detect_linux_host_identity_with_python()


def _g23_detect_windows_host_identity_with_python() -> str:
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    computer_name = os.environ.get("COMPUTERNAME", "")
    user_domain = os.environ.get("USERDOMAIN", "")
    logon_server_present = bool(os.environ.get("LOGONSERVER", ""))
    machine_guid_present = _g23_windows_machine_guid_is_readable()

    return (
        f"hostname={hostname}; "
        f"fqdn={fqdn}; "
        f"computer_name={computer_name}; "
        f"user_domain={user_domain}; "
        f"logon_server_present={logon_server_present}; "
        f"machine_guid_present={machine_guid_present}"
    )


def _g23_detect_linux_host_identity_with_python() -> str:
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    node = platform.uname().node
    machine_id_present = any(path.exists() for path in _g23_LINUX_MACHINE_ID_PATHS)
    readable_machine_id = any(
        path.is_file() and os.access(path, os.R_OK)
        for path in _g23_LINUX_MACHINE_ID_PATHS
    )
    readable_domain_config = [
        str(path)
        for path in _g23_LINUX_DOMAIN_PATHS
        if path.is_file() and os.access(path, os.R_OK)
    ]

    return (
        f"hostname={hostname}; "
        f"fqdn={fqdn}; "
        f"node={node}; "
        f"machine_id_present={machine_id_present}; "
        f"machine_id_readable={readable_machine_id}; "
        f"domain_config_present=[{','.join(readable_domain_config)}]"
    )


def _g23_windows_machine_guid_is_readable() -> bool:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            machine_guid, _value_type = winreg.QueryValueEx(key, "MachineGuid")

        return bool(machine_guid)
    except OSError:
        return False


def _g23_decode_linux_capabilities(capability_hex: str) -> list[str]:
    capability_value = int(capability_hex, 16)
    capability_names: list[str] = []

    for bit, name in _g23_LINUX_CAPABILITY_NAMES.items():
        if capability_value & (1 << bit):
            capability_names.append(name)

    return capability_names


def _g23_read_linux_namespaces() -> dict[str, str]:
    namespaces: dict[str, str] = {}

    if not _g23_LINUX_SELF_NAMESPACE_DIRECTORY.exists():
        return namespaces

    for path in sorted(_g23_LINUX_SELF_NAMESPACE_DIRECTORY.iterdir()):
        namespaces[path.name] = os.readlink(path)

    return namespaces


def _g23_read_linux_status_values(keys: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}

    if not _g23_LINUX_SELF_STATUS_PATH.exists():
        return values

    with _g23_LINUX_SELF_STATUS_PATH.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        for line in file:
            name, separator, value = line.partition(":")

            if separator and name in keys:
                values[name] = value.strip()

    return values


def _g23_detect_cloud_environment_names() -> list[str]:
    names: list[str] = []

    for name in os.environ:
        if name in _g23_CLOUD_ENVIRONMENT_NAMES:
            names.append(name)
            continue

        if any(name.startswith(prefix) for prefix in _g23_CLOUD_ENVIRONMENT_PREFIXES):
            names.append(name)

    return sorted(names)


def _g23_read_text_sample(path: Path) -> str:
    if not path.exists():
        return ""

    with path.open("r", encoding="utf-8", errors="replace") as file:
        return file.read(200).replace("\n", "|")


def _g23_not_applicable_completed_process(
    message: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=_g23_NO_SHELL_CANDIDATE_EXIT_CODE,
        stdout="",
        stderr=message,
    )


def _g23_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


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


class G01_T16:
    id = "T16"
    title = "Read Linux process namespace links"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g24_run_shell_process_namespace_link_read,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux process namespace links.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g24_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux process namespace links are not applicable.",
                    evidence=_g24_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux process namespace links.",
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
                summary="Shell process namespace link read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell process namespace link read failed.",
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
                summary="Linux process namespace links are not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g24_read_process_namespace_links_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read Linux process namespace links.",
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
                summary="Python runtime process namespace link read failed.",
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
            _g24_build_process_namespace_alternate_attempts(self._operating_system),
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
    sample=$(ls -A "$path" 2>/dev/null | head -n 5 | paste -sd, -)
    status=$?
    if [ "$status" -eq 0 ]; then
        evidence="${{evidence}}$path:readable:sample=[$sample];"
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
sample=$(awk '{
    separator = 0
    for (i = 1; i <= NF; i++) {
        if ($i == "-") {
            separator = i
            break
        }
    }
    if (separator > 0) {
        print $5 ":" $(separator + 1) ":" $(separator + 2) ":" $6
    }
}' /proc/self/mountinfo | head -n 8 | paste -sd, -)
printf 'mount_count=%s; rw_option_count=%s; bind_like_count=%s; sample=[%s]\\n' \
    "$mount_count" \
    "$rw_count" \
    "$bind_like_count" \
    "$sample"
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
            evidence="${{evidence}}$root:file:size=$size;"
        else
            denied=$((denied + 1))
            evidence="${{evidence}}$root:file:denied;"
        fi
        continue
    fi
    if [ -d "$root" ]; then
        while IFS= read -r file; do
            [ -n "$file" ] || continue
            size=$(wc -c < "$file" 2>/dev/null || true)
            if [ -n "$size" ]; then
                readable=$((readable + 1))
                evidence="${{evidence}}$file:file:size=$size;"
            else
                denied=$((denied + 1))
                evidence="${{evidence}}$file:file:denied;"
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
            sample = [child.name for child in list(path.iterdir())[:5]]
            entries.append(f"{path}:readable:sample=[{','.join(sample)}]")
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
            size = path.stat().st_size
            readable_count += 1
            entries.append(f"{path}:file:size={size}")
        except PermissionError:
            denied_count += 1
            entries.append(f"{path}:file:denied")

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

    sample_mounts = bind_like_mounts[:8]

    if not sample_mounts:
        sample_mounts = mounts[:8]

    sample = ",".join(
        (
            f"{mount['mount_point']}:{mount['filesystem_type']}:"
            f"{mount['mount_source']}:{mount['options']}"
        )
        for mount in sample_mounts
    )

    return (
        f"mount_count={len(mounts)}; "
        f"rw_option_count={rw_option_count}; "
        f"writable_mountpoint_count={writable_mountpoint_count}; "
        f"bind_like_count={len(bind_like_mounts)}; "
        f"sample=[{sample}]"
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
        id="G01",
        title="Runtime identity and execution context",
        tests=[
            G01_T01(capability_context),
            G01_T02(capability_context),
            G01_T03(capability_context),
            G01_T04(capability_context),
            G01_T05(capability_context),
            G01_T06(capability_context),
            G01_T07(capability_context),
            G01_T08(capability_context),
            G01_T09(capability_context),
            G01_T10(capability_context),
            G01_T11(capability_context),
            G01_T12(capability_context),
            G01_T13(capability_context),
            G01_T14(capability_context),
            G01_T15(capability_context),
            G01_T16(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateRuntimeAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]
    evidence_builder: Callable[[subprocess.CompletedProcess[str], str], str] | None = (
        None
    )


def _build_working_directory_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Identify working directory via cmd environment",
                bypass_class="alternate_command",
                command_family="cmd/environment",
                command=["cmd", "/c", "echo %CD%"],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Identify working directory via PowerShell",
                bypass_class="alternate_command",
                command_family="powershell",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "(Get-Location).Path",
                ],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Identify working directory via physical pwd",
            bypass_class="alternate_command",
            command_family="pwd",
            command=["pwd", "-P"],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Identify working directory via shell PWD",
            bypass_class="alternate_command",
            command_family="sh/environment",
            command=["sh", "-c", "printf '%s\\n' \"$PWD\""],
        ),
    ]


def _build_current_user_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Identify current user via environment",
                bypass_class="alternate_command",
                command_family="cmd/environment",
                command=["cmd", "/c", "echo %USERDOMAIN%\\%USERNAME%"],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Identify current user SID via whoami",
                bypass_class="alternate_command",
                command_family="whoami",
                command=["whoami", "/user"],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Identify current user via whoami",
            bypass_class="alternate_command",
            command_family="whoami",
            command=["whoami"],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Identify current user via id",
            bypass_class="alternate_command",
            command_family="id",
            command=["id"],
        ),
    ]


def _build_process_id_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Identify process ID via PowerShell .NET",
                bypass_class="alternate_command",
                command_family="powershell/dotnet",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "[System.Diagnostics.Process]::GetCurrentProcess().Id",
                ],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Identify process details via WMIC",
                bypass_class="alternate_command",
                command_family="wmic",
                command=[
                    "wmic",
                    "process",
                    "where",
                    "name='cmd.exe'",
                    "get",
                    "ProcessId",
                ],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Identify process ID via ps",
            bypass_class="alternate_command",
            command_family="ps",
            command=["sh", "-c", "ps -o pid= -p $$"],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Identify process ID via proc self",
            bypass_class="alternate_command",
            command_family="procfs",
            command=["sh", "-c", "readlink /proc/self"],
        ),
    ]


def _build_operating_system_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Identify operating system via systeminfo",
                bypass_class="alternate_command",
                command_family="systeminfo",
                command=["systeminfo"],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Identify operating system via WMIC",
                bypass_class="alternate_command",
                command_family="wmic",
                command=["wmic", "os", "get", "Caption,Version"],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Identify operating system via os-release",
            bypass_class="alternate_command",
            command_family="cat/os-release",
            command=["sh", "-c", "cat /etc/os-release"],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Identify operating system via hostnamectl",
            bypass_class="alternate_command",
            command_family="hostnamectl",
            command=["hostnamectl"],
        ),
    ]


def _build_cpu_architecture_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Identify CPU architecture via environment",
                bypass_class="alternate_command",
                command_family="cmd/environment",
                command=["cmd", "/c", "echo %PROCESSOR_ARCHITECTURE%"],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Identify CPU architecture via WMIC",
                bypass_class="alternate_command",
                command_family="wmic",
                command=["wmic", "os", "get", "OSArchitecture"],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Identify CPU architecture via arch",
            bypass_class="alternate_command",
            command_family="arch",
            command=["arch"],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Identify CPU word size via getconf",
            bypass_class="alternate_command",
            command_family="getconf",
            command=["getconf", "LONG_BIT"],
        ),
    ]


def _build_hostname_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Identify hostname via environment",
                bypass_class="alternate_command",
                command_family="cmd/environment",
                command=["cmd", "/c", "echo %COMPUTERNAME%"],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Identify hostname via WMIC",
                bypass_class="alternate_command",
                command_family="wmic",
                command=["wmic", "computersystem", "get", "Name"],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Identify hostname via uname",
            bypass_class="alternate_command",
            command_family="uname",
            command=["uname", "-n"],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Identify hostname via hostname file",
            bypass_class="alternate_command",
            command_family="cat/hostname",
            command=["sh", "-c", "cat /etc/hostname"],
        ),
    ]


def _build_container_vm_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Identify VM indicators via systeminfo",
                bypass_class="alternate_command",
                command_family="systeminfo",
                command=["systeminfo"],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Identify container indicators via environment",
                bypass_class="alternate_command",
                command_family="cmd/environment",
                command=[
                    "cmd",
                    "/c",
                    (
                        "set container & set KUBERNETES_SERVICE_HOST "
                        "& set WSL_INTEROP & exit /b 0"
                    ),
                ],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Identify container indicators via marker files",
            bypass_class="alternate_command",
            command_family="test/cat",
            command=[
                "sh",
                "-c",
                (
                    "for path in /.dockerenv /run/.containerenv "
                    "/proc/1/cgroup; do "
                    '[ -e "$path" ] && printf "%s;" "$path"; '
                    "done"
                ),
            ],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Identify VM indicators via systemd-detect-virt",
            bypass_class="alternate_command",
            command_family="systemd-detect-virt",
            command=[
                "sh",
                "-c",
                (
                    "command -v systemd-detect-virt >/dev/null 2>&1 "
                    "|| exit 127; systemd-detect-virt --vm --container"
                ),
            ],
        ),
    ]


def _build_command_line_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Read command line via cmd variable",
                bypass_class="alternate_command",
                command_family="cmd/environment",
                command=["cmd", "/c", "echo %CMDCMDLINE%"],
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Read command line via WMIC",
                bypass_class="alternate_command",
                command_family="wmic",
                command=[
                    "wmic",
                    "process",
                    "where",
                    "name='cmd.exe'",
                    "get",
                    "CommandLine",
                ],
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Read command line via ps",
            bypass_class="alternate_command",
            command_family="ps",
            command=["sh", "-c", "ps -o args= -p $$"],
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Read command line via proc cmdline",
            bypass_class="alternate_command",
            command=["sh", "-c", "tr '\\0' ' ' < /proc/$$/cmdline"],
            command_family="procfs",
        ),
    ]


def _build_environment_summary_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateRuntimeAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateRuntimeAttempt(
                id="A01",
                title="Read environment via cmd set",
                bypass_class="alternate_command",
                command_family="cmd/set",
                command=["cmd", "/c", "set"],
                evidence_builder=_environment_names_evidence,
            ),
            _AlternateRuntimeAttempt(
                id="A02",
                title="Read environment via PowerShell provider",
                bypass_class="alternate_command",
                command_family="powershell/env",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "Get-ChildItem Env:",
                ],
                evidence_builder=_environment_names_evidence,
            ),
        ]

    return [
        _AlternateRuntimeAttempt(
            id="A01",
            title="Read environment via printenv",
            bypass_class="alternate_command",
            command_family="printenv",
            command=["printenv"],
            evidence_builder=_environment_names_evidence,
        ),
        _AlternateRuntimeAttempt(
            id="A02",
            title="Read environment via proc environ",
            bypass_class="alternate_command",
            command_family="procfs",
            command=["sh", "-c", "tr '\\0' '\\n' < /proc/self/environ"],
            evidence_builder=_environment_names_evidence,
        ),
    ]


def _run_runtime_alternate_attempts(
    attempts: list[_AlternateRuntimeAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_runtime_alternate_attempt(attempt) for attempt in attempts]
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


def _run_runtime_alternate_attempt(
    attempt: _AlternateRuntimeAttempt,
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
            evidence=_alternate_evidence(attempt, completed, combined_output),
        )
    except FileNotFoundError as error:
        return _runtime_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _runtime_alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _runtime_alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _runtime_alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _runtime_alternate_exception_result(attempt, Outcome.ERROR, error)


def _runtime_alternate_exception_result(
    attempt: _AlternateRuntimeAttempt,
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


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def _alternate_evidence(
    attempt: _AlternateRuntimeAttempt,
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if attempt.evidence_builder is not None:
        return attempt.evidence_builder(completed, combined_output)

    return _failure_evidence(completed, combined_output)


def _environment_names_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if completed.returncode != 0:
        return _failure_evidence(completed, combined_output)

    names = sorted(_extract_environment_names(completed.stdout))
    displayed_names = ", ".join(names[:20])
    return f"count={len(names)}; names={displayed_names}"[:500]


def _extract_environment_names(output: str) -> list[str]:
    names: list[str] = []

    for line in output.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if "=" in stripped_line:
            name = stripped_line.split("=", 1)[0].strip()
        else:
            parts = stripped_line.split()
            name = parts[0] if parts else ""

        if name and name not in {"Name", "----"}:
            names.append(name)

    return names
