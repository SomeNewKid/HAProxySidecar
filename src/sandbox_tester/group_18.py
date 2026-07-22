"""Group 18: Identity, authentication, and credential stores."""

from __future__ import annotations

import asyncio
import ctypes
import importlib
import platform
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_CREDENTIAL_SECRET = "sandbox-tester-secret"


class G18_T01:
    id = "T01"
    title = "Read local credential store entry"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if not _credential_store_is_available(self._operating_system):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported local credential store was available.",
            )

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                _build_credential_name(),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read a local credential store entry.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read a local credential store entry.",
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
                summary="Shell credential store entry read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell credential store entry read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if not _credential_store_is_available(self._operating_system):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported local credential store was available.",
            )

        try:
            evidence = await asyncio.to_thread(
                _write_read_delete_credential,
                self._operating_system,
                _build_credential_name(),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read a local credential store entry.",
                evidence=evidence,
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
                summary="Python runtime credential store entry read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime credential store entry read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if not _credential_store_is_available(self._operating_system):
            return _no_supported_alternate_surface(
                "No supported local credential store was available."
            )

        return await asyncio.to_thread(
            _run_identity_alternate_attempts,
            _build_credential_store_alternate_attempts(
                self._operating_system,
                _build_credential_name(),
                bypass_class="credential_store_entry_read",
                success_evidence=(
                    "entry_created=True, entry_read=True, entry_deleted=True"
                ),
            ),
        )

    def _run_shell_command(
        self,
        credential_name: str,
    ) -> subprocess.CompletedProcess[str]:
        command = _build_shell_credential_command(
            self._operating_system,
            credential_name,
            success_evidence="entry_created=True, entry_read=True, entry_deleted=True",
        )

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )


class G18_T02:
    id = "T02"
    title = "Request credential store lookup"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if not _credential_store_is_available(self._operating_system):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported local credential store was available.",
            )

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                _build_credential_name(),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell requested a credential store lookup.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not request a credential store lookup.",
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
                summary="Shell credential store lookup timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell credential store lookup failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if not _credential_store_is_available(self._operating_system):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported local credential store was available.",
            )

        try:
            evidence = await asyncio.to_thread(
                _write_lookup_delete_credential,
                self._operating_system,
                _build_credential_name(),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime requested a credential store lookup.",
                evidence=evidence,
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
                summary="Python runtime credential store lookup timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime credential store lookup failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if not _credential_store_is_available(self._operating_system):
            return _no_supported_alternate_surface(
                "No supported local credential store was available."
            )

        return await asyncio.to_thread(
            _run_identity_alternate_attempts,
            _build_credential_store_alternate_attempts(
                self._operating_system,
                _build_credential_name(),
                bypass_class="credential_store_lookup",
                success_evidence=(
                    "entry_created=True, lookup_requested=True, entry_deleted=True"
                ),
            ),
        )

    def _run_shell_command(
        self,
        credential_name: str,
    ) -> subprocess.CompletedProcess[str]:
        command = _build_shell_credential_command(
            self._operating_system,
            credential_name,
            success_evidence=(
                "entry_created=True, lookup_requested=True, entry_deleted=True"
            ),
        )

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )


class G18_T03:
    id = "T03"
    title = "Use SSH agent to sign challenge"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if not _ssh_signing_tools_are_available():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="OpenSSH signing tools were not available.",
            )

        try:
            completed = await asyncio.to_thread(
                _run_shell_ssh_agent_sign_command,
                self._operating_system,
                self._allowed_directory,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell used the SSH agent to sign a challenge.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 3:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No SSH agent identities were loaded.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not use the SSH agent to sign a challenge.",
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
                summary="Shell SSH agent signing timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell SSH agent signing failed.",
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
            evidence = await asyncio.to_thread(_sign_challenge_with_paramiko_agent)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime used the SSH agent to sign a challenge.",
                evidence=evidence,
            )
        except LookupError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SSH agent identities were loaded.",
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
                summary="Python runtime SSH agent signing failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if not _ssh_signing_tools_are_available():
            return _no_supported_alternate_surface(
                "OpenSSH signing tools were not available."
            )

        return await asyncio.to_thread(
            _run_identity_alternate_attempts,
            _build_ssh_agent_alternate_attempts(),
        )


