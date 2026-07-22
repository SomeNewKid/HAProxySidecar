"""Group 19: System configuration and administration."""

from __future__ import annotations

import asyncio
import os
import platform
import socket
import subprocess
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

_NO_SHELL_CANDIDATE_EXIT_CODE = 127
_LINUX_DPKG_STATUS_PATH = Path("/var/lib/dpkg/status")
_RUNTIME_ENVIRONMENT_VARIABLE = "SANDBOX_TESTER_RUNTIME_PROBE"
_RUNTIME_ENVIRONMENT_VALUE = "sandbox-tester-value"
_USER_SETTING_NAME = "SandboxTesterUserSettingProbe"
_USER_SETTING_VALUE = "sandbox-tester-user-value"
_USER_SETTING_DIRECTORY_NAME = "sandbox-tester"
_USER_SETTING_FILE_NAME = "user-setting-probe.conf"
_SYSTEM_SETTING_NAME = "SandboxTesterSystemSettingProbe"
_SYSTEM_SETTING_VALUE = "sandbox-tester-system-value"
_SYSTEM_SETTING_DIRECTORY = Path("/etc/sandbox-tester")
_SYSTEM_SETTING_FILE = _SYSTEM_SETTING_DIRECTORY / "system-setting-probe.conf"
_SYSTEM_SERVICE_PREFIX = "SandboxTesterProbe"
_LINUX_SYSTEMD_SYSTEM_DIRECTORY = Path("/etc/systemd/system")
_STARTUP_ITEM_NAME = "SandboxTesterStartupProbe"
_STARTUP_ITEM_VALUE = "cmd.exe /c exit 0"
_LINUX_AUTOSTART_DIRECTORY_NAME = "autostart"
_LINUX_AUTOSTART_FILE_NAME = "sandbox-tester-startup-probe.desktop"
_LINUX_AUTOSTART_FILE_CONTENT = (
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=Sandbox Tester Startup Probe\n"
    "Exec=/bin/true\n"
    "X-GNOME-Autostart-enabled=false\n"
)
_SCHEDULED_TASK_FOLDER = "SandboxTester"
_SCHEDULED_TASK_PREFIX = "Probe"
_CRONTAB_MARKER_PREFIX = "# SandboxTesterProbe"
_FIREWALL_RULE_PREFIX = "SandboxTesterFirewallProbe"
_FIREWALL_RULE_PORT = 65000


class G19_T01:
    id = "T01"
    title = "Read system configuration summary"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read a system configuration summary.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read a system configuration summary.",
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
                summary="Shell system configuration query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system configuration query failed.",
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
            evidence = await asyncio.to_thread(_read_system_configuration_summary)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read a system configuration summary.",
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
                summary="Python runtime system configuration query failed.",
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
            _run_system_alternate_attempts,
            _build_system_summary_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_system_summary_command()
        else:
            command = _build_linux_system_summary_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )


class G19_T02:
    id = "T02"
    title = "Read installed software list"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read an installed software list.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary=(
                        "No supported shell software listing command was available."
                    ),
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read an installed software list.",
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
                summary="Shell installed software query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell installed software query failed.",
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
                _read_installed_software_list,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read an installed software list.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported installed software data source was available.",
                evidence=repr(error),
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
                summary="Python runtime installed software query failed.",
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
            _run_system_alternate_attempts,
            _build_installed_software_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_installed_software_command()
        else:
            command = _build_linux_installed_software_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=30,
            check=False,
        )


class G19_T03:
    id = "T03"
    title = "Read network configuration"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read network configuration.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary=(
                        "No supported shell network configuration command was "
                        "available."
                    ),
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read network configuration.",
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
                summary="Shell network configuration query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell network configuration query failed.",
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
            evidence = await asyncio.to_thread(_read_network_configuration)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read network configuration.",
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
                summary="Python runtime network configuration query failed.",
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
            _run_system_alternate_attempts,
            _build_network_configuration_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_network_configuration_command()
        else:
            command = _build_linux_network_configuration_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )


class G19_T04:
    id = "T04"
    title = "Read host firewall status"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read host firewall status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary=(
                        "No supported shell host firewall status command was available."
                    ),
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read host firewall status.",
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
                summary="Shell host firewall status query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell host firewall status query failed.",
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
            completed = await asyncio.to_thread(
                _run_tool_firewall_status_command,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime read host firewall status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported host firewall status command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not read host firewall status.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Python runtime host firewall status query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime host firewall status query failed.",
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
            _run_system_alternate_attempts,
            _build_firewall_status_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_firewall_status_command()
        else:
            command = _build_linux_firewall_status_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )


class G19_T05:
    id = "T05"
    title = "Change runtime environment configuration"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed runtime environment configuration.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not change runtime environment configuration.",
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
                summary="Shell runtime environment mutation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell runtime environment mutation failed.",
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
            evidence = await asyncio.to_thread(_change_runtime_environment)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime changed runtime environment configuration.",
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
                summary="Python runtime environment mutation failed.",
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
            _run_system_alternate_attempts,
            _build_runtime_environment_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_runtime_environment_command()
        else:
            command = _build_linux_runtime_environment_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )


class G19_T06:
    id = "T06"
    title = "Change user-level settings"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed a user-level setting.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not change a user-level setting.",
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
                summary="Shell user-level setting mutation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell user-level setting mutation failed.",
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
                _change_user_level_setting,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime changed a user-level setting.",
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
                summary="Python runtime user-level setting mutation failed.",
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
            _run_system_alternate_attempts,
            _build_user_setting_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_user_setting_command()
        else:
            command = _build_linux_user_setting_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )


class G19_T07:
    id = "T07"
    title = "Change system-level settings"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed a system-level setting.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not change a system-level setting.",
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
                summary="Shell system-level setting mutation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system-level setting mutation failed.",
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
                _change_system_level_setting,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime changed a system-level setting.",
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
                summary="Python runtime system-level setting mutation failed.",
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
            _run_system_alternate_attempts,
            _build_system_setting_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_system_setting_command()
        else:
            command = _build_linux_system_setting_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )


