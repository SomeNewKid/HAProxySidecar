"""Docker sandbox hardening profile."""

from __future__ import annotations

from dataclasses import replace

from .models import (
    BrowserSurfaceProfile,
    DockerProfile,
    DockerSysctl,
    DockerUlimit,
    EnvironmentVariablePolicy,
    LandlockPathRule,
    NetworkDnsPolicy,
    NetworkGatewayProfile,
)

NO_SHELL_ACCESS_PROFILE_NAME = "no-shell-access"
NO_SHELL_ACCESS_IMAGE_NAME = "sandbox-agent/sandbox-agent"
MINIMAL_PROFILE_NAME = "minimal"
MINIMAL_IMAGE_NAME = "sandbox-agent/sandbox-agent:minimal"

_PROFILES: dict[str, DockerProfile] = {
    NO_SHELL_ACCESS_PROFILE_NAME: DockerProfile(
        name=NO_SHELL_ACCESS_PROFILE_NAME,
        description=(
            "Run Sandbox Agent with the hardened no-shell-access Docker profile."
        ),
        image_name=NO_SHELL_ACCESS_IMAGE_NAME,
        image_build_arguments=(
            "--build-arg",
            "SANDBOX_MINIMIZE_IMAGE=true",
            "--build-arg",
            "SANDBOX_REMOVE_PYTHON_PACKAGING=true",
            "--build-arg",
            "SANDBOX_REMOVE_DESKTOP_AUTOMATION=true",
            "--build-arg",
            "SANDBOX_REMOVE_PACKAGE_METADATA=true",
        ),
        ipc_mode="private",
        shm_size="1g",
        cgroupns_mode="private",
        pids_limit=512,
        memory="2g",
        memory_swap="2g",
        cpus="2",
        ulimits=(
            DockerUlimit("nofile", 4096, 4096),
            DockerUlimit("nproc", 512, 512),
            DockerUlimit("fsize", 104857600, 104857600),
        ),
        sysctls=(DockerSysctl("net.ipv4.ip_unprivileged_port_start", "1024"),),
        cap_drop=("ALL",),
        security_options=("no-new-privileges",),
        container_run_options=(
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=1g",
            "--tmpfs",
            "/sandbox-work:rw,nosuid,nodev,noexec,size=256m",
            "--tmpfs",
            "/proc/acpi:rw,nosuid,nodev,noexec,size=1k",
            "--tmpfs",
            "/sys/firmware:rw,nosuid,nodev,noexec,size=1k",
            "--env",
            "HOME=/tmp/sandbox-home",
            "--env",
            "XDG_CACHE_HOME=/tmp/sandbox-cache",
            "--env",
            "XDG_CONFIG_HOME=/tmp/sandbox-config",
            "--env",
            "XDG_RUNTIME_DIR=/tmp/sandbox-runtime",
        ),
        remote_run_root="/sandbox-work",
        allowed_directory_template="{remote_run_directory}/allowed",
        denied_directory_template="/sandbox-denied",
        readonly_denied_mount_target="/sandbox-denied",
        landlock_rules=(
            LandlockPathRule("/bin", "rx"),
            LandlockPathRule("/etc", "r"),
            LandlockPathRule("/lib", "rx"),
            LandlockPathRule("/lib64", "rx"),
            LandlockPathRule("/ms-playwright", "rx"),
            LandlockPathRule("/opt/sandbox-agent", "rx"),
            LandlockPathRule("/sbin", "rx"),
            LandlockPathRule("/usr", "rx"),
            LandlockPathRule("/var", "r"),
            LandlockPathRule("/dev", "rw"),
            LandlockPathRule("/proc", "r"),
            LandlockPathRule("/sandbox-source", "r"),
            LandlockPathRule("/sandbox-output", "rw"),
            LandlockPathRule("/sandbox-work", "rw"),
            LandlockPathRule("/tmp", "rw"),
        ),
        network_gateway=NetworkGatewayProfile(
            image_name="ubuntu/squid:latest",
            proxy_host="egress-gateway",
            proxy_port=3128,
            allowed_domains=(
                ".openai.com",
                ".example.com",
                ".github.com",
                ".gov.uk",
            ),
            no_proxy_hosts=(
                "169.254.169.254",
                "metadata.google.internal",
            ),
        ),
        network_dns_policy=NetworkDnsPolicy(
            blocked_hostnames=(
                "host.docker.internal",
                "gateway.docker.internal",
                "kubernetes.docker.internal",
                "metadata.google.internal",
            )
        ),
        readonly_persistence_directories=(
            "/tmp/sandbox-home/.config/autostart",
            "/tmp/sandbox-config/autostart",
            "/tmp/sandbox-home/.config/systemd/user",
            "/tmp/sandbox-config/systemd/user",
        ),
        browser_surface=BrowserSurfaceProfile(),
        environment=(
            EnvironmentVariablePolicy("SSH_AUTH_SOCK", None),
            EnvironmentVariablePolicy("GPG_AGENT_INFO", None),
            EnvironmentVariablePolicy("DBUS_SESSION_BUS_ADDRESS", None),
            EnvironmentVariablePolicy("DISPLAY", None),
            EnvironmentVariablePolicy("WAYLAND_DISPLAY", None),
            EnvironmentVariablePolicy("GNUPGHOME", "/tmp/sandbox-gnupg-empty"),
            EnvironmentVariablePolicy("SANDBOX_DENY_UDP", "1"),
            EnvironmentVariablePolicy("SANDBOX_DENY_METADATA_ENDPOINTS", "1"),
            EnvironmentVariablePolicy("SANDBOX_DENY_ALL_INTERFACE_BIND", "1"),
            EnvironmentVariablePolicy("SANDBOX_DENY_HARDWARE_DEVICE_ENUMERATION", "1"),
            # EnvironmentVariablePolicy("SANDBOX_DENY_PROCESS_SPAWN", "1"),
        ),
        remove_desktop_automation_tools=True,
    )
}

