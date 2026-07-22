"""Tests for Docker MCP sidecar container orchestration."""

from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

from docker_sandbox.models import (
    DockerConfiguration,
    HAProxyConfiguration,
    NetworkGatewayProfile,
)
from docker_sandbox.profiles import MINIMAL_PROFILE_NAME, get_docker_profile
from docker_sandbox.sandbox_container import (
    _build_code_sidecar_cleanup_commands,
    _build_code_sidecar_container_name,
    _build_code_sidecar_image_build_command,
    _build_code_sidecar_image_inspect_command,
    _build_code_sidecar_run_command,
    _build_container_environment,
    _build_docker_run_command,
    _build_haproxy_sidecar_cleanup_commands,
    _build_haproxy_sidecar_container_name,
    _build_haproxy_sidecar_network_connect_command,
    _build_haproxy_sidecar_run_command,
    _build_jina_reader_cleanup_commands,
    _build_jina_reader_container_name,
    _build_jina_reader_run_command,
    _build_mcp_sidecar_cleanup_commands,
    _build_mcp_sidecar_container_name,
    _build_mcp_sidecar_image_build_command,
    _build_mcp_sidecar_image_inspect_command,
    _build_mcp_sidecar_run_command,
    _build_ollama_sidecar_cleanup_commands,
    _build_ollama_sidecar_container_name,
    _build_ollama_sidecar_image_build_command,
    _build_ollama_sidecar_image_inspect_command,
    _build_ollama_sidecar_models_probe_script,
    _build_ollama_sidecar_run_command,
    _build_ollama_sidecar_tcp_probe_script,
    _generate_haproxy_configuration,
    _generate_ollama_sidecar_dockerfile,
    _start_haproxy_sidecar,
    _start_jina_reader,
    _start_mcp_sidecar,
    _start_ollama_sidecar,
    _wait_for_jina_reader_ready,
    _wait_for_ollama_sidecar_ready,
    _write_code_sidecar_logs,
    _write_haproxy_configuration,
    _write_haproxy_sidecar_logs,
    _write_jina_reader_logs,
    _write_mcp_sidecar_exposure,
    _write_mcp_sidecar_logs,
    _write_ollama_sidecar_dockerfile,
    _write_ollama_sidecar_logs,
)
from docker_sandbox.sandbox_spec import resolve_ollama_image_name


def test_mcp_sidecar_container_name_is_created_for_agent_network_runs() -> None:
    """Verify agent runs with a network gateway get an MCP sidecar container."""
    configuration = _create_network_configuration()

    container_name = _build_mcp_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name == "mcp-sidecar-2026-07-20-16-00-00"


def test_mcp_sidecar_container_name_is_omitted_without_network() -> None:
    """Verify no-network runs do not get an MCP sidecar container."""
    configuration = _create_minimal_configuration()

    container_name = _build_mcp_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name is None


def test_jina_reader_container_name_is_created_for_agent_network_runs() -> None:
    """Verify agent runs with a network gateway get a Jina Reader container."""
    configuration = _create_jina_reader_configuration()

    container_name = _build_jina_reader_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name == "jina-reader-2026-07-20-16-00-00"


def test_jina_reader_container_name_is_omitted_without_network() -> None:
    """Verify no-network runs do not get a Jina Reader container."""
    configuration = _create_minimal_configuration()

    container_name = _build_jina_reader_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name is None


def test_jina_reader_container_name_is_omitted_without_capability() -> None:
    """Verify network access alone does not get a Jina Reader container."""
    configuration = _create_network_configuration()

    container_name = _build_jina_reader_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name is None


def test_code_sidecar_container_name_is_created_for_agent_network_runs() -> None:
    """Verify code_execution runs get a code sidecar container."""
    configuration = _create_code_execution_configuration()

    container_name = _build_code_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name == "code-sidecar-2026-07-20-16-00-00"


def test_code_sidecar_container_name_is_omitted_without_capability() -> None:
    """Verify network access alone does not get a code sidecar container."""
    configuration = _create_network_configuration()

    container_name = _build_code_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name is None


def test_haproxy_sidecar_container_name_is_created_for_agent_network_runs() -> None:
    """Verify haproxy runs get an HAProxy sidecar container."""
    configuration = _create_haproxy_configuration()

    container_name = _build_haproxy_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name == "haproxy-sidecar-2026-07-20-16-00-00"


def test_haproxy_sidecar_container_name_is_omitted_without_capability() -> None:
    """Verify network access alone does not get an HAProxy sidecar container."""
    configuration = _create_network_configuration()

    container_name = _build_haproxy_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name is None


def test_ollama_sidecar_container_name_is_created_for_agent_network_runs(
    tmp_path: Path,
) -> None:
    """Verify ollama runs get an Ollama sidecar container."""
    configuration = _create_ollama_configuration(tmp_path)

    container_name = _build_ollama_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name == "ollama-sidecar-2026-07-20-16-00-00"


def test_ollama_sidecar_container_name_is_omitted_without_capability() -> None:
    """Verify network access alone does not get an Ollama sidecar container."""
    configuration = _create_network_configuration()

    container_name = _build_ollama_sidecar_container_name(
        configuration,
        "2026-07-20-16-00-00",
    )

    assert container_name is None


