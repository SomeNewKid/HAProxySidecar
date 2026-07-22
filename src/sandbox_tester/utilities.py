"""Utilities for the Sandbox Tester."""

from .models import CapabilityGroupResult


def render_markdown_report(groups: list[CapabilityGroupResult]) -> str:
    lines: list[str] = []
    lines.append("# Sandbox Report")
    lines.append("")

    for group in groups:
        lines.append(f"## {group.id}. {group.title}")
        lines.append("")
        if not group.capabilities:
            lines.append("No capabilities were tested in this group.")
        else:
            lines.append("| Shell | Tool | Alternate Shell | ID | Title |")
            lines.append("| --- | --- | --- | --- | --- |")

            for capability in group.capabilities:
                lines.append(
                    "| "
                    f"{capability.shell.outcome} | "
                    f"{capability.tool.outcome} | "
                    f"{capability.alternates.outcome} | "
                    f"{capability.id} | "
                    f"{capability.title} |"
                )

        lines.append("")

    return "\n".join(lines)
