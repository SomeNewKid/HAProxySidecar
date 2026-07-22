"""Tests for the MCP sidecar package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from mcp_sidecar.cli import _parse_arguments
from mcp_sidecar.resources import ANSWER_FORMAT_RESOURCE_URI, get_answer_format
from mcp_sidecar.server import create_mcp_server
from mcp_sidecar.tools import (
    get_html_element_name,
    jina_read_url,
    microsoft_code_sample_search,
    microsoft_docs_fetch,
    microsoft_docs_search,
    run_python_script,
)


def test_get_html_element_name_returns_table() -> None:
    """Verify the initial MCP tool returns the expected element."""
    assert get_html_element_name() == "<table>"


def test_get_html_element_name_writes_audit_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify local sidecar tool calls are written to the audit log."""
    audit_log_path = tmp_path / "mcp-sidecar-tool-calls.jsonl"
    monkeypatch.setenv("MCP_SIDECAR_AUDIT_LOG_PATH", str(audit_log_path))

    assert get_html_element_name() == "<table>"

    records = _read_jsonl(audit_log_path)
    assert records[0]["tool"] == "get_html_element_name"
    assert records[0]["arguments"] == {}
    assert records[0]["success"] is True
    assert records[0]["result_preview"] == "<table>"


def test_get_answer_format_writes_audit_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify sidecar resource reads are written to the audit log."""
    audit_log_path = tmp_path / "mcp-sidecar-tool-calls.jsonl"
    monkeypatch.setenv("MCP_SIDECAR_AUDIT_LOG_PATH", str(audit_log_path))

    answer_format = get_answer_format()

    records = _read_jsonl(audit_log_path)
    assert "## Recommended Approach" in answer_format
    assert records[0]["type"] == "resource"
    assert records[0]["resource"] == ANSWER_FORMAT_RESOURCE_URI
    assert records[0]["arguments"] == {}
    assert records[0]["success"] is True
    assert "## Recommended Approach" in str(records[0]["result_preview"])


@pytest.mark.anyio
async def test_jina_read_url_calls_local_reader_endpoint(monkeypatch) -> None:
    """Verify Jina Reader receives the fully-qualified URL through its prefix route."""
    requested_urls = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            _ = args

        def getcode(self) -> int:
            return 200

        def read(self) -> bytes:
            return b"# Example\n\nReader output."

    def fake_urlopen(url: str, timeout: float) -> FakeResponse:
        requested_urls.append((url, timeout))
        return FakeResponse()

    monkeypatch.setenv("JINA_READER_URL", "http://jina-reader:8081")
    monkeypatch.setattr("mcp_sidecar.tools.urlopen", fake_urlopen)

    result = await jina_read_url("https://example.com/docs?q=hello world#section")

    assert result == "# Example\n\nReader output."
    assert requested_urls == [
        (
            "http://jina-reader:8081/"
            "https://example.com/docs?q=hello%20world%23section",
            60.0,
        )
    ]


@pytest.mark.anyio
async def test_run_python_script_calls_code_sidecar(monkeypatch) -> None:
    """Verify Python execution requests are forwarded to the code sidecar."""
    requested_payloads = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            _ = args

        def getcode(self) -> int:
            return 200

        def read(self) -> bytes:
            return (
                b'{"exit_code": 0, "stdout": "42\\n", "stderr": "", '
                b'"timed_out": false, "duration_ms": 10, '
                b'"stdout_truncated": false, "stderr_truncated": false}'
            )

    def fake_urlopen(request, timeout: float) -> FakeResponse:
        requested_payloads.append((request.full_url, request.data, timeout))
        return FakeResponse()

    monkeypatch.setenv("CODE_SIDECAR_URL", "http://code-sidecar:8090")
    monkeypatch.setattr("mcp_sidecar.tools.urlopen", fake_urlopen)

    result = await run_python_script(
        "def main(argv):\n    print(42)\n    return 0\n",
        args=["x"],
        timeout_seconds=3,
    )

    assert result["exit_code"] == 0
    assert result["stdout"] == "42\n"
    assert requested_payloads[0][0] == "http://code-sidecar:8090/run"
    assert json.loads(requested_payloads[0][1]) == {
        "script": "def main(argv):\n    print(42)\n    return 0\n",
        "args": ["x"],
        "timeout_seconds": 3,
    }
    assert requested_payloads[0][2] == 5.0


@pytest.mark.anyio
async def test_run_python_script_audits_metadata_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify MCP audit logs omit submitted source code."""
    audit_log_path = tmp_path / "mcp-sidecar-tool-calls.jsonl"

    def fake_run(script: str, args: list[str], timeout_seconds: int | None):
        _ = script
        _ = args
        _ = timeout_seconds
        return {
            "exit_code": 0,
            "stdout": "ok\n",
            "stderr": "",
            "timed_out": False,
            "duration_ms": 10,
            "stdout_truncated": False,
            "stderr_truncated": False,
        }

    monkeypatch.setenv("MCP_SIDECAR_AUDIT_LOG_PATH", str(audit_log_path))
    monkeypatch.setattr("mcp_sidecar.tools._run_python_script_sync", fake_run)

    await run_python_script("def main(argv):\n    print('secret')\n", ["a"], 5)

    records = _read_jsonl(audit_log_path)
    assert records[0]["tool"] == "run_python_script"
    assert records[0]["arguments"] == {
        "script_length": 36,
        "args_count": 1,
        "timeout_seconds": 5,
        "script_exit_code": 0,
    }
    assert "secret" not in json.dumps(records[0])


