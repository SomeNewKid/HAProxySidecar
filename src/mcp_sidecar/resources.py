"""Resources provided by the MCP sidecar server."""

from __future__ import annotations

from .audit import write_mcp_audit_record

ANSWER_FORMAT_RESOURCE_URI = "mcp-sidecar://instructions/answer-format.md"
_ANSWER_FORMAT = """# Answer Format

Every answer must use this structure:

## Recommended Approach

State the recommended approach in one or two sentences.

## Code Sample

Provide the most relevant code sample in a fenced code block.

## Notes

Include important caveats, alternatives, or source context.
"""


def get_answer_format() -> str:
    """Return the required answer format for sandbox agent responses."""
    arguments: dict[str, str] = {}
    try:
        result = _ANSWER_FORMAT
    except Exception as error:
        write_mcp_audit_record(
            "resource",
            ANSWER_FORMAT_RESOURCE_URI,
            arguments,
            error=error,
        )
        raise

    write_mcp_audit_record(
        "resource",
        ANSWER_FORMAT_RESOURCE_URI,
        arguments,
        result=result,
    )
    return result
