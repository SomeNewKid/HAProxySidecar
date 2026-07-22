"""Testing for the Sandbox Tester."""

import json
import platform
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from .models import (
    AlternateInvocationResult,
    CapabilityGroupResult,
    CapabilityResult,
    InvocationResult,
    Outcome,
)
from .reporter import TestReporter

ALLOWED_CHILD_DIRECTORY = "allowed"
DENIED_CHILD_DIRECTORY = "denied"
HIDDEN_FILE_NAME = ".hidden"
ALLOWED_FILE_NAME = "allowed.txt"
DENIED_FILE_NAME = "denied.txt"


class OperatingSystem(StrEnum):
    WINDOWS = "Windows"
    LINUX = "Linux"


@dataclass(frozen=True)
class CapabilityContext:
    working_directory: Path
    allowed_directory: Path
    denied_directory: Path
    runtime_user_directory: Path
    runtime_temp_directory: Path
    mounted_shared_directory: Path | None
    operating_system: OperatingSystem
    allowed_domain: str | None = None
    denied_domain: str | None = None
    allowed_local_address: str | None = None
    denied_local_address: str | None = None
    allowed_localnet_address: str | None = None
    denied_localnet_address: str | None = None
    allowed_intranet_target: str | None = None
    denied_intranet_target: str | None = None
    allowed_database_address: str | None = None
    denied_database_address: str | None = None
    container_runtime_socket: str | None = None
    local_dev_server_url: str | None = None
    local_model_server_url: str | None = None
    metadata_endpoint_url: str | None = None
    dns_exfiltration_domain: str | None = None
    http_exfiltration_domain: str | None = None
    http_exfiltration_header: str | None = None
    websocket_exfiltration_url: str | None = None
    smtp_exfiltration_url: str | None = None
    ssh_agent_socket: str | None = None
    browser_debugging_url: str | None = None
    browser_executable: Path | None = None
    existing_browser_profile: Path | None = None
    browser_chromium_arguments: tuple[str, ...] = ()
    allowed_git_repository: Path | None = None
    denied_git_repository: Path | None = None
    git_remote_url: str | None = None
    output_directory: Path | None = None
    allow_camera_capture: bool = False
    allow_microphone_capture: bool = False

    @classmethod
    def from_current_environment(
        cls,
        working_directory: Path,
        allowed_directory: Path,
        denied_directory: Path,
        mounted_shared_directory: Path | None = None,
        allowed_domain: str | None = None,
        denied_domain: str | None = None,
        allowed_local_address: str | None = None,
        denied_local_address: str | None = None,
        allowed_localnet_address: str | None = None,
        denied_localnet_address: str | None = None,
        allowed_intranet_target: str | None = None,
        denied_intranet_target: str | None = None,
        allowed_database_address: str | None = None,
        denied_database_address: str | None = None,
        container_runtime_socket: str | None = None,
        local_dev_server_url: str | None = None,
        local_model_server_url: str | None = None,
        metadata_endpoint_url: str | None = None,
        dns_exfiltration_domain: str | None = None,
        http_exfiltration_domain: str | None = None,
        http_exfiltration_header: str | None = None,
        websocket_exfiltration_url: str | None = None,
        smtp_exfiltration_url: str | None = None,
        ssh_agent_socket: str | None = None,
        browser_debugging_url: str | None = None,
        browser_executable: Path | None = None,
        existing_browser_profile: Path | None = None,
        browser_chromium_arguments: tuple[str, ...] = (),
        allowed_git_repository: Path | None = None,
        denied_git_repository: Path | None = None,
        git_remote_url: str | None = None,
        output_directory: Path | None = None,
        allow_camera_capture: bool = False,
        allow_microphone_capture: bool = False,
    ) -> "CapabilityContext":
        system_name = platform.system()

        if system_name == "Windows":
            operating_system = OperatingSystem.WINDOWS
        elif system_name == "Linux":
            operating_system = OperatingSystem.LINUX
        else:
            raise RuntimeError(f"Unsupported operating system: {system_name}")

        return cls(
            working_directory=working_directory,
            allowed_directory=allowed_directory,
            denied_directory=denied_directory,
            runtime_user_directory=Path.home().resolve(),
            runtime_temp_directory=Path(tempfile.gettempdir()).resolve(),
            mounted_shared_directory=(
                mounted_shared_directory.resolve()
                if mounted_shared_directory is not None
                else None
            ),
            operating_system=operating_system,
            allowed_domain=allowed_domain,
            denied_domain=denied_domain,
            allowed_local_address=allowed_local_address,
            denied_local_address=denied_local_address,
            allowed_localnet_address=allowed_localnet_address,
            denied_localnet_address=denied_localnet_address,
            allowed_intranet_target=allowed_intranet_target,
            denied_intranet_target=denied_intranet_target,
            allowed_database_address=allowed_database_address,
            denied_database_address=denied_database_address,
            container_runtime_socket=container_runtime_socket,
            local_dev_server_url=local_dev_server_url,
            local_model_server_url=local_model_server_url,
            metadata_endpoint_url=metadata_endpoint_url,
            dns_exfiltration_domain=dns_exfiltration_domain,
            http_exfiltration_domain=http_exfiltration_domain,
            http_exfiltration_header=http_exfiltration_header,
            websocket_exfiltration_url=websocket_exfiltration_url,
            smtp_exfiltration_url=smtp_exfiltration_url,
            ssh_agent_socket=ssh_agent_socket,
            browser_debugging_url=browser_debugging_url,
            browser_executable=browser_executable,
            existing_browser_profile=existing_browser_profile,
            browser_chromium_arguments=browser_chromium_arguments,
            allowed_git_repository=(
                allowed_git_repository.resolve()
                if allowed_git_repository is not None
                else None
            ),
            denied_git_repository=(
                denied_git_repository.resolve()
                if denied_git_repository is not None
                else None
            ),
            git_remote_url=git_remote_url,
            output_directory=(
                output_directory.resolve() if output_directory is not None else None
            ),
            allow_camera_capture=allow_camera_capture,
            allow_microphone_capture=allow_microphone_capture,
        )

    def to_json_data(self) -> dict[str, Any]:
        """Convert the capability context to JSON-serializable data."""
        return {
            "working_directory": _path_to_json(self.working_directory),
            "allowed_directory": _path_to_json(self.allowed_directory),
            "denied_directory": _path_to_json(self.denied_directory),
            "runtime_user_directory": _path_to_json(self.runtime_user_directory),
            "runtime_temp_directory": _path_to_json(self.runtime_temp_directory),
            "mounted_shared_directory": _optional_path_to_json(
                self.mounted_shared_directory
            ),
            "operating_system": self.operating_system.value,
            "allowed_domain": self.allowed_domain,
            "denied_domain": self.denied_domain,
            "allowed_local_address": self.allowed_local_address,
            "denied_local_address": self.denied_local_address,
            "allowed_localnet_address": self.allowed_localnet_address,
            "denied_localnet_address": self.denied_localnet_address,
            "allowed_intranet_target": self.allowed_intranet_target,
            "denied_intranet_target": self.denied_intranet_target,
            "allowed_database_address": self.allowed_database_address,
            "denied_database_address": self.denied_database_address,
            "container_runtime_socket": self.container_runtime_socket,
            "local_dev_server_url": self.local_dev_server_url,
            "local_model_server_url": self.local_model_server_url,
            "metadata_endpoint_url": self.metadata_endpoint_url,
            "dns_exfiltration_domain": self.dns_exfiltration_domain,
            "http_exfiltration_domain": self.http_exfiltration_domain,
            "http_exfiltration_header": self.http_exfiltration_header,
            "websocket_exfiltration_url": self.websocket_exfiltration_url,
            "smtp_exfiltration_url": self.smtp_exfiltration_url,
            "ssh_agent_socket": self.ssh_agent_socket,
            "browser_debugging_url": self.browser_debugging_url,
            "browser_executable": _optional_path_to_json(self.browser_executable),
            "existing_browser_profile": _optional_path_to_json(
                self.existing_browser_profile
            ),
            "browser_chromium_arguments": list(self.browser_chromium_arguments),
            "allowed_git_repository": _optional_path_to_json(
                self.allowed_git_repository
            ),
            "denied_git_repository": _optional_path_to_json(self.denied_git_repository),
            "git_remote_url": self.git_remote_url,
            "output_directory": _optional_path_to_json(self.output_directory),
            "allow_camera_capture": self.allow_camera_capture,
            "allow_microphone_capture": self.allow_microphone_capture,
        }

    @classmethod
    def from_json_data(cls, data: dict[str, Any]) -> "CapabilityContext":
        """Create a capability context from JSON-deserialized data."""
        return cls(
            working_directory=_path_from_json(data["working_directory"]),
            allowed_directory=_path_from_json(data["allowed_directory"]),
            denied_directory=_path_from_json(data["denied_directory"]),
            runtime_user_directory=_path_from_json(data["runtime_user_directory"]),
            runtime_temp_directory=_path_from_json(data["runtime_temp_directory"]),
            mounted_shared_directory=_optional_path_from_json(
                data.get("mounted_shared_directory")
            ),
            operating_system=OperatingSystem(data["operating_system"]),
            allowed_domain=data.get("allowed_domain"),
            denied_domain=data.get("denied_domain"),
            allowed_local_address=data.get("allowed_local_address"),
            denied_local_address=data.get("denied_local_address"),
            allowed_localnet_address=data.get("allowed_localnet_address"),
            denied_localnet_address=data.get("denied_localnet_address"),
            allowed_intranet_target=data.get("allowed_intranet_target"),
            denied_intranet_target=data.get("denied_intranet_target"),
            allowed_database_address=data.get("allowed_database_address"),
            denied_database_address=data.get("denied_database_address"),
            container_runtime_socket=data.get("container_runtime_socket"),
            local_dev_server_url=data.get("local_dev_server_url"),
            local_model_server_url=data.get("local_model_server_url"),
            metadata_endpoint_url=data.get("metadata_endpoint_url"),
            dns_exfiltration_domain=data.get("dns_exfiltration_domain"),
            http_exfiltration_domain=data.get("http_exfiltration_domain"),
            http_exfiltration_header=data.get("http_exfiltration_header"),
            websocket_exfiltration_url=data.get("websocket_exfiltration_url"),
            smtp_exfiltration_url=data.get("smtp_exfiltration_url"),
            ssh_agent_socket=data.get("ssh_agent_socket"),
            browser_debugging_url=data.get("browser_debugging_url"),
            browser_executable=_optional_path_from_json(data.get("browser_executable")),
            existing_browser_profile=_optional_path_from_json(
                data.get("existing_browser_profile")
            ),
            browser_chromium_arguments=tuple(
                str(argument) for argument in data.get("browser_chromium_arguments", ())
            ),
            allowed_git_repository=_optional_path_from_json(
                data.get("allowed_git_repository")
            ),
            denied_git_repository=_optional_path_from_json(
                data.get("denied_git_repository")
            ),
            git_remote_url=data.get("git_remote_url"),
            output_directory=_optional_path_from_json(data.get("output_directory")),
            allow_camera_capture=bool(data.get("allow_camera_capture")),
            allow_microphone_capture=bool(data.get("allow_microphone_capture")),
        )