def test_mcp_sidecar_run_command_uses_internal_network_and_proxy() -> None:
    """Verify the sidecar is started on the internal network with Squid proxy env."""
    command = _build_mcp_sidecar_run_command(
        _create_network_configuration(),
        Path(".docker_sandbox") / "runs" / "run-1",
        "sandbox-agent-net-1",
        "mcp-sidecar-1",
    )

    assert command[:4] == ["docker", "run", "--detach", "--name"]
    assert "mcp-sidecar-1" in command
    assert _option_value(command, "--network") == "sandbox-agent-net-1"
    assert _option_value(command, "--network-alias") == "mcp-sidecar"
    assert "HTTP_PROXY=http://egress-gateway:3128" in _option_values(
        command,
        "--env",
    )
    assert "HTTPS_PROXY=http://egress-gateway:3128" in _option_values(
        command,
        "--env",
    )
    env_values = _option_values(command, "--env")
    assert "NO_PROXY=localhost,127.0.0.1,mcp-sidecar,jina-reader,code-sidecar" in (
        env_values
    )
    assert not any(value.startswith("MARIADB_") for value in env_values)
    assert "SANDBOX_TESTER_MARIADB_CREDENTIALS" not in env_values
    assert "JINA_READER_URL=http://jina-reader:8081" in _option_values(
        command,
        "--env",
    )
    assert "CODE_SIDECAR_URL=http://code-sidecar:8090" in _option_values(
        command,
        "--env",
    )
    assert (
        "MCP_SIDECAR_AUDIT_LOG_PATH=/mcp-sidecar-output/mcp-sidecar-tool-calls.jsonl"
    ) in _option_values(command, "--env")
    assert (
        "MCP_SIDECAR_EXPOSURE_PATH=/mcp-sidecar-config/mcp-sidecar-exposure.json"
    ) in _option_values(command, "--env")
    assert _option_values(command, "--mount") == [
        "type=bind,source=src\\mcp_sidecar,target=/opt/mcp-sidecar/mcp_sidecar,readonly",
        ("type=bind,source=.docker_sandbox\\runs\\run-1,target=/mcp-sidecar-output"),
        (
            "type=bind,source=.docker_sandbox\\runs\\run-1\\mcp-sidecar-exposure.json,"
            "target=/mcp-sidecar-config/mcp-sidecar-exposure.json,readonly"
        ),
    ]
    assert command[-8:] == [
        "mcp-sidecar:dev",
        "python",
        "-m",
        "mcp_sidecar",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]


def test_mcp_sidecar_run_command_includes_database_env_only_for_haproxy() -> None:
    """Verify only the MCP sidecar receives MariaDB settings through HAProxy."""
    command = _build_mcp_sidecar_run_command(
        _create_haproxy_configuration(),
        Path(".docker_sandbox") / "runs" / "run-1",
        "sandbox-agent-net-1",
        "mcp-sidecar-1",
    )

    env_values = _option_values(command, "--env")
    assert (
        "NO_PROXY=localhost,127.0.0.1,mcp-sidecar,jina-reader,code-sidecar,haproxy-sidecar"
        in (env_values)
    )
    assert "MARIADB_HOST=haproxy-sidecar" in env_values
    assert "MARIADB_PORT=3306" in env_values
    assert "MARIADB_DATABASE=agent_allowed" in env_values
    assert "SANDBOX_TESTER_MARIADB_CREDENTIALS" in env_values
    assert "MARIADB_USER" not in env_values
    assert not any("sandbox_tester.secret" in value for value in env_values)


def test_mcp_sidecar_database_env_prefers_mariadb_port() -> None:
    """Verify MCP uses port 3306 when HAProxy exposes multiple ports."""
    configuration = _create_haproxy_configuration(ports=(5432, 3306))

    command = _build_mcp_sidecar_run_command(
        configuration,
        Path(".docker_sandbox") / "runs" / "run-1",
        "sandbox-agent-net-1",
        "mcp-sidecar-1",
    )

    env_values = _option_values(command, "--env")
    assert "MARIADB_PORT=3306" in env_values


def test_mcp_sidecar_database_env_falls_back_to_first_haproxy_port() -> None:
    """Verify non-MariaDB HAProxy configs still produce one MCP port value."""
    configuration = _create_haproxy_configuration(ports=(5432,))

    command = _build_mcp_sidecar_run_command(
        configuration,
        Path(".docker_sandbox") / "runs" / "run-1",
        "sandbox-agent-net-1",
        "mcp-sidecar-1",
    )

    env_values = _option_values(command, "--env")
    assert "MARIADB_PORT=5432" in env_values


def test_jina_reader_run_command_uses_internal_network_and_proxy() -> None:
    """Verify Jina Reader is started on the internal network with Squid proxy env."""
    command = _build_jina_reader_run_command(
        "sandbox-agent-net-1",
        "jina-reader-1",
    )

    assert command[:4] == ["docker", "run", "--detach", "--name"]
    assert "jina-reader-1" in command
    assert _option_value(command, "--network") == "sandbox-agent-net-1"
    assert _option_value(command, "--network-alias") == "jina-reader"
    assert "HTTP_PROXY=http://egress-gateway:3128" in _option_values(
        command,
        "--env",
    )
    assert "HTTPS_PROXY=http://egress-gateway:3128" in _option_values(
        command,
        "--env",
    )
    assert "NO_PROXY=localhost,127.0.0.1,jina-reader,mcp-sidecar" in _option_values(
        command,
        "--env",
    )
    assert command[-1] == "ghcr.io/jina-ai/reader:oss"


