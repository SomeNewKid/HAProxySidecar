"""Tests for Sandbox Tester report serialization."""

from __future__ import annotations

from sandbox_tester.models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    CapabilityGroupResult,
    CapabilityResult,
    InvocationResult,
    Outcome,
)
from sandbox_tester.runner import _results_to_json_data


def test_report_serialization_removes_evidence_by_default() -> None:
    """Verify evidence values are redacted unless explicitly requested."""
    report_data = _results_to_json_data([_build_result()])

    capability = report_data[0]["capabilities"][0]  # type: ignore[index]
    assert capability["shell"]["evidence"] == "[REMOVED]"
    assert capability["tool"]["evidence"] == "[REMOVED]"
    assert capability["alternates"]["attempts"][0]["evidence"] == "[REMOVED]"


def test_report_serialization_can_include_evidence() -> None:
    """Verify evidence values are serialized when explicitly requested."""
    report_data = _results_to_json_data([_build_result()], serialize_evidence=True)

    capability = report_data[0]["capabilities"][0]  # type: ignore[index]
    assert capability["shell"]["evidence"] == "shell evidence"
    assert capability["tool"]["evidence"] == "tool evidence"
    assert capability["alternates"]["attempts"][0]["evidence"] == "alternate evidence"


def _build_result() -> CapabilityGroupResult:
    return CapabilityGroupResult(
        id="G01",
        title="Runtime identity and execution context",
        capabilities=[
            CapabilityResult(
                id="T01",
                title="Identify current working directory",
                shell=InvocationResult(
                    outcome=Outcome.DENIED,
                    summary="Shell invocation was denied.",
                    evidence="shell evidence",
                ),
                tool=InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation succeeded.",
                    evidence="tool evidence",
                ),
                alternates=AlternateInvocationResult(
                    outcome=Outcome.DENIED,
                    summary="No alternate shell attempts succeeded.",
                    attempts=[
                        AlternateAttemptResult(
                            id="A01",
                            title="Identify working directory via physical pwd",
                            outcome=Outcome.DENIED,
                            bypass_class="alternate_command",
                            command_family="pwd",
                            evidence="alternate evidence",
                        )
                    ],
                ),
            )
        ],
    )