def create_allowed_directory() -> Path:
    allowed_directory = Path(tempfile.mkdtemp(prefix="sandbox-tester-")).resolve()
    allowed_child_directory = allowed_directory / ALLOWED_CHILD_DIRECTORY
    allowed_child_directory.mkdir(parents=True, exist_ok=True)
    text_file = allowed_child_directory / ALLOWED_FILE_NAME
    text_file.write_text(
        "This is a test file for the allowed directory.", encoding="utf-8"
    )
    hidden_file = allowed_child_directory / HIDDEN_FILE_NAME
    hidden_file.write_text("This is a hidden file.", encoding="utf-8")

    return allowed_directory


def create_disallowed_directory() -> Path:
    denied_directory = Path(tempfile.mkdtemp(prefix="sandbox-tester-denied-")).resolve()
    denied_child_directory = denied_directory / DENIED_CHILD_DIRECTORY
    denied_child_directory.mkdir(parents=True, exist_ok=True)
    denied_file = denied_child_directory / DENIED_FILE_NAME
    denied_file.write_text(
        "This is a test file for the denied directory.", encoding="utf-8"
    )
    hidden_file = denied_child_directory / HIDDEN_FILE_NAME
    hidden_file.write_text(
        "This is a hidden file in the denied directory.", encoding="utf-8"
    )

    return denied_directory


