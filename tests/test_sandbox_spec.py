"""Tests for declarative sandbox specifications."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from docker_sandbox.cli import _configuration_from_arguments
from docker_sandbox.sandbox_container import _build_allowed_gateway_domains
from docker_sandbox.sandbox_spec import (
    generate_dockerfile,
    load_sandbox_spec,
    resolve_environment_variables,
    resolve_local_environment_variable_names,
    resolve_ollama_image_name,
    resolve_profile,
)


def test_network_capability_resolves_gateway_profile(tmp_path: Path) -> None:
    """Verify network specs enable the gateway and remove Docker network none."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network"]',
                "[squid_proxy]",
                'allowed_domains = [".example.com"]',
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    profile = resolve_profile(load_sandbox_spec(spec_path))

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".example.com",)
    assert "127.0.0.1" in profile.network_gateway.no_proxy_hosts
    assert "localhost" in profile.network_gateway.no_proxy_hosts
    assert "--network" not in profile.container_run_options
    assert "none" not in profile.container_run_options


def test_allowlists_require_network_capability(tmp_path: Path) -> None:
    """Verify allowlists cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                "[squid_proxy]",
                'allowed_domains = [".example.com"]',
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="require the network capability"):
        load_sandbox_spec(spec_path)


def test_squid_proxy_supports_domains_and_ip_addresses(tmp_path: Path) -> None:
    """Verify Squid proxy allowlists are loaded from their own table."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network"]',
                "[squid_proxy]",
                'allowed_domains = [".example.com"]',
                'allowed_ip_addresses = ["203.0.113.10"]',
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)

    assert spec.allowed_domains == (".example.com",)
    assert spec.allowed_ip_addresses == ("203.0.113.10",)
    assert spec.to_dict()["squid_proxy"] == {
        "allowed_domains": [".example.com"],
        "allowed_ip_addresses": ["203.0.113.10"],
    }


def test_squid_proxy_rejects_unknown_keys(tmp_path: Path) -> None:
    """Verify Squid proxy settings fail closed for unsupported spec keys."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "transparent = true",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported squid_proxy key"):
        load_sandbox_spec(spec_path)


def test_top_level_allowlists_are_unsupported(tmp_path: Path) -> None:
    """Verify allowlists must be declared under the Squid proxy table."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network"]',
                'allowed_domains = [".example.com"]',
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported sandbox spec key"):
        load_sandbox_spec(spec_path)


def test_gateway_domains_use_only_configured_allowlist() -> None:
    """Verify legacy fixture metadata does not widen the network allowlist."""
    domains = _build_allowed_gateway_domains(
        (".example.com",),
        {
            "allowed_domain": "ignored.test",
            "git_remote_url": "https://github.com/example/project.git",
        },
    )

    assert domains == (".example.com",)


def test_environment_variables_support_explicit_and_host_values(
    tmp_path: Path,
) -> None:
    """Verify environment variables support explicit and host-sourced values."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[[environment_variables]]",
                'name = "API_BASE_URL"',
                'value = "https://example.com"',
                "",
                "[[environment_variables]]",
                'name = "OPENAI_API_KEY"',
                "from_host = true",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)

    assert resolve_environment_variables(spec) == (
        ("API_BASE_URL", "https://example.com"),
        ("OPENAI_API_KEY", "[local]"),
    )
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"OPENAI_API_KEY"}
    )


def test_environment_variables_require_exactly_one_value_source(
    tmp_path: Path,
) -> None:
    """Verify environment variable entries fail closed when ambiguous."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[[environment_variables]]",
                'name = "API_BASE_URL"',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exactly one"):
        load_sandbox_spec(spec_path)


def test_mcp_sidecar_exposure_supports_tools_and_resources(
    tmp_path: Path,
) -> None:
    """Verify MCP sidecar exposure is loaded from the sandbox spec."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[mcp_sidecar]",
                'tools = ["jina_read_url"]',
                'resources = ["answer_format"]',
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)

    assert spec.mcp_sidecar_tools == ("jina_read_url",)
    assert spec.mcp_sidecar_resources == ("answer_format",)
    assert spec.to_dict()["mcp_sidecar"] == {
        "tools": ["jina_read_url"],
        "resources": ["answer_format"],
    }


def test_mcp_sidecar_exposure_rejects_unknown_keys(tmp_path: Path) -> None:
    """Verify MCP sidecar exposure fails closed for unsupported spec keys."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[mcp_sidecar]",
                'toolz = ["jina_read_url"]',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported mcp_sidecar key"):
        load_sandbox_spec(spec_path)