def test_code_sidecar_run_command_uses_internal_network_without_proxy() -> None:
    """Verify the code sidecar starts with tight local-only hardening."""
    command = _build_code_sidecar_run_command(
        _create_code_execution_configuration(),
        Path(".docker_sandbox") / "runs" / "run-1",
        "sandbox-agent-net-1",
        "code-sidecar-1",
    )

    assert command[:5] == ["docker", "run", "--detach", "--init", "--read-only"]
    assert "code-sidecar-1" in command
    assert _option_value(command, "--network") == "sandbox-agent-net-1"
    assert _option_value(command, "--network-alias") == "code-sidecar"
    assert _option_value(command, "--pids-limit") == "32"
    assert _option_value(command, "--memory") == "128m"
    assert _option_value(command, "--memory-swap") == "128m"
    assert _option_value(command, "--cpus") == "0.5"
    assert "--cap-drop=ALL" in command
    assert "no-new-privileges" in _option_values(command, "--security-opt")
    assert (
        "seccomp=.docker_sandbox\\runs\\run-1\\seccomp-profile.json"
    ) in _option_values(command, "--security-opt")
    assert _option_value(command, "--tmpfs") == "/tmp:rw,nosuid,nodev,noexec,size=16m"
    assert "HTTP_PROXY=http://egress-gateway:3128" not in _option_values(
        command,
        "--env",
    )
    assert ("CODE_SIDECAR_OUTPUT_DIRECTORY=/code-sidecar-output") in _option_values(
        command, "--env"
    )
    assert _option_values(command, "--mount") == [
        "type=bind,source=src\\code_sidecar,target=/opt/code-sidecar/code_sidecar,readonly",
        "type=bind,source=.docker_sandbox\\runs\\run-1,target=/code-sidecar-output",
    ]
    assert command[-8:] == [
        "code-sidecar:dev",
        "python",
        "-m",
        "code_sidecar",
        "--host",
        "0.0.0.0",
        "--port",
        "8090",
    ]


def test_haproxy_sidecar_run_command_uses_internal_network(
    tmp_path: Path,
) -> None:
    """Verify HAProxy starts on the internal Docker network with a mounted config."""
    command = _build_haproxy_sidecar_run_command(
        tmp_path,
        "haproxy-sidecar-1",
    )

    assert command[:4] == ["docker", "run", "--detach", "--name"]
    assert "haproxy-sidecar-1" in command
    assert _option_value(command, "--network") == "bridge"
    assert _option_value(command, "--add-host") == "host.docker.internal:host-gateway"
    assert _option_values(command, "--mount") == [
        (
            f"type=bind,source={tmp_path / 'haproxy.cfg'},"
            "target=/usr/local/etc/haproxy/haproxy.cfg,readonly"
        )
    ]
    assert command[-1] == "haproxy:latest"
    assert "--publish" not in command
    assert "-p" not in command


def test_haproxy_sidecar_network_connect_command_adds_internal_alias() -> None:
    """Verify HAProxy joins the internal network under the sidecar alias."""
    command = _build_haproxy_sidecar_network_connect_command(
        "sandbox-agent-net-1",
        "haproxy-sidecar-1",
    )

    assert command == [
        "docker",
        "network",
        "connect",
        "--alias",
        "haproxy-sidecar",
        "sandbox-agent-net-1",
        "haproxy-sidecar-1",
    ]


def test_ollama_sidecar_run_command_uses_internal_network(
    tmp_path: Path,
) -> None:
    """Verify the Ollama sidecar starts on the internal Docker network."""
    configuration = _create_ollama_configuration(tmp_path)
    assert configuration.ollama_image_name is not None

    command = _build_ollama_sidecar_run_command(
        configuration,
        "sandbox-agent-net-1",
        "ollama-sidecar-1",
    )

    assert command[:4] == ["docker", "run", "--detach", "--init"]
    assert "ollama-sidecar-1" in command
    assert _option_value(command, "--network") == "sandbox-agent-net-1"
    assert _option_value(command, "--network-alias") == "ollama-sidecar"
    assert "OLLAMA_HOST=0.0.0.0:11434" in _option_values(command, "--env")
    assert command[-1] == configuration.ollama_image_name


def test_mcp_sidecar_image_commands_use_static_dockerfile() -> None:
    """Verify the MCP sidecar image commands target the static Dockerfile."""
    configuration = _create_network_configuration()

    inspect_command = _build_mcp_sidecar_image_inspect_command()
    build_command = _build_mcp_sidecar_image_build_command(configuration)

    assert inspect_command == ["docker", "image", "inspect", "mcp-sidecar:dev"]
    assert build_command == [
        "docker",
        "build",
        "--file",
        str(Path("src") / "mcp_sidecar" / "dockerfile" / "Dockerfile"),
        "--tag",
        "mcp-sidecar:dev",
        ".",
    ]