_PROFILES[MINIMAL_PROFILE_NAME] = replace(
    _PROFILES[NO_SHELL_ACCESS_PROFILE_NAME],
    name=MINIMAL_PROFILE_NAME,
    description="Run the minimal Sandbox Agent workload with a hardened profile.",
    image_name=MINIMAL_IMAGE_NAME,
    ipc_mode=None,
    shm_size=None,
    pids_limit=64,
    memory="128m",
    memory_swap="128m",
    cpus="1",
    ulimits=(
        DockerUlimit("nofile", 256, 256),
        DockerUlimit("nproc", 64, 64),
        DockerUlimit("fsize", 1048576, 1048576),
    ),
    container_run_options=(
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=16m",
        "--tmpfs",
        "/sandbox-work:rw,nosuid,nodev,noexec,size=1m",
        "--tmpfs",
        "/proc/acpi:rw,nosuid,nodev,noexec,size=1k",
        "--tmpfs",
        "/sys/firmware:rw,nosuid,nodev,noexec,size=1k",
        "--env",
        "HOME=/tmp/sandbox-home",
        "--env",
        "XDG_CACHE_HOME=/tmp/sandbox-cache",
        "--env",
        "XDG_CONFIG_HOME=/tmp/sandbox-config",
        "--env",
        "XDG_RUNTIME_DIR=/tmp/sandbox-runtime",
    ),
    landlock_rules=(
        LandlockPathRule("/bin", "rx"),
        LandlockPathRule("/etc", "r"),
        LandlockPathRule("/lib", "rx"),
        LandlockPathRule("/lib64", "rx"),
        LandlockPathRule("/opt/sandbox-agent", "rx"),
        LandlockPathRule("/sbin", "rx"),
        LandlockPathRule("/usr", "rx"),
        LandlockPathRule("/usr/local", "rx"),
        LandlockPathRule("/var", "r"),
        LandlockPathRule("/dev", "rw"),
        LandlockPathRule("/proc", "r"),
        LandlockPathRule("/sandbox-source", "r"),
        LandlockPathRule("/sandbox-output", "rw"),
        LandlockPathRule("/sandbox-work", "rw"),
        LandlockPathRule("/tmp", "rw"),
    ),
    network_gateway=None,
    network_dns_policy=None,
    browser_surface=None,
    environment=(
        EnvironmentVariablePolicy("OPENAI_API_KEY", None),
        EnvironmentVariablePolicy("SSH_AUTH_SOCK", None),
        EnvironmentVariablePolicy("GPG_AGENT_INFO", None),
        EnvironmentVariablePolicy("DBUS_SESSION_BUS_ADDRESS", None),
        EnvironmentVariablePolicy("DISPLAY", None),
        EnvironmentVariablePolicy("WAYLAND_DISPLAY", None),
        EnvironmentVariablePolicy("GNUPGHOME", "/tmp/sandbox-gnupg-empty"),
        EnvironmentVariablePolicy("SANDBOX_DENY_UDP", "1"),
        EnvironmentVariablePolicy("SANDBOX_DENY_METADATA_ENDPOINTS", "1"),
        EnvironmentVariablePolicy("SANDBOX_DENY_ALL_INTERFACE_BIND", "1"),
        EnvironmentVariablePolicy("SANDBOX_DENY_HARDWARE_DEVICE_ENUMERATION", "1"),
        EnvironmentVariablePolicy("SANDBOX_DENY_PROCESS_SPAWN", "1"),
    ),
)

SUPPORTED_PROFILE_NAMES = tuple(sorted(_PROFILES))


def get_docker_profile(name: str) -> DockerProfile:
    """Return the Docker hardening profile with the given name."""
    try:
        return _PROFILES[name]
    except KeyError as error:
        raise ValueError(f"Unsupported Docker sandbox profile: {name}") from error
