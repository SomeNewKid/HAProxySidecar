"""Declarative sandbox specification support."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .models import (
    BrowserSurfaceProfile,
    DockerProfile,
    DockerUlimit,
    EnvironmentVariablePolicy,
    LandlockPathRule,
    NetworkDnsPolicy,
    NetworkGatewayProfile,
)
from .profiles import MINIMAL_PROFILE_NAME, get_docker_profile

_IMAGE_REPOSITORY = "sandbox-agent/sandbox-agent"
_OLLAMA_IMAGE_REPOSITORY = "sandbox-agent/ollama-sidecar"
_SUPPORTED_SCHEMA_VERSION = 1
_NETWORK_CAPABILITY = "network"
_MCP_CLIENT_CAPABILITY = "mcp_client"
_JINA_READER_CAPABILITY = "jina_reader"
_CODE_EXECUTION_CAPABILITY = "code_execution"
_OLLAMA_CAPABILITY = "ollama"
_OPENAI_CAPABILITY = "openai"
_OPENAI_AGENTS_CAPABILITY = "openai_agents"
_ANTHROPIC_CLAUDE_CAPABILITY = "anthropic_claude"
_ANTHROPIC_PYTHON_CAPABILITY = "anthropic_python"
_BEEAI_CAPABILITY = "ibm_beeai"
_GOOGLE_ADK_CAPABILITY = "google_adk"
_LANGCHAIN_CAPABILITY = "langchain"
_LANGGRAPH_CAPABILITY = "langgraph"
_MICROSOFT_AGENT_CAPABILITY = "microsoft_agent"
_CREWAI_CAPABILITY = "crewai"
_OTTO_AGENT_CAPABILITY = "otto_agent"
_PLAYWRIGHT_CHROMIUM_CAPABILITY = "playwright_chromium"
_SHELL_ACCESS_CAPABILITY = "shell_access"
_RUN_PYTHON_SCRIPT_TOOL = "run_python_script"
_SUPPORTED_KEYS = {
    "schema_version",
    "capabilities",
    "environment_variables",
    "mcp_sidecar",
    "ollama_sidecar",
    "squid_proxy",
}
_MCP_SIDECAR_KEYS = {
    "tools",
    "resources",
}
_SQUID_PROXY_KEYS = {
    "allowed_domains",
    "allowed_ip_addresses",
}
_OLLAMA_SIDECAR_KEYS = {
    "models",
}
_SUPPORTED_CAPABILITIES = {
    _NETWORK_CAPABILITY,
    _MCP_CLIENT_CAPABILITY,
    _JINA_READER_CAPABILITY,
    _CODE_EXECUTION_CAPABILITY,
    _OLLAMA_CAPABILITY,
    _OPENAI_CAPABILITY,
    _OPENAI_AGENTS_CAPABILITY,
    _ANTHROPIC_CLAUDE_CAPABILITY,
    _ANTHROPIC_PYTHON_CAPABILITY,
    _BEEAI_CAPABILITY,
    _GOOGLE_ADK_CAPABILITY,
    _LANGCHAIN_CAPABILITY,
    _LANGGRAPH_CAPABILITY,
    _MICROSOFT_AGENT_CAPABILITY,
    _CREWAI_CAPABILITY,
    _OTTO_AGENT_CAPABILITY,
    _PLAYWRIGHT_CHROMIUM_CAPABILITY,
    _SHELL_ACCESS_CAPABILITY,
}
_HASH_LENGTH = 16
_MCP_PACKAGE = "mcp==1.28.1"
_OPENAI_PACKAGE = "openai==2.45.0"
_OPENAI_AGENTS_PACKAGE = "openai-agents==0.18.2"
_CLAUDE_AGENT_SDK_PACKAGE = "claude-agent-sdk==0.2.120"
_ANTHROPIC_PACKAGE = "anthropic==0.116.0"
_BEEAI_PACKAGE = "beeai-framework==0.1.81"
_GOOGLE_ADK_PACKAGE = "google-adk==2.5.0"
_LANGCHAIN_PACKAGE = "langchain==1.3.14"
_LANGCHAIN_OPENAI_PACKAGE = "langchain-openai==1.3.5"
_LANGGRAPH_PACKAGE = "langgraph==1.2.9"
_MICROSOFT_AGENT_PACKAGE = "agent-framework==1.11.0"
_CREWAI_PACKAGE = "crewai==1.15.3"
_LITELLM_PROXY_PACKAGE = "'litellm[proxy]==1.92.0'"
_PLAYWRIGHT_PACKAGE = "playwright==1.61.0"
_CREWAI_WRITABLE_TMPFS_OPTIONS = (
    "/tmp/sandbox-home:rw,nosuid,nodev,noexec,size=64m,uid=1000,gid=1000,mode=700",
    "/tmp/sandbox-cache:rw,nosuid,nodev,noexec,size=64m,uid=1000,gid=1000,mode=700",
    "/tmp/sandbox-config:rw,nosuid,nodev,noexec,size=64m,uid=1000,gid=1000,mode=700",
    "/tmp/sandbox-runtime:rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=700",
)
_PROBE_PACKAGES = (
    "paramiko==5.0.0",
    "pillow==12.3.0",
    "pymysql==1.2.0",
)
_PLAYWRIGHT_BROWSERS_PATH = "/ms-playwright"
_OPENAI_API_KEY_ENVIRONMENT_VARIABLE = "OPENAI_API_KEY"
_ANTHROPIC_API_KEY_ENVIRONMENT_VARIABLE = "ANTHROPIC_API_KEY"
_PROCESS_SPAWN_POLICY_ENVIRONMENT_VARIABLE = "SANDBOX_DENY_PROCESS_SPAWN"
_OPENAI_ALLOWED_DOMAIN = ".openai.com"
_ANTHROPIC_ALLOWED_DOMAIN = ".anthropic.com"
_GATEWAY_IMAGE_NAME = "ubuntu/squid:latest"
_GATEWAY_PROXY_HOST = "egress-gateway"
_GATEWAY_PROXY_PORT = 3128
_NO_PROXY_HOSTS = (
    "127.0.0.1",
    "localhost",
    "169.254.169.254",
    "metadata.google.internal",
)
_BLOCKED_HOSTNAMES = (
    "host.docker.internal",
    "gateway.docker.internal",
    "kubernetes.docker.internal",
    "metadata.google.internal",
)


@dataclass(frozen=True)
class SandboxSpec:
    """Normalized declarative description of the hosted workload."""

    schema_version: int
    capabilities: tuple[str, ...] = ()
    allowed_domains: tuple[str, ...] = ()
    allowed_ip_addresses: tuple[str, ...] = ()
    environment_variables: tuple[SandboxEnvironmentVariable, ...] = ()
    mcp_sidecar_tools: tuple[str, ...] = ()
    mcp_sidecar_resources: tuple[str, ...] = ()
    ollama_models: tuple[str, ...] = ()

    @property
    def image_tag(self) -> str:
        return f"{self.schema_version}-{self.agent_image_hash}"

    @property
    def image_name(self) -> str:
        return f"{_IMAGE_REPOSITORY}:{self.image_tag}"

    @property
    def ollama_image_tag(self) -> str | None:
        """Return the hash tag for the Ollama sidecar image when configured."""
        if not self.ollama_models:
            return None

        return f"{self.schema_version}-{self.ollama_image_hash}"

    @property
    def ollama_image_name(self) -> str | None:
        """Return the Ollama sidecar image name when configured."""
        tag = self.ollama_image_tag
        if tag is None:
            return None

        return f"{_OLLAMA_IMAGE_REPOSITORY}:{tag}"

    @property
    def normalized_hash(self) -> str:
        return self.agent_image_hash

    @property
    def agent_image_hash(self) -> str:
        digest = hashlib.sha256(self.normalized_json.encode("utf-8")).hexdigest()
        return digest[:_HASH_LENGTH]

    @property
    def ollama_image_hash(self) -> str:
        """Return the stable hash for the Ollama sidecar configuration."""
        digest = hashlib.sha256(self.ollama_normalized_json.encode("utf-8")).hexdigest()
        return digest[:_HASH_LENGTH]

    @property
    def normalized_json(self) -> str:
        return json.dumps(
            self.to_agent_image_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def ollama_normalized_json(self) -> str:
        """Return the normalized Ollama sidecar configuration as JSON."""
        return json.dumps(
            self.to_ollama_image_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capabilities": list(self.capabilities),
            "environment_variables": [
                variable.to_dict()
                for variable in sorted(
                    self.environment_variables,
                    key=lambda variable: variable.name,
                )
            ],
            "squid_proxy": {
                "allowed_domains": list(self.allowed_domains),
                "allowed_ip_addresses": list(self.allowed_ip_addresses),
            },
            "mcp_sidecar": {
                "tools": list(self.mcp_sidecar_tools),
                "resources": list(self.mcp_sidecar_resources),
            },
            "ollama_sidecar": {
                "models": list(self.ollama_models),
            },
        }

    def to_agent_image_dict(self) -> dict[str, object]:
        """Return normalized data that affects only the agent container image."""
        data = self.to_dict()
        capabilities = [
            capability
            for capability in self.capabilities
            if capability != _OLLAMA_CAPABILITY
        ]
        data["capabilities"] = capabilities
        data.pop("ollama_sidecar")
        return data

    def to_ollama_image_dict(self) -> dict[str, object]:
        """Return normalized data that affects only the Ollama sidecar image."""
        return {
            "schema_version": self.schema_version,
            "ollama_sidecar": {
                "models": list(self.ollama_models),
            },
        }

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True)
class SandboxEnvironmentVariable:
    """Environment variable declaration from the sandbox spec."""

    name: str
    value: str | None = None
    from_host: bool = False

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"name": self.name}
        if self.from_host:
            data["from_host"] = True
        else:
            data["value"] = self.value if self.value is not None else ""
        return data


def load_sandbox_spec(path: Path) -> SandboxSpec:
    """Load and validate a sandbox spec TOML file."""
    if not path.exists():
        raise ValueError(f"Sandbox spec was not found: {path}")

    with path.open("rb") as file:
        data = tomllib.load(file)

    unknown_keys = set(data) - _SUPPORTED_KEYS
    if unknown_keys:
        names = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unsupported sandbox spec key: {names}")

    schema_version = data.get("schema_version", _SUPPORTED_SCHEMA_VERSION)
    if schema_version != _SUPPORTED_SCHEMA_VERSION:
        raise ValueError(f"Unsupported sandbox spec schema_version: {schema_version}")

    capabilities = _read_string_tuple(data, "capabilities")
    unsupported_capabilities = set(capabilities) - _SUPPORTED_CAPABILITIES
    if unsupported_capabilities:
        names = ", ".join(sorted(unsupported_capabilities))
        raise ValueError(f"Unsupported sandbox capability: {names}")

    allowed_domains, allowed_ip_addresses = _read_squid_proxy(data)
    environment_variables = _read_environment_variables(data)
    mcp_sidecar_tools, mcp_sidecar_resources = _read_mcp_sidecar(data)
    ollama_models = _read_ollama_sidecar(data, capabilities)
    _validate_network_settings(capabilities, allowed_domains, allowed_ip_addresses)
    _validate_mcp_sidecar_settings(capabilities, mcp_sidecar_tools)

    return SandboxSpec(
        schema_version=schema_version,
        capabilities=capabilities,
        allowed_domains=allowed_domains,
        allowed_ip_addresses=allowed_ip_addresses,
        environment_variables=environment_variables,
        mcp_sidecar_tools=mcp_sidecar_tools,
        mcp_sidecar_resources=mcp_sidecar_resources,
        ollama_models=ollama_models,
    )


def resolve_ollama_image_name(models: tuple[str, ...]) -> str:
    """Return the deterministic Ollama sidecar image name for model names."""
    normalized_models = _normalize_ollama_models(models)
    spec = SandboxSpec(
        schema_version=_SUPPORTED_SCHEMA_VERSION,
        capabilities=(_OLLAMA_CAPABILITY,),
        ollama_models=normalized_models,
    )
    image_name = spec.ollama_image_name
    if image_name is None:
        raise ValueError("Ollama sidecar image requires at least one model.")

    return image_name


def resolve_profile(spec: SandboxSpec) -> DockerProfile:
    """Resolve a low-level Docker profile from a high-level sandbox spec."""
    minimal_profile = get_docker_profile(MINIMAL_PROFILE_NAME)
    network_gateway = None
    network_dns_policy = None
    container_run_options = minimal_profile.container_run_options
    environment = minimal_profile.environment
    landlock_rules = minimal_profile.landlock_rules
    pids_limit = minimal_profile.pids_limit
    memory = minimal_profile.memory
    memory_swap = minimal_profile.memory_swap
    shm_size = minimal_profile.shm_size
    ulimits = minimal_profile.ulimits
    browser_surface = minimal_profile.browser_surface
    if spec.has_capability(_NETWORK_CAPABILITY):
        network_gateway = NetworkGatewayProfile(
            image_name=_GATEWAY_IMAGE_NAME,
            proxy_host=_GATEWAY_PROXY_HOST,
            proxy_port=_GATEWAY_PROXY_PORT,
            allowed_domains=_resolve_allowed_domains(spec),
            allowed_ip_addresses=spec.allowed_ip_addresses,
            no_proxy_hosts=_NO_PROXY_HOSTS,
        )
        network_dns_policy = NetworkDnsPolicy(blocked_hostnames=_BLOCKED_HOSTNAMES)
        container_run_options = _without_docker_network_none(container_run_options)

    if _has_openai_family_capability(spec):
        environment = _without_environment_policy(
            environment,
            _OPENAI_API_KEY_ENVIRONMENT_VARIABLE,
        )
    if _has_anthropic_family_capability(spec):
        environment = _without_environment_policy(
            environment,
            _ANTHROPIC_API_KEY_ENVIRONMENT_VARIABLE,
        )

    if spec.has_capability(_SHELL_ACCESS_CAPABILITY) or spec.has_capability(
        _ANTHROPIC_CLAUDE_CAPABILITY
    ):
        environment = _replace_environment_policy(
            environment,
            _PROCESS_SPAWN_POLICY_ENVIRONMENT_VARIABLE,
            "0",
        )

    if spec.has_capability(_CREWAI_CAPABILITY):
        environment = _append_environment_policy(
            environment,
            "CREWAI_TRACING_ENABLED",
            "false",
        )
        environment = _append_environment_policy(
            environment,
            "OTEL_SDK_DISABLED",
            "true",
        )
        for tmpfs_option in _CREWAI_WRITABLE_TMPFS_OPTIONS:
            container_run_options = _append_tmpfs_option(
                container_run_options,
                tmpfs_option,
            )

    if spec.has_capability(_PLAYWRIGHT_CHROMIUM_CAPABILITY):
        browser_surface = BrowserSurfaceProfile()
        environment = _append_environment_policy(
            environment,
            "PLAYWRIGHT_BROWSERS_PATH",
            _PLAYWRIGHT_BROWSERS_PATH,
        )
        landlock_rules = _append_landlock_rule(
            landlock_rules,
            _PLAYWRIGHT_BROWSERS_PATH,
            "rx",
        )
        container_run_options = _replace_tmpfs_option(
            container_run_options,
            "/tmp",
            "/tmp:rw,nosuid,nodev,noexec,size=512m",
        )
        container_run_options = _replace_tmpfs_option(
            container_run_options,
            "/sandbox-work",
            "/sandbox-work:rw,nosuid,nodev,noexec,size=128m",
        )
        pids_limit = 512
        memory = "2g"
        memory_swap = "2g"
        shm_size = "1g"
        ulimits = (
            DockerUlimit("nofile", 4096, 4096),
            DockerUlimit("nproc", 512, 512),
            DockerUlimit("fsize", 52428800, 52428800),
        )

    return replace(
        minimal_profile,
        name=f"sandbox-spec-{spec.image_tag}",
        description="Generated hardened profile for the sandbox spec.",
        image_name=spec.image_name,
        image_build_arguments=(),
        container_run_options=container_run_options,
        network_gateway=network_gateway,
        network_dns_policy=network_dns_policy,
        environment=environment,
        landlock_rules=landlock_rules,
        pids_limit=pids_limit,
        memory=memory,
        memory_swap=memory_swap,
        shm_size=shm_size,
        ulimits=ulimits,
        browser_surface=browser_surface,
    )


def generate_dockerfile(
    spec: SandboxSpec,
    include_probe_dependencies: bool = False,
) -> str:
    """Generate the Dockerfile needed by the sandbox spec."""
    package_install_command = _build_python_package_install_command(
        spec,
        include_probe_dependencies=include_probe_dependencies,
    )
    return f"""FROM python:3.12-slim