def test_start_mcp_sidecar_rebuilds_image_before_running(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify MCP startup refreshes the dev image before running the sidecar."""
    configuration = _create_network_configuration()
    calls = []

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert check is False
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert errors == "replace"
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    commands = _start_mcp_sidecar(
        configuration,
        tmp_path,
        "sandbox-agent-net-1",
        "mcp-sidecar-1",
    )

    expected_commands = [
        _build_mcp_sidecar_image_inspect_command(),
        _build_mcp_sidecar_image_build_command(configuration),
        _build_mcp_sidecar_run_command(
            configuration,
            tmp_path,
            "sandbox-agent-net-1",
            "mcp-sidecar-1",
        ),
    ]
    start_results = json.loads(
        (tmp_path / "mcp-sidecar-start-results.json").read_text()
    )

    assert commands == expected_commands
    assert calls == expected_commands
    assert [result["command"] for result in start_results] == expected_commands


def test_code_sidecar_image_commands_use_static_dockerfile() -> None:
    """Verify the code sidecar image commands target the static Dockerfile."""
    configuration = _create_network_configuration()

    inspect_command = _build_code_sidecar_image_inspect_command()
    build_command = _build_code_sidecar_image_build_command(configuration)

    assert inspect_command == ["docker", "image", "inspect", "code-sidecar:dev"]
    assert build_command == [
        "docker",
        "build",
        "--file",
        str(Path("src") / "code_sidecar" / "dockerfile" / "Dockerfile"),
        "--tag",
        "code-sidecar:dev",
        ".",
    ]


def test_ollama_sidecar_image_commands_use_generated_dockerfile(
    tmp_path: Path,
) -> None:
    """Verify Ollama image commands target the generated model Dockerfile."""
    configuration = _create_ollama_configuration(tmp_path)
    image_name = resolve_ollama_image_name(
        ("qwen3:4b", "phi4-mini:latest"),
    )

    inspect_command = _build_ollama_sidecar_image_inspect_command(configuration)
    build_command = _build_ollama_sidecar_image_build_command(configuration)

    dockerfile_path = (
        tmp_path
        / "generated"
        / "ollama-sidecar"
        / image_name.rsplit(":", 1)[-1]
        / "Dockerfile"
    )
    assert inspect_command == ["docker", "image", "inspect", image_name]
    assert build_command == [
        "docker",
        "build",
        "--file",
        str(dockerfile_path),
        "--tag",
        image_name,
        ".",
    ]
    assert dockerfile_path.exists()


def test_ollama_sidecar_dockerfile_pulls_declared_models() -> None:
    """Verify the generated Ollama Dockerfile bakes each model into the image."""
    dockerfile = _generate_ollama_sidecar_dockerfile(
        ("phi4-mini:latest", "qwen3:4b"),
    )

    assert "FROM ollama/ollama:latest" in dockerfile
    assert "ENV OLLAMA_HOST=0.0.0.0:11434" in dockerfile
    assert "EXPOSE 11434" in dockerfile
    assert "ollama serve > /tmp/ollama-build.log 2>&1" in dockerfile
    assert "ollama pull phi4-mini:latest;" in dockerfile
    assert "ollama pull qwen3:4b;" in dockerfile
    assert 'kill "$server_pid";' in dockerfile


def test_ollama_sidecar_dockerfile_quotes_model_names() -> None:
    """Verify shell-sensitive model names are safely quoted in Dockerfile output."""
    dockerfile = _generate_ollama_sidecar_dockerfile(("custom model:latest",))

    assert "ollama pull 'custom model:latest';" in dockerfile


def test_haproxy_configuration_proxies_declared_ports() -> None:
    """Verify HAProxy config maps each listen port to the same backend port."""
    config = _generate_haproxy_configuration(
        "host.docker.internal",
        (3306, 5432),
    )

    assert "mode tcp" in config
    assert "frontend tcp_3306" in config
    assert "bind *:3306" in config
    assert "default_backend backend_3306" in config
    assert "server host host.docker.internal:3306" in config
    assert "frontend tcp_5432" in config
    assert "bind *:5432" in config
    assert "server host host.docker.internal:5432" in config


def test_write_haproxy_configuration_writes_run_artifact(tmp_path: Path) -> None:
    """Verify HAProxy config is generated inside the run directory."""
    configuration = _create_haproxy_configuration()

    _write_haproxy_configuration(configuration, tmp_path)

    config = (tmp_path / "haproxy.cfg").read_text(encoding="utf-8")
    assert "bind *:3306" in config
    assert "server host host.docker.internal:3306" in config


def test_write_ollama_sidecar_dockerfile_uses_image_tag_directory(
    tmp_path: Path,
) -> None:
    """Verify generated Ollama Dockerfiles are isolated by image tag."""
    configuration = _create_ollama_configuration(tmp_path)
    assert configuration.ollama_image_name is not None
    image_tag = configuration.ollama_image_name.rsplit(":", 1)[-1]

    dockerfile_path = _write_ollama_sidecar_dockerfile(configuration)

    assert dockerfile_path == (
        tmp_path / "generated" / "ollama-sidecar" / image_tag / "Dockerfile"
    )
    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    assert "ollama pull phi4-mini:latest;" in dockerfile
    assert "ollama pull qwen3:4b;" in dockerfile


def test_mcp_sidecar_cleanup_removes_sidecar_before_network_cleanup() -> None:
    """Verify MCP sidecar cleanup removes the sidecar container."""
    configuration = _create_network_configuration()

    cleanup_commands = _build_mcp_sidecar_cleanup_commands(
        configuration,
        "mcp-sidecar-1",
    )

    assert cleanup_commands == [["docker", "rm", "--force", "mcp-sidecar-1"]]


def test_jina_reader_cleanup_removes_reader_before_network_cleanup() -> None:
    """Verify Jina Reader cleanup removes the reader container."""
    configuration = _create_jina_reader_configuration()

    cleanup_commands = _build_jina_reader_cleanup_commands(
        configuration,
        "jina-reader-1",
    )

    assert cleanup_commands == [["docker", "rm", "--force", "jina-reader-1"]]


def test_code_sidecar_cleanup_removes_sidecar_before_network_cleanup() -> None:
    """Verify code sidecar cleanup removes the sidecar container."""
    configuration = _create_code_execution_configuration()

    cleanup_commands = _build_code_sidecar_cleanup_commands(
        configuration,
        "code-sidecar-1",
    )

    assert cleanup_commands == [["docker", "rm", "--force", "code-sidecar-1"]]


def test_haproxy_sidecar_cleanup_removes_sidecar_before_network_cleanup() -> None:
    """Verify HAProxy sidecar cleanup removes the sidecar container."""
    configuration = _create_haproxy_configuration()

    cleanup_commands = _build_haproxy_sidecar_cleanup_commands(
        configuration,
        "haproxy-sidecar-1",
    )

    assert cleanup_commands == [["docker", "rm", "--force", "haproxy-sidecar-1"]]


def test_ollama_sidecar_cleanup_removes_sidecar_before_network_cleanup(
    tmp_path: Path,
) -> None:
    """Verify Ollama sidecar cleanup removes the sidecar container."""
    configuration = _create_ollama_configuration(tmp_path)

    cleanup_commands = _build_ollama_sidecar_cleanup_commands(
        configuration,
        "ollama-sidecar-1",
    )

    assert cleanup_commands == [["docker", "rm", "--force", "ollama-sidecar-1"]]


def test_agent_environment_includes_mcp_sidecar_url() -> None:
    """Verify the agent container receives the MCP sidecar URL."""
    configuration = _create_network_configuration()

    environment = _build_container_environment(configuration, {})

    assert environment["MCP_SIDECAR_URL"] == "http://mcp-sidecar:8000/mcp"
    assert "mcp-sidecar" in environment["NO_PROXY"].split(",")
    assert "mcp-sidecar" in environment["no_proxy"].split(",")


def test_agent_environment_omits_database_settings_with_haproxy() -> None:
    """Verify MariaDB settings are not passed into the AI agent container."""
    configuration = _create_haproxy_configuration()

    environment = _build_container_environment(
        configuration,
        {
            "SANDBOX_TESTER_MARIADB_CREDENTIALS": "sandbox_tester.secret",
        },
    )

    assert "MARIADB_HOST" not in environment
    assert "MARIADB_PORT" not in environment
    assert "MARIADB_DATABASE" not in environment
    assert "SANDBOX_TESTER_MARIADB_CREDENTIALS" not in environment


def test_agent_environment_omits_mcp_sidecar_url_without_network() -> None:
    """Verify no-network agent containers do not receive MCP sidecar settings."""
    configuration = _create_minimal_configuration()

    environment = _build_container_environment(configuration, {})

    assert "MCP_SIDECAR_URL" not in environment


def test_agent_environment_includes_ollama_openai_compatible_urls(
    tmp_path: Path,
) -> None:
    """Verify Ollama runs receive native and OpenAI-compatible local URLs."""
    configuration = _create_ollama_configuration(tmp_path)

    environment = _build_container_environment(
        configuration,
        {"OPENAI_API_KEY": "host-secret"},
    )

    assert environment["OLLAMA_BASE_URL"] == "http://ollama-sidecar:11434"
    assert environment["OLLAMA_MODEL"] == "phi4-mini:latest"
    assert environment["OPENAI_BASE_URL"] == "http://ollama-sidecar:11434/v1"
    assert environment["OPENAI_API_KEY"] == "ollama"
    assert "ollama-sidecar" in environment["NO_PROXY"].split(",")
    assert "ollama-sidecar" in environment["no_proxy"].split(",")


def test_agent_docker_run_command_includes_mcp_sidecar_url() -> None:
    """Verify the agent Docker command passes MCP sidecar connection info."""
    configuration = _create_network_configuration()

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=Path(".docker_sandbox") / "runs" / "run-1",
        container_name="sandbox-agent-run-1",
        remote_run_directory="/tmp/sandbox-tester/run-1",
        network_name="sandbox-agent-net-1",
    )

    env_values = _option_values(command, "--env")
    assert "MCP_SIDECAR_URL=http://mcp-sidecar:8000/mcp" in env_values


def test_agent_docker_run_command_includes_ollama_environment(
    tmp_path: Path,
) -> None:
    """Verify Ollama agent Docker env uses local model endpoint settings."""
    configuration = _create_ollama_configuration(tmp_path)

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=Path(".docker_sandbox") / "runs" / "run-1",
        container_name="sandbox-agent-run-1",
        remote_run_directory="/tmp/sandbox-tester/run-1",
        network_name="sandbox-agent-net-1",
        environment_variables={"OPENAI_API_KEY": "host-secret"},
        local_environment_variable_names=frozenset({"OPENAI_API_KEY"}),
    )

    env_values = _option_values(command, "--env")
    assert "OLLAMA_BASE_URL=http://ollama-sidecar:11434" in env_values
    assert "OLLAMA_MODEL=phi4-mini:latest" in env_values
    assert "OPENAI_BASE_URL=http://ollama-sidecar:11434/v1" in env_values
    assert "OPENAI_API_KEY=ollama" in env_values
    assert "OPENAI_API_KEY" not in env_values
    no_proxy_value = next(
        value for value in env_values if value.startswith("NO_PROXY=")
    )
    assert "ollama-sidecar" in no_proxy_value.split("=", 1)[1].split(",")


def test_write_mcp_sidecar_logs_persists_debug_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify MCP sidecar logs are persisted as text and metadata artifacts."""
    configuration = _create_network_configuration()

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["docker", "logs", "mcp-sidecar-1"]
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="sidecar stdout\n",
            stderr="sidecar stderr\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _write_mcp_sidecar_logs(configuration, tmp_path, "mcp-sidecar-1")

    metadata = json.loads((tmp_path / "mcp-sidecar-metadata.json").read_text())
    assert (tmp_path / "mcp-sidecar-stdout.txt").read_text() == "sidecar stdout\n"
    assert (tmp_path / "mcp-sidecar-stderr.txt").read_text() == "sidecar stderr\n"
    assert metadata == {
        "container_name": "mcp-sidecar-1",
        "image_name": "mcp-sidecar:dev",
        "log_command": ["docker", "logs", "mcp-sidecar-1"],
        "log_returncode": 0,
    }


def test_write_mcp_sidecar_exposure_persists_config(tmp_path: Path) -> None:
    """Verify MCP sidecar exposure config is persisted as a run artifact."""
    configuration = _create_network_configuration()
    configuration = replace(
        configuration,
        mcp_sidecar_tools=("jina_read_url",),
        mcp_sidecar_resources=("answer_format",),
    )

    _write_mcp_sidecar_exposure(configuration, tmp_path)

    exposure = json.loads((tmp_path / "mcp-sidecar-exposure.json").read_text())
    assert exposure == {
        "tools": ["jina_read_url"],
        "resources": ["answer_format"],
    }


def test_write_jina_reader_logs_persists_debug_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Jina Reader logs are persisted as text and metadata artifacts."""
    configuration = _create_jina_reader_configuration()

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["docker", "logs", "jina-reader-1"]
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="reader stdout\n",
            stderr="reader stderr\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _write_jina_reader_logs(configuration, tmp_path, "jina-reader-1")

    metadata = json.loads((tmp_path / "jina-reader-metadata.json").read_text())
    assert (tmp_path / "jina-reader-stdout.txt").read_text() == "reader stdout\n"
    assert (tmp_path / "jina-reader-stderr.txt").read_text() == "reader stderr\n"
    assert metadata == {
        "container_name": "jina-reader-1",
        "image_name": "ghcr.io/jina-ai/reader:oss",
        "log_command": ["docker", "logs", "jina-reader-1"],
        "log_returncode": 0,
    }


def test_write_code_sidecar_logs_persists_debug_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify code sidecar logs are persisted as text and metadata artifacts."""
    configuration = _create_code_execution_configuration()

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["docker", "logs", "code-sidecar-1"]
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="code stdout\n",
            stderr="code stderr\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _write_code_sidecar_logs(configuration, tmp_path, "code-sidecar-1")

    metadata = json.loads((tmp_path / "code-sidecar-metadata.json").read_text())
    assert (tmp_path / "code-sidecar-stdout.txt").read_text() == "code stdout\n"
    assert (tmp_path / "code-sidecar-stderr.txt").read_text() == "code stderr\n"
    assert metadata == {
        "container_name": "code-sidecar-1",
        "image_name": "code-sidecar:dev",
        "log_command": ["docker", "logs", "code-sidecar-1"],
        "log_returncode": 0,
    }


def test_write_ollama_sidecar_logs_persists_debug_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Ollama sidecar logs are persisted as text and metadata artifacts."""
    configuration = _create_ollama_configuration(tmp_path)
    assert configuration.ollama_image_name is not None

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["docker", "logs", "ollama-sidecar-1"]
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ollama stdout\n",
            stderr="ollama stderr\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _write_ollama_sidecar_logs(configuration, tmp_path, "ollama-sidecar-1")

    metadata = json.loads((tmp_path / "ollama-sidecar-metadata.json").read_text())
    assert (tmp_path / "ollama-sidecar-stdout.txt").read_text() == "ollama stdout\n"
    assert (tmp_path / "ollama-sidecar-stderr.txt").read_text() == "ollama stderr\n"
    assert metadata == {
        "container_name": "ollama-sidecar-1",
        "image_name": configuration.ollama_image_name,
        "models": ["phi4-mini:latest", "qwen3:4b"],
        "log_command": ["docker", "logs", "ollama-sidecar-1"],
        "log_returncode": 0,
    }


def test_write_haproxy_sidecar_logs_persists_debug_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify HAProxy logs are persisted as text and metadata artifacts."""
    configuration = _create_haproxy_configuration()

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["docker", "logs", "haproxy-sidecar-1"]
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="haproxy stdout\n",
            stderr="haproxy stderr\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _write_haproxy_sidecar_logs(configuration, tmp_path, "haproxy-sidecar-1")

    metadata = json.loads((tmp_path / "haproxy-sidecar-metadata.json").read_text())
    assert (tmp_path / "haproxy-sidecar-stdout.txt").read_text() == ("haproxy stdout\n")
    assert (tmp_path / "haproxy-sidecar-stderr.txt").read_text() == ("haproxy stderr\n")
    assert metadata == {
        "container_name": "haproxy-sidecar-1",
        "image_name": "haproxy:latest",
        "backend_host": "host.docker.internal",
        "ports": [3306],
        "log_command": ["docker", "logs", "haproxy-sidecar-1"],
        "log_returncode": 0,
    }


def test_start_jina_reader_persists_start_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Jina Reader startup command results are persisted for debugging."""
    configuration = _create_jina_reader_configuration()

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert command == _build_jina_reader_run_command(
            "sandbox-agent-net-1",
            "jina-reader-1",
        )
        assert check is False
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert errors == "replace"
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="reader started\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    commands = _start_jina_reader(
        configuration,
        tmp_path,
        "sandbox-agent-net-1",
        "jina-reader-1",
    )

    start_results = json.loads(
        (tmp_path / "jina-reader-start-results.json").read_text()
    )
    assert commands == [
        _build_jina_reader_run_command("sandbox-agent-net-1", "jina-reader-1")
    ]
    assert commands is not None
    assert start_results == [
        {
            "command": commands[0],
            "returncode": 0,
            "stdout": "reader started\n",
            "stderr": "",
        }
    ]


def test_start_haproxy_sidecar_persists_start_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify HAProxy startup command results are persisted for debugging."""
    configuration = _create_haproxy_configuration()
    calls = []

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert check is False
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert errors == "replace"
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="haproxy started\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    commands = _start_haproxy_sidecar(
        configuration,
        tmp_path,
        "sandbox-agent-net-1",
        "haproxy-sidecar-1",
    )

    start_results = json.loads(
        (tmp_path / "haproxy-sidecar-start-results.json").read_text()
    )
    assert commands is not None
    assert commands == [
        _build_haproxy_sidecar_run_command(
            tmp_path,
            "haproxy-sidecar-1",
        ),
        _build_haproxy_sidecar_network_connect_command(
            "sandbox-agent-net-1",
            "haproxy-sidecar-1",
        ),
    ]
    assert calls == commands
    assert start_results == [
        {
            "command": commands[0],
            "returncode": 0,
            "stdout": "haproxy started\n",
            "stderr": "",
        },
        {
            "command": commands[1],
            "returncode": 0,
            "stdout": "haproxy started\n",
            "stderr": "",
        },
    ]