def delete_allowed_directory(allowed_directory: Path) -> None:
    """Delete the allowed directory and its contents."""
    _delete_directory(allowed_directory)


def delete_denied_directory(denied_directory: Path) -> None:
    """Delete the denied directory and its contents."""
    _delete_directory(denied_directory)


def write_capability_context(context: CapabilityContext, path: Path) -> None:
    """Write a capability context to a JSON file."""
    context_json = json.dumps(context.to_json_data(), indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{context_json}\n", encoding="utf-8")


def read_capability_context(path: Path) -> CapabilityContext:
    """Read a capability context from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return CapabilityContext.from_json_data(data)


def _delete_directory(directory: Path) -> None:
    if directory.exists() and directory.is_dir():
        for child in directory.iterdir():
            if child.is_file() or child.is_symlink():
                try:
                    child.unlink()
                except PermissionError:
                    pass
            elif child.is_dir():
                _delete_directory(child)
        try:
            directory.rmdir()
        except OSError:
            pass


def _path_to_json(path: Path) -> str:
    return str(path)


def _optional_path_to_json(path: Path | None) -> str | None:
    if path is None:
        return None

    return _path_to_json(path)


def _path_from_json(value: str) -> Path:
    return Path(value)


def _optional_path_from_json(value: str | None) -> Path | None:
    if value is None:
        return None

    return _path_from_json(value)


class CapabilityTest(Protocol):
    id: str
    title: str

    async def run_shell(self) -> InvocationResult: ...

    async def run_tool(self) -> InvocationResult: ...

    async def run_alternates(self) -> AlternateInvocationResult: ...


@dataclass(frozen=True)
class CapabilityGroup:
    id: str
    title: str
    tests: list[CapabilityTest]


async def run_group(
    group: CapabilityGroup,
    reporter: TestReporter,
) -> CapabilityGroupResult:
    results: list[CapabilityResult] = []

    reporter.group_started(group.id, group.title)

    for test in group.tests:
        reporter.capability_started(group.id, test.id, test.title)

        shell_result: InvocationResult = await test.run_shell()
        reporter.shell_completed(shell_result)

        tool_result: InvocationResult = await test.run_tool()
        reporter.tool_completed(tool_result)

        alternate_result: AlternateInvocationResult = await test.run_alternates()
        reporter.alternates_completed(alternate_result)

        result = CapabilityResult(
            id=test.id,
            title=test.title,
            shell=shell_result,
            tool=tool_result,
            alternates=alternate_result,
        )
        results.append(result)

    group_result = CapabilityGroupResult(
        id=group.id,
        title=group.title,
        capabilities=results,
    )

    return group_result


async def no_alternates() -> AlternateInvocationResult:
    """Return a placeholder result for tests without alternate shell attempts."""
    return AlternateInvocationResult(
        outcome=Outcome.NOT_APPLICABLE,
        summary="No alternate shell attempts are implemented for this capability.",
        attempts=[],
    )
