"""Tests for the Ollama-backed Sandbox Agent workload."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

from sandbox_agent.openai_agent import run_html_element_agent, run_ollama_smoke_agent


def test_run_html_element_agent_uses_ollama_and_html_tools(
    tmp_path,
    monkeypatch,
) -> None:
    """Verify the workload uses Ollama through Agents SDK and HTML tools."""
    answer_path = tmp_path / "answer.txt"
    site_path = tmp_path / "site"
    calls = []

    class _FakeAsyncOpenAI:
        def __init__(self, api_key: str, base_url: str) -> None:
            calls.append(
                {
                    "type": "client",
                    "api_key": api_key,
                    "base_url": base_url,
                }
            )

    class _FakeChatCompletionsModel:
        def __init__(self, model: str, openai_client: _FakeAsyncOpenAI) -> None:
            calls.append(
                {
                    "type": "model",
                    "model": model,
                    "openai_client": openai_client,
                }
            )

    class _FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            calls.append({"type": "agent", **kwargs})

    class _FakeModelSettings:
        def __init__(self, **kwargs: Any) -> None:
            calls.append({"type": "model_settings", **kwargs})

    class _FakeRunner:
        @staticmethod
        def run_sync(
            agent: _FakeAgent,
            prompt: str,
            max_turns: int,
        ) -> SimpleNamespace:
            calls.append(
                {
                    "type": "run",
                    "agent": agent,
                    "prompt": prompt,
                    "max_turns": max_turns,
                }
            )
            return SimpleNamespace(
                final_output="<html><body><h1>Table</h1></body></html>"
            )

    def _fake_set_tracing_disabled(disabled: bool) -> None:
        calls.append({"type": "tracing", "disabled": disabled})

    _install_fake_agent_dependencies(
        monkeypatch,
        async_openai=_FakeAsyncOpenAI,
        chat_completions_model=_FakeChatCompletionsModel,
        agent=_FakeAgent,
        runner=_FakeRunner,
        model_settings=_FakeModelSettings,
        set_tracing_disabled_func=_fake_set_tracing_disabled,
    )
    monkeypatch.setenv("OPENAI_BASE_URL", "http://ollama-sidecar:11434/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:0.6b")
    monkeypatch.setattr("sandbox_agent.openai_agent._ANSWER_FILE_PATH", answer_path)
    monkeypatch.setattr("sandbox_agent.openai_agent._SITE_DIRECTORY", site_path)
    monkeypatch.setattr(
        "sandbox_agent.openai_agent._get_html_element_name_from_mcp",
        lambda: "<table>",
    )
    monkeypatch.setattr(
        "sandbox_agent.openai_agent._save_html_document",
        lambda html_document: calls.append(
            {
                "type": "save",
                "html_document": html_document,
            }
        ),
    )

    result = run_html_element_agent()

    assert result == "index.html was created for <table>."
    assert (
        answer_path.read_text(encoding="utf-8") == "index.html was created for <table>."
    )
    assert site_path.exists()
    assert calls[0] == {
        "type": "tracing",
        "disabled": True,
    }
    assert calls[1] == {
        "type": "client",
        "api_key": "ollama",
        "base_url": "http://ollama-sidecar:11434/v1",
    }
    assert calls[2]["type"] == "model"
    assert calls[2]["model"] == "qwen3:0.6b"
    assert calls[3] == {
        "type": "model_settings",
        "temperature": 0,
    }
    assert calls[4]["type"] == "agent"
    assert calls[4]["name"] == "HTML Element Document Generator"
    assert calls[4]["tools"] == []
    assert calls[5]["type"] == "run"
    assert "<table>" in calls[5]["prompt"]
    assert calls[5]["max_turns"] == 1
    assert calls[6] == {
        "type": "save",
        "html_document": "<html><body><h1>Table</h1></body></html>",
    }


def test_run_html_element_agent_accepts_explicit_model(tmp_path, monkeypatch) -> None:
    """Verify an explicit model overrides the environment model."""
    answer_path = tmp_path / "answer.txt"
    requested_models = []

    class _FakeAsyncOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            pass

    class _FakeChatCompletionsModel:
        def __init__(self, model: str, **kwargs: Any) -> None:
            requested_models.append(model)

    class _FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            pass

    class _FakeModelSettings:
        def __init__(self, **kwargs: Any) -> None:
            pass

    class _FakeRunner:
        @staticmethod
        def run_sync(
            agent: _FakeAgent,
            prompt: str,
            max_turns: int,
        ) -> SimpleNamespace:
            return SimpleNamespace(final_output="<html><body>ok</body></html>")

    _install_fake_agent_dependencies(
        monkeypatch,
        async_openai=_FakeAsyncOpenAI,
        chat_completions_model=_FakeChatCompletionsModel,
        agent=_FakeAgent,
        runner=_FakeRunner,
        model_settings=_FakeModelSettings,
    )
    monkeypatch.setenv("OPENAI_BASE_URL", "http://ollama-sidecar:11434/v1")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:0.6b")
    monkeypatch.setattr("sandbox_agent.openai_agent._ANSWER_FILE_PATH", answer_path)
    monkeypatch.setattr("sandbox_agent.openai_agent._SITE_DIRECTORY", tmp_path / "site")
    monkeypatch.setattr(
        "sandbox_agent.openai_agent._get_html_element_name_from_mcp",
        lambda: "<table>",
    )
    monkeypatch.setattr(
        "sandbox_agent.openai_agent._save_html_document",
        lambda html_document: None,
    )

    result = run_html_element_agent("granite4.1:3b")

    assert result == "index.html was created for <table>."
    assert requested_models == ["granite4.1:3b"]


def test_run_ollama_smoke_agent_uses_current_workload(monkeypatch) -> None:
    """Verify the previous entry point remains a compatibility wrapper."""
    calls = []

    def _fake_run_html_element_agent(model: str | None = None) -> str:
        calls.append(model)
        return "ok"

    monkeypatch.setattr(
        "sandbox_agent.openai_agent.run_html_element_agent",
        _fake_run_html_element_agent,
    )

    result = run_ollama_smoke_agent("qwen3:0.6b")

    assert result == "ok"
    assert calls == ["qwen3:0.6b"]


def test_run_html_element_agent_requires_openai_base_url(monkeypatch) -> None:
    """Verify the workload requires a local endpoint URL."""
    _install_fake_agent_dependencies(monkeypatch)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr(
        "sandbox_agent.openai_agent._get_html_element_name_from_mcp",
        lambda: "<table>",
    )

    try:
        run_html_element_agent()
    except RuntimeError as error:
        assert str(error) == "OPENAI_BASE_URL is not configured."
    else:
        raise AssertionError("Expected missing OPENAI_BASE_URL failure.")


def _install_fake_agent_dependencies(
    monkeypatch,
    *,
    async_openai: type | None = None,
    chat_completions_model: type | None = None,
    agent: type | None = None,
    runner: type | None = None,
    model_settings: type | None = None,
    set_tracing_disabled_func: Any | None = None,
) -> None:
    if async_openai is None:

        class _FakeAsyncOpenAI:
            def __init__(self, **kwargs: Any) -> None:
                pass

        async_openai = _FakeAsyncOpenAI

    if chat_completions_model is None:

        class _FakeChatCompletionsModel:
            def __init__(self, **kwargs: Any) -> None:
                pass

        chat_completions_model = _FakeChatCompletionsModel

    if agent is None:

        class _FakeAgent:
            def __init__(self, **kwargs: Any) -> None:
                pass

        agent = _FakeAgent

    if runner is None:

        class _FakeRunner:
            @staticmethod
            def run_sync(
                agent: Any,
                prompt: str,
                max_turns: int,
            ) -> SimpleNamespace:
                return SimpleNamespace(final_output="ok")

        runner = _FakeRunner

    if model_settings is None:

        class _FakeModelSettings:
            def __init__(self, **kwargs: Any) -> None:
                pass

        model_settings = _FakeModelSettings

    if set_tracing_disabled_func is None:

        def _set_tracing_disabled(disabled: bool) -> None:
            pass

        set_tracing_disabled_func = _set_tracing_disabled

    fake_agents_module = SimpleNamespace(
        Agent=agent,
        Runner=runner,
        set_tracing_disabled=set_tracing_disabled_func,
    )
    fake_chat_completions_module = SimpleNamespace(
        OpenAIChatCompletionsModel=chat_completions_model,
    )
    fake_openai_tools_module = SimpleNamespace(
        get_html_element_name_tool="tool:get_html_element_name",
        save_html_document_tool="tool:save_html_document",
    )
    fake_model_settings_module = SimpleNamespace(ModelSettings=model_settings)
    monkeypatch.setitem(sys.modules, "agents", fake_agents_module)
    monkeypatch.setitem(sys.modules, "agents.models", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules, "agents.model_settings", fake_model_settings_module
    )
    monkeypatch.setitem(
        sys.modules,
        "agents.models.openai_chatcompletions",
        fake_chat_completions_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(AsyncOpenAI=async_openai),
    )
    monkeypatch.setitem(
        sys.modules,
        "sandbox_agent.openai_tools",
        fake_openai_tools_module,
    )