def test_start_ollama_sidecar_builds_missing_image_and_persists_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Ollama startup records inspect, build, and run command results."""
    configuration = _create_ollama_configuration(tmp_path)
    calls = []

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert check is False
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert errors == "replace"
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr="missing image\n",
            )

        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    commands = _start_ollama_sidecar(
        configuration,
        tmp_path,
        "sandbox-agent-net-1",
        "ollama-sidecar-1",
    )

    start_results = json.loads(
        (tmp_path / "ollama-sidecar-start-results.json").read_text()
    )
    assert commands is not None
    assert commands == [
        _build_ollama_sidecar_image_inspect_command(configuration),
        _build_ollama_sidecar_image_build_command(configuration),
        _build_ollama_sidecar_run_command(
            configuration,
            "sandbox-agent-net-1",
            "ollama-sidecar-1",
        ),
    ]
    assert start_results == [
        {
            "command": commands[0],
            "returncode": 1,
            "stdout": "",
            "stderr": "missing image\n",
        },
        {
            "command": commands[1],
            "returncode": 0,
            "stdout": "ok\n",
            "stderr": "",
        },
        {
            "command": commands[2],
            "returncode": 0,
            "stdout": "ok\n",
            "stderr": "",
        },
    ]


def test_wait_for_jina_reader_ready_persists_two_phase_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Jina Reader readiness writes TCP and fetch probe results."""
    configuration = _create_jina_reader_configuration()
    calls = []
    sleeps = []

    def fake_sleep(interval_seconds: float) -> None:
        sleeps.append(interval_seconds)

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert check is False
        assert capture_output is True
        assert text is True
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr="connection refused",
            )

        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ready\n",
            stderr="",
        )

    monkeypatch.setattr("docker_sandbox.sandbox_container.time.sleep", fake_sleep)
    monkeypatch.setattr(subprocess, "run", fake_run)

    _wait_for_jina_reader_ready(
        configuration,
        tmp_path,
        "sandbox-agent-net-1",
        "jina-reader-1",
        intervals_seconds=(0.0, 1.0),
    )

    readiness_results = json.loads(
        (tmp_path / "jina-reader-readiness-results.json").read_text()
    )
    assert sleeps == [1.0]
    assert readiness_results["container_name"] == "jina-reader-1"
    assert readiness_results["reader_url"] == "http://jina-reader:8081"
    assert readiness_results["fetch_url"] == "https://example.com"
    assert readiness_results["ready"] is True
    assert [phase["name"] for phase in readiness_results["phases"]] == [
        "tcp",
        "fetch",
    ]
    assert readiness_results["phases"][0]["success"] is True
    assert readiness_results["phases"][0]["attempts"][0]["success"] is False
    assert readiness_results["phases"][0]["attempts"][1]["success"] is True
    assert readiness_results["phases"][1]["success"] is True
    assert len(calls) == 3
    assert all(
        command[:5] == ["docker", "run", "--rm", "--network", "sandbox-agent-net-1"]
        for command in calls
    )
    assert all("sandbox-agent/sandbox-agent:minimal" in command for command in calls)