def test_code_execution_capability_is_supported(tmp_path: Path) -> None:
    """Verify code_execution is a supported standalone capability."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["code_execution"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)

    assert spec.has_capability("code_execution") is True


def test_run_python_script_tool_requires_mcp_client(tmp_path: Path) -> None:
    """Verify Python execution exposure requires MCP client support."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["code_execution"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[mcp_sidecar]",
                'tools = ["run_python_script"]',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires mcp_client"):
        load_sandbox_spec(spec_path)


def test_run_python_script_tool_requires_code_execution(tmp_path: Path) -> None:
    """Verify Python execution exposure requires the code sidecar capability."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "mcp_client"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[mcp_sidecar]",
                'tools = ["run_python_script"]',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires code_execution"):
        load_sandbox_spec(spec_path)


def test_run_python_script_tool_accepts_required_capabilities(tmp_path: Path) -> None:
    """Verify Python execution exposure accepts its required capabilities."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "mcp_client", "code_execution"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[mcp_sidecar]",
                'tools = ["run_python_script"]',
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)

    assert spec.mcp_sidecar_tools == ("run_python_script",)


def test_openai_capability_requires_network(tmp_path: Path) -> None:
    """Verify OpenAI cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["openai"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_openai_agents_capability_requires_network(tmp_path: Path) -> None:
    """Verify OpenAI Agents cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["openai_agents"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_mcp_client_capability_requires_network(tmp_path: Path) -> None:
    """Verify MCP client support cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["mcp_client"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_jina_reader_capability_requires_network(tmp_path: Path) -> None:
    """Verify Jina Reader cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["jina_reader"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_ollama_capability_requires_network(tmp_path: Path) -> None:
    """Verify Ollama sidecar support requires the internal Docker network."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b"]',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_ollama_sidecar_models_are_normalized(tmp_path: Path) -> None:
    """Verify Ollama models are sorted for stable sidecar image hashing."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b", "phi4-mini:latest", "granite4.1:3b"]',
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)

    assert spec.has_capability("ollama") is True
    assert spec.ollama_models == (
        "granite4.1:3b",
        "phi4-mini:latest",
        "qwen3:4b",
    )
    assert spec.to_dict()["ollama_sidecar"] == {
        "models": [
            "granite4.1:3b",
            "phi4-mini:latest",
            "qwen3:4b",
        ],
    }


def test_ollama_capability_requires_sidecar_table(tmp_path: Path) -> None:
    """Verify Ollama capability eagerly fails without sidecar configuration."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"requires \[ollama_sidecar\]"):
        load_sandbox_spec(spec_path)


def test_ollama_capability_requires_models(tmp_path: Path) -> None:
    """Verify Ollama capability eagerly fails without declared models."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                "models = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"requires \[ollama_sidecar\]\.models"):
        load_sandbox_spec(spec_path)


def test_ollama_models_reject_empty_entries(tmp_path: Path) -> None:
    """Verify Ollama model names must be non-empty after trimming."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b", " "]',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="entries must not be empty"):
        load_sandbox_spec(spec_path)


def test_ollama_models_reject_duplicates(tmp_path: Path) -> None:
    """Verify duplicate Ollama model declarations fail closed."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b", "qwen3:4b"]',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate Ollama model"):
        load_sandbox_spec(spec_path)


def test_ollama_sidecar_rejects_unknown_keys(tmp_path: Path) -> None:
    """Verify Ollama sidecar settings fail closed for unsupported spec keys."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b"]',
                'default_model = "qwen3:4b"',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported ollama_sidecar key"):
        load_sandbox_spec(spec_path)


def test_ollama_sidecar_models_require_capability(tmp_path: Path) -> None:
    """Verify Ollama sidecar config cannot silently enable the sidecar."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b"]',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the ollama capability"):
        load_sandbox_spec(spec_path)


