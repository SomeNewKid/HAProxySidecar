"""AI agent that builds a simple HTML document through local sidecars."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent
    from agents.models.interface import Model

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_ANSWER_FILE_PATH = _OUTPUT_DIRECTORY / "answer.txt"
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_DEFAULT_MODEL = "qwen3:0.6b"
_HTML_DOCUMENT_PROMPT_TEMPLATE = """
Return a single basic-style HTML document that explains the
{element_name} HTML element to a new developer at a middle-school student level.

Write a friendly, self-contained page about that element. Include
what the element is for, a tiny example, and a short note about when to use it.
Use embedded CSS in a <style> block so the page is readable and pleasant, but
keep the design simple.

Return only the complete HTML document. Do not use markdown fences.
"""
_OPENAI_API_KEY_ENVIRONMENT_VARIABLE = "OPENAI_API_KEY"
_OPENAI_BASE_URL_ENVIRONMENT_VARIABLE = "OPENAI_BASE_URL"
_OLLAMA_MODEL_ENVIRONMENT_VARIABLE = "OLLAMA_MODEL"
_DEFAULT_API_KEY = "ollama"


def create_openai_agent(model: str | None = None) -> Agent:
    """Create the Sandbox Agent HTML document generator."""
    from agents import Agent
    from agents.model_settings import ModelSettings

    selected_model = _resolve_model(model)
    chat_model = _create_openai_compatible_chat_model(selected_model)
    return Agent(
        name="HTML Element Document Generator",
        instructions=(
            "You are a careful web page builder. Return one complete HTML "
            "document. Do not use local resources or tools."
        ),
        model=chat_model,
        model_settings=ModelSettings(temperature=0),
        tools=[],
    )


def run_ollama_smoke_agent(model: str | None = None) -> str:
    """Run the current Ollama-backed Sandbox Agent workload."""
    return run_html_element_agent(model)


def run_html_element_agent(model: str | None = None) -> str:
    """Run the HTML element agent and save its final response."""
    from agents import Runner, set_tracing_disabled

    set_tracing_disabled(True)
    selected_model = _resolve_model(model)
    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    element_name = _get_html_element_name_from_mcp()
    html_prompt = _HTML_DOCUMENT_PROMPT_TEMPLATE.format(element_name=element_name)
    result = Runner.run_sync(
        create_openai_agent(selected_model), html_prompt, max_turns=1
    )
    html_document = _read_html_document(result.final_output)
    _save_html_document(html_document)
    answer_text = f"index.html was created for {element_name}."
    _save_answer(answer_text)
    return answer_text


def _resolve_model(model: str | None) -> str:
    if model:
        return model

    configured_model = os.environ.get(_OLLAMA_MODEL_ENVIRONMENT_VARIABLE)
    if configured_model:
        return configured_model

    return _DEFAULT_MODEL


def _get_html_element_name_from_mcp() -> str:
    from .tools import get_html_element_name

    element_name = get_html_element_name().strip()
    if not element_name:
        raise RuntimeError("MCP sidecar did not return an HTML element name.")

    return element_name


def _create_openai_compatible_chat_model(model: str) -> Model:
    base_url = os.environ.get(_OPENAI_BASE_URL_ENVIRONMENT_VARIABLE)
    if not base_url:
        raise RuntimeError("OPENAI_BASE_URL is not configured.")

    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=os.environ.get(_OPENAI_API_KEY_ENVIRONMENT_VARIABLE, _DEFAULT_API_KEY),
        base_url=base_url,
    )
    return OpenAIChatCompletionsModel(
        model=model,
        openai_client=client,
    )


def _read_final_output(final_output: object) -> str:
    if not isinstance(final_output, str) or not final_output.strip():
        raise RuntimeError("OpenAI Agents SDK response did not include text content.")

    return final_output.strip()


def _read_html_document(final_output: object) -> str:
    html_document = _read_final_output(final_output)
    html_document = html_document.removeprefix("```html").removeprefix("```")
    html_document = html_document.removesuffix("```").strip()
    if "<html" not in html_document.lower():
        raise RuntimeError(
            "OpenAI Agents SDK response did not include an HTML document."
        )

    return html_document


def _save_html_document(html_document: str) -> None:
    from .tools import save_html_document

    result = save_html_document("index.html", html_document)
    if result.get("success") is not True:
        message = result.get("message", "Failed to create index.html")
        raise RuntimeError(str(message))


def _save_answer(answer: str) -> None:
    _ANSWER_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ANSWER_FILE_PATH.write_text(answer, encoding="utf-8")
