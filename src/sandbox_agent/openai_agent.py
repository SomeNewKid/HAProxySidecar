"""AI agent that builds a simple HTML document through declared tools."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_DEFAULT_MODEL = "gpt-4.1-mini"
_AGENT_PROMPT = """
Create a single basic-style HTML document named index.html that explains the
HTML element returned by the get_html_element_name tool to a new developer at a
middle-school student level.

Use the get_html_element_name tool first. Then write a friendly, self-contained
page about that element. Include what the element is for, a tiny example, and a
short note about when to use it. Use embedded CSS in a <style> block so the page
is readable and pleasant, but keep the design simple.

Save the document with the save_html_document tool. After saving index.html,
save a short status message with the save_answer tool. The status message should
say which file was created and which HTML element it explains.
"""


def create_openai_agent(model: str = _DEFAULT_MODEL) -> Agent:
    """Create the Sandbox Agent HTML document generator."""
    from agents import Agent

    from .openai_tools import (
        get_html_element_name_tool,
        save_answer_tool,
        save_html_document_tool,
    )

    return Agent(
        name="HTML Element Document Generator",
        model=model,
        instructions=(
            "You are a careful web page builder. Use the provided tools to "
            "retrieve the required HTML element, save exactly one HTML file, "
            "and save the final status message. Do not finish until all three "
            "tool calls have succeeded."
        ),
        tools=[
            get_html_element_name_tool,
            save_html_document_tool,
            save_answer_tool,
        ],
    )


def run_html_element_agent(model: str = _DEFAULT_MODEL) -> str:
    """Run the HTML element agent and save its final response."""
    from agents import Runner

    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    result = Runner.run_sync(
        create_openai_agent(model),
        _AGENT_PROMPT,
        max_turns=10,
    )
    return str(result.final_output)
