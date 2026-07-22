"""Tools provided by the MCP sidecar server."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .audit import write_mcp_audit_record

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