@pytest.mark.anyio
async def test_jina_read_url_rejects_non_http_urls() -> None:
    """Verify Jina Reader only accepts fully-qualified HTTP or HTTPS URLs."""
    with pytest.raises(ValueError, match="fully-qualified HTTP or HTTPS"):
        await jina_read_url("file:///etc/passwd")


@pytest.mark.anyio
async def test_jina_read_url_rejects_relative_urls() -> None:
    """Verify Jina Reader rejects URLs without a host."""
    with pytest.raises(ValueError, match="fully-qualified HTTP or HTTPS"):
        await jina_read_url("/docs/page")


@pytest.mark.anyio
async def test_jina_read_url_raises_clear_error_for_non_success(monkeypatch) -> None:
    """Verify non-2xx Reader responses produce clear errors."""

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            _ = args

        def getcode(self) -> int:
            return 502

        def read(self) -> bytes:
            return b"bad gateway"

    def fake_urlopen(url: str, timeout: float) -> FakeResponse:
        _ = url
        _ = timeout
        return FakeResponse()

    monkeypatch.setattr("mcp_sidecar.tools.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Jina Reader returned HTTP 502"):
        await jina_read_url("https://example.com")


@pytest.mark.anyio
async def test_jina_read_url_writes_audit_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Jina Reader tool calls are written to the audit log."""
    audit_log_path = tmp_path / "mcp-sidecar-tool-calls.jsonl"

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            _ = args

        def getcode(self) -> int:
            return 200

        def read(self) -> bytes:
            return b"# Example\n\nReader output."

    def fake_urlopen(url: str, timeout: float) -> FakeResponse:
        _ = url
        _ = timeout
        return FakeResponse()

    monkeypatch.setenv("MCP_SIDECAR_AUDIT_LOG_PATH", str(audit_log_path))
    monkeypatch.setattr("mcp_sidecar.tools.urlopen", fake_urlopen)

    result = await jina_read_url("https://example.com")

    records = _read_jsonl(audit_log_path)
    assert result == "# Example\n\nReader output."
    assert records[0]["tool"] == "jina_read_url"
    assert records[0]["arguments"] == {"url": "https://example.com"}
    assert records[0]["success"] is True
    assert records[0]["result_length"] == len(result)
    assert records[0]["result_preview"] == "# Example\n\nReader output."


@pytest.mark.anyio
async def test_jina_read_url_audits_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify failed Jina Reader tool calls are written to the audit log."""
    audit_log_path = tmp_path / "mcp-sidecar-tool-calls.jsonl"

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            _ = args

        def getcode(self) -> int:
            return 502

        def read(self) -> bytes:
            return b"bad gateway"

    def fake_urlopen(url: str, timeout: float) -> FakeResponse:
        _ = url
        _ = timeout
        return FakeResponse()

    monkeypatch.setenv("MCP_SIDECAR_AUDIT_LOG_PATH", str(audit_log_path))
    monkeypatch.setattr("mcp_sidecar.tools.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Jina Reader returned HTTP 502"):
        await jina_read_url("https://example.com")

    records = _read_jsonl(audit_log_path)
    assert records[0]["tool"] == "jina_read_url"
    assert records[0]["arguments"] == {"url": "https://example.com"}
    assert records[0]["success"] is False
    assert records[0]["error_type"] == "RuntimeError"
    assert records[0]["error"] == (
        "Jina Reader returned HTTP 502 for URL: https://example.com"
    )


