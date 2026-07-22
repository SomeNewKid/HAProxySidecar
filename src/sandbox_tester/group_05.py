"""Group 05: Environment variables and secrets exposure."""

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


class G05_T01:
    id = "T01"
    title = "List environment variable names"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                names = self._summarize_environment_names(completed.stdout)
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed environment variable names.",
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
                summary="Python runtime listed environment variable names.",
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
            _run_environment_alternate_attempts,
            _build_environment_name_alternate_attempts(self._operating_system),
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


class G05_T04:
    id = "T04"
    title = "Read path/search-path variable"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the path/search-path environment variable.",
                    evidence=_path_variable_evidence(completed.stdout),
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
            path_variable_name = "Path"
            if self._operating_system == OperatingSystem.LINUX:
                path_variable_name = "PATH"

            path_variable = os.environ.get(path_variable_name)
            if path_variable is None:
                return InvocationResult(
                    outcome=Outcome.DENIED,
                    summary="Path/search-path environment variable was not present.",
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read the path/search-path variable.",
                evidence=_path_variable_evidence(path_variable),
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
            _run_environment_alternate_attempts,
            _build_path_variable_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "[Environment]::GetEnvironmentVariable('Path', 'Process')",
            ]
        else:
            command = ["sh", "-c", "printf '%s' \"$PATH\""]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


_g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES = [
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "COHERE_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "HUGGINGFACE_API_TOKEN",
    "HF_TOKEN",
]


class G05_T05:
    id = "T05"
    title = "Access model/API credentials in environment/config"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g29_run_shell_ai_credential_environment_probe,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode != 0:
                return InvocationResult(
                    outcome=Outcome.DENIED,
                    summary="Shell could not inspect AI credential environment names.",
                    evidence=_g29_failure_evidence(completed, combined_output),
                )

            if combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected AI credential environment variables.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No known AI credential environment variables were present.",
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to inspect the environment.",
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
                summary="Shell AI credential environment probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell AI credential environment probe failed.",
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
            credential_names = await asyncio.to_thread(
                _g29_find_ai_credential_environment_names
            )

            if credential_names:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime detected AI credential environment variables."
                    ),
                    evidence=_g29_credential_name_evidence(credential_names),
                )

            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No known AI credential environment variables were present.",
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
                summary="Python runtime AI credential environment probe failed.",
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
            _g29_run_ai_credential_alternate_attempts,
            _g29_build_ai_credential_alternate_attempts(self._operating_system),
        )