class G19_T08:
    id = "T08"
    title = "Install system service"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell installed a system service.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported system service manager was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not install a system service.",
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
                summary="Shell system service installation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system service installation failed.",
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
            completed = await asyncio.to_thread(
                _run_tool_install_system_service,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime installed a system service.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported system service manager was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not install a system service.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Python runtime system service installation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime system service installation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        service_name = _build_system_service_name()
        return await asyncio.to_thread(
            _run_system_alternate_attempts,
            _build_system_service_alternate_attempts(
                self._operating_system,
                service_name,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        service_name = _build_system_service_name()
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_install_system_service_command(service_name)
        else:
            command = _build_linux_install_system_service_command(service_name)

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )


class G19_T09:
    id = "T09"
    title = "Modify startup item"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell modified a startup item.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not modify a startup item.",
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
                summary="Shell startup item mutation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell startup item mutation failed.",
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
                _modify_startup_item,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime modified a startup item.",
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
                summary="Python runtime startup item mutation failed.",
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
            _run_system_alternate_attempts,
            _build_startup_item_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_startup_item_command()
        else:
            command = _build_linux_startup_item_command()

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )


class G19_T10:
    id = "T10"
    title = "Change firewall rule"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed a firewall rule.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported firewall rule command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not change a firewall rule.",
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
                summary="Shell firewall rule mutation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell firewall rule mutation failed.",
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
            completed = await asyncio.to_thread(
                _run_tool_change_firewall_rule,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime changed a firewall rule.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported firewall rule command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not change a firewall rule.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Python runtime firewall rule mutation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime firewall rule mutation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        rule_name = _build_firewall_rule_name()
        return await asyncio.to_thread(
            _run_system_alternate_attempts,
            _build_firewall_rule_alternate_attempts(
                self._operating_system,
                rule_name,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        rule_name = _build_firewall_rule_name()
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_firewall_rule_command(rule_name)
        else:
            command = _build_linux_firewall_rule_command(rule_name)

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )


class G19_T11:
    id = "T11"
    title = "Create scheduled task"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a scheduled task.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported scheduled task command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create a scheduled task.",
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
                summary="Shell scheduled task creation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell scheduled task creation failed.",
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
            completed = await asyncio.to_thread(
                _run_tool_create_scheduled_task,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime created a scheduled task.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported scheduled task command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not create a scheduled task.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Python runtime scheduled task creation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime scheduled task creation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        task_name = _build_scheduled_task_name()
        return await asyncio.to_thread(
            _run_system_alternate_attempts,
            _build_scheduled_task_alternate_attempts(
                self._operating_system,
                task_name,
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        task_name = _build_scheduled_task_name()
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_scheduled_task_command(task_name)
        else:
            command = _build_linux_scheduled_task_command(task_name)

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G19",
        title="System configuration and administration",
        tests=[
            G19_T01(capability_context),
            G19_T02(capability_context),
            G19_T03(capability_context),
            G19_T04(capability_context),
            G19_T05(capability_context),
            G19_T06(capability_context),
            G19_T07(capability_context),
            G19_T08(capability_context),
            G19_T09(capability_context),
            G19_T10(capability_context),
            G19_T11(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateSystemAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_system_summary_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Read system summary via systeminfo",
                bypass_class="system_configuration_read",
                command_family="systeminfo",
                command=["systeminfo"],
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Read system summary via hostnamectl",
            bypass_class="system_configuration_read",
            command_family="hostnamectl",
            command=["hostnamectl"],
        ),
        _AlternateSystemAttempt(
            id="A02",
            title="Read system summary via uname",
            bypass_class="system_configuration_read",
            command_family="uname",
            command=["uname", "-a"],
        ),
    ]


def _build_installed_software_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Read installed software via winget",
                bypass_class="installed_software_inventory",
                command_family="winget",
                command=["winget", "list", "--disable-interactivity"],
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Read installed software via apt list",
            bypass_class="installed_software_inventory",
            command_family="apt",
            command=[
                "sh",
                "-c",
                (
                    "command -v apt >/dev/null 2>&1 "
                    f"|| exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
                    "output=$(apt list --installed 2>/dev/null); "
                    "status=$?; "
                    'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
                    'printf "%s\\n" "$output" | head -n 25'
                ),
            ],
        )
    ]


def _build_network_configuration_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Read network configuration via netsh",
                bypass_class="network_configuration_read",
                command_family="netsh",
                command=["netsh", "interface", "ip", "show", "config"],
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Read network configuration via route and resolv.conf",
            bypass_class="network_configuration_read",
            command_family="route/resolv.conf",
            command=["sh", "-c", "ip route show; grep '^nameserver' /etc/resolv.conf"],
        )
    ]


def _build_firewall_status_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Read firewall status via netsh",
                bypass_class="host_firewall_status_read",
                command_family="netsh",
                command=["netsh", "advfirewall", "show", "allprofiles", "state"],
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Read firewall status via iptables",
            bypass_class="host_firewall_status_read",
            command_family="iptables",
            command=["iptables", "-S"],
        ),
        _AlternateSystemAttempt(
            id="A02",
            title="Read firewall status via nft",
            bypass_class="host_firewall_status_read",
            command_family="nft",
            command=["nft", "list", "ruleset"],
        ),
    ]


def _build_runtime_environment_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        command = (
            f"set {_RUNTIME_ENVIRONMENT_VARIABLE}={_RUNTIME_ENVIRONMENT_VALUE} "
            f'&& if "!{_RUNTIME_ENVIRONMENT_VARIABLE}!"'
            f'=="{_RUNTIME_ENVIRONMENT_VALUE}" '
            "echo variable_set=True"
        )
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Change runtime environment via cmd set",
                bypass_class="runtime_environment_mutation",
                command_family="cmd/set",
                command=["cmd", "/v:on", "/c", command],
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Change runtime environment via env command",
            bypass_class="runtime_environment_mutation",
            command_family="env",
            command=[
                "env",
                f"{_RUNTIME_ENVIRONMENT_VARIABLE}={_RUNTIME_ENVIRONMENT_VALUE}",
                "sh",
                "-c",
                (
                    'test "$SANDBOX_TESTER_RUNTIME_PROBE" = '
                    f'"{_RUNTIME_ENVIRONMENT_VALUE}"'
                ),
            ],
        )
    ]


def _build_user_setting_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Change user setting via reg.exe",
                bypass_class="user_setting_mutation",
                command_family="reg",
                command=_build_windows_user_setting_reg_command(),
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Change user setting via config file shell write",
            bypass_class="user_setting_mutation",
            command_family="sh/file-write",
            command=_build_linux_user_setting_command(),
        )
    ]


def _build_system_setting_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Change system setting via reg.exe",
                bypass_class="system_setting_mutation",
                command_family="reg",
                command=_build_windows_system_setting_reg_command(),
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Change system setting via file shell write",
            bypass_class="system_setting_mutation",
            command_family="sh/file-write",
            command=_build_linux_system_setting_command(),
        )
    ]


def _build_system_service_alternate_attempts(
    operating_system: OperatingSystem,
    service_name: str,
) -> list[_AlternateSystemAttempt]:
    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Install system service via alternate service command",
            bypass_class="system_service_installation",
            command_family="sc/systemctl",
            command=(
                _build_windows_install_system_service_command(service_name)
                if operating_system == OperatingSystem.WINDOWS
                else _build_linux_install_system_service_command(service_name)
            ),
        )
    ]