def test_ollama_sidecar_probe_scripts_target_service_and_models() -> None:
    """Verify Ollama readiness probes target TCP and declared models."""
    tcp_script = _build_ollama_sidecar_tcp_probe_script()
    models_script = _build_ollama_sidecar_models_probe_script(
        ("phi4-mini:latest", "qwen3:4b"),
    )

    assert "socket.create_connection(('ollama-sidecar', 11434), timeout=5)" in (
        tcp_script
    )
    assert "http://ollama-sidecar:11434/api/tags" in models_script
    assert "expected_models = ['phi4-mini:latest', 'qwen3:4b']" in models_script
    assert "missing_models" in models_script
    assert "model.get('name') or model.get('model')" in models_script


def test_wait_for_ollama_sidecar_ready_persists_model_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Ollama readiness writes TCP and model probe results."""
    configuration = _create_ollama_configuration(tmp_path)
    calls = []
    sleeps = []

    def fake_sleep(interval_seconds: float) -> None:
        sleeps.append(interval_seconds)

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert check is False
        assert capture_output is True
        assert text is True
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr="connection refused",
            )

        if len(calls) == 3:
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout='{"missing_models": ["qwen3:4b"]}\n',
                stderr="",
            )

        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ready\n",
            stderr="",
        )

    monkeypatch.setattr("docker_sandbox.sandbox_container.time.sleep", fake_sleep)
    monkeypatch.setattr(subprocess, "run", fake_run)

    _wait_for_ollama_sidecar_ready(
        configuration,
        tmp_path,
        "sandbox-agent-net-1",
        "ollama-sidecar-1",
        intervals_seconds=(0.0, 1.0),
    )

    readiness_results = json.loads(
        (tmp_path / "ollama-sidecar-readiness-results.json").read_text()
    )
    assert sleeps == [1.0, 1.0]
    assert readiness_results["container_name"] == "ollama-sidecar-1"
    assert readiness_results["ollama_url"] == "http://ollama-sidecar:11434"
    assert readiness_results["models"] == ["phi4-mini:latest", "qwen3:4b"]
    assert readiness_results["ready"] is True
    assert [phase["name"] for phase in readiness_results["phases"]] == [
        "tcp",
        "models",
    ]
    assert readiness_results["phases"][0]["success"] is True
    assert readiness_results["phases"][0]["attempts"][0]["success"] is False
    assert readiness_results["phases"][0]["attempts"][1]["success"] is True
    assert readiness_results["phases"][1]["success"] is True
    assert readiness_results["phases"][1]["attempts"][0]["success"] is False
    assert readiness_results["phases"][1]["attempts"][1]["success"] is True
    assert len(calls) == 4
    assert all(
        command[:5] == ["docker", "run", "--rm", "--network", "sandbox-agent-net-1"]
        for command in calls
    )
    assert all("sandbox-agent/sandbox-agent:minimal" in command for command in calls)


def test_wait_for_ollama_sidecar_ready_raises_when_models_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Ollama readiness fails when declared models are unavailable."""
    configuration = _create_ollama_configuration(tmp_path)

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        assert capture_output is True
        assert text is True
        if "socket.create_connection" in command[-1]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="ready\n",
                stderr="",
            )

        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout='{"missing_models": ["qwen3:4b"]}\n',
            stderr="",
        )

    monkeypatch.setattr("docker_sandbox.sandbox_container.time.sleep", lambda _: None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        _wait_for_ollama_sidecar_ready(
            configuration,
            tmp_path,
            "sandbox-agent-net-1",
            "ollama-sidecar-1",
            intervals_seconds=(0.0,),
        )
    except RuntimeError as error:
        assert str(error) == "Ollama sidecar did not become ready."
    else:
        raise AssertionError("Expected Ollama readiness failure.")

    readiness_results = json.loads(
        (tmp_path / "ollama-sidecar-readiness-results.json").read_text()
    )
    assert readiness_results["ready"] is False
    assert readiness_results["phases"][0]["success"] is True
    assert readiness_results["phases"][1]["success"] is False


def _create_network_configuration() -> DockerConfiguration:
    profile = get_docker_profile(MINIMAL_PROFILE_NAME)
    network_gateway = NetworkGatewayProfile(
        image_name="ubuntu/squid:latest",
        proxy_host="egress-gateway",
        proxy_port=3128,
    )
    profile = replace(
        profile,
        network_gateway=network_gateway,
    )
    return DockerConfiguration(
        base_directory=Path(".docker_sandbox"),
        dockerfile_path=Path("Dockerfile"),
        build_context=Path("."),
        guest_user="sandbox",
        profile=profile,
    )


def _create_jina_reader_configuration() -> DockerConfiguration:
    configuration = _create_network_configuration()
    return replace(
        configuration,
        enabled_capabilities=frozenset({"jina_reader"}),
    )


def _create_code_execution_configuration() -> DockerConfiguration:
    configuration = _create_network_configuration()
    return replace(
        configuration,
        enabled_capabilities=frozenset({"code_execution"}),
    )


def _create_haproxy_configuration(
    ports: tuple[int, ...] = (3306,),
) -> DockerConfiguration:
    configuration = _create_network_configuration()
    return replace(
        configuration,
        enabled_capabilities=frozenset({"haproxy"}),
        haproxy=HAProxyConfiguration(
            backend_host="host.docker.internal",
            ports=ports,
        ),
    )


def _create_ollama_configuration(base_directory: Path) -> DockerConfiguration:
    configuration = _create_network_configuration()
    models = ("phi4-mini:latest", "qwen3:4b")
    return replace(
        configuration,
        base_directory=base_directory,
        enabled_capabilities=frozenset({"ollama"}),
        ollama_models=models,
        ollama_image_name=resolve_ollama_image_name(models),
    )


def _create_minimal_configuration() -> DockerConfiguration:
    return DockerConfiguration(
        base_directory=Path(".docker_sandbox"),
        dockerfile_path=Path("Dockerfile"),
        build_context=Path("."),
        guest_user="sandbox",
        profile=get_docker_profile(MINIMAL_PROFILE_NAME),
    )


def _option_value(command: list[str], option: str) -> str:
    return command[command.index(option) + 1]


def _option_values(command: list[str], option: str) -> list[str]:
    return [
        value
        for index, value in enumerate(command)
        if index > 0 and command[index - 1] == option
    ]
