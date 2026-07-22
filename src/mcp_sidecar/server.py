"""MCP server construction for the sidecar container."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .resources import ANSWER_FORMAT_RESOURCE_URI, get_answer_format
from .tools import (
    get_html_element_name,
    jina_read_url,
    microsoft_code_sample_search,
    microsoft_docs_fetch,
    microsoft_docs_search,
    run_python_script,
)

_SERVER_NAME = "McpSidecar"
_SERVER_INSTRUCTIONS = (
    "Expose only the tools and resources enabled by the sandbox specification. "
    "Use these capabilities to retrieve permitted content or task instructions "
    "for the sandboxed AI agent."
)
_EXPOSURE_PATH_ENVIRONMENT_VARIABLE = "MCP_SIDECAR_EXPOSURE_PATH"


@dataclass(frozen=True)
class _ToolDefinition:
    name: str
    description: str
    handler: Callable[..., Any]


@dataclass(frozen=True)
class _ResourceDefinition:
    name: str
    uri: str
    description: str
    mime_type: str
    handler: Callable[..., Any]


_TOOL_REGISTRY = {
    "get_html_element_name": _ToolDefinition(
        name="get_html_element_name",
        description=(
            "Return the configured HTML element name for legacy HTML explanation "
            "tasks. Use only when the task asks which HTML element should be "
            "explained. Returns a short string containing the element name."
        ),
        handler=get_html_element_name,
    ),
    "microsoft_docs_search": _ToolDefinition(
        name="microsoft_docs_search",
        description=(
            "Search official Microsoft Learn documentation for pages relevant to "
            "a query. Use when authoritative Microsoft product, platform, API, "
            "or SDK documentation is needed. Returns search results with page "
            "metadata and snippets; use microsoft_docs_fetch to read a selected "
            "page."
        ),
        handler=microsoft_docs_search,
    ),
    "microsoft_docs_fetch": _ToolDefinition(
        name="microsoft_docs_fetch",
        description=(
            "Fetch a specific Microsoft Learn documentation page and return its "
            "content as Markdown text. Use after identifying a relevant Learn "
            "URL, especially when exact API behavior, parameters, examples, or "
            "remarks are needed from one documentation page."
        ),
        handler=microsoft_docs_fetch,
    ),
    "microsoft_code_sample_search": _ToolDefinition(
        name="microsoft_code_sample_search",
        description=(
            "Search official Microsoft Learn code samples for examples matching "
            "a query. Use when sample code, repository examples, or SDK usage "
            "patterns are needed rather than prose documentation. Returns "
            "matching sample metadata and snippets that can guide code or "
            "implementation choices."
        ),
        handler=microsoft_code_sample_search,
    ),
    "jina_read_url": _ToolDefinition(
        name="jina_read_url",
        description=(
            "Fetch a fully-qualified http or https URL through the local Jina "
            "Reader service and return the readable page or document content as "
            "cleaned Markdown-like text. Use when the agent needs the contents "
            "of a web page, PDF, or document URL before summarizing, extracting "
            "facts, or answering questions about it. This tool retrieves and "
            "converts content; it does not summarize by itself."
        ),
        handler=jina_read_url,
    ),
    "run_python_script": _ToolDefinition(
        name="run_python_script",
        description=(
            "The tool runs one small Python script. "
            "The tool returns structured execution metadata, including exit_code, "
            "stdout, stderr, timeout, duration, and truncation flags."
            "The submitted script must define main(argv), "
            "print its primary result to stdout, and return an integer exit code. "
            "Put executable logic inside main(argv). "
            "Top-level code may only contain imports, constants, "
            "function definitions, and class definitions. "
            "Only allowlisted Python standard-library modules may be imported, "
            "such as math, statistics, decimal, fractions, datetime, json, csv, "
            "re, collections, itertools, functools, hashlib, heapq, bisect, "
            "and textwrap. "
            "Common modules including sys, os, pathlib, subprocess, socket, "
            "threading, multiprocessing, urllib, and io are not available."
        ),
        handler=run_python_script,
    ),
}
_RESOURCE_REGISTRY = {
    "answer_format": _ResourceDefinition(
        name="answer_format",
        uri=ANSWER_FORMAT_RESOURCE_URI,
        description=(
            "Return the required Markdown response format for tasks that opt "
            "into a fixed answer structure. Use before composing a final answer "
            "when the sandbox specification exposes this resource. Returns "
            "formatting instructions that should be followed exactly."
        ),
        mime_type="text/markdown",
        handler=get_answer_format,
    ),
}


def create_mcp_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    tool_names: tuple[str, ...] | None = None,
    resource_names: tuple[str, ...] | None = None,
) -> FastMCP:
    """Create the MCP sidecar server."""
    exposure = _resolve_exposure(tool_names, resource_names)
    server = FastMCP(
        name=_SERVER_NAME,
        instructions=_SERVER_INSTRUCTIONS,
        host=host,
        port=port,
    )
    _register_tools(server, exposure[0])
    _register_resources(server, exposure[1])
    return server


def _resolve_exposure(
    tool_names: tuple[str, ...] | None,
    resource_names: tuple[str, ...] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if tool_names is not None or resource_names is not None:
        return tool_names or (), resource_names or ()

    exposure_path = os.environ.get(_EXPOSURE_PATH_ENVIRONMENT_VARIABLE)
    if not exposure_path:
        return (), ()

    return _read_exposure_file(Path(exposure_path))


def _read_exposure_file(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(
            f"MCP sidecar exposure file could not be read: {path}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"MCP sidecar exposure file is not valid JSON: {path}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError("MCP sidecar exposure must be a JSON object.")

    tools = _read_name_list(data, "tools")
    resources = _read_name_list(data, "resources")
    return tools, resources


def _read_name_list(data: dict[str, object], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeError(f"MCP sidecar exposure key must be a string list: {key}")

    return tuple(value)


def _register_tools(server: FastMCP, tool_names: tuple[str, ...]) -> None:
    for tool_name in tool_names:
        tool = _TOOL_REGISTRY.get(tool_name)
        if tool is None:
            raise RuntimeError(f"Unknown MCP sidecar tool: {tool_name}")

        server.tool(name=tool.name, description=tool.description)(tool.handler)


def _register_resources(server: FastMCP, resource_names: tuple[str, ...]) -> None:
    for resource_name in resource_names:
        resource = _RESOURCE_REGISTRY.get(resource_name)
        if resource is None:
            raise RuntimeError(f"Unknown MCP sidecar resource: {resource_name}")

        server.resource(
            uri=resource.uri,
            name=resource.name,
            description=resource.description,
            mime_type=resource.mime_type,
        )(resource.handler)
