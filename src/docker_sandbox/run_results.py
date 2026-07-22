"""Persist Docker sandbox run results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .models import DockerRunResult

_STDOUT_FILE_NAME = "stdout.txt"
_STDERR_FILE_NAME = "stderr.txt"
_METADATA_FILE_NAME = "run-metadata.json"


def save_run_results(result: DockerRunResult) -> None:
    """Save Docker container output and metadata to the run directory."""
    result.run_directory.mkdir(parents=True, exist_ok=True)
    _write_text(result.run_directory / _STDOUT_FILE_NAME, result.stdout)
    _write_text(result.run_directory / _STDERR_FILE_NAME, result.stderr)
    _write_json(
        result.run_directory / _METADATA_FILE_NAME,
        _create_metadata_data(result),
    )


def _create_metadata_data(result: DockerRunResult) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "image_name": result.image_name,
        "profile_name": result.profile_name,
        "container_name": result.container_name,
        "network_name": result.network_name,
        "gateway_container_name": result.gateway_container_name,
        "exit_code": result.exit_code,
        "command": result.command,
        "remove_command": result.remove_command,
        "gateway_commands": result.gateway_commands,
        "gateway_ip_address": result.gateway_ip_address,
        "gateway_cleanup_commands": result.gateway_cleanup_commands,
        "mcp_sidecar_container_name": result.mcp_sidecar_container_name,
        "mcp_sidecar_commands": result.mcp_sidecar_commands,
        "mcp_sidecar_cleanup_commands": result.mcp_sidecar_cleanup_commands,
        "jina_reader_container_name": result.jina_reader_container_name,
        "jina_reader_commands": result.jina_reader_commands,
        "jina_reader_cleanup_commands": result.jina_reader_cleanup_commands,
        "code_sidecar_container_name": result.code_sidecar_container_name,
        "code_sidecar_commands": result.code_sidecar_commands,
        "code_sidecar_cleanup_commands": result.code_sidecar_cleanup_commands,
        "haproxy_sidecar_container_name": result.haproxy_sidecar_container_name,
        "haproxy_sidecar_commands": result.haproxy_sidecar_commands,
        "haproxy_sidecar_cleanup_commands": result.haproxy_sidecar_cleanup_commands,
        "ollama_sidecar_container_name": result.ollama_sidecar_container_name,
        "ollama_sidecar_commands": result.ollama_sidecar_commands,
        "ollama_sidecar_cleanup_commands": result.ollama_sidecar_cleanup_commands,
    }


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, data: dict[str, object]) -> None:
    text = json.dumps(data, indent=2)
    path.write_text(f"{text}\n", encoding="utf-8")
