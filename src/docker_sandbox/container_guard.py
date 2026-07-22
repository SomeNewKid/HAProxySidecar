"""Runtime guard for code that must run inside the Docker sandbox."""

from __future__ import annotations

import os
from pathlib import Path

CONTAINER_MARKER_ENVIRONMENT_VARIABLE = "SANDBOX_AGENT_CONTAINER"
CONTAINER_MARKER_VALUE = "1"

REQUIRED_CONTAINER_PATHS = (
    Path("/sandbox-output"),
    Path("/sandbox-work"),
    Path("/sandbox-source/src"),
)


def ensure_running_in_docker_sandbox() -> None:
    """Exit unless this process is running inside the expected Docker sandbox."""
    if is_running_in_docker_sandbox():
        return

    raise SystemExit(
        "Sandbox Agent must be run inside the Docker sandbox. "
        "Use: python -m sandbox_agent"
    )


def is_running_in_docker_sandbox() -> bool:
    """Return whether the current process appears to be in the Docker sandbox."""
    return _has_container_marker_environment() and _has_required_container_paths()


def _has_container_marker_environment() -> bool:
    return (
        os.environ.get(CONTAINER_MARKER_ENVIRONMENT_VARIABLE) == CONTAINER_MARKER_VALUE
    )


def _has_required_container_paths() -> bool:
    return all(path.exists() for path in REQUIRED_CONTAINER_PATHS)
