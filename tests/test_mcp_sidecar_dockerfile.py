"""Tests for the MCP sidecar Docker image definition."""

from __future__ import annotations

from pathlib import Path

_DOCKERFILE_PATH = Path("src") / "mcp_sidecar" / "dockerfile" / "Dockerfile"


def test_mcp_sidecar_dockerfile_uses_python_slim_base() -> None:
    """Verify the MCP sidecar image uses the expected Python base image."""
    dockerfile = _DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile


def test_mcp_sidecar_dockerfile_installs_mcp_dependency() -> None:
    """Verify the MCP sidecar image installs MCP server dependencies."""
    dockerfile = _DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "python -m pip install --no-cache-dir mcp" in dockerfile
    assert "pymysql" in dockerfile


def test_mcp_sidecar_dockerfile_copies_package_source() -> None:
    """Verify the MCP sidecar image copies the MCP package source."""
    dockerfile = _DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "COPY src/mcp_sidecar ./mcp_sidecar" in dockerfile


def test_mcp_sidecar_dockerfile_runs_mcp_sidecar_module() -> None:
    """Verify the MCP sidecar image starts the MCP sidecar module."""
    dockerfile = _DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert 'CMD ["python", "-m", "mcp_sidecar"]' in dockerfile
