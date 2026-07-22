"""Tests for Sandbox Agent tools."""

from __future__ import annotations

import pytest

from sandbox_agent.tools import (
    get_active_items,
    get_answer_format,
    get_html_element_name,
    jina_read_url,
    microsoft_code_sample_search,
    microsoft_docs_fetch,
    microsoft_docs_search,
    run_python_script,
    save_answer,
    validate_html5_element,
)


def test_validate_html5_element_accepts_element_name() -> None:
    """Verify HTML5 element validation accepts a plain element name."""
    result = validate_html5_element("main")

    assert result == {
        "element": "main",
        "is_html5": True,
    }


def test_validate_html5_element_normalizes_angle_brackets() -> None:
    """Verify HTML5 element validation accepts bracketed element names."""
    result = validate_html5_element("<IMG />")

    assert result == {
        "element": "img",
        "is_html5": True,
    }


def test_validate_html5_element_rejects_unknown_name() -> None:
    """Verify HTML5 element validation rejects unknown element names."""
    result = validate_html5_element("sparkle-box")

    assert result == {
        "element": "sparkle-box",
        "is_html5": False,
    }


def test_get_html_element_name_calls_mcp_sidecar(monkeypatch) -> None:
    """Verify the HTML element tool calls the configured MCP sidecar."""
    called_urls = []

    def fake_call_mcp_html_element_tool(sidecar_url: str) -> str:
        called_urls.append(sidecar_url)
        return "<div>"

    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr(
        "sandbox_agent.tools._call_mcp_html_element_tool",
        fake_call_mcp_html_element_tool,
    )

    element_name = get_html_element_name()

    assert element_name == "<div>"
    assert called_urls == ["http://mcp-sidecar:8000/mcp"]


def test_get_html_element_name_requires_mcp_sidecar_url(monkeypatch) -> None:
    """Verify the HTML element tool requires MCP sidecar connection info."""
    monkeypatch.delenv("MCP_SIDECAR_URL", raising=False)

    with pytest.raises(RuntimeError, match="MCP_SIDECAR_URL"):
        get_html_element_name()


def test_get_active_items_calls_mcp_sidecar(monkeypatch) -> None:
    """Verify active item lookups call the sidecar wrapper tool."""
    calls = []

    def fake_call(tool_name: str, arguments: dict[str, object]) -> str:
        calls.append((tool_name, arguments))
        return '[{"id": 2, "status": "active"}]'

    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr("sandbox_agent.tools._call_mcp_sidecar_tool", fake_call)

    assert get_active_items() == '[{"id": 2, "status": "active"}]'
    assert calls == [("get_active_items", {})]


def test_microsoft_docs_search_calls_mcp_sidecar(monkeypatch) -> None:
    """Verify Microsoft docs search calls the sidecar wrapper tool."""
    calls = []

    def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        calls.append((tool_name, arguments))
        return "search result"

    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr("sandbox_agent.tools._call_mcp_sidecar_tool", fake_call)

    assert microsoft_docs_search("MCP tool calling") == "search result"
    assert calls == [("microsoft_docs_search", {"query": "MCP tool calling"})]


def test_microsoft_docs_fetch_calls_mcp_sidecar(monkeypatch) -> None:
    """Verify Microsoft docs fetch calls the sidecar wrapper tool."""
    calls = []

    def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        calls.append((tool_name, arguments))
        return "markdown"

    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr("sandbox_agent.tools._call_mcp_sidecar_tool", fake_call)

    assert microsoft_docs_fetch("https://learn.microsoft.com/test") == "markdown"
    assert calls == [
        ("microsoft_docs_fetch", {"url": "https://learn.microsoft.com/test"})
    ]


def test_microsoft_code_sample_search_calls_mcp_sidecar(monkeypatch) -> None:
    """Verify Microsoft code sample search calls the sidecar wrapper tool."""
    calls = []

    def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        calls.append((tool_name, arguments))
        return "code"

    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr("sandbox_agent.tools._call_mcp_sidecar_tool", fake_call)

    assert microsoft_code_sample_search("agent framework", "python") == "code"
    assert calls == [
        (
            "microsoft_code_sample_search",
            {"query": "agent framework", "language": "python"},
        )
    ]


def test_jina_read_url_calls_mcp_sidecar(monkeypatch) -> None:
    """Verify Jina Reader calls the sidecar wrapper tool."""
    calls = []

    def fake_call(tool_name: str, arguments: dict[str, str]) -> str:
        calls.append((tool_name, arguments))
        return "markdown"

    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr("sandbox_agent.tools._call_mcp_sidecar_tool", fake_call)

    assert jina_read_url("https://www.nibblon.com/movies/10") == "markdown"
    assert calls == [("jina_read_url", {"url": "https://www.nibblon.com/movies/10"})]


def test_run_python_script_calls_mcp_sidecar(monkeypatch) -> None:
    """Verify Python execution calls the sidecar wrapper tool."""
    calls = []

    def fake_call(tool_name: str, arguments: dict[str, object]) -> str:
        calls.append((tool_name, arguments))
        return '{"exit_code": 0, "stdout": "42\\n"}'

    script = "def main(argv):\n    print(42)\n    return 0\n"
    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr("sandbox_agent.tools._call_mcp_sidecar_tool", fake_call)

    result = run_python_script(script, args=["x"], timeout_seconds=5)

    assert result == '{"exit_code": 0, "stdout": "42\\n"}'
    assert calls == [
        (
            "run_python_script",
            {
                "script": script,
                "args": ["x"],
                "timeout_seconds": 5,
            },
        )
    ]


def test_get_answer_format_reads_mcp_sidecar_resource(monkeypatch) -> None:
    """Verify answer format reads the configured MCP sidecar resource."""
    calls = []

    def fake_call(sidecar_url: str, resource_uri: str) -> str:
        calls.append((sidecar_url, resource_uri))
        return "## Recommended Approach"

    monkeypatch.setenv("MCP_SIDECAR_URL", "http://mcp-sidecar:8000/mcp")
    monkeypatch.setattr("sandbox_agent.tools._call_mcp_resource", fake_call)

    assert get_answer_format() == "## Recommended Approach"
    assert calls == [
        (
            "http://mcp-sidecar:8000/mcp",
            "mcp-sidecar://instructions/answer-format.md",
        )
    ]


def test_save_answer_writes_answer_file(tmp_path, monkeypatch) -> None:
    """Verify answer text is saved to the sandbox output directory."""
    answer_path = tmp_path / "answer.txt"
    monkeypatch.setattr("sandbox_agent.tools._ANSWER_FILE_PATH", answer_path)

    result = save_answer("Answer text")

    assert result == {
        "success": True,
        "message": "Created answer.txt",
    }
    assert answer_path.read_text(encoding="utf-8") == "Answer text"