def _g29_run_shell_ai_credential_environment_probe(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _g29_build_shell_ai_credential_environment_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _g29_build_shell_ai_credential_environment_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        names = ", ".join(
            _g29_quote_powershell_string(name)
            for name in _g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES
        )
        script = (
            f"$names = @({names}); "
            "$present = @(); "
            "foreach ($name in $names) { "
            'if (Test-Path "Env:$name") { $present += $name } '
            "} "
            "if ($present.Count -gt 0) { "
            "Write-Output ('names=' + ($present -join ',')) "
            "}"
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    checks = []
    for name in _g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES:
        quoted_name = _g29_shell_quote(name)
        checks.append(
            f"if printenv {quoted_name} >/dev/null 2>&1; "
            f"then printf '%s\\n' {quoted_name}; fi"
        )
    script = "\n".join(checks)
    script = (
        f'present=$({script}); [ -n "$present" ] && printf \'names=%s\\n\' "$present"'
    )
    return ["sh", "-c", script]


def _g29_find_ai_credential_environment_names() -> list[str]:
    return [
        name for name in _g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES if name in os.environ
    ]


@dataclass(frozen=True)
class _g29_AlternateAiCredentialAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _g29_build_ai_credential_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g29_AlternateAiCredentialAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        checks = []
        for name in _g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES:
            checks.append(f"if defined {name} echo {name}")
        names = ", ".join(
            _g29_quote_powershell_string(name)
            for name in _g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES
        )
        script = (
            f"$names = @({names}); "
            "foreach ($name in $names) { "
            'if (Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue) { '
            "Write-Output $name "
            "} "
            "}"
        )
        return [
            _g29_AlternateAiCredentialAttempt(
                id="A01",
                title="Detect AI credential environment names via cmd",
                bypass_class="ai_credential_environment_detection",
                command_family="cmd/if-defined",
                command=["cmd", "/c", " & ".join(checks)],
            ),
            _g29_AlternateAiCredentialAttempt(
                id="A02",
                title="Detect AI credential environment names via PowerShell provider",
                bypass_class="ai_credential_environment_detection",
                command_family="powershell/env",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
            ),
        ]

    pattern = "|".join(_g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES)
    script = f"env | grep -E '^({pattern})=' | sed 's/=.*//'"
    shell_checks = []
    for name in _g29_AI_CREDENTIAL_ENVIRONMENT_VARIABLES:
        quoted_name = _g29_shell_quote(name)
        shell_checks.append(
            f"eval '[ \"${{{name}+set}}\" = set ]' && printf '%s\\n' {quoted_name}"
        )
    return [
        _g29_AlternateAiCredentialAttempt(
            id="A01",
            title="Detect AI credential environment names via env grep",
            bypass_class="ai_credential_environment_detection",
            command_family="env/grep",
            command=["sh", "-c", script],
        ),
        _g29_AlternateAiCredentialAttempt(
            id="A02",
            title="Detect AI credential environment names via shell parameter checks",
            bypass_class="ai_credential_environment_detection",
            command_family="sh/parameter-expansion",
            command=["sh", "-c", "; ".join(shell_checks)],
        ),
    ]


def _g29_run_ai_credential_alternate_attempts(
    attempts: list[_g29_AlternateAiCredentialAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _g29_run_ai_credential_alternate_attempt(attempt) for attempt in attempts
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
        outcome = Outcome.NOT_APPLICABLE
        summary = "No known AI credential environment variables were present."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _g29_run_ai_credential_alternate_attempt(
    attempt: _g29_AlternateAiCredentialAttempt,
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
        if completed.returncode == 0 and combined_output:
            outcome = Outcome.ALLOWED
        elif completed.returncode == 0:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_g29_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g29_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g29_alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _g29_alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _g29_alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _g29_alternate_exception_result(attempt, Outcome.ERROR, error)


def _g29_alternate_exception_result(
    attempt: _g29_AlternateAiCredentialAttempt,
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


def _g29_credential_name_evidence(credential_names: list[str]) -> str:
    return f"names={','.join(credential_names)}"


def _g29_quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _g29_shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _g29_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G05",
        title="Environment variables and secrets exposure",
        tests=[
            G05_T01(capability_context),
            G05_T04(capability_context),
            G05_T05(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternateEnvironmentAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_environment_name_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateEnvironmentAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateEnvironmentAttempt(
                id="A01",
                title="List environment variable names via cmd set",
                bypass_class="alternate_command",
                command_family="cmd/set",
                command=[
                    "cmd",
                    "/v:on",
                    "/c",
                    "for /f tokens^=1^ delims^=^= %A in ('set') do @echo %A",
                ],
            ),
            _AlternateEnvironmentAttempt(
                id="A02",
                title="List environment variable names via PowerShell .NET",
                bypass_class="alternate_command",
                command_family="powershell/dotnet-environment",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "[Environment]::GetEnvironmentVariables('Process').Keys",
                ],
            ),
        ]

    return [
        _AlternateEnvironmentAttempt(
            id="A01",
            title="List environment variable names via printenv",
            bypass_class="alternate_command",
            command_family="printenv/sed",
            command=["sh", "-c", "printenv | sed 's/=.*//'"],
        ),
        _AlternateEnvironmentAttempt(
            id="A02",
            title="List environment variable names via bash",
            bypass_class="alternate_command",
            command_family="bash/compgen",
            command=["bash", "-c", "compgen -e"],
        ),
        _AlternateEnvironmentAttempt(
            id="A03",
            title="List environment variable names via proc environ",
            bypass_class="alternate_command",
            command_family="procfs",
            command=["sh", "-c", "tr '\\0' '\\n' < /proc/self/environ | cut -d= -f1"],
        ),
    ]


def _build_path_variable_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateEnvironmentAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateEnvironmentAttempt(
                id="A01",
                title="Read path variable via cmd expansion",
                bypass_class="alternate_command",
                command_family="cmd/echo",
                command=["cmd", "/c", "echo %PATH%"],
            ),
            _AlternateEnvironmentAttempt(
                id="A02",
                title="Read path variable via cmd path command",
                bypass_class="alternate_command",
                command_family="cmd/path",
                command=["cmd", "/c", "path"],
            ),
            _AlternateEnvironmentAttempt(
                id="A03",
                title="Read persistent path values via registry",
                bypass_class="alternate_command",
                command_family="reg",
                command=[
                    "cmd",
                    "/c",
                    (
                        'reg query "HKCU\\Environment" /v Path '
                        "& reg query "
                        '"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager'
                        '\\Environment" /v Path & exit /b 0'
                    ),
                ],
            ),
        ]

    return [
        _AlternateEnvironmentAttempt(
            id="A01",
            title="Read path variable via printenv",
            bypass_class="alternate_command",
            command_family="printenv",
            command=["printenv", "PATH"],
        ),
        _AlternateEnvironmentAttempt(
            id="A02",
            title="Read path variable via shell expansion",
            bypass_class="alternate_command",
            command_family="sh/printf",
            command=["sh", "-c", 'printf "%s" "$PATH"'],
        ),
        _AlternateEnvironmentAttempt(
            id="A03",
            title="Read path variable via proc environ",
            bypass_class="alternate_command",
            command_family="procfs",
            command=[
                "sh",
                "-c",
                ("tr '\\0' '\\n' < /proc/self/environ | sed -n 's/^PATH=//p'"),
            ],
        ),
    ]


def _run_environment_alternate_attempts(
    attempts: list[_AlternateEnvironmentAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _run_environment_alternate_attempt(attempt) for attempt in attempts
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
        outcome = Outcome.DENIED
        summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _run_environment_alternate_attempt(
    attempt: _AlternateEnvironmentAttempt,
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
    attempt: _AlternateEnvironmentAttempt,
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
        if _is_path_variable_attempt(completed.args):
            return _path_variable_evidence(combined_output)

        return combined_output[:500]

    return f"returncode={completed.returncode}"


def _is_path_variable_attempt(args: object) -> bool:
    if not isinstance(args, list):
        return False

    command_text = " ".join(str(arg).lower() for arg in args)
    return "path" in command_text


def _path_variable_evidence(value: str) -> str:
    entries = [entry for entry in value.split(os.pathsep) if entry]
    return f"path_entry_count={len(entries)}; bytes={len(value.encode())}"