WORKDIR /opt/sandbox-agent

RUN useradd --create-home --shell /usr/sbin/nologin sandbox

COPY src/docker_sandbox/dockerfile/runtime_sitecustomize.py \\
    /tmp/runtime_sitecustomize.py
COPY src/docker_sandbox/dockerfile/remove_python_packaging.py \\
    /tmp/remove_python_packaging.py
ENV PLAYWRIGHT_BROWSERS_PATH={_PLAYWRIGHT_BROWSERS_PATH}
{package_install_command}

RUN rm -f \\
        /usr/local/bin/pip \\
        /usr/local/bin/pip3 \\
        /usr/local/bin/pip3.* \\
        /usr/local/bin/wheel \\
        /usr/bin/apt \\
        /usr/bin/apt-get \\
        /usr/bin/bash \\
        /usr/bin/busctl \\
        /usr/bin/dbus-send \\
        /usr/bin/dpkg \\
        /usr/bin/dpkg-query \\
        /usr/bin/findmnt \\
        /usr/bin/git \\
        /usr/bin/gpg \\
        /usr/bin/gpg-connect-agent \\
        /usr/bin/gpgconf \\
        /usr/bin/journalctl \\
        /usr/bin/loginctl \\
        /usr/bin/mount \\
        /usr/bin/nice \\
        /usr/bin/nohup \\
        /usr/bin/nsenter \\
        /usr/bin/perl \\
        /usr/bin/renice \\
        /usr/bin/scp \\
        /usr/bin/sftp \\
        /usr/bin/setsid \\
        /usr/bin/ssh \\
        /usr/bin/ssh-add \\
        /usr/bin/su \\
        /usr/bin/systemd-run \\
        /usr/bin/systemctl \\
        /usr/bin/umount \\
        /usr/bin/unshare \\
        /usr/sbin/service \\
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

