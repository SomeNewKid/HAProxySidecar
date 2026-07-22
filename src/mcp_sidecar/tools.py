"""Tools provided by the MCP sidecar server."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from typing import Any, TypedDict
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .audit import write_mcp_audit_record

_GET_ACTIVE_ITEMS_TOOL_NAME = "get_active_items"
_MICROSOFT_LEARN_MCP_URL_ENVIRONMENT_VARIABLE = "MICROSOFT_LEARN_MCP_URL"
_DEFAULT_MICROSOFT_LEARN_MCP_URL = "https://learn.microsoft.com/api/mcp"
_MICROSOFT_DOCS_SEARCH_TOOL_NAME = "microsoft_docs_search"
_MICROSOFT_DOCS_FETCH_TOOL_NAME = "microsoft_docs_fetch"
_MICROSOFT_CODE_SAMPLE_SEARCH_TOOL_NAME = "microsoft_code_sample_search"
_JINA_READ_URL_TOOL_NAME = "jina_read_url"
_RUN_PYTHON_SCRIPT_TOOL_NAME = "run_python_script"
_JINA_READER_URL_ENVIRONMENT_VARIABLE = "JINA_READER_URL"
_CODE_SIDECAR_URL_ENVIRONMENT_VARIABLE = "CODE_SIDECAR_URL"
_DEFAULT_JINA_READER_URL = "http://jina-reader:8081"
_DEFAULT_CODE_SIDECAR_URL = "http://code-sidecar:8090"
_JINA_READER_TIMEOUT_SECONDS = 60.0
_CODE_SIDECAR_TIMEOUT_BUFFER_SECONDS = 2.0
_MARIADB_HOST_ENVIRONMENT_VARIABLE = "MARIADB_HOST"
_MARIADB_PORT_ENVIRONMENT_VARIABLE = "MARIADB_PORT"
_MARIADB_DATABASE_ENVIRONMENT_VARIABLE = "MARIADB_DATABASE"
_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE = "SANDBOX_TESTER_MARIADB_CREDENTIALS"
_DEFAULT_MARIADB_HOST = "haproxy-sidecar"
_DEFAULT_MARIADB_PORT = 3306
_DEFAULT_MARIADB_DATABASE = "agent_allowed"
_ACTIVE_ITEMS_QUERY = """
SELECT id, item_key, title, status, notes, quantity, created_at, updated_at
FROM items
WHERE status = 'active'
ORDER BY id
"""


class _MariaDBConnectionSettings(TypedDict):
    host: str
    port: int
    user: str
    password: str
    database: str


def get_html_element_name() -> str:
    """Return the HTML element that the sandbox agent should explain."""
    arguments: dict[str, str] = {}
    try:
        result = "<table>"
    except Exception as error:
        write_mcp_audit_record("tool", "get_html_element_name", arguments, error=error)
        raise

    write_mcp_audit_record("tool", "get_html_element_name", arguments, result=result)
    return result


async def microsoft_docs_search(query: str) -> str:
    """Search official Microsoft Learn documentation through upstream MCP."""
    arguments = {"query": query}
    return await _call_audited_microsoft_learn_tool(
        _MICROSOFT_DOCS_SEARCH_TOOL_NAME,
        arguments,
    )


async def microsoft_docs_fetch(url: str) -> str:
    """Fetch a Microsoft Learn documentation page through upstream MCP."""
    arguments = {"url": url}
    return await _call_audited_microsoft_learn_tool(
        _MICROSOFT_DOCS_FETCH_TOOL_NAME,
        arguments,
    )


async def microsoft_code_sample_search(query: str, language: str | None = None) -> str:
    """Search official Microsoft Learn code samples through upstream MCP."""
    arguments = {"query": query}
    if language:
        arguments["language"] = language

    return await _call_audited_microsoft_learn_tool(
        _MICROSOFT_CODE_SAMPLE_SEARCH_TOOL_NAME,
        arguments,
    )


async def jina_read_url(url: str) -> str:
    """Return Markdown content for a fully-qualified URL."""
    arguments = {"url": url}
    try:
        result = await asyncio.to_thread(_read_jina_url_sync, url)
    except Exception as error:
        write_mcp_audit_record("tool", _JINA_READ_URL_TOOL_NAME, arguments, error=error)
        raise

    write_mcp_audit_record("tool", _JINA_READ_URL_TOOL_NAME, arguments, result=result)
    return result


async def get_active_items() -> str:
    """Return active items from the configured MariaDB database."""
    arguments: dict[str, object] = _build_active_items_audit_arguments()
    try:
        result = await asyncio.to_thread(_get_active_items_sync)
    except Exception as error:
        write_mcp_audit_record(
            "tool",
            _GET_ACTIVE_ITEMS_TOOL_NAME,
            arguments,
            error=error,
        )
        raise

    write_mcp_audit_record(
        "tool",
        _GET_ACTIVE_ITEMS_TOOL_NAME,
        arguments,
        result=result,
    )
    return result


async def run_python_script(
    script: str,
    args: list[str] | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, object]:
    """Run a small Python script through the local code-execution sidecar."""
    arguments: dict[str, object] = {
        "script_length": len(script),
        "args_count": len(args or []),
    }
    if timeout_seconds is not None:
        arguments["timeout_seconds"] = timeout_seconds

    try:
        result = await asyncio.to_thread(
            _run_python_script_sync,
            script,
            args or [],
            timeout_seconds,
        )
    except Exception as error:
        write_mcp_audit_record(
            "tool",
            _RUN_PYTHON_SCRIPT_TOOL_NAME,
            arguments,
            error=error,
        )
        raise

    script_exit_code = result.get("exit_code")
    if isinstance(script_exit_code, int):
        arguments["script_exit_code"] = script_exit_code
    result_text = json.dumps(result, sort_keys=True)
    write_mcp_audit_record(
        "tool",
        _RUN_PYTHON_SCRIPT_TOOL_NAME,
        arguments,
        result=result_text,
    )
    return result


def _get_active_items_sync() -> str:
    connection_settings = _read_mariadb_connection_settings()
    connection = _connect_to_mariadb(connection_settings)
    try:
        with connection.cursor() as cursor:
            cursor.execute(_ACTIVE_ITEMS_QUERY)
            rows = cursor.fetchall()
    finally:
        connection.close()

    normalized_rows = [_normalize_database_row(row) for row in rows]
    return json.dumps(normalized_rows, sort_keys=True, default=str)


def _read_mariadb_connection_settings() -> _MariaDBConnectionSettings:
    username, password = _read_mariadb_credentials()
    return {
        "host": os.environ.get(
            _MARIADB_HOST_ENVIRONMENT_VARIABLE,
            _DEFAULT_MARIADB_HOST,
        ),
        "port": _read_mariadb_port(),
        "user": username,
        "password": password,
        "database": os.environ.get(
            _MARIADB_DATABASE_ENVIRONMENT_VARIABLE,
            _DEFAULT_MARIADB_DATABASE,
        ),
    }


def _read_mariadb_credentials() -> tuple[str, str]:
    value = os.environ.get(_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE)
    if value is None:
        raise RuntimeError(
            f"{_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE} is not configured."
        )

    username, separator, password = value.partition(",")
    if not separator or not username.strip() or not password:
        raise RuntimeError(
            f"{_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE} must use "
            "the format 'username,password'."
        )

    return username.strip(), password


def _read_mariadb_port() -> int:
    value = os.environ.get(_MARIADB_PORT_ENVIRONMENT_VARIABLE)
    if value is None:
        return _DEFAULT_MARIADB_PORT

    try:
        port = int(value)
    except ValueError as error:
        raise RuntimeError("MARIADB_PORT must be an integer TCP port.") from error

    if port < 1 or port > 65535:
        raise RuntimeError("MARIADB_PORT must be between 1 and 65535.")

    return port


def _connect_to_mariadb(connection_settings: _MariaDBConnectionSettings) -> Any:
    pymysql: Any = importlib.import_module("pymysql")

    return pymysql.connect(
        host=connection_settings["host"],
        port=connection_settings["port"],
        user=connection_settings["user"],
        password=connection_settings["password"],
        database=connection_settings["database"],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
    )


def _normalize_database_row(row: object) -> dict[str, object]:
    if isinstance(row, dict):
        return dict(row)

    raise RuntimeError("MariaDB query returned an unexpected row shape.")


def _build_active_items_audit_arguments() -> dict[str, object]:
    return {
        "host": os.environ.get(
            _MARIADB_HOST_ENVIRONMENT_VARIABLE,
            _DEFAULT_MARIADB_HOST,
        ),
        "port": os.environ.get(
            _MARIADB_PORT_ENVIRONMENT_VARIABLE,
            str(_DEFAULT_MARIADB_PORT),
        ),
        "database": os.environ.get(
            _MARIADB_DATABASE_ENVIRONMENT_VARIABLE,
            _DEFAULT_MARIADB_DATABASE,
        ),
    }


def _read_jina_url_sync(url: str) -> str:
    _validate_jina_reader_target_url(url)
    reader_url = _build_jina_reader_endpoint(url)
    try:
        with urlopen(reader_url, timeout=_JINA_READER_TIMEOUT_SECONDS) as response:
            status_code = response.getcode()
            body = response.read()
    except HTTPError as error:
        raise RuntimeError(
            f"Jina Reader returned HTTP {error.code} for URL: {url}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Jina Reader request failed for URL: {url}") from error

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"Jina Reader returned HTTP {status_code} for URL: {url}")

    return body.decode("utf-8", errors="replace")


def _run_python_script_sync(
    script: str,
    args: list[str],
    timeout_seconds: int | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "script": script,
        "args": args,
    }
    if timeout_seconds is not None:
        payload["timeout_seconds"] = timeout_seconds

    request = Request(
        _build_code_sidecar_endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = _resolve_code_sidecar_timeout(timeout_seconds)
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            body = response.read()
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Code sidecar returned HTTP {error.code}: {body}"
        ) from error
    except URLError as error:
        raise RuntimeError("Code sidecar request failed.") from error

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"Code sidecar returned HTTP {status_code}.")

    data = json.loads(body.decode("utf-8", errors="replace"))
    if not isinstance(data, dict):
        raise RuntimeError("Code sidecar did not return a JSON object.")

    return data


async def _call_audited_microsoft_learn_tool(
    tool_name: str, arguments: dict[str, str]
) -> str:
    try:
        result = await _call_microsoft_learn_tool(tool_name, arguments)
    except Exception as error:
        write_mcp_audit_record("tool", tool_name, arguments, error=error)
        raise

    write_mcp_audit_record("tool", tool_name, arguments, result=result)
    return result


async def _call_microsoft_learn_tool(tool_name: str, arguments: dict[str, str]) -> str:
    mcp_url = os.environ.get(
        _MICROSOFT_LEARN_MCP_URL_ENVIRONMENT_VARIABLE,
        _DEFAULT_MICROSOFT_LEARN_MCP_URL,
    )
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(mcp_url) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

    return _read_mcp_tool_result(result)


def _validate_jina_reader_target_url(url: str) -> None:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Jina Reader URL must be fully-qualified HTTP or HTTPS.")


def _build_jina_reader_endpoint(url: str) -> str:
    reader_base_url = os.environ.get(
        _JINA_READER_URL_ENVIRONMENT_VARIABLE,
        _DEFAULT_JINA_READER_URL,
    )
    encoded_url = quote(url, safe=":/?=&%")
    return f"{reader_base_url.rstrip('/')}/{encoded_url}"


def _build_code_sidecar_endpoint() -> str:
    sidecar_url = os.environ.get(
        _CODE_SIDECAR_URL_ENVIRONMENT_VARIABLE,
        _DEFAULT_CODE_SIDECAR_URL,
    )
    return f"{sidecar_url.rstrip('/')}/run"


def _resolve_code_sidecar_timeout(timeout_seconds: int | None) -> float:
    requested_timeout = 5 if timeout_seconds is None else max(timeout_seconds, 1)
    return min(requested_timeout, 30) + _CODE_SIDECAR_TIMEOUT_BUFFER_SECONDS


def _read_mcp_tool_result(result: Any) -> str:
    structured_content = getattr(result, "structuredContent", None)
    if structured_content is not None:
        return json.dumps(structured_content, indent=2)

    content_blocks = getattr(result, "content", ())
    text_blocks = [
        text
        for block in content_blocks
        if isinstance((text := getattr(block, "text", None)), str)
    ]
    if text_blocks:
        return "\n\n".join(text_blocks)

    raise RuntimeError("Microsoft Learn MCP tool did not return text content.")