def test_ollama_image_hash_is_independent_from_agent_image_hash(
    tmp_path: Path,
) -> None:
    """Verify Ollama image identity is stable and separate from agent images."""
    first_spec_path = tmp_path / "first_sandbox_spec.toml"
    first_spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "openai_agents", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b", "phi4-mini:latest"]',
            ]
        ),
        encoding="utf-8",
    )
    reordered_spec_path = tmp_path / "reordered_sandbox_spec.toml"
    reordered_spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "openai_agents", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["phi4-mini:latest", "qwen3:4b"]',
            ]
        ),
        encoding="utf-8",
    )
    changed_models_spec_path = tmp_path / "changed_models_sandbox_spec.toml"
    changed_models_spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "openai_agents", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["granite4.1:3b", "qwen3:4b"]',
            ]
        ),
        encoding="utf-8",
    )

    first_spec = load_sandbox_spec(first_spec_path)
    reordered_spec = load_sandbox_spec(reordered_spec_path)
    changed_models_spec = load_sandbox_spec(changed_models_spec_path)

    assert first_spec.image_name == reordered_spec.image_name
    assert first_spec.ollama_image_name == reordered_spec.ollama_image_name
    assert first_spec.image_name == changed_models_spec.image_name
    assert first_spec.ollama_image_name != changed_models_spec.ollama_image_name
    assert first_spec.ollama_image_name == resolve_ollama_image_name(
        ("phi4-mini:latest", "qwen3:4b"),
    )


