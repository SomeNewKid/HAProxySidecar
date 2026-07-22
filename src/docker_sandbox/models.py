"""Models for Docker sandbox orchestration."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class LandlockPathRule:
    """Path rule for the container-side Landlock launcher."""

    path: str
    access: str


@dataclass(frozen=True)
class NetworkGatewayProfile:
    """Network egress gateway settings for a Docker profile."""

    image_name: str
    proxy_host: str
    proxy_port: int
    allowed_domains: tuple[str, ...] = ()
    allowed_ip_addresses: tuple[str, ...] = ()
    no_proxy_hosts: tuple[str, ...] = ()


@dataclass(frozen=True)
class NetworkDnsPolicy:
    """DNS and Docker host-name hardening for a Docker profile."""

    use_gateway_as_dns: bool = True
    fallback_dns_address: str = "127.0.0.1"
    dns_options: tuple[str, ...] = (
        "attempts:1",
        "timeout:1",
    )
    blocked_hostnames: tuple[str, ...] = (
        "host.docker.internal",
        "gateway.docker.internal",
        "kubernetes.docker.internal",
    )
    blocked_hostname_address: str = "0.0.0.0"


@dataclass(frozen=True)
class SocketMount:
    """Explicit host socket mount allowed for a Docker profile."""

    source_path: Path
    target_path: str
    readonly: bool = True


@dataclass(frozen=True)
class AgentSocketForward:
    """Explicit SSH or GPG agent socket forwarding for a Docker profile."""

    source_path: Path
    target_path: str


@dataclass(frozen=True)
class BrowserDebuggingProfile:
    """Explicit browser debugging surface allowed for a Docker profile."""

    debugging_url: str | None = None
    browser_executable: str | None = None
    existing_browser_profile: str | None = None


@dataclass(frozen=True)
class BrowserSurfaceProfile:
    """Browser hardening settings advertised to Sandbox Tester."""

    chromium_arguments: tuple[str, ...] = (
        "--disable-background-networking",
        "--disable-breakpad",
        "--disable-component-extensions-with-background-pages",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-features=AutofillServerCommunication,MediaRouter,OptimizationHints",
        "--disable-gpu",
        "--disable-hang-monitor",
        "--disable-popup-blocking",
        "--disable-prompt-on-repost",
        "--disable-sync",
        "--disable-translate",
        "--metrics-recording-only",
        "--mute-audio",
        "--no-default-browser-check",
        "--no-first-run",
        "--password-store=basic",
        "--use-mock-keychain",
    )
    allow_camera_capture: bool = False
    allow_microphone_capture: bool = False


@dataclass(frozen=True)
class EnvironmentVariablePolicy:
    """Environment variable override for a Docker profile."""

    name: str
    value: str | None


@dataclass(frozen=True)
class SeccompProfile:
    """Docker seccomp deny profile for risky syscall families."""

    denied_syscalls: tuple[str, ...] = (
        "acct",
        "add_key",
        "bpf",
        "delete_module",
        "finit_module",
        "get_mempolicy",
        "init_module",
        "ioperm",
        "iopl",
        "keyctl",
        "kcmp",
        "lookup_dcookie",
        "mbind",
        "mount",
        "move_mount",
        "name_to_handle_at",
        "nfsservctl",
        "open_by_handle_at",
        "open_tree",
        "perf_event_open",
        "personality",
        "pidfd_getfd",
        "pivot_root",
        "process_vm_readv",
        "process_vm_writev",
        "ptrace",
        "quotactl",
        "reboot",
        "request_key",
        "set_mempolicy",
        "setns",
        "syslog",
        "umount",
        "umount2",
        "unshare",
    )
    action: str = "SCMP_ACT_ERRNO"
    default_action: str = "SCMP_ACT_ALLOW"


@dataclass(frozen=True)
class DockerUlimit:
    """Docker ulimit setting for a hardening profile."""

    name: str
    soft: int
    hard: int


@dataclass(frozen=True)
class DockerSysctl:
    """Docker sysctl setting for a hardening profile."""

    name: str
    value: str


@dataclass(frozen=True)
class DockerProfile:
    """Docker image and container hardening profile."""

    name: str
    description: str
    image_name: str
    image_build_arguments: tuple[str, ...] = ()
    ipc_mode: str | None = "host"
    shm_size: str | None = None
    cgroupns_mode: str | None = "private"
    pids_limit: int | None = 512
    memory: str | None = "2g"
    memory_swap: str | None = "2g"
    cpus: str | None = "2"
    ulimits: tuple[DockerUlimit, ...] = (
        DockerUlimit("nofile", 4096, 4096),
        DockerUlimit("nproc", 512, 512),
    )
    sysctls: tuple[DockerSysctl, ...] = ()
    cap_drop: tuple[str, ...] = ("ALL",)
    cap_add: tuple[str, ...] = ()
    security_options: tuple[str, ...] = ("no-new-privileges",)
    seccomp_profile: SeccompProfile | None = SeccompProfile()
    container_run_options: tuple[str, ...] = ()
    remote_run_root: str = "/tmp/sandbox-tester"
    allowed_directory_template: str = "{remote_run_directory}/allowed"
    denied_directory_template: str = "{remote_run_directory}/denied"
    readonly_denied_mount_target: str | None = None
    landlock_rules: tuple[LandlockPathRule, ...] = ()
    network_gateway: NetworkGatewayProfile | None = None
    network_dns_policy: NetworkDnsPolicy | None = NetworkDnsPolicy()
    socket_mounts: tuple[SocketMount, ...] = ()
    ssh_agent_socket: AgentSocketForward | None = None
    gpg_agent_socket: AgentSocketForward | None = None
    allow_desktop_automation_channel: bool = False
    remove_desktop_automation_tools: bool = False
    readonly_persistence_directories: tuple[str, ...] = ()
    browser_debugging: BrowserDebuggingProfile | None = None
    browser_surface: BrowserSurfaceProfile | None = BrowserSurfaceProfile()
    environment: tuple[EnvironmentVariablePolicy, ...] = ()
    denied_executables: tuple[str, ...] = ()
    denied_executable_paths: tuple[str, ...] = (
        "/opt/sandbox-agent/.venv/bin/pip",
        "/opt/sandbox-agent/.venv/bin/pip3",
        "/usr/local/bin/pip",
        "/usr/local/bin/pip3",
        "/usr/bin/apt",
        "/usr/bin/apt-get",
        "/usr/bin/bash",
        "/usr/bin/busctl",
        "/usr/bin/dbus-send",
        "/usr/bin/dpkg",
        "/usr/bin/dpkg-query",
        "/usr/bin/findmnt",
        "/usr/bin/git",
        "/usr/bin/gpg",
        "/usr/bin/gpg-connect-agent",
        "/usr/bin/gpgconf",
        "/usr/bin/journalctl",
        "/usr/bin/loginctl",
        "/usr/bin/mount",
        "/usr/bin/nice",
        "/usr/bin/nohup",
        "/usr/bin/nsenter",
        "/usr/bin/perl",
        "/usr/bin/renice",
        "/usr/bin/scp",
        "/usr/bin/sftp",
        "/usr/bin/setsid",
        "/usr/bin/ssh",
        "/usr/bin/ssh-add",
        "/usr/bin/su",
        "/usr/bin/systemd-run",
        "/usr/bin/systemctl",
        "/usr/bin/umount",
        "/usr/bin/unshare",
        "/usr/sbin/service",
    )


class DockerImageStatus(StrEnum):
    """Result status for a Docker sandbox image request."""

    EXISTS = "exists"
    CREATED = "created"
    BUILD_FAILED = "build_failed"
    DOCKER_MISSING = "docker_missing"
    DOCKERFILE_MISSING = "dockerfile_missing"


class SandboxRunTarget(StrEnum):
    """Workload to execute inside the Docker sandbox."""

    AGENT = "sandbox_agent"
    TESTER = "sandbox_tester"


@dataclass(frozen=True)
class DockerConfiguration:
    """Configuration for creating Docker sandbox images."""

    base_directory: Path
    dockerfile_path: Path
    build_context: Path
    guest_user: str
    profile: DockerProfile
    generated_dockerfile: str | None = None
    resolved_spec: dict[str, object] | None = None
    environment_variables: tuple[tuple[str, str], ...] = ()
    local_environment_variable_names: frozenset[str] = frozenset()
    run_target: SandboxRunTarget = SandboxRunTarget.AGENT
    enabled_capabilities: frozenset[str] = frozenset()
    mcp_sidecar_tools: tuple[str, ...] = ()
    mcp_sidecar_resources: tuple[str, ...] = ()
    ollama_models: tuple[str, ...] = ()
    ollama_image_name: str | None = None


@dataclass(frozen=True)
class DockerImageResult:
    """Result of ensuring the Docker sandbox image exists."""

    status: DockerImageStatus
    image_name: str
    dockerfile_path: Path
    command: list[str] | None = None


@dataclass(frozen=True)
class DockerRunResult:
    """Result of running Sandbox Tester in a disposable Docker container."""

    image_name: str
    profile_name: str
    container_name: str
    run_directory: Path
    command: list[str]
    remove_command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    network_name: str | None = None
    gateway_container_name: str | None = None
    gateway_ip_address: str | None = None
    gateway_commands: list[list[str]] | None = None
    gateway_cleanup_commands: list[list[str]] | None = None
    mcp_sidecar_container_name: str | None = None
    mcp_sidecar_commands: list[list[str]] | None = None
    mcp_sidecar_cleanup_commands: list[list[str]] | None = None
    jina_reader_container_name: str | None = None
    jina_reader_commands: list[list[str]] | None = None
    jina_reader_cleanup_commands: list[list[str]] | None = None
    code_sidecar_container_name: str | None = None
    code_sidecar_commands: list[list[str]] | None = None
    code_sidecar_cleanup_commands: list[list[str]] | None = None
    ollama_sidecar_container_name: str | None = None
    ollama_sidecar_commands: list[list[str]] | None = None
    ollama_sidecar_cleanup_commands: list[list[str]] | None = None

    def remove_container(self) -> None:
        """Remove disposable Docker resources for this run."""
        import subprocess

        subprocess.run(
            self.remove_command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self.gateway_cleanup_commands is None:
            return

        cleanup_commands = []
        if self.mcp_sidecar_cleanup_commands is not None:
            cleanup_commands.extend(self.mcp_sidecar_cleanup_commands)
        if self.jina_reader_cleanup_commands is not None:
            cleanup_commands.extend(self.jina_reader_cleanup_commands)
        if self.code_sidecar_cleanup_commands is not None:
            cleanup_commands.extend(self.code_sidecar_cleanup_commands)
        if self.ollama_sidecar_cleanup_commands is not None:
            cleanup_commands.extend(self.ollama_sidecar_cleanup_commands)
        cleanup_commands.extend(self.gateway_cleanup_commands)

        for command in cleanup_commands:
            subprocess.run(
                command,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