@pytest.mark.anyio
async def test_mcp_server_exposes_html_element_tool() -> None:
    """Verify the MCP server exposes and runs the HTML element tool."""
    server = create_mcp_server(tool_names=("get_html_element_name",))

    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}
    result = await server.call_tool("get_html_element_name", {})
    content_blocks, structured_content = cast(tuple[list[Any], dict[str, str]], result)

    assert "get_html_element_name" in tool_names
    assert content_blocks[0].text == "<table>"
    assert structured_content == {"result": "<table>"}


@pytest.mark.anyio
async def test_mcp_server_exposes_answer_format_resource() -> None:
    """Verify the MCP server exposes and reads the answer format resource."""
    server = create_mcp_server(resource_names=("answer_format",))

    resources = await server.list_resources()
    resource_uris = {str(resource.uri) for resource in resources}
    result = await server.read_resource(ANSWER_FORMAT_RESOURCE_URI)
    contents = list(result)
    content = contents[0].content

    assert ANSWER_FORMAT_RESOURCE_URI in resource_uris
    assert isinstance(content, str)
    assert "## Recommended Approach" in content
    assert contents[0].mime_type == "text/markdown"


def test_mcp_server_exposes_microsoft_learn_wrapper_tools() -> None:
    """Verify the sidecar exposes Microsoft Learn proxy wrapper tools."""
    server = create_mcp_server(
        tool_names=(
            "microsoft_docs_search",
            "microsoft_docs_fetch",
            "microsoft_code_sample_search",
        )
    )

    tools = anyio.run(server.list_tools)
    tool_names = {tool.name for tool in tools}

    assert "microsoft_docs_search" in tool_names
    assert "microsoft_docs_fetch" in tool_names
    assert "microsoft_code_sample_search" in tool_names


def test_mcp_server_exposes_jina_reader_tool() -> None:
    """Verify the sidecar exposes the Jina Reader wrapper tool."""
    server = create_mcp_server(tool_names=("jina_read_url",))

    tools = anyio.run(server.list_tools)
    tool_names = {tool.name for tool in tools}

    assert "jina_read_url" in tool_names


def test_mcp_server_exposes_code_execution_tool() -> None:
    """Verify the sidecar exposes the Python execution wrapper tool."""
    server = create_mcp_server(tool_names=("run_python_script",))

    tools = anyio.run(server.list_tools)
    tool_names = {tool.name for tool in tools}

    assert "run_python_script" in tool_names


def test_mcp_server_exposes_nothing_by_default(monkeypatch) -> None:
    """Verify MCP tools and resources are disabled unless explicitly configured."""
    monkeypatch.delenv("MCP_SIDECAR_EXPOSURE_PATH", raising=False)
    server = create_mcp_server()

    tools = anyio.run(server.list_tools)
    resources = anyio.run(server.list_resources)

    assert tools == []
    assert resources == []


def test_mcp_server_rejects_unknown_tool() -> None:
    """Verify unknown MCP tool names fail closed."""
    with pytest.raises(RuntimeError, match="Unknown MCP sidecar tool"):
        create_mcp_server(tool_names=("missing_tool",))