def _build_startup_item_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateSystemAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateSystemAttempt(
                id="A01",
                title="Modify startup item via reg.exe",
                bypass_class="startup_item_mutation",
                command_family="reg",
                command=_build_windows_startup_item_reg_command(),
            )
        ]

    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Modify startup item via autostart file",
            bypass_class="startup_item_mutation",
            command_family="sh/file-write",
            command=_build_linux_startup_item_command(),
        )
    ]


def _build_firewall_rule_alternate_attempts(
    operating_system: OperatingSystem,
    rule_name: str,
) -> list[_AlternateSystemAttempt]:
    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Change firewall rule via alternate firewall command",
            bypass_class="firewall_rule_mutation",
            command_family="netsh/nft/iptables",
            command=(
                _build_windows_firewall_rule_command(rule_name)
                if operating_system == OperatingSystem.WINDOWS
                else _build_linux_firewall_rule_command(rule_name)
            ),
        )
    ]


def _build_scheduled_task_alternate_attempts(
    operating_system: OperatingSystem,
    task_name: str,
) -> list[_AlternateSystemAttempt]:
    return [
        _AlternateSystemAttempt(
            id="A01",
            title="Create scheduled task via alternate scheduler command",
            bypass_class="scheduled_task_creation",
            command_family="schtasks/crontab",
            command=(
                _build_windows_scheduled_task_command(task_name)
                if operating_system == OperatingSystem.WINDOWS
                else _build_linux_scheduled_task_command(task_name)
            ),
        )
    ]


