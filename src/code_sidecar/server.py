"""HTTP server for running constrained Python scripts."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

_DEFAULT_TIMEOUT_SECONDS = 5
_MAX_TIMEOUT_SECONDS = 30
_MAX_OUTPUT_BYTES = 512 * 1024
_OUTPUT_DIRECTORY_ENVIRONMENT_VARIABLE = "CODE_SIDECAR_OUTPUT_DIRECTORY"
_DEFAULT_OUTPUT_DIRECTORY = "/code-sidecar-output"
_SCRIPT_ARTIFACT_PREFIX = "code-sidecar-script"


@dataclass(frozen=True)
class ScriptRunResult:
    """Structured result returned by the code-execution sidecar."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int
    stdout_truncated: bool
    stderr_truncated: bool


def run_server(host: str = "0.0.0.0", port: int = 8090) -> None:
    """Serve code-execution requests until the process exits."""
    server = ThreadingHTTPServer((host, port), _CodeExecutionHandler)
    print(f"Code sidecar listening on {host}:{port}", flush=True)
    server.serve_forever()


def run_python_script(
    script: str,
    args: list[str] | None = None,
    timeout_seconds: int | None = None,
) -> ScriptRunResult:
    """Run one Python script and capture a bounded structured result."""
    _save_script_artifact(script)
    start_time = time.monotonic()
    completed = _run_child_process(script, args or [], timeout_seconds)
    duration_ms = round((time.monotonic() - start_time) * 1000)
    _clean_tmp_directory()
    stdout, stdout_truncated = _truncate_text(completed.stdout)
    stderr, stderr_truncated = _truncate_text(completed.stderr)
    return ScriptRunResult(
        exit_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=completed.timed_out,
        duration_ms=duration_ms,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
    )


@dataclass(frozen=True)
class _ChildProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


class _CodeExecutionHandler(BaseHTTPRequestHandler):
    server_version = "CodeSidecar/0.1"

    def do_GET(self) -> None:
        """Handle readiness checks."""
        if self.path != "/health":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        self._write_json({"status": "ok"})

    def do_POST(self) -> None:
        """Handle script execution requests."""
        if self.path != "/run":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            request = self._read_request()
            result = run_python_script(
                script=request["script"],
                args=request.get("args", []),
                timeout_seconds=request.get("timeout_seconds"),
            )
        except Exception as error:
            self._write_json(
                {
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        self._write_json(asdict(result))

    def log_message(self, format: str, *args: object) -> None:
        """Write HTTP logs to stderr using the default server style."""
        sys.stderr.write(f"{self.address_string()} - {format % args}\n")

    def _read_request(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")

        script = data.get("script")
        if not isinstance(script, str):
            raise ValueError("script must be a string")

        args = data.get("args", [])
        if not isinstance(args, list) or not all(
            isinstance(item, str) for item in args
        ):
            raise ValueError("args must be a list of strings")

        timeout = data.get("timeout_seconds")
        if timeout is not None and not isinstance(timeout, int):
            raise ValueError("timeout_seconds must be an integer")

        return {
            "script": script,
            "args": args,
            "timeout_seconds": timeout,
        }

    def _write_json(
        self,
        data: dict[str, object],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _run_child_process(
    script: str,
    args: list[str],
    timeout_seconds: int | None,
) -> _ChildProcessResult:
    request = json.dumps({"script": script, "args": args})
    timeout = _resolve_timeout_seconds(timeout_seconds)
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "code_sidecar.runner"],
            input=request,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        return _ChildProcessResult(
            returncode=124,
            stdout=_timeout_output_text(error.stdout),
            stderr=_timeout_output_text(error.stderr),
            timed_out=True,
        )

    return _ChildProcessResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=False,
    )


def _resolve_timeout_seconds(timeout_seconds: int | None) -> int:
    if timeout_seconds is None:
        return _DEFAULT_TIMEOUT_SECONDS
    return min(max(timeout_seconds, 1), _MAX_TIMEOUT_SECONDS)


def _timeout_output_text(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def _truncate_text(text: str) -> tuple[str, bool]:
    data = text.encode("utf-8", errors="replace")
    if len(data) <= _MAX_OUTPUT_BYTES:
        return text, False

    truncated = data[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    return truncated, True


def _save_script_artifact(script: str) -> None:
    output_directory = Path(
        os.environ.get(
            _OUTPUT_DIRECTORY_ENVIRONMENT_VARIABLE,
            _DEFAULT_OUTPUT_DIRECTORY,
        )
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")[:-3]
    artifact_path = output_directory / f"{_SCRIPT_ARTIFACT_PREFIX}-{timestamp}.py.txt"
    artifact_path.write_text(script, encoding="utf-8")


def _clean_tmp_directory() -> None:
    tmp_directory = Path("/tmp")
    if not tmp_directory.exists():
        return

    for child in tmp_directory.iterdir():
        try:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        except OSError:
            continue