def test_mcp_server_rejects_unknown_resource() -> None:
    """Verify unknown MCP resource names fail closed."""
    with pytest.raises(RuntimeError, match="Unknown MCP sidecar resource"):
        create_mcp_server(resource_names=("missing_resource",))


@pytest.mark.anyio
async def test_microsoft_docs_search_calls_upstream_tool(monkeypatch) -> None:
    """Verify Microsoft docs search forwards to the upstream MCP tool."""
    calls = []

    async def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        calls.append((tool_name, arguments))
        return "search result"

    monkeypatch.setattr("mcp_sidecar.tools._call_microsoft_learn_tool", fake_call)

    assert await microsoft_docs_search("azure functions") == "search result"
    assert calls == [("microsoft_docs_search", {"query": "azure functions"})]


@pytest.mark.anyio
async def test_microsoft_docs_search_writes_audit_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify Microsoft wrapper calls are written to the audit log."""
    audit_log_path = tmp_path / "mcp-sidecar-tool-calls.jsonl"

    async def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        _ = tool_name
        _ = arguments
        return "search result"

    monkeypatch.setenv("MCP_SIDECAR_AUDIT_LOG_PATH", str(audit_log_path))
    monkeypatch.setattr("mcp_sidecar.tools._call_microsoft_learn_tool", fake_call)

    assert await microsoft_docs_search("azure functions") == "search result"

    records = _read_jsonl(audit_log_path)
    assert records[0]["tool"] == "microsoft_docs_search"
    assert records[0]["arguments"] == {"query": "azure functions"}
    assert records[0]["success"] is True
    assert records[0]["result_preview"] == "search result"


@pytest.mark.anyio
async def test_microsoft_docs_search_audits_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify failed Microsoft wrapper calls are written to the audit log."""
    audit_log_path = tmp_path / "mcp-sidecar-tool-calls.jsonl"

    async def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        _ = tool_name
        _ = arguments
        raise RuntimeError("upstream failed")

    monkeypatch.setenv("MCP_SIDECAR_AUDIT_LOG_PATH", str(audit_log_path))
    monkeypatch.setattr("mcp_sidecar.tools._call_microsoft_learn_tool", fake_call)

    with pytest.raises(RuntimeError, match="upstream failed"):
        await microsoft_docs_search("azure functions")

    records = _read_jsonl(audit_log_path)
    assert records[0]["tool"] == "microsoft_docs_search"
    assert records[0]["arguments"] == {"query": "azure functions"}
    assert records[0]["success"] is False
    assert records[0]["error_type"] == "RuntimeError"
    assert records[0]["error"] == "upstream failed"


@pytest.mark.anyio
async def test_microsoft_docs_fetch_calls_upstream_tool(monkeypatch) -> None:
    """Verify Microsoft docs fetch forwards to the upstream MCP tool."""
    calls = []

    async def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        calls.append((tool_name, arguments))
        return "markdown"

    monkeypatch.setattr("mcp_sidecar.tools._call_microsoft_learn_tool", fake_call)

    result = await microsoft_docs_fetch("https://learn.microsoft.com/test")

    assert result == "markdown"
    assert calls == [
        ("microsoft_docs_fetch", {"url": "https://learn.microsoft.com/test"})
    ]


@pytest.mark.anyio
async def test_microsoft_code_sample_search_calls_upstream_tool(monkeypatch) -> None:
    """Verify Microsoft code search forwards query and language upstream."""
    calls = []

    async def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        calls.append((tool_name, arguments))
        return "code result"

    monkeypatch.setattr("mcp_sidecar.tools._call_microsoft_learn_tool", fake_call)

    result = await microsoft_code_sample_search("blob storage", "python")

    assert result == "code result"
    assert calls == [
        (
            "microsoft_code_sample_search",
            {"query": "blob storage", "language": "python"},
        )
    ]


def test_parse_arguments_defaults_to_streamable_http() -> None:
    """Verify the sidecar defaults to an HTTP transport for containers."""
    arguments = _parse_arguments([])

    assert arguments.transport == "streamable-http"
    assert arguments.host == "0.0.0.0"
    assert arguments.port == 8000


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