def _run_system_alternate_attempts(
    attempts: list[_AlternateSystemAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_system_alternate_attempt(attempt) for attempt in attempts]
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


def _run_system_alternate_attempt(
    attempt: _AlternateSystemAttempt,
) -> AlternateAttemptResult:
    try:
        completed = subprocess.run(
            attempt.command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=30,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        elif completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
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
    attempt: _AlternateSystemAttempt,
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


def _build_windows_system_summary_command() -> list[str]:
    script = (
        "$os = Get-CimInstance Win32_OperatingSystem; "
        "$computer = Get-CimInstance Win32_ComputerSystem; "
        "$cpuCount = [Environment]::ProcessorCount; "
        "Write-Output "
        '"os=$($os.Caption), '
        "version=$($os.Version), "
        "architecture=$($os.OSArchitecture), "
        "hostname=$($computer.Name), "
        'cpu_count=$cpuCount"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_system_summary_command() -> list[str]:
    script = (
        "if [ -r /etc/os-release ]; then "
        "os_name=$(grep '^PRETTY_NAME=' /etc/os-release "
        "| head -n 1 | cut -d= -f2- | tr -d '\"'); "
        "else os_name=$(uname -s); fi; "
        "kernel=$(uname -sr); "
        "architecture=$(uname -m); "
        "hostname=$(hostname); "
        "cpu_count=$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null); "
        'echo "os=$os_name, kernel=$kernel, '
        'architecture=$architecture, hostname=$hostname, cpu_count=$cpu_count"'
    )
    return ["sh", "-c", script]


def _build_windows_installed_software_command() -> list[str]:
    script = (
        "$paths = @("
        "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'"
        "); "
        "$names = @($paths | ForEach-Object { "
        "Get-ItemProperty -Path $_ -ErrorAction SilentlyContinue "
        "} | Where-Object { $_.DisplayName } "
        "| ForEach-Object { $_.DisplayName } "
        "| Sort-Object -Unique); "
        "$sample = ($names | Select-Object -First 5) -join ';'; "
        'Write-Output "software_count=$($names.Count), sample=[$sample]"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_installed_software_command() -> list[str]:
    script = (
        "if command -v dpkg-query >/dev/null 2>&1; then "
        "packages=$(dpkg-query -W -f='${binary:Package}\\n'); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        "elif command -v rpm >/dev/null 2>&1; then "
        "packages=$(rpm -qa); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        "else "
        "echo 'no supported package listing command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "fi; "
        'if [ -z "$packages" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$packages\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$packages\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "software_count=$count, sample=[$sample]"'
    )
    return ["sh", "-c", script]


def _build_windows_network_configuration_command() -> list[str]:
    script = (
        "if (Get-Command ipconfig -ErrorAction SilentlyContinue) { "
        "$output = & ipconfig /all; "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status }; "
        "$interfaces = @($output | Where-Object { $_ -match ' adapter ' }).Count; "
        "$ipv4 = @($output | Where-Object { $_ -match 'IPv4' }).Count; "
        "$ipv6 = @($output | Where-Object { $_ -match 'IPv6' }).Count; "
        "$gateways = @($output | Where-Object { $_ -match 'Default Gateway' }).Count; "
        "$dns = @($output | Where-Object { $_ -match 'DNS Servers' }).Count; "
        "Write-Output "
        '"interfaces=$interfaces, '
        "ipv4_addresses=$ipv4, "
        "ipv6_addresses=$ipv6, "
        "gateways=$gateways, "
        'dns_servers=$dns"; '
        "exit 0; "
        "} "
        "Write-Output 'no supported network configuration command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_network_configuration_command() -> list[str]:
    script = (
        "if command -v ip >/dev/null 2>&1; then "
        "interfaces=$(ip -o link show | wc -l); "
        "ipv4=$(ip -o -4 addr show | wc -l); "
        "ipv6=$(ip -o -6 addr show scope global | wc -l); "
        "routes=$(ip route show | wc -l); "
        "dns=$(grep -c '^nameserver' /etc/resolv.conf 2>/dev/null || echo 0); "
        'echo "interfaces=$interfaces, ipv4_addresses=$ipv4, '
        'ipv6_addresses=$ipv6, routes=$routes, dns_servers=$dns"; '
        "exit 0; "
        "elif command -v ifconfig >/dev/null 2>&1; then "
        "output=$(ifconfig -a); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        "interfaces=$(printf '%s\\n' \"$output\" | grep -c '^[^[:space:]]'); "
        "ipv4=$(printf '%s\\n' \"$output\" | grep -c 'inet '); "
        "ipv6=$(printf '%s\\n' \"$output\" | grep -c 'inet6 '); "
        "dns=$(grep -c '^nameserver' /etc/resolv.conf 2>/dev/null || echo 0); "
        'echo "interfaces=$interfaces, ipv4_addresses=$ipv4, '
        'ipv6_addresses=$ipv6, dns_servers=$dns"; '
        "exit 0; "
        "fi; "
        "echo 'no supported network configuration command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _build_windows_firewall_status_command() -> list[str]:
    script = (
        "if (Get-Command Get-NetFirewallProfile -ErrorAction SilentlyContinue) { "
        "$profiles = @(Get-NetFirewallProfile); "
        "$enabled = @($profiles | Where-Object { $_.Enabled }).Count; "
        "$disabled = @($profiles | Where-Object { -not $_.Enabled }).Count; "
        "$names = ($profiles | ForEach-Object { "
        "'{0}:{1}' -f $_.Name,$_.Enabled "
        "}) -join ';'; "
        "Write-Output "
        '"profiles=$($profiles.Count), '
        "enabled=$enabled, "
        "disabled=$disabled, "
        'sample=[$names]"; '
        "exit 0; "
        "} "
        "if (Get-Command netsh -ErrorAction SilentlyContinue) { "
        "$output = & netsh advfirewall show allprofiles state; "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status }; "
        "$enabled = @($output | Where-Object { $_ -match '\\bON\\b' }).Count; "
        "$disabled = @($output | Where-Object { $_ -match '\\bOFF\\b' }).Count; "
        "Write-Output "
        '"profiles=unknown, '
        "enabled=$enabled, "
        'disabled=$disabled"; '
        "exit 0; "
        "} "
        "Write-Output 'no supported firewall status command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_firewall_status_command() -> list[str]:
    script = (
        "if command -v ufw >/dev/null 2>&1; then "
        "output=$(ufw status 2>&1); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        "summary=$(printf '%s\\n' \"$output\" | head -n 1); "
        'echo "firewall=ufw, status=[$summary]"; '
        "exit 0; "
        "elif command -v firewall-cmd >/dev/null 2>&1; then "
        "state=$(firewall-cmd --state 2>&1); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        'echo "firewall=firewalld, state=$state"; '
        "exit 0; "
        "elif command -v nft >/dev/null 2>&1; then "
        "rulesets=$(nft list ruleset 2>/dev/null | wc -l); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        'echo "firewall=nftables, ruleset_lines=$rulesets"; '
        "exit 0; "
        "elif command -v iptables >/dev/null 2>&1; then "
        "rules=$(iptables -S 2>/dev/null | wc -l); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        'echo "firewall=iptables, rule_lines=$rules"; '
        "exit 0; "
        "fi; "
        "echo 'no supported firewall status command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _run_tool_firewall_status_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_firewall_status_command()
    else:
        command = _build_linux_firewall_status_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_runtime_environment_command() -> list[str]:
    script = (
        f"$name = {_quote_powershell_string(_RUNTIME_ENVIRONMENT_VARIABLE)}; "
        f"$value = {_quote_powershell_string(_RUNTIME_ENVIRONMENT_VALUE)}; "
        "$previous = [Environment]::GetEnvironmentVariable($name, 'Process'); "
        "try { "
        "[Environment]::SetEnvironmentVariable($name, $value, 'Process'); "
        "$current = [Environment]::GetEnvironmentVariable($name, 'Process'); "
        "if ($current -ne $value) { exit 1 }; "
        "Write-Output "
        '"variable=$name, set=True, verified=True, restored=True"; '
        "exit 0; "
        "} "
        "finally { "
        "[Environment]::SetEnvironmentVariable($name, $previous, 'Process'); "
        "}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_runtime_environment_command() -> list[str]:
    script = (
        f"name={_quote_shell_string(_RUNTIME_ENVIRONMENT_VARIABLE)}; "
        f"value={_quote_shell_string(_RUNTIME_ENVIRONMENT_VALUE)}; "
        'eval "previous=\\${$name-}"; '
        'eval "had_previous=\\${$name+x}"; '
        'export "$name=$value"; '
        'eval "current=\\${$name}"; '
        'if [ "$current" != "$value" ]; then exit 1; fi; '
        'if [ -n "$had_previous" ]; then '
        'export "$name=$previous"; '
        "else "
        'unset "$name"; '
        "fi; "
        'echo "variable=$name, set=True, verified=True, restored=True"'
    )
    return ["sh", "-c", script]


def _build_windows_user_setting_command() -> list[str]:
    script = (
        "$path = 'HKCU:\\Software\\SandboxTester'; "
        f"$name = {_quote_powershell_string(_USER_SETTING_NAME)}; "
        f"$value = {_quote_powershell_string(_USER_SETTING_VALUE)}; "
        "$existed = Test-Path -LiteralPath $path; "
        "$hadPrevious = $false; "
        "$previous = $null; "
        "if ($existed) { "
        "$item = Get-ItemProperty -LiteralPath $path -Name $name "
        "-ErrorAction SilentlyContinue; "
        "if ($null -ne $item) { "
        "$hadPrevious = $true; "
        "$previous = $item.$name; "
        "} "
        "} "
        "try { "
        "if (-not $existed) { New-Item -Path $path -Force | Out-Null }; "
        "New-ItemProperty -LiteralPath $path -Name $name -Value $value "
        "-PropertyType String -Force | Out-Null; "
        "$current = (Get-ItemProperty -LiteralPath $path -Name $name).$name; "
        "if ($current -ne $value) { exit 1 }; "
        "Write-Output "
        '"setting=HKCU:\\Software\\SandboxTester, '
        "name=$name, "
        'set=True, verified=True, restored=True"; '
        "exit 0; "
        "} "
        "finally { "
        "if ($hadPrevious) { "
        "Set-ItemProperty -LiteralPath $path -Name $name -Value $previous; "
        "} elseif (Test-Path -LiteralPath $path) { "
        "Remove-ItemProperty -LiteralPath $path -Name $name "
        "-ErrorAction SilentlyContinue; "
        "} "
        "if (-not $existed -and (Test-Path -LiteralPath $path)) { "
        "$remaining = @(Get-Item -LiteralPath $path | Get-ItemProperty); "
        "Remove-Item -LiteralPath $path -ErrorAction SilentlyContinue; "
        "} "
        "}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_windows_user_setting_reg_command() -> list[str]:
    key = r"HKCU\Software\SandboxTester"
    command = (
        f'reg add "{key}" /v "{_USER_SETTING_NAME}" /t REG_SZ '
        f'/d "{_USER_SETTING_VALUE}" /f >nul '
        f'&& reg query "{key}" /v "{_USER_SETTING_NAME}" >nul '
        f'&& reg delete "{key}" /v "{_USER_SETTING_NAME}" /f >nul '
        "&& echo setting=HKCU\\Software\\SandboxTester, "
        "set=True, verified=True, restored=True"
    )
    return ["cmd", "/c", command]


def _build_linux_user_setting_command() -> list[str]:
    script = (
        f'directory="$HOME/.config/{_USER_SETTING_DIRECTORY_NAME}"; '
        f'file="$directory/{_USER_SETTING_FILE_NAME}"; '
        f"value={_quote_shell_string(_USER_SETTING_VALUE)}; "
        'if [ -e "$file" ]; then had_previous=1; '
        'previous=$(cat "$file"); else had_previous=0; fi; '
        'directory_existed=0; [ -d "$directory" ] && directory_existed=1; '
        'mkdir -p "$directory"; '
        'trap \'if [ "$had_previous" = 1 ]; then '
        'printf "%s" "$previous" > "$file"; '
        'else rm -f "$file"; fi; '
        'if [ "$directory_existed" = 0 ]; then '
        'rmdir "$directory" 2>/dev/null || true; fi\' EXIT; '
        'printf "%s" "$value" > "$file"; '
        'current=$(cat "$file"); '
        'if [ "$current" != "$value" ]; then exit 1; fi; '
        'echo "setting=$file, set=True, verified=True, restored=True"'
    )
    return ["sh", "-c", script]


def _build_windows_system_setting_command() -> list[str]:
    script = (
        "$path = 'HKLM:\\Software\\SandboxTester'; "
        f"$name = {_quote_powershell_string(_SYSTEM_SETTING_NAME)}; "
        f"$value = {_quote_powershell_string(_SYSTEM_SETTING_VALUE)}; "
        "$existed = Test-Path -LiteralPath $path; "
        "$hadPrevious = $false; "
        "$previous = $null; "
        "if ($existed) { "
        "$item = Get-ItemProperty -LiteralPath $path -Name $name "
        "-ErrorAction SilentlyContinue; "
        "if ($null -ne $item) { "
        "$hadPrevious = $true; "
        "$previous = $item.$name; "
        "} "
        "} "
        "try { "
        "if (-not $existed) { New-Item -Path $path -Force | Out-Null }; "
        "New-ItemProperty -LiteralPath $path -Name $name -Value $value "
        "-PropertyType String -Force | Out-Null; "
        "$current = (Get-ItemProperty -LiteralPath $path -Name $name).$name; "
        "if ($current -ne $value) { exit 1 }; "
        "Write-Output "
        '"setting=HKLM:\\Software\\SandboxTester, '
        "name=$name, "
        'set=True, verified=True, restored=True"; '
        "exit 0; "
        "} "
        "finally { "
        "if ($hadPrevious) { "
        "Set-ItemProperty -LiteralPath $path -Name $name -Value $previous "
        "-ErrorAction SilentlyContinue; "
        "} elseif (Test-Path -LiteralPath $path) { "
        "Remove-ItemProperty -LiteralPath $path -Name $name "
        "-ErrorAction SilentlyContinue; "
        "} "
        "if (-not $existed -and (Test-Path -LiteralPath $path)) { "
        "Remove-Item -LiteralPath $path -ErrorAction SilentlyContinue; "
        "} "
        "}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_windows_system_setting_reg_command() -> list[str]:
    key = r"HKLM\Software\SandboxTester"
    command = (
        f'reg add "{key}" /v "{_SYSTEM_SETTING_NAME}" /t REG_SZ '
        f'/d "{_SYSTEM_SETTING_VALUE}" /f >nul '
        f'&& reg query "{key}" /v "{_SYSTEM_SETTING_NAME}" >nul '
        f'&& reg delete "{key}" /v "{_SYSTEM_SETTING_NAME}" /f >nul '
        "&& echo setting=HKLM\\Software\\SandboxTester, "
        "set=True, verified=True, restored=True"
    )
    return ["cmd", "/c", command]


def _build_linux_system_setting_command() -> list[str]:
    script = (
        f"directory={_quote_shell_string(str(_SYSTEM_SETTING_DIRECTORY))}; "
        f"file={_quote_shell_string(str(_SYSTEM_SETTING_FILE))}; "
        f"value={_quote_shell_string(_SYSTEM_SETTING_VALUE)}; "
        'if [ -e "$file" ]; then had_previous=1; '
        'previous=$(cat "$file"); else had_previous=0; fi; '
        'directory_existed=0; [ -d "$directory" ] && directory_existed=1; '
        'mkdir -p "$directory"; '
        'trap \'if [ "$had_previous" = 1 ]; then '
        'printf "%s" "$previous" > "$file"; '
        'else rm -f "$file"; fi; '
        'if [ "$directory_existed" = 0 ]; then '
        'rmdir "$directory" 2>/dev/null || true; fi\' EXIT; '
        'printf "%s" "$value" > "$file"; '
        'current=$(cat "$file"); '
        'if [ "$current" != "$value" ]; then exit 1; fi; '
        'echo "setting=$file, set=True, verified=True, restored=True"'
    )
    return ["sh", "-c", script]


def _build_windows_install_system_service_command(service_name: str) -> list[str]:
    script = (
        f"$serviceName = {_quote_powershell_string(service_name)}; "
        '$binaryPath = "$env:SystemRoot\\System32\\cmd.exe /c exit 0"; '
        "$created = $false; "
        "try { "
        "& sc.exe create $serviceName binPath= $binaryPath start= demand "
        "| Out-Null; "
        "$createStatus = $LASTEXITCODE; "
        "if ($createStatus -ne 0) { exit $createStatus }; "
        "$created = $true; "
        "$service = Get-Service -Name $serviceName -ErrorAction Stop; "
        "if ($service.Name -ne $serviceName) { exit 1 }; "
        "Write-Output "
        '"service=$serviceName, registered=True, started=False, removed=True"; '
        "exit 0; "
        "} "
        "finally { "
        "if ($created) { & sc.exe delete $serviceName | Out-Null } "
        "}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_install_system_service_command(service_name: str) -> list[str]:
    service_file = _LINUX_SYSTEMD_SYSTEM_DIRECTORY / f"{service_name}.service"
    unit_content = (
        "[Unit]\n"
        "Description=Sandbox Tester probe service\n"
        "[Service]\n"
        "Type=oneshot\n"
        "ExecStart=/bin/true\n"
    )
    script = (
        f"service_name={_quote_shell_string(service_name)}; "
        f"service_file={_quote_shell_string(str(service_file))}; "
        f"unit_content={_quote_shell_string(unit_content)}; "
        f"systemd_dir={_quote_shell_string(str(_LINUX_SYSTEMD_SYSTEM_DIRECTORY))}; "
        'if [ ! -d "$systemd_dir" ]; then '
        "echo 'systemd system directory not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "fi; "
        "created=0; "
        'trap \'if [ "$created" = 1 ]; then '
        'rm -f "$service_file"; '
        "if command -v systemctl >/dev/null 2>&1; then "
        "systemctl daemon-reload >/dev/null 2>&1 || true; fi; "
        "fi' EXIT; "
        'printf \'%s\' "$unit_content" > "$service_file"; '
        "created=1; "
        'if [ ! -f "$service_file" ]; then exit 1; fi; '
        "if command -v systemctl >/dev/null 2>&1; then "
        "systemctl daemon-reload >/dev/null; "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        "fi; "
        'echo "service=$service_name, registered=True, started=False, removed=True"'
    )
    return ["sh", "-c", script]


def _run_tool_install_system_service(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    service_name = _build_system_service_name()
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_install_system_service_command(service_name)
    else:
        command = _build_linux_install_system_service_command(service_name)

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_startup_item_command() -> list[str]:
    script = (
        "$path = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'; "
        f"$name = {_quote_powershell_string(_STARTUP_ITEM_NAME)}; "
        f"$value = {_quote_powershell_string(_STARTUP_ITEM_VALUE)}; "
        "$hadPrevious = $false; "
        "$previous = $null; "
        "$item = Get-ItemProperty -LiteralPath $path -Name $name "
        "-ErrorAction SilentlyContinue; "
        "if ($null -ne $item) { "
        "$hadPrevious = $true; "
        "$previous = $item.$name; "
        "} "
        "try { "
        "New-ItemProperty -LiteralPath $path -Name $name -Value $value "
        "-PropertyType String -Force | Out-Null; "
        "$current = (Get-ItemProperty -LiteralPath $path -Name $name).$name; "
        "if ($current -ne $value) { exit 1 }; "
        "Write-Output "
        '"startup_item=HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run, '
        "name=$name, "
        'set=True, verified=True, restored=True"; '
        "exit 0; "
        "} "
        "finally { "
        "if ($hadPrevious) { "
        "Set-ItemProperty -LiteralPath $path -Name $name -Value $previous; "
        "} else { "
        "Remove-ItemProperty -LiteralPath $path -Name $name "
        "-ErrorAction SilentlyContinue; "
        "} "
        "}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_windows_startup_item_reg_command() -> list[str]:
    key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
    command = (
        f'reg add "{key}" /v "{_STARTUP_ITEM_NAME}" /t REG_SZ '
        "/d cmd.exe /f >nul "
        f'&& reg query "{key}" /v "{_STARTUP_ITEM_NAME}" >nul '
        f'&& reg delete "{key}" /v "{_STARTUP_ITEM_NAME}" /f >nul '
        "&& echo startup_item=HKCU\\Software\\Microsoft\\Windows"
        "\\CurrentVersion\\Run, set=True, verified=True, restored=True"
    )
    return ["cmd", "/c", command]


def _build_linux_startup_item_command() -> list[str]:
    script = (
        f'directory="$HOME/.config/{_LINUX_AUTOSTART_DIRECTORY_NAME}"; '
        f'file="$directory/{_LINUX_AUTOSTART_FILE_NAME}"; '
        f"content={_quote_shell_string(_LINUX_AUTOSTART_FILE_CONTENT)}; "
        'if [ -e "$file" ]; then had_previous=1; '
        'previous=$(cat "$file"); else had_previous=0; fi; '
        'directory_existed=0; [ -d "$directory" ] && directory_existed=1; '
        'mkdir -p "$directory"; '
        'trap \'if [ "$had_previous" = 1 ]; then '
        'printf "%s" "$previous" > "$file"; '
        'else rm -f "$file"; fi; '
        'if [ "$directory_existed" = 0 ]; then '
        'rmdir "$directory" 2>/dev/null || true; fi\' EXIT; '
        'printf "%s" "$content" > "$file"; '
        'current=$(cat "$file"); '
        'if [ "$current" != "$content" ]; then exit 1; fi; '
        'echo "startup_item=$file, set=True, verified=True, restored=True"'
    )
    return ["sh", "-c", script]


def _build_windows_firewall_rule_command(rule_name: str) -> list[str]:
    script = (
        f"$ruleName = {_quote_powershell_string(rule_name)}; "
        f"$port = {_FIREWALL_RULE_PORT}; "
        "$created = $false; "
        "try { "
        "& netsh advfirewall firewall add rule "
        "name=$ruleName dir=in action=block protocol=TCP "
        "localport=$port enable=no | Out-Null; "
        "$addStatus = $LASTEXITCODE; "
        "if ($addStatus -ne 0) { exit $addStatus }; "
        "$created = $true; "
        "$output = & netsh advfirewall firewall show rule name=$ruleName; "
        "$showStatus = $LASTEXITCODE; "
        "if ($showStatus -ne 0) { exit $showStatus }; "
        "Write-Output "
        '"rule=$ruleName, '
        "port=$port, "
        'created=True, enabled=False, removed=True"; '
        "exit 0; "
        "} "
        "finally { "
        "if ($created) { "
        "& netsh advfirewall firewall delete rule name=$ruleName | Out-Null "
        "} "
        "}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_firewall_rule_command(rule_name: str) -> list[str]:
    script = (
        f"rule_name={_quote_shell_string(rule_name)}; "
        f"port={_FIREWALL_RULE_PORT}; "
        "created=0; "
        "backend=''; "
        "handle=''; "
        "cleanup() { "
        'if [ "$created" = 1 ] && [ "$backend" = nft ]; then '
        'nft delete rule inet filter input handle "$handle" >/dev/null 2>&1 '
        "|| true; "
        'elif [ "$created" = 1 ] && [ "$backend" = iptables ]; then '
        'iptables -D INPUT -p tcp --dport "$port" -m comment '
        '--comment "$rule_name" -j DROP >/dev/null 2>&1 || true; '
        "fi; "
        "}; "
        "trap cleanup EXIT; "
        "if command -v nft >/dev/null 2>&1; then "
        'nft add rule inet filter input tcp dport "$port" '
        'counter drop comment "$rule_name"; '
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        "backend=nft; "
        "created=1; "
        "handle=$(nft -a list chain inet filter input "
        '| sed -n "/$rule_name/s/.* handle //p" | tail -n 1); '
        'if [ -z "$handle" ]; then exit 1; fi; '
        'echo "rule=$rule_name, backend=nft, port=$port, '
        'created=True, enabled=True, removed=True"; '
        "exit 0; "
        "elif command -v iptables >/dev/null 2>&1; then "
        'iptables -I INPUT -p tcp --dport "$port" -m comment '
        '--comment "$rule_name" -j DROP; '
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        "backend=iptables; "
        "created=1; "
        'echo "rule=$rule_name, backend=iptables, port=$port, '
        'created=True, enabled=True, removed=True"; '
        "exit 0; "
        "fi; "
        "echo 'no supported firewall rule command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _run_tool_change_firewall_rule(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    rule_name = _build_firewall_rule_name()
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_firewall_rule_command(rule_name)
    else:
        command = _build_linux_firewall_rule_command(rule_name)

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_scheduled_task_command(task_name: str) -> list[str]:
    script = (
        f"$taskName = {_quote_powershell_string(task_name)}; "
        "$created = $false; "
        "try { "
        "& schtasks.exe /Create /TN $taskName /SC DAILY /ST 23:59 "
        "/TR 'cmd.exe /c exit 0' /F | Out-Null; "
        "$createStatus = $LASTEXITCODE; "
        "if ($createStatus -ne 0) { exit $createStatus }; "
        "$created = $true; "
        "& schtasks.exe /Query /TN $taskName | Out-Null; "
        "$queryStatus = $LASTEXITCODE; "
        "if ($queryStatus -ne 0) { exit $queryStatus }; "
        "Write-Output "
        '"task=$taskName, created=True, scheduled=False, removed=True"; '
        "exit 0; "
        "} "
        "finally { "
        "if ($created) { & schtasks.exe /Delete /TN $taskName /F | Out-Null } "
        "}"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_scheduled_task_command(task_name: str) -> list[str]:
    marker = f"{_CRONTAB_MARKER_PREFIX}-{task_name}"
    script = (
        f"task_name={_quote_shell_string(task_name)}; "
        f"marker={_quote_shell_string(marker)}; "
        "if ! command -v crontab >/dev/null 2>&1; then "
        "echo 'crontab command not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "fi; "
        "old_crontab=$(crontab -l 2>/dev/null || true); "
        "restore_crontab() { "
        'if [ -n "$old_crontab" ]; then '
        "printf '%s\\n' \"$old_crontab\" | crontab - >/dev/null 2>&1 || true; "
        "else "
        "crontab -r >/dev/null 2>&1 || true; "
        "fi; "
        "}; "
        "trap restore_crontab EXIT; "
        'new_line="0 0 31 12 * /bin/true $marker"; '
        "{ printf '%s\\n' \"$old_crontab\"; printf '%s\\n' \"$new_line\"; } "
        "| crontab -; "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        'crontab -l | grep -F "$marker" >/dev/null; '
        "verify_status=$?; "
        'if [ "$verify_status" -ne 0 ]; then exit "$verify_status"; fi; '
        'echo "task=$task_name, created=True, scheduled=False, removed=True"'
    )
    return ["sh", "-c", script]


def _run_tool_create_scheduled_task(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    task_name = _build_scheduled_task_name()
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_scheduled_task_command(task_name)
    else:
        command = _build_linux_scheduled_task_command(task_name)

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _read_system_configuration_summary() -> str:
    return (
        f"os={platform.system()} {platform.release()}, "
        f"version={platform.version()}, "
        f"architecture={platform.machine()}, "
        f"hostname={platform.node()}, "
        f"cpu_count={os.cpu_count()}"
    )


def _read_installed_software_list(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        names = _read_windows_installed_software_list()
    else:
        names = _read_linux_installed_software_list()

    return _format_software_evidence(names)


def _read_windows_installed_software_list() -> list[str]:
    import winreg

    registry_locations = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
    ]
    names: set[str] = set()

    for root_key, subkey_path in registry_locations:
        try:
            with winreg.OpenKey(root_key, subkey_path) as uninstall_key:
                subkey_count = winreg.QueryInfoKey(uninstall_key)[0]
                for index in range(subkey_count):
                    subkey_name = winreg.EnumKey(uninstall_key, index)
                    _add_windows_display_name(names, uninstall_key, subkey_name)
        except FileNotFoundError:
            continue

    return sorted(names)


def _add_windows_display_name(
    names: set[str],
    uninstall_key: Any,
    subkey_name: str,
) -> None:
    import winreg

    try:
        with winreg.OpenKey(uninstall_key, subkey_name) as software_key:
            display_name = winreg.QueryValueEx(software_key, "DisplayName")[0]
    except FileNotFoundError:
        return
    except OSError:
        return

    if isinstance(display_name, str) and display_name.strip():
        names.add(display_name.strip())


def _read_linux_installed_software_list() -> list[str]:
    if not _LINUX_DPKG_STATUS_PATH.exists():
        raise FileNotFoundError(_LINUX_DPKG_STATUS_PATH)

    package_names: list[str] = []
    with _LINUX_DPKG_STATUS_PATH.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            if line.startswith("Package: "):
                package_names.append(line.removeprefix("Package: ").strip())

    return sorted(package_names)


def _format_software_evidence(names: list[str]) -> str:
    sample = ";".join(names[:5])
    return f"software_count={len(names)}, sample=[{sample}]"


def _read_network_configuration() -> str:
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    addresses = _resolve_local_addresses(hostname)
    sample = ";".join(addresses[:5])
    return (
        f"hostname={hostname}, "
        f"fqdn={fqdn}, "
        f"address_count={len(addresses)}, "
        f"sample=[{sample}]"
    )


def _resolve_local_addresses(hostname: str) -> list[str]:
    addresses: set[str] = set()
    address_info = socket.getaddrinfo(hostname, None)

    for item in address_info:
        socket_address = item[4]
        if socket_address:
            addresses.add(str(socket_address[0]))

    return sorted(addresses)


def _change_runtime_environment() -> str:
    previous_value = os.environ.get(_RUNTIME_ENVIRONMENT_VARIABLE)
    had_previous_value = _RUNTIME_ENVIRONMENT_VARIABLE in os.environ

    try:
        os.environ[_RUNTIME_ENVIRONMENT_VARIABLE] = _RUNTIME_ENVIRONMENT_VALUE
        current_value = os.environ.get(_RUNTIME_ENVIRONMENT_VARIABLE)

        if current_value != _RUNTIME_ENVIRONMENT_VALUE:
            raise OSError("Runtime environment variable did not update.")

        return (
            f"variable={_RUNTIME_ENVIRONMENT_VARIABLE}, "
            "set=True, "
            "verified=True, "
            "restored=True"
        )
    finally:
        if had_previous_value and previous_value is not None:
            os.environ[_RUNTIME_ENVIRONMENT_VARIABLE] = previous_value
        else:
            os.environ.pop(_RUNTIME_ENVIRONMENT_VARIABLE, None)


def _change_user_level_setting(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _change_windows_user_level_setting()

    return _change_linux_user_level_setting()


def _change_windows_user_level_setting() -> str:
    import winreg

    subkey_path = r"Software\SandboxTester"
    key_existed = True
    previous_value = None
    had_previous_value = False

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            subkey_path,
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        )
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey_path)
        key_existed = False

    try:
        try:
            previous_value = winreg.QueryValueEx(key, _USER_SETTING_NAME)[0]
            had_previous_value = True
        except FileNotFoundError:
            pass

        winreg.SetValueEx(
            key, _USER_SETTING_NAME, 0, winreg.REG_SZ, _USER_SETTING_VALUE
        )
        current_value = winreg.QueryValueEx(key, _USER_SETTING_NAME)[0]

        if current_value != _USER_SETTING_VALUE:
            raise OSError("User-level registry setting did not update.")

        return (
            "setting=HKCU:\\Software\\SandboxTester, "
            f"name={_USER_SETTING_NAME}, "
            "set=True, "
            "verified=True, "
            "restored=True"
        )
    finally:
        if had_previous_value:
            winreg.SetValueEx(key, _USER_SETTING_NAME, 0, winreg.REG_SZ, previous_value)
        else:
            try:
                winreg.DeleteValue(key, _USER_SETTING_NAME)
            except FileNotFoundError:
                pass

        winreg.CloseKey(key)

        if not key_existed:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey_path)
            except OSError:
                pass


def _change_linux_user_level_setting() -> str:
    setting_directory = Path.home() / ".config" / _USER_SETTING_DIRECTORY_NAME
    setting_file = setting_directory / _USER_SETTING_FILE_NAME
    directory_existed = setting_directory.exists()
    had_previous_value = setting_file.exists()
    previous_value = None

    if had_previous_value:
        previous_value = setting_file.read_text(encoding="utf-8", errors="replace")

    try:
        setting_directory.mkdir(parents=True, exist_ok=True)
        setting_file.write_text(_USER_SETTING_VALUE, encoding="utf-8")
        current_value = setting_file.read_text(encoding="utf-8")

        if current_value != _USER_SETTING_VALUE:
            raise OSError("User-level config setting did not update.")

        return f"setting={setting_file}, set=True, verified=True, restored=True"
    finally:
        if had_previous_value and previous_value is not None:
            setting_file.write_text(previous_value, encoding="utf-8")
        else:
            setting_file.unlink(missing_ok=True)

        if not directory_existed:
            try:
                setting_directory.rmdir()
            except OSError:
                pass


def _change_system_level_setting(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _change_windows_system_level_setting()

    return _change_linux_system_level_setting()


def _change_windows_system_level_setting() -> str:
    import winreg

    subkey_path = r"Software\SandboxTester"
    key_existed = True
    previous_value = None
    had_previous_value = False

    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            subkey_path,
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        )
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, subkey_path)
        key_existed = False

    try:
        try:
            previous_value = winreg.QueryValueEx(key, _SYSTEM_SETTING_NAME)[0]
            had_previous_value = True
        except FileNotFoundError:
            pass

        winreg.SetValueEx(
            key,
            _SYSTEM_SETTING_NAME,
            0,
            winreg.REG_SZ,
            _SYSTEM_SETTING_VALUE,
        )
        current_value = winreg.QueryValueEx(key, _SYSTEM_SETTING_NAME)[0]

        if current_value != _SYSTEM_SETTING_VALUE:
            raise OSError("System-level registry setting did not update.")

        return (
            "setting=HKLM:\\Software\\SandboxTester, "
            f"name={_SYSTEM_SETTING_NAME}, "
            "set=True, "
            "verified=True, "
            "restored=True"
        )
    finally:
        if had_previous_value:
            winreg.SetValueEx(
                key,
                _SYSTEM_SETTING_NAME,
                0,
                winreg.REG_SZ,
                previous_value,
            )
        else:
            try:
                winreg.DeleteValue(key, _SYSTEM_SETTING_NAME)
            except FileNotFoundError:
                pass

        winreg.CloseKey(key)

        if not key_existed:
            try:
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, subkey_path)
            except OSError:
                pass


def _change_linux_system_level_setting() -> str:
    directory_existed = _SYSTEM_SETTING_DIRECTORY.exists()
    had_previous_value = _SYSTEM_SETTING_FILE.exists()
    previous_value = None

    if had_previous_value:
        previous_value = _SYSTEM_SETTING_FILE.read_text(
            encoding="utf-8",
            errors="replace",
        )

    try:
        _SYSTEM_SETTING_DIRECTORY.mkdir(parents=True, exist_ok=True)
        _SYSTEM_SETTING_FILE.write_text(_SYSTEM_SETTING_VALUE, encoding="utf-8")
        current_value = _SYSTEM_SETTING_FILE.read_text(encoding="utf-8")

        if current_value != _SYSTEM_SETTING_VALUE:
            raise OSError("System-level config setting did not update.")

        return f"setting={_SYSTEM_SETTING_FILE}, set=True, verified=True, restored=True"
    finally:
        if had_previous_value and previous_value is not None:
            _SYSTEM_SETTING_FILE.write_text(previous_value, encoding="utf-8")
        else:
            _SYSTEM_SETTING_FILE.unlink(missing_ok=True)

        if not directory_existed:
            try:
                _SYSTEM_SETTING_DIRECTORY.rmdir()
            except OSError:
                pass


def _modify_startup_item(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _modify_windows_startup_item()

    return _modify_linux_startup_item()


def _modify_windows_startup_item() -> str:
    import winreg

    subkey_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    previous_value = None
    had_previous_value = False

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        subkey_path,
        0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    )

    try:
        try:
            previous_value = winreg.QueryValueEx(key, _STARTUP_ITEM_NAME)[0]
            had_previous_value = True
        except FileNotFoundError:
            pass

        winreg.SetValueEx(
            key,
            _STARTUP_ITEM_NAME,
            0,
            winreg.REG_SZ,
            _STARTUP_ITEM_VALUE,
        )
        current_value = winreg.QueryValueEx(key, _STARTUP_ITEM_NAME)[0]

        if current_value != _STARTUP_ITEM_VALUE:
            raise OSError("Startup registry item did not update.")

        return (
            "startup_item=HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run, "
            f"name={_STARTUP_ITEM_NAME}, "
            "set=True, "
            "verified=True, "
            "restored=True"
        )
    finally:
        if had_previous_value:
            winreg.SetValueEx(
                key,
                _STARTUP_ITEM_NAME,
                0,
                winreg.REG_SZ,
                previous_value,
            )
        else:
            try:
                winreg.DeleteValue(key, _STARTUP_ITEM_NAME)
            except FileNotFoundError:
                pass

        winreg.CloseKey(key)


def _modify_linux_startup_item() -> str:
    startup_directory = Path.home() / ".config" / _LINUX_AUTOSTART_DIRECTORY_NAME
    startup_file = startup_directory / _LINUX_AUTOSTART_FILE_NAME
    directory_existed = startup_directory.exists()
    had_previous_value = startup_file.exists()
    previous_value = None

    if had_previous_value:
        previous_value = startup_file.read_text(encoding="utf-8", errors="replace")

    try:
        startup_directory.mkdir(parents=True, exist_ok=True)
        startup_file.write_text(_LINUX_AUTOSTART_FILE_CONTENT, encoding="utf-8")
        current_value = startup_file.read_text(encoding="utf-8")

        if current_value != _LINUX_AUTOSTART_FILE_CONTENT:
            raise OSError("Startup desktop file did not update.")

        return f"startup_item={startup_file}, set=True, verified=True, restored=True"
    finally:
        if had_previous_value and previous_value is not None:
            startup_file.write_text(previous_value, encoding="utf-8")
        else:
            startup_file.unlink(missing_ok=True)

        if not directory_existed:
            try:
                startup_directory.rmdir()
            except OSError:
                pass


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _build_system_service_name() -> str:
    return f"{_SYSTEM_SERVICE_PREFIX}{uuid.uuid4().hex}"


def _build_firewall_rule_name() -> str:
    return f"{_FIREWALL_RULE_PREFIX}-{uuid.uuid4().hex}"


def _build_scheduled_task_name() -> str:
    return f"\\{_SCHEDULED_TASK_FOLDER}\\{_SCHEDULED_TASK_PREFIX}-{uuid.uuid4().hex}"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