class G18_T04:
    id = "T04"
    title = "Access GPG/PGP agent"

    async def run_shell(self) -> InvocationResult:
        if not _gpg_agent_tools_are_available():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="GPG agent tools were not available.",
            )

        try:
            completed = await asyncio.to_thread(_run_shell_gpg_agent_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the GPG agent.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 3:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No GPG agent socket was found.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not connect to the GPG agent.",
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
                summary="Shell GPG agent access timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell GPG agent access failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if not _gpg_agent_tools_are_available():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="GPG agent tools were not available.",
            )

        try:
            evidence = await asyncio.to_thread(_connect_to_gpg_agent)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the GPG agent.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No GPG agent socket was found.",
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
                summary="Python runtime GPG agent access timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime GPG agent access failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if not _gpg_agent_tools_are_available():
            return _no_supported_alternate_surface(
                "GPG agent tools were not available."
            )

        return await asyncio.to_thread(
            _run_identity_alternate_attempts,
            _build_gpg_agent_alternate_attempts(),
        )


class G18_T05:
    id = "T05"
    title = "Access OS keychain/wallet"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if not _os_keychain_is_available(self._operating_system):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported OS keychain or wallet was available.",
            )

        try:
            completed = await asyncio.to_thread(
                _run_shell_keychain_query,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell accessed OS keychain or wallet metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not access OS keychain or wallet metadata.",
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
                summary="Shell OS keychain or wallet access timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell OS keychain or wallet access failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if not _os_keychain_is_available(self._operating_system):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported OS keychain or wallet was available.",
            )

        try:
            evidence = await asyncio.to_thread(
                _query_os_keychain_metadata,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime accessed OS keychain or wallet metadata.",
                evidence=evidence,
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
                summary="Python runtime OS keychain or wallet access timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime OS keychain or wallet access failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if not _os_keychain_is_available(self._operating_system):
            return _no_supported_alternate_surface(
                "No supported OS keychain or wallet was available."
            )

        return await asyncio.to_thread(
            _run_identity_alternate_attempts,
            _build_keychain_query_alternate_attempts(self._operating_system),
        )


class G18_T09:
    id = "T09"
    title = "Detect logged-in user sessions"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_logged_in_sessions_query,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected logged-in operating-system sessions.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not detect logged-in operating-system sessions.",
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
                summary="Shell logged-in session detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell logged-in session detection failed.",
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
                _query_logged_in_sessions,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected logged-in operating-system sessions.",
                evidence=evidence,
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
                summary="Python runtime logged-in session detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime logged-in session detection failed.",
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
            _run_identity_alternate_attempts,
            _build_logged_in_session_alternate_attempts(self._operating_system),
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G18",
        title="Identity, authentication, and credential stores",
        tests=[
            G18_T01(capability_context),
            G18_T02(capability_context),
            G18_T03(capability_context),
            G18_T04(),
            G18_T05(capability_context),
            G18_T09(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateIdentityAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_credential_store_alternate_attempts(
    operating_system: OperatingSystem,
    credential_name: str,
    bypass_class: str,
    success_evidence: str,
) -> list[_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateIdentityAttempt(
                id="A01",
                title="Use credential store via cmdkey in cmd",
                bypass_class=bypass_class,
                command_family="cmd/cmdkey",
                command=_build_windows_cmd_credential_command(
                    credential_name,
                    success_evidence,
                ),
            )
        ]

    return [
        _AlternateIdentityAttempt(
            id="A01",
            title="Use credential store via direct secret-tool commands",
            bypass_class=bypass_class,
            command_family="secret-tool",
            command=_build_linux_credential_command(
                credential_name,
                success_evidence,
            ),
        )
    ]


def _build_ssh_agent_alternate_attempts() -> list[_AlternateIdentityAttempt]:
    return [
        _AlternateIdentityAttempt(
            id="A01",
            title="List SSH agent identities via ssh-add",
            bypass_class="ssh_agent_identity_listing",
            command_family="ssh-add",
            command=_build_ssh_agent_identity_command(),
        )
    ]


def _build_gpg_agent_alternate_attempts() -> list[_AlternateIdentityAttempt]:
    return [
        _AlternateIdentityAttempt(
            id="A01",
            title="Query GPG agent socket via gpgconf",
            bypass_class="gpg_agent_socket_query",
            command_family="gpgconf",
            command=_build_gpg_agent_socket_query_command(),
        )
    ]


def _build_keychain_query_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateIdentityAttempt(
                id="A01",
                title="Query OS keychain via cmdkey in cmd",
                bypass_class="os_keychain_metadata_query",
                command_family="cmd/cmdkey",
                command=[
                    "cmd",
                    "/c",
                    "cmdkey /list >nul && echo credential_query_completed=True",
                ],
            )
        ]

    return [
        _AlternateIdentityAttempt(
            id="A01",
            title="Query OS wallet via secret-tool search",
            bypass_class="os_keychain_metadata_query",
            command_family="secret-tool",
            command=[
                "secret-tool",
                "search",
                "--all",
                "application",
                "sandbox-tester",
            ],
        )
    ]


def _build_logged_in_session_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateIdentityAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateIdentityAttempt(
                id="A01",
                title="Detect logged-in sessions via quser",
                bypass_class="logged_in_session_enumeration",
                command_family="quser",
                command=["quser"],
            ),
            _AlternateIdentityAttempt(
                id="A02",
                title="Detect logged-in sessions via qwinsta",
                bypass_class="logged_in_session_enumeration",
                command_family="qwinsta",
                command=["qwinsta"],
            ),
        ]

    return [
        _AlternateIdentityAttempt(
            id="A01",
            title="Detect logged-in sessions via w",
            bypass_class="logged_in_session_enumeration",
            command_family="w",
            command=["w", "-h"],
        ),
        _AlternateIdentityAttempt(
            id="A02",
            title="Detect logged-in sessions via users",
            bypass_class="logged_in_session_enumeration",
            command_family="users",
            command=["users"],
        ),
    ]


def _run_identity_alternate_attempts(
    attempts: list[_AlternateIdentityAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_identity_alternate_attempt(attempt) for attempt in attempts]
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


def _run_identity_alternate_attempt(
    attempt: _AlternateIdentityAttempt,
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
        elif completed.returncode == 3:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_identity_alternate_evidence(attempt, completed, combined_output),
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
    attempt: _AlternateIdentityAttempt,
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


def _no_supported_alternate_surface(summary: str) -> AlternateInvocationResult:
    return AlternateInvocationResult(
        outcome=Outcome.NOT_APPLICABLE,
        summary=summary,
        attempts=[],
    )


def _identity_alternate_evidence(
    attempt: _AlternateIdentityAttempt,
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if completed.returncode != 0:
        return _failure_evidence(completed, combined_output)

    if attempt.command_family in {"quser", "qwinsta", "w", "users"}:
        session_rows = len([line for line in completed.stdout.splitlines() if line])
        return f"session_rows={session_rows}"

    if attempt.command_family in {"cmd/cmdkey", "secret-tool"}:
        return "credential_query_completed=True"

    return _failure_evidence(completed, combined_output)


def _credential_store_is_available(operating_system: OperatingSystem) -> bool:
    if operating_system == OperatingSystem.WINDOWS:
        return True

    return shutil.which("secret-tool") is not None


def _os_keychain_is_available(operating_system: OperatingSystem) -> bool:
    if operating_system == OperatingSystem.WINDOWS:
        return shutil.which("cmdkey") is not None

    return shutil.which("secret-tool") is not None


def _run_shell_keychain_query(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_keychain_query_command()
    else:
        command = _build_linux_keychain_query_command()

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def _build_shell_credential_command(
    operating_system: OperatingSystem,
    credential_name: str,
    success_evidence: str,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _build_windows_credential_command(credential_name, success_evidence)

    return _build_linux_credential_command(credential_name, success_evidence)


def _build_windows_credential_command(
    credential_name: str,
    success_evidence: str,
) -> list[str]:
    script = (
        f"$target = {_quote_powershell_string(credential_name)}; "
        f"$secret = {_quote_powershell_string(_CREDENTIAL_SECRET)}; "
        "& cmdkey /generic:$target /user:SandboxTester /pass:$secret | Out-Null; "
        "$storeStatus = $LASTEXITCODE; "
        "try { "
        "if ($storeStatus -ne 0) { exit $storeStatus }; "
        "$output = & cmdkey /list:$target; "
        "$lookupStatus = $LASTEXITCODE; "
        "if ($lookupStatus -ne 0) { exit $lookupStatus }; "
        "if ($output -match [regex]::Escape($target)) { "
        f"Write-Output {_quote_powershell_string(success_evidence)}; "
        "exit 0; "
        "} "
        "exit 2; "
        "} "
        "finally { & cmdkey /delete:$target | Out-Null }"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_windows_cmd_credential_command(
    credential_name: str,
    success_evidence: str,
) -> list[str]:
    target = _escape_cmd_argument(credential_name)
    secret = _escape_cmd_argument(_CREDENTIAL_SECRET)
    evidence = _escape_cmd_argument(success_evidence)
    command = (
        f"cmdkey /generic:{target} /user:SandboxTester /pass:{secret} >nul "
        f"&& cmdkey /list:{target} >nul "
        f"&& echo {evidence} "
        f"& cmdkey /delete:{target} >nul"
    )
    return ["cmd", "/c", command]


def _build_linux_credential_command(
    credential_name: str,
    success_evidence: str,
) -> list[str]:
    script = (
        f"name={_quote_shell_string(credential_name)}; "
        f"secret={_quote_shell_string(_CREDENTIAL_SECRET)}; "
        "printf '%s' \"$secret\" | secret-tool store "
        "--label='Sandbox Tester' application sandbox-tester entry \"$name\"; "
        "store_status=$?; "
        'trap \'secret-tool clear application sandbox-tester entry "$name" '
        ">/dev/null 2>&1' EXIT; "
        'if [ "$store_status" -ne 0 ]; then exit "$store_status"; fi; '
        'lookup=$(secret-tool lookup application sandbox-tester entry "$name"); '
        "lookup_status=$?; "
        'if [ "$lookup_status" -ne 0 ]; then exit "$lookup_status"; fi; '
        'if [ "$lookup" != "$secret" ]; then exit 2; fi; '
        f"echo {_quote_shell_string(success_evidence)}"
    )
    return ["sh", "-c", script]


def _build_windows_keychain_query_command() -> list[str]:
    script = (
        "$output = & cmdkey /list; "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status }; "
        "$entries = @($output | Where-Object { $_ -match '^\\s*Target:' }); "
        'Write-Output "credential_entries=$($entries.Count)"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_keychain_query_command() -> list[str]:
    script = (
        "secret-tool search --all application sandbox-tester >/dev/null 2>&1; "
        "status=$?; "
        'if [ "$status" -eq 0 ] || [ "$status" -eq 1 ]; then '
        "echo 'wallet_query_completed=True'; exit 0; "
        "fi; "
        'exit "$status"'
    )
    return ["sh", "-c", script]


def _query_os_keychain_metadata(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _query_windows_keychain_metadata()

    return _query_secret_tool_wallet_metadata()


def _query_windows_keychain_metadata() -> str:
    credentials = _enumerate_windows_credentials()
    return f"credential_entries={len(credentials)}"


def _query_secret_tool_wallet_metadata() -> str:
    completed = subprocess.run(
        [
            "secret-tool",
            "search",
            "--all",
            "application",
            "sandbox-tester",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    if completed.returncode not in {0, 1}:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(combined_output)

    return "wallet_query_completed=True"


def _run_shell_logged_in_sessions_query(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_logged_in_sessions_command()
    else:
        command = _build_linux_logged_in_sessions_command()

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_logged_in_sessions_command() -> list[str]:
    script = (
        "$output = & query user 2>$null; "
        "$rows = @($output | Select-Object -Skip 1); "
        "if ($rows.Count -eq 0) { exit $LASTEXITCODE }; "
        "$active = @($rows | Where-Object { $_ -match '\\sActive\\s' }); "
        "$disconnected = @($rows | Where-Object { $_ -match '\\sDisc\\s' }); "
        "Write-Output "
        '"session_rows=$($rows.Count), '
        "active_sessions=$($active.Count), "
        'disconnected_sessions=$($disconnected.Count)"; '
        "exit 0"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_logged_in_sessions_command() -> list[str]:
    script = (
        "output=$(who 2>/dev/null); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        'if [ -z "$output" ]; then rows=0; '
        "else rows=$(printf '%s\n' \"$output\" | wc -l); fi; "
        'echo "session_rows=$rows"'
    )
    return ["sh", "-c", script]


def _build_ssh_agent_identity_command() -> list[str]:
    if platform.system() == "Windows":
        script = (
            "$keys = @(& ssh-add -L 2>$null); "
            "if ($LASTEXITCODE -ne 0) { Write-Output 'loaded_keys=0'; exit 3 }; "
            "if ($keys.Count -eq 0) { Write-Output 'loaded_keys=0'; exit 3 }; "
            'Write-Output "loaded_keys=$($keys.Count)"'
        )
        return [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ]

    script = (
        "keys=$(ssh-add -L 2>/dev/null); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then echo "loaded_keys=0"; exit 3; fi; '
        'if [ -z "$keys" ]; then echo "loaded_keys=0"; exit 3; fi; '
        'count=$(printf "%s\\n" "$keys" | sed "/^$/d" | wc -l); '
        'printf "loaded_keys=%s\\n" "$count"'
    )
    return ["sh", "-c", script]


def _build_gpg_agent_socket_query_command() -> list[str]:
    if platform.system() == "Windows":
        script = (
            "$socket = (& gpgconf --list-dirs agent-socket); "
            "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
            "if (-not $socket) { Write-Output 'agent_socket_detected=False'; exit 3 }; "
            'Write-Output "agent_socket_detected=True"'
        )
        return [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ]

    script = (
        "socket=$(gpgconf --list-dirs agent-socket); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        'if [ -z "$socket" ]; then echo "agent_socket_detected=False"; exit 3; fi; '
        'echo "agent_socket_detected=True"'
    )
    return ["sh", "-c", script]


def _query_logged_in_sessions(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _query_windows_logged_in_sessions()

    return _query_linux_logged_in_sessions()


def _query_windows_logged_in_sessions() -> str:
    sessions = _enumerate_windows_sessions()
    active_sessions = sum(
        1 for session in sessions if session.state == _WTS_CONNECTSTATE_ACTIVE
    )
    disconnected_sessions = sum(
        1 for session in sessions if session.state == _WTS_CONNECTSTATE_DISCONNECTED
    )
    user_sessions = sum(1 for session in sessions if session.has_user)

    return (
        f"session_rows={len(sessions)}, "
        f"user_sessions={user_sessions}, "
        f"active_sessions={active_sessions}, "
        f"disconnected_sessions={disconnected_sessions}"
    )


def _query_linux_logged_in_sessions() -> str:
    completed = subprocess.run(
        ["who"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(combined_output)

    rows = [line for line in completed.stdout.splitlines() if line.strip()]
    return f"session_rows={len(rows)}"


def _enumerate_windows_sessions() -> list[_WindowsSession]:
    wtsapi32 = ctypes.WinDLL("Wtsapi32", use_last_error=True)
    session_count = ctypes.c_uint32()
    session_array = ctypes.POINTER(_WTS_SESSION_INFOW)()

    try:
        if not wtsapi32.WTSEnumerateSessionsW(
            None,
            0,
            1,
            ctypes.byref(session_array),
            ctypes.byref(session_count),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        sessions: list[_WindowsSession] = []
        for index in range(session_count.value):
            session_info = session_array[index]
            username = _query_windows_session_username(
                wtsapi32,
                session_info.SessionId,
            )
            session = _WindowsSession(
                state=session_info.State,
                has_user=bool(username),
            )
            sessions.append(session)

        return sessions
    finally:
        if session_array:
            wtsapi32.WTSFreeMemory(session_array)


def _query_windows_session_username(
    wtsapi32: ctypes.WinDLL,
    session_id: int,
) -> str:
    buffer = ctypes.c_void_p()
    bytes_returned = ctypes.c_uint32()

    try:
        if not wtsapi32.WTSQuerySessionInformationW(
            None,
            session_id,
            _WTS_INFO_CLASS_USER_NAME,
            ctypes.byref(buffer),
            ctypes.byref(bytes_returned),
        ):
            return ""

        if not buffer.value:
            return ""

        return ctypes.wstring_at(buffer)
    finally:
        if buffer:
            wtsapi32.WTSFreeMemory(buffer)


def _write_read_delete_credential(
    operating_system: OperatingSystem,
    credential_name: str,
) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _write_read_delete_windows_credential(credential_name)

    return _write_read_delete_secret_tool_credential(credential_name)


def _write_lookup_delete_credential(
    operating_system: OperatingSystem,
    credential_name: str,
) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _write_lookup_delete_windows_credential(credential_name)

    return _write_lookup_delete_secret_tool_credential(credential_name)


def _write_read_delete_windows_credential(credential_name: str) -> str:
    _write_windows_credential(credential_name, _CREDENTIAL_SECRET)
    try:
        secret = _read_windows_credential(credential_name)
    finally:
        _delete_windows_credential(credential_name)

    if secret != _CREDENTIAL_SECRET:
        raise OSError("Credential store entry did not round-trip.")

    return "entry_created=True, entry_read=True, entry_deleted=True"


def _write_lookup_delete_windows_credential(credential_name: str) -> str:
    _write_windows_credential(credential_name, _CREDENTIAL_SECRET)
    try:
        secret = _read_windows_credential(credential_name)
    finally:
        _delete_windows_credential(credential_name)

    if secret != _CREDENTIAL_SECRET:
        raise OSError("Credential store lookup did not retrieve the test entry.")

    return "entry_created=True, lookup_requested=True, entry_deleted=True"


def _write_windows_credential(credential_name: str, secret: str) -> None:
    advapi32 = ctypes.WinDLL("Advapi32", use_last_error=True)
    credential_blob = secret.encode("utf-16-le")
    credential_blob_buffer = ctypes.create_string_buffer(credential_blob)
    credential = _CREDENTIALW()
    credential.Type = _CRED_TYPE_GENERIC
    credential.TargetName = ctypes.c_wchar_p(credential_name)
    credential.CredentialBlobSize = len(credential_blob)
    credential.CredentialBlob = ctypes.cast(
        credential_blob_buffer,
        ctypes.POINTER(ctypes.c_byte),
    )
    credential.Persist = _CRED_PERSIST_SESSION
    credential.UserName = ctypes.c_wchar_p("SandboxTester")

    if not advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def _read_windows_credential(credential_name: str) -> str:
    advapi32 = ctypes.WinDLL("Advapi32", use_last_error=True)
    credential_pointer = ctypes.POINTER(_CREDENTIALW)()

    try:
        if not advapi32.CredReadW(
            credential_name,
            _CRED_TYPE_GENERIC,
            0,
            ctypes.byref(credential_pointer),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        credential = credential_pointer.contents
        blob_bytes = ctypes.string_at(
            credential.CredentialBlob,
            credential.CredentialBlobSize,
        )
        return blob_bytes.decode("utf-16-le")
    finally:
        if credential_pointer:
            advapi32.CredFree(credential_pointer)


def _delete_windows_credential(credential_name: str) -> None:
    advapi32 = ctypes.WinDLL("Advapi32", use_last_error=True)
    advapi32.CredDeleteW(credential_name, _CRED_TYPE_GENERIC, 0)


def _enumerate_windows_credentials() -> list[str]:
    advapi32 = ctypes.WinDLL("Advapi32", use_last_error=True)
    credential_count = ctypes.c_uint32()
    credential_array = ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))()

    try:
        if not advapi32.CredEnumerateW(
            None,
            0,
            ctypes.byref(credential_count),
            ctypes.byref(credential_array),
        ):
            error_code = ctypes.get_last_error()
            if error_code == _ERROR_NOT_FOUND:
                return []

            raise ctypes.WinError(error_code)

        credentials: list[str] = []
        for index in range(credential_count.value):
            credential = credential_array[index].contents
            if credential.TargetName:
                credentials.append(credential.TargetName)

        return credentials
    finally:
        if credential_array:
            advapi32.CredFree(credential_array)


def _write_read_delete_secret_tool_credential(credential_name: str) -> str:
    store_command = [
        "secret-tool",
        "store",
        "--label=Sandbox Tester",
        "application",
        "sandbox-tester",
        "entry",
        credential_name,
    ]
    lookup_command = [
        "secret-tool",
        "lookup",
        "application",
        "sandbox-tester",
        "entry",
        credential_name,
    ]
    clear_command = [
        "secret-tool",
        "clear",
        "application",
        "sandbox-tester",
        "entry",
        credential_name,
    ]

    try:
        subprocess.run(
            store_command,
            input=_CREDENTIAL_SECRET,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        completed = subprocess.run(
            lookup_command,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
    finally:
        subprocess.run(
            clear_command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    if completed.stdout.strip() != _CREDENTIAL_SECRET:
        raise OSError("Credential store entry did not round-trip.")

    return "entry_created=True, entry_read=True, entry_deleted=True"


def _write_lookup_delete_secret_tool_credential(credential_name: str) -> str:
    store_command = [
        "secret-tool",
        "store",
        "--label=Sandbox Tester",
        "application",
        "sandbox-tester",
        "entry",
        credential_name,
    ]
    lookup_command = [
        "secret-tool",
        "lookup",
        "application",
        "sandbox-tester",
        "entry",
        credential_name,
    ]
    clear_command = [
        "secret-tool",
        "clear",
        "application",
        "sandbox-tester",
        "entry",
        credential_name,
    ]

    try:
        subprocess.run(
            store_command,
            input=_CREDENTIAL_SECRET,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        completed = subprocess.run(
            lookup_command,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
    finally:
        subprocess.run(
            clear_command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    if completed.stdout.strip() != _CREDENTIAL_SECRET:
        raise OSError("Credential store lookup did not retrieve the test entry.")

    return "entry_created=True, lookup_requested=True, entry_deleted=True"


def _ssh_signing_tools_are_available() -> bool:
    return (
        shutil.which("ssh-add") is not None and shutil.which("ssh-keygen") is not None
    )


def _run_shell_ssh_agent_sign_command(
    operating_system: OperatingSystem,
    allowed_directory: Path,
) -> subprocess.CompletedProcess[str]:
    challenge_path = _build_temp_file_path(allowed_directory, "ssh-challenge")
    public_key_path = _build_temp_file_path(allowed_directory, "ssh-public-key")
    signature_path = Path(f"{challenge_path}.sig")

    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_ssh_sign_command(
            challenge_path,
            public_key_path,
            signature_path,
        )
    else:
        command = _build_linux_ssh_sign_command(
            challenge_path,
            public_key_path,
            signature_path,
        )

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        challenge_path.unlink(missing_ok=True)
        public_key_path.unlink(missing_ok=True)
        signature_path.unlink(missing_ok=True)


def _build_windows_ssh_sign_command(
    challenge_path: Path,
    public_key_path: Path,
    signature_path: Path,
) -> list[str]:
    script = (
        f"$challenge = {_quote_powershell_string(challenge_path)}; "
        f"$publicKey = {_quote_powershell_string(public_key_path)}; "
        f"$signature = {_quote_powershell_string(signature_path)}; "
        "$key = (& ssh-add -L 2>$null | Select-Object -First 1); "
        "if ($LASTEXITCODE -ne 0) { Write-Output 'loaded_keys=0'; exit 3 }; "
        "if (-not $key) { Write-Output 'loaded_keys=0'; exit 3 }; "
        "Set-Content -LiteralPath $publicKey -Value $key -NoNewline; "
        "Set-Content -LiteralPath $challenge "
        "-Value 'sandbox-tester-challenge' -NoNewline; "
        "& ssh-keygen -Y sign -f $publicKey -n sandbox-tester $challenge "
        "| Out-Null; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "if (-not (Test-Path -LiteralPath $signature)) { exit 2 }; "
        "Write-Output 'loaded_keys=1, signed=True'"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_ssh_sign_command(
    challenge_path: Path,
    public_key_path: Path,
    signature_path: Path,
) -> list[str]:
    script = (
        "key=$(ssh-add -L 2>/dev/null | head -n 1 || true); "
        "if [ -z \"$key\" ]; then echo 'loaded_keys=0'; exit 3; fi; "
        f"printf '%s' \"$key\" > {_quote_shell_string(public_key_path)}; "
        "printf '%s' 'sandbox-tester-challenge' "
        f"> {_quote_shell_string(challenge_path)}; "
        "ssh-keygen -Y sign "
        f"-f {_quote_shell_string(public_key_path)} "
        f"-n sandbox-tester {_quote_shell_string(challenge_path)} >/dev/null; "
        f"test -f {_quote_shell_string(signature_path)} || exit 2; "
        "echo 'loaded_keys=1, signed=True'"
    )
    return ["sh", "-c", script]


def _sign_challenge_with_paramiko_agent() -> str:
    paramiko = cast(Any, importlib.import_module("paramiko"))

    agent = paramiko.Agent()
    try:
        keys = agent.get_keys()
        if not keys:
            raise LookupError("No SSH agent identities were loaded.")

        key = keys[0]
        signature = key.sign_ssh_data(b"sandbox-tester-challenge")
        if len(signature.asbytes()) == 0:
            raise OSError("SSH agent returned an empty signature.")

        return f"loaded_keys={len(keys)}, signed=True"
    finally:
        agent.close()


def _gpg_agent_tools_are_available() -> bool:
    return (
        shutil.which("gpgconf") is not None
        and shutil.which("gpg-connect-agent") is not None
    )


def _run_shell_gpg_agent_command() -> subprocess.CompletedProcess[str]:
    if platform.system() == "Windows":
        command = _build_windows_gpg_agent_command()
    else:
        command = _build_linux_gpg_agent_command()

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_gpg_agent_command() -> list[str]:
    script = (
        "$socket = (& gpgconf --list-dirs agent-socket); "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status }; "
        "if (-not $socket) { Write-Output 'agent_socket_detected=False'; exit 3 }; "
        "if (-not (Test-Path -LiteralPath $socket)) { "
        "Write-Output 'agent_socket_detected=False'; exit 3; "
        "} "
        "& gpg-connect-agent /bye | Out-Null; "
        "$connectStatus = $LASTEXITCODE; "
        "if ($connectStatus -ne 0) { exit $connectStatus }; "
        "Write-Output 'agent_socket_detected=True, agent_connectable=True'"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_gpg_agent_command() -> list[str]:
    script = (
        "socket=$(gpgconf --list-dirs agent-socket); "
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        'if [ -z "$socket" ]; then '
        "echo 'agent_socket_detected=False'; exit 3; "
        "fi; "
        'if [ ! -S "$socket" ] && [ ! -e "$socket" ]; then '
        "echo 'agent_socket_detected=False'; exit 3; "
        "fi; "
        "gpg-connect-agent /bye >/dev/null; "
        "connect_status=$?; "
        'if [ "$connect_status" -ne 0 ]; then exit "$connect_status"; fi; '
        "echo 'agent_socket_detected=True, agent_connectable=True'"
    )
    return ["sh", "-c", script]


def _connect_to_gpg_agent() -> str:
    socket_path = _get_gpg_agent_socket_path()
    if not socket_path:
        raise FileNotFoundError("No GPG agent socket path was reported.")

    socket_exists = Path(socket_path).exists()
    if not socket_exists:
        raise FileNotFoundError(f"GPG agent socket was not found: {socket_path}")

    completed = subprocess.run(
        ["gpg-connect-agent", "/bye"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(combined_output)

    return "agent_socket_detected=True, agent_connectable=True"


def _get_gpg_agent_socket_path() -> str:
    completed = subprocess.run(
        ["gpgconf", "--list-dirs", "agent-socket"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(combined_output)

    return completed.stdout.strip()


def _build_temp_file_path(allowed_directory: Path, prefix: str) -> Path:
    temp_file = tempfile.NamedTemporaryFile(
        prefix=f"{prefix}-",
        dir=allowed_directory,
        delete=False,
    )
    temp_path = Path(temp_file.name)
    temp_file.close()
    temp_path.unlink(missing_ok=True)
    return temp_path


def _quote_powershell_string(value: Path | str) -> str:
    escaped_value = str(value).replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: Path | str) -> str:
    escaped_value = str(value).replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _escape_cmd_argument(value: str) -> str:
    escaped_value = value.replace("^", "^^")
    escaped_value = escaped_value.replace("&", "^&")
    escaped_value = escaped_value.replace("|", "^|")
    escaped_value = escaped_value.replace("<", "^<")
    escaped_value = escaped_value.replace(">", "^>")
    return escaped_value


def _build_credential_name() -> str:
    return f"SandboxTester-{uuid.uuid4().hex}"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_SESSION = 1
_ERROR_NOT_FOUND = 1168
_WTS_CONNECTSTATE_ACTIVE = 0
_WTS_CONNECTSTATE_DISCONNECTED = 4
_WTS_INFO_CLASS_USER_NAME = 5


@dataclass(frozen=True)
class _WindowsSession:
    state: int
    has_user: bool


class _CREDENTIAL_ATTRIBUTEW(ctypes.Structure):
    _fields_ = [
        ("Keyword", ctypes.c_wchar_p),
        ("Flags", ctypes.c_uint32),
        ("ValueSize", ctypes.c_uint32),
        ("Value", ctypes.POINTER(ctypes.c_byte)),
    ]


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
        ("TargetName", ctypes.c_wchar_p),
        ("Comment", ctypes.c_wchar_p),
        ("LastWritten", ctypes.c_uint64),
        ("CredentialBlobSize", ctypes.c_uint32),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", ctypes.c_uint32),
        ("AttributeCount", ctypes.c_uint32),
        ("Attributes", ctypes.POINTER(_CREDENTIAL_ATTRIBUTEW)),
        ("TargetAlias", ctypes.c_wchar_p),
        ("UserName", ctypes.c_wchar_p),
    ]


class _WTS_SESSION_INFOW(ctypes.Structure):
    _fields_ = [
        ("SessionId", ctypes.c_uint32),
        ("pWinStationName", ctypes.c_wchar_p),
        ("State", ctypes.c_int),
    ]
