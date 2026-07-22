"""OpenAI Agents SDK adapters for Sandbox Agent tools."""

from __future__ import annotations

from agents import function_tool

from .tools import (
    get_answer_format,
    get_html_element_name,
    jina_read_url,
    microsoft_code_sample_search,
    microsoft_docs_fetch,
    microsoft_docs_search,
    run_python_script,
    save_answer,
    save_html_document,
    validate_html5_element,
)

get_answer_format_tool = function_tool(get_answer_format)
get_html_element_name_tool = function_tool(get_html_element_name)
jina_read_url_tool = function_tool(jina_read_url)
microsoft_code_sample_search_tool = function_tool(microsoft_code_sample_search)
microsoft_docs_fetch_tool = function_tool(microsoft_docs_fetch)
microsoft_docs_search_tool = function_tool(microsoft_docs_search)
run_python_script_tool = function_tool(run_python_script)
save_answer_tool = function_tool(save_answer)
save_html_document_tool = function_tool(save_html_document)
validate_html5_element_tool = function_tool(validate_html5_element)
