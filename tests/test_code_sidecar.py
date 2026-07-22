"""Tests for the code-execution sidecar package."""

from __future__ import annotations

from pathlib import Path

from code_sidecar.server import run_python_script


def test_run_python_script_executes_main_with_args(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify scripts execute through main(argv) and return structured output."""
    monkeypatch.setenv("CODE_SIDECAR_OUTPUT_DIRECTORY", str(tmp_path))
    monkeypatch.setattr("code_sidecar.server._clean_tmp_directory", lambda: None)
    script = "\n".join(
        [
            "def main(argv):",
            "    print(','.join(argv))",
            "    return 7",
        ]
    )

    result = run_python_script(script, args=["a", "b"], timeout_seconds=5)

    assert result.exit_code == 7
    assert result.stdout == "a,b\n"
    assert result.stderr == ""
    assert result.timed_out is False
    assert result.stdout_truncated is False
    assert result.stderr_truncated is False
    artifacts = list(tmp_path.glob("code-sidecar-script-*.py.txt"))
    assert len(artifacts) == 1
    assert artifacts[0].read_text(encoding="utf-8") == script


def test_run_python_script_rejects_missing_main(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify scripts must define main(argv)."""
    monkeypatch.setenv("CODE_SIDECAR_OUTPUT_DIRECTORY", str(tmp_path))
    monkeypatch.setattr("code_sidecar.server._clean_tmp_directory", lambda: None)

    result = run_python_script("print('top level')", timeout_seconds=5)

    assert result.exit_code == 1
    assert "ValueError: top-level expressions must be constants" in result.stderr


def test_run_python_script_rejects_disallowed_import(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify scripts cannot import non-allowlisted modules."""
    monkeypatch.setenv("CODE_SIDECAR_OUTPUT_DIRECTORY", str(tmp_path))
    monkeypatch.setattr("code_sidecar.server._clean_tmp_directory", lambda: None)
    script = "\n".join(
        [
            "import socket",
            "",
            "def main(argv):",
            "    return 0",
        ]
    )

    result = run_python_script(script, timeout_seconds=5)

    assert result.exit_code == 1
    assert "ImportError: module is not allowed: socket" in result.stderr