def test_ollama_configuration_is_carried_into_docker_configuration(
    tmp_path: Path,
) -> None:
    """Verify CLI configuration plumbing preserves Ollama sidecar data."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ollama"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[ollama_sidecar]",
                'models = ["qwen3:4b", "phi4-mini:latest"]',
            ]
        ),
        encoding="utf-8",
    )
    arguments = argparse.Namespace(
        base_directory=tmp_path / "sandbox",
        dockerfile=Path("unused"),
        guest_user="sandbox",
        profile=None,
        sandbox_spec=spec_path,
        test_sandbox=False,
    )

    configuration = _configuration_from_arguments(arguments)

    assert configuration.ollama_models == ("phi4-mini:latest", "qwen3:4b")
    assert configuration.ollama_image_name == resolve_ollama_image_name(
        ("qwen3:4b", "phi4-mini:latest"),
    )
    assert configuration.resolved_spec is not None
    assert configuration.resolved_spec["ollama_image_name"] == (
        configuration.ollama_image_name
    )


def test_anthropic_python_capability_requires_network(tmp_path: Path) -> None:
    """Verify Anthropic Python SDK cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["anthropic_python"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_anthropic_claude_capability_requires_network(tmp_path: Path) -> None:
    """Verify Claude Agent SDK cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["anthropic_claude"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_beeai_capability_requires_network(tmp_path: Path) -> None:
    """Verify BeeAI cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["ibm_beeai"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_google_adk_capability_requires_network(tmp_path: Path) -> None:
    """Verify Google ADK cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["google_adk"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_langchain_capability_requires_network(tmp_path: Path) -> None:
    """Verify LangChain cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["langchain"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_langgraph_capability_requires_network(tmp_path: Path) -> None:
    """Verify LangGraph cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["langgraph"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_microsoft_agent_capability_requires_network(tmp_path: Path) -> None:
    """Verify Microsoft Agent Framework cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["microsoft_agent"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_crewai_capability_requires_network(tmp_path: Path) -> None:
    """Verify CrewAI cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["crewai"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_otto_agent_capability_requires_network(tmp_path: Path) -> None:
    """Verify Otto Agent cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["otto_agent"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_openai_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify OpenAI adds only its needed package, domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "openai"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"OPENAI_API_KEY"}
    )
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert "openai==2.45.0" in generate_dockerfile(spec)


def test_openai_agents_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify OpenAI Agents adds its package without broad shell access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "openai_agents"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "openai-agents==0.18.2" in dockerfile
    assert "openai==2.45.0" not in dockerfile


def test_mcp_client_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify MCP client capability adds the MCP SDK package."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "mcp_client"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)
    dockerfile = generate_dockerfile(spec)

    assert profile.network_gateway is not None
    assert "mcp==1.28.1" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_jina_reader_capability_resolves_without_mcp_client_runtime(
    tmp_path: Path,
) -> None:
    """Verify Jina Reader is an explicit capability independent of MCP client."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "jina_reader"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)
    dockerfile = generate_dockerfile(spec)

    assert spec.has_capability("jina_reader") is True
    assert spec.has_capability("mcp_client") is False
    assert profile.network_gateway is not None
    assert "mcp==1.28.1" not in dockerfile


def test_anthropic_python_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Anthropic Python SDK adds its package, domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "anthropic_python"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".anthropic.com",)
    assert resolve_environment_variables(spec) == (("ANTHROPIC_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"ANTHROPIC_API_KEY"}
    )
    assert all(policy.name != "ANTHROPIC_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "anthropic==0.116.0" in dockerfile
    assert "openai==2.45.0" not in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_anthropic_claude_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Claude Agent SDK adds its package, domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "anthropic_claude"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".anthropic.com",)
    assert resolve_environment_variables(spec) == (("ANTHROPIC_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"ANTHROPIC_API_KEY"}
    )
    assert all(policy.name != "ANTHROPIC_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "0"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "claude-agent-sdk==0.2.120" in dockerfile
    assert "anthropic==0.116.0" not in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_beeai_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify BeeAI adds its package, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ibm_beeai"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "beeai-framework==0.1.81" in dockerfile
    assert "'litellm[proxy]==1.92.0'" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_google_adk_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Google ADK adds its package, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "google_adk"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "google-adk==2.5.0" in dockerfile
    assert "'litellm[proxy]==1.92.0'" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_langchain_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify LangChain adds its packages, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "langchain"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "langchain==1.3.14" in dockerfile
    assert "langchain-openai==1.3.5" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_langgraph_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify LangGraph adds its packages, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "langgraph"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "langgraph==1.2.9" in dockerfile
    assert "langchain-openai==1.3.5" in dockerfile
    assert "langchain==1.3.14" not in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_microsoft_agent_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Microsoft Agent Framework adds its package and OpenAI support."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "microsoft_agent"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "agent-framework==1.11.0" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_crewai_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify CrewAI adds its package and OpenAI support."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "crewai"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    assert any(
        policy.name == "CREWAI_TRACING_ENABLED" and policy.value == "false"
        for policy in profile.environment
    )
    assert any(
        policy.name == "OTEL_SDK_DISABLED" and policy.value == "true"
        for policy in profile.environment
    )
    assert (
        "/tmp/sandbox-home:rw,nosuid,nodev,noexec,size=64m,uid=1000,gid=1000,mode=700"
        in profile.container_run_options
    )
    dockerfile = generate_dockerfile(spec)
    assert "crewai==1.15.3" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_otto_agent_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Otto Agent adds only OpenAI runtime support."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "otto_agent"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"OPENAI_API_KEY"}
    )
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "openai==2.45.0" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile
    assert "crewai==1.15.3" not in dockerfile


def test_playwright_chromium_capability_resolves_browser_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Playwright adds Chromium packages without broad shell access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["playwright_chromium"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)
    dockerfile = generate_dockerfile(spec)

    assert profile.network_gateway is None
    assert profile.browser_surface is not None
    assert "playwright==1.61.0" in dockerfile
    assert "python -m playwright install --with-deps chromium" in dockerfile
    assert any(rule.path == "/ms-playwright" for rule in profile.landlock_rules)
    assert profile.pids_limit == 512
    assert profile.memory == "2g"
    assert profile.shm_size == "1g"
    assert any(
        ulimit.name == "fsize" and ulimit.soft == 52428800 for ulimit in profile.ulimits
    )
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )


def test_shell_access_capability_allows_process_spawn(tmp_path: Path) -> None:
    """Verify shell access is an explicit capability."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["shell_access"]',
                "[squid_proxy]",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    profile = resolve_profile(load_sandbox_spec(spec_path))

    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "0"
        for policy in profile.environment
    )
