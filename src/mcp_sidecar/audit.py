"""Audit logging helpers for MCP sidecar calls."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

_AUDIT_LOG_PATH_ENVIRONMENT_VARIABLE = "MCP_SIDECAR_AUDIT_LOG_PATH"


def write_mcp_audit_record(
    call_type: str,
    name: str,
    arguments: Mapping[str, object],
    result: str | None = None,
    error: Exception | None = None,
) -> None:
    """Write a JSONL audit record for an MCP sidecar interaction."""
    audit_log_path = os.environ.get(_AUDIT_LOG_PATH_ENVIRONMENT_VARIABLE)
    if not audit_log_path:
        return

    record: dict[str, object] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "type": call_type,
        "arguments": dict(arguments),
        "success": error is None,
    }
    if call_type == "tool":
        record["tool"] = name
    else:
        record["resource"] = name
    if result is not None:
        record["result_length"] = len(result)
        record["result_preview"] = result[:500]
    if error is not None:
        record["error_type"] = type(error).__name__
        record["error"] = str(error)

    try:
        path = Path(audit_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(f"{json.dumps(record, sort_keys=True)}\n")
    except OSError:
        return