RUN python /tmp/remove_python_packaging.py \\
    && rm -f \\
        /usr/local/bin/pip \\
        /usr/local/bin/pip3 \\
        /usr/local/bin/pip3.* \\
        /usr/local/bin/wheel \\
        /usr/bin/pip \\
        /usr/bin/pip3 \\
        /usr/bin/pip3.* \\
        /usr/bin/wheel

RUN rm -f \\
        /usr/bin/gdbus \\
        /usr/bin/qdbus \\
        /usr/bin/wmctrl \\
        /usr/bin/xdotool \\
    && rm -rf \\
        /var/cache/apt \\
        /var/lib/apt \\
        /var/lib/dpkg \\
        /var/log/apt
"""


def resolved_profile_data(profile: DockerProfile) -> dict[str, Any]:
    """Convert a resolved profile to JSON-safe diagnostic data."""
    return _json_safe(asdict(profile))


def _read_string_tuple(data: dict[str, object], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Sandbox spec key must be a list of strings: {key}")
    return tuple(value)


def resolve_environment_variables(
    spec: SandboxSpec,
) -> tuple[tuple[str, str], ...]:
    """Return profile-style environment variable declarations."""
    variables: list[tuple[str, str]] = []
    variable_names = {variable.name for variable in spec.environment_variables}
    for variable in spec.environment_variables:
        if variable.from_host:
            variables.append((variable.name, "[local]"))
            continue

        variables.append((variable.name, variable.value or ""))

    if (
        _has_openai_family_capability(spec)
        and _OPENAI_API_KEY_ENVIRONMENT_VARIABLE not in variable_names
    ):
        variables.append((_OPENAI_API_KEY_ENVIRONMENT_VARIABLE, "[local]"))
    if (
        _has_anthropic_family_capability(spec)
        and _ANTHROPIC_API_KEY_ENVIRONMENT_VARIABLE not in variable_names
    ):
        variables.append((_ANTHROPIC_API_KEY_ENVIRONMENT_VARIABLE, "[local]"))

    return tuple(variables)


def resolve_local_environment_variable_names(spec: SandboxSpec) -> frozenset[str]:
    """Return environment variable names copied from the host."""
    names = {
        variable.name for variable in spec.environment_variables if variable.from_host
    }
    if _has_openai_family_capability(spec):
        names.add(_OPENAI_API_KEY_ENVIRONMENT_VARIABLE)
    if _has_anthropic_family_capability(spec):
        names.add(_ANTHROPIC_API_KEY_ENVIRONMENT_VARIABLE)
    return frozenset(names)


def _read_environment_variables(
    data: dict[str, object],
) -> tuple[SandboxEnvironmentVariable, ...]:
    entries = data.get("environment_variables", [])
    if not isinstance(entries, list):
        raise ValueError("environment_variables must be an array of tables.")

    variables = []
    names = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("environment_variables entries must be tables.")

        variable = _read_environment_variable(entry)
        if variable.name in names:
            raise ValueError(f"Duplicate environment variable: {variable.name}")

        names.add(variable.name)
        variables.append(variable)

    return tuple(variables)


def _read_mcp_sidecar(
    data: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    value = data.get("mcp_sidecar", {})
    if not isinstance(value, dict):
        raise ValueError("mcp_sidecar must be a table.")

    unknown_keys = set(value) - _MCP_SIDECAR_KEYS
    if unknown_keys:
        names = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unsupported mcp_sidecar key: {names}")

    tools = _read_string_tuple(value, "tools")
    resources = _read_string_tuple(value, "resources")
    return tools, resources


def _read_ollama_sidecar(
    data: dict[str, object],
    capabilities: tuple[str, ...],
) -> tuple[str, ...]:
    value = data.get("ollama_sidecar")
    has_ollama_capability = _OLLAMA_CAPABILITY in capabilities
    if value is None:
        if has_ollama_capability:
            raise ValueError("The ollama capability requires [ollama_sidecar].")

        return ()

    if not isinstance(value, dict):
        raise ValueError("ollama_sidecar must be a table.")

    unknown_keys = set(value) - _OLLAMA_SIDECAR_KEYS
    if unknown_keys:
        names = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unsupported ollama_sidecar key: {names}")

    models = _read_string_tuple(value, "models")
    if not has_ollama_capability:
        if models:
            raise ValueError("[ollama_sidecar].models requires the ollama capability.")

        return ()

    if not models:
        raise ValueError("The ollama capability requires [ollama_sidecar].models.")

    return _normalize_ollama_models(models)


def _read_squid_proxy(
    data: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    value = data.get("squid_proxy", {})
    if not isinstance(value, dict):
        raise ValueError("squid_proxy must be a table.")

    unknown_keys = set(value) - _SQUID_PROXY_KEYS
    if unknown_keys:
        names = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unsupported squid_proxy key: {names}")

    allowed_domains = _read_string_tuple(value, "allowed_domains")
    allowed_ip_addresses = _read_string_tuple(value, "allowed_ip_addresses")
    return allowed_domains, allowed_ip_addresses


def _read_environment_variable(
    entry: dict[str, object],
) -> SandboxEnvironmentVariable:
    allowed_keys = {"name", "value", "from_host"}
    unknown_keys = set(entry) - allowed_keys
    if unknown_keys:
        names = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unsupported environment variable key: {names}")

    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("environment_variables entries require a non-empty name.")

    has_value = "value" in entry
    has_from_host = "from_host" in entry
    if has_value == has_from_host:
        raise ValueError(
            "environment_variables entries require exactly one of value or from_host."
        )

    if has_value:
        value = entry["value"]
        if not isinstance(value, str):
            raise ValueError("environment_variables value must be a string.")
        return SandboxEnvironmentVariable(name=name, value=value)

    from_host = entry["from_host"]
    if from_host is not True:
        raise ValueError("environment_variables from_host must be true.")

    return SandboxEnvironmentVariable(name=name, from_host=True)


def _validate_network_settings(
    capabilities: tuple[str, ...],
    allowed_domains: tuple[str, ...],
    allowed_ip_addresses: tuple[str, ...],
) -> None:
    has_network = _NETWORK_CAPABILITY in capabilities
    openai_capabilities = {
        _OPENAI_CAPABILITY,
        _OPENAI_AGENTS_CAPABILITY,
        _BEEAI_CAPABILITY,
        _GOOGLE_ADK_CAPABILITY,
        _LANGCHAIN_CAPABILITY,
        _LANGGRAPH_CAPABILITY,
        _MICROSOFT_AGENT_CAPABILITY,
        _CREWAI_CAPABILITY,
        _OTTO_AGENT_CAPABILITY,
    }.intersection(capabilities)
    if openai_capabilities and not has_network:
        names = ", ".join(sorted(openai_capabilities))
        raise ValueError(f"The {names} capability requires the network capability.")
    anthropic_capabilities = {
        _ANTHROPIC_CLAUDE_CAPABILITY,
        _ANTHROPIC_PYTHON_CAPABILITY,
    }.intersection(capabilities)
    if anthropic_capabilities and not has_network:
        names = ", ".join(sorted(anthropic_capabilities))
        raise ValueError(f"The {names} capability requires the network capability.")

    if (allowed_domains or allowed_ip_addresses) and not has_network:
        raise ValueError(
            "allowed_domains and allowed_ip_addresses require the network capability."
        )
    if _MCP_CLIENT_CAPABILITY in capabilities and not has_network:
        raise ValueError("The mcp_client capability requires the network capability.")
    if _JINA_READER_CAPABILITY in capabilities and not has_network:
        raise ValueError("The jina_reader capability requires the network capability.")
    if _OLLAMA_CAPABILITY in capabilities and not has_network:
        raise ValueError("The ollama capability requires the network capability.")

    for domain in allowed_domains:
        _validate_domain_allowlist_entry(domain)

    for ip_address in allowed_ip_addresses:
        ipaddress.ip_network(ip_address.strip().strip("[]"), strict=False)


def _validate_mcp_sidecar_settings(
    capabilities: tuple[str, ...],
    mcp_sidecar_tools: tuple[str, ...],
) -> None:
    if _RUN_PYTHON_SCRIPT_TOOL not in mcp_sidecar_tools:
        return

    if _MCP_CLIENT_CAPABILITY not in capabilities:
        raise ValueError("The run_python_script MCP tool requires mcp_client.")
    if _CODE_EXECUTION_CAPABILITY not in capabilities:
        raise ValueError("The run_python_script MCP tool requires code_execution.")


def _validate_domain_allowlist_entry(domain: str) -> None:
    normalized_domain = domain.strip().lower()
    if not normalized_domain:
        raise ValueError("allowed_domains entries must not be empty.")

    if "://" in normalized_domain or "/" in normalized_domain:
        raise ValueError(
            "allowed_domains entries must be host names, not URLs or paths."
        )


def _normalize_ollama_models(models: tuple[str, ...]) -> tuple[str, ...]:
    normalized_models = tuple(sorted(model.strip() for model in models))
    if any(not model for model in normalized_models):
        raise ValueError("[ollama_sidecar].models entries must not be empty.")

    duplicate_models = _find_duplicate_ollama_models(normalized_models)
    if duplicate_models:
        names = ", ".join(duplicate_models)
        raise ValueError(f"Duplicate Ollama model: {names}")

    return normalized_models


def _find_duplicate_ollama_models(models: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    duplicates = []
    for model in models:
        if model in seen and model not in duplicates:
            duplicates.append(model)
            continue

        seen.add(model)

    return tuple(duplicates)


def _without_docker_network_none(options: tuple[str, ...]) -> tuple[str, ...]:
    filtered_options = []
    skip_next = False
    for index, option in enumerate(options):
        if skip_next:
            skip_next = False
            continue

        if option == "--network" and index + 1 < len(options):
            if options[index + 1] == "none":
                skip_next = True
                continue

        if option == "--network=none":
            continue

        filtered_options.append(option)

    return tuple(filtered_options)


def _resolve_allowed_domains(spec: SandboxSpec) -> tuple[str, ...]:
    domains = list(spec.allowed_domains)
    if _has_openai_family_capability(spec):
        domains.append(_OPENAI_ALLOWED_DOMAIN)
    if _has_anthropic_family_capability(spec):
        domains.append(_ANTHROPIC_ALLOWED_DOMAIN)

    return tuple(dict.fromkeys(domains))


def _build_python_package_install_command(
    spec: SandboxSpec,
    include_probe_dependencies: bool = False,
) -> str:
    packages = []
    if spec.has_capability(_OPENAI_CAPABILITY):
        packages.append(_OPENAI_PACKAGE)
    if spec.has_capability(_OPENAI_AGENTS_CAPABILITY):
        packages.append(_OPENAI_AGENTS_PACKAGE)
    if spec.has_capability(_MCP_CLIENT_CAPABILITY):
        packages.append(_MCP_PACKAGE)
    if spec.has_capability(_ANTHROPIC_CLAUDE_CAPABILITY):
        packages.append(_CLAUDE_AGENT_SDK_PACKAGE)
    if spec.has_capability(_ANTHROPIC_PYTHON_CAPABILITY):
        packages.append(_ANTHROPIC_PACKAGE)
    if spec.has_capability(_BEEAI_CAPABILITY):
        packages.append(_BEEAI_PACKAGE)
        packages.append(_LITELLM_PROXY_PACKAGE)
    if spec.has_capability(_GOOGLE_ADK_CAPABILITY):
        packages.append(_GOOGLE_ADK_PACKAGE)
        packages.append(_LITELLM_PROXY_PACKAGE)
    if spec.has_capability(_LANGCHAIN_CAPABILITY):
        packages.append(_LANGCHAIN_PACKAGE)
        packages.append(_LANGCHAIN_OPENAI_PACKAGE)
    if spec.has_capability(_LANGGRAPH_CAPABILITY):
        packages.append(_LANGGRAPH_PACKAGE)
        packages.append(_LANGCHAIN_OPENAI_PACKAGE)
    if spec.has_capability(_MICROSOFT_AGENT_CAPABILITY):
        packages.append(_MICROSOFT_AGENT_PACKAGE)
    if spec.has_capability(_CREWAI_CAPABILITY):
        packages.append(_CREWAI_PACKAGE)
    if spec.has_capability(_OTTO_AGENT_CAPABILITY):
        packages.append(_OPENAI_PACKAGE)
    if spec.has_capability(_PLAYWRIGHT_CHROMIUM_CAPABILITY):
        packages.append(_PLAYWRIGHT_PACKAGE)
    if include_probe_dependencies:
        packages.extend(_PROBE_PACKAGES)

    if not packages:
        return ""

    package_arguments = " ".join(packages)
    install_command = f"\nRUN python -m pip install --no-cache-dir {package_arguments}"
    if spec.has_capability(_PLAYWRIGHT_CHROMIUM_CAPABILITY):
        install_command += (
            " \\\n    && python -m playwright install --with-deps chromium"
        )

    return f"{install_command}\n"


def _without_environment_policy(
    policies: tuple[EnvironmentVariablePolicy, ...],
    name: str,
) -> tuple[EnvironmentVariablePolicy, ...]:
    return tuple(policy for policy in policies if policy.name != name)


def _replace_environment_policy(
    policies: tuple[EnvironmentVariablePolicy, ...],
    name: str,
    value: str,
) -> tuple[EnvironmentVariablePolicy, ...]:
    return tuple(
        EnvironmentVariablePolicy(policy.name, value) if policy.name == name else policy
        for policy in policies
    )


def _append_environment_policy(
    policies: tuple[EnvironmentVariablePolicy, ...],
    name: str,
    value: str,
) -> tuple[EnvironmentVariablePolicy, ...]:
    if any(policy.name == name for policy in policies):
        return _replace_environment_policy(policies, name, value)

    return (*policies, EnvironmentVariablePolicy(name, value))


def _append_landlock_rule(
    rules: tuple[LandlockPathRule, ...],
    path: str,
    access: str,
) -> tuple[LandlockPathRule, ...]:
    if any(getattr(rule, "path", None) == path for rule in rules):
        return rules

    return (*rules, LandlockPathRule(path, access))


def _replace_tmpfs_option(
    options: tuple[str, ...],
    mount_path: str,
    replacement: str,
) -> tuple[str, ...]:
    replaced_options = []
    skip_next = False
    for index, option in enumerate(options):
        if skip_next:
            skip_next = False
            continue

        if option == "--tmpfs" and index + 1 < len(options):
            tmpfs_value = options[index + 1]
            if tmpfs_value.startswith(f"{mount_path}:"):
                replaced_options.extend(["--tmpfs", replacement])
                skip_next = True
                continue

        replaced_options.append(option)

    return tuple(replaced_options)


def _append_tmpfs_option(
    options: tuple[str, ...],
    tmpfs_option: str,
) -> tuple[str, ...]:
    if tmpfs_option in options:
        return options

    return (*options, "--tmpfs", tmpfs_option)


def _has_openai_family_capability(spec: SandboxSpec) -> bool:
    return (
        spec.has_capability(_OPENAI_CAPABILITY)
        or spec.has_capability(_OPENAI_AGENTS_CAPABILITY)
        or spec.has_capability(_BEEAI_CAPABILITY)
        or spec.has_capability(_GOOGLE_ADK_CAPABILITY)
        or spec.has_capability(_LANGCHAIN_CAPABILITY)
        or spec.has_capability(_LANGGRAPH_CAPABILITY)
        or spec.has_capability(_MICROSOFT_AGENT_CAPABILITY)
        or spec.has_capability(_CREWAI_CAPABILITY)
        or spec.has_capability(_OTTO_AGENT_CAPABILITY)
    )


def _has_anthropic_family_capability(spec: SandboxSpec) -> bool:
    return spec.has_capability(_ANTHROPIC_CLAUDE_CAPABILITY) or spec.has_capability(
        _ANTHROPIC_PYTHON_CAPABILITY
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
