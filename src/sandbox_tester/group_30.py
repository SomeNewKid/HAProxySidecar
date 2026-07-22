"""Group 30: Local AI agents."""

from __future__ import annotations

import asyncio
import ctypes
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass

from openai import OpenAI, OpenAIError

from .models import (
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup

_DEFAULT_MODEL = "gpt-4.1-mini"
_MODEL_ENVIRONMENT_VARIABLE = "SANDBOX_TESTER_OPENAI_MODEL"


@dataclass(frozen=True)
class _EnvironmentDetails:
    operating_system: str
    total_ram_bytes: int | None
    cpu_count: int | None
    gpu_count: int | None


class G30_T01:
    id = "T01"
    title = "Local tool call, remote LLM call"

    async def run_shell(self) -> InvocationResult:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="This capability is only tested through Python tool code.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            summary = await asyncio.to_thread(_summarize_local_environment)
            if summary.strip():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python collected local environment details and received "
                        "a remote LLM summary."
                    ),
                    evidence=summary,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="The remote LLM returned an empty response.",
            )
        except OpenAIError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="The OpenAI Responses API was not available.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Local AI agent probe raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G30",
        title="Local AI agents",
        tests=[
            G30_T01(),
        ],
    )


def _summarize_local_environment() -> str:
    details = _collect_environment_details()
    prompt = _build_prompt(details)
    client = OpenAI()
    response = client.responses.create(
        model=os.environ.get(_MODEL_ENVIRONMENT_VARIABLE, _DEFAULT_MODEL),
        input=prompt,
    )
    return _response_text(response)


def _collect_environment_details() -> _EnvironmentDetails:
    return _EnvironmentDetails(
        operating_system=platform.platform(),
        total_ram_bytes=_detect_total_ram_bytes(),
        cpu_count=os.cpu_count(),
        gpu_count=_detect_gpu_count(),
    )


def _build_prompt(details: _EnvironmentDetails) -> str:
    details_json = json.dumps(asdict(details), indent=2)
    return (
        "You are reviewing the local execution environment available to an AI "
        "agent. Use the following structured details to write one short "
        "paragraph summarizing the environment. Do not mention missing fields "
        "unless they materially affect the summary.\n\n"
        f"{details_json}"
    )


def _response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text.strip()

    return str(response).strip()


def _detect_total_ram_bytes() -> int | None:
    if platform.system() == "Windows":
        return _detect_windows_total_ram_bytes()

    if hasattr(os, "sysconf"):
        return _detect_posix_total_ram_bytes()

    return None


def _detect_windows_total_ram_bytes() -> int | None:
    class _MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)

    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None

    return int(status.ullTotalPhys)


def _detect_posix_total_ram_bytes() -> int | None:
    sysconf = getattr(os, "sysconf", None)
    if sysconf is None:
        return None

    try:
        page_size = sysconf("SC_PAGE_SIZE")
        page_count = sysconf("SC_PHYS_PAGES")
    except (OSError, ValueError):
        return None

    if not isinstance(page_size, int) or not isinstance(page_count, int):
        return None

    return page_size * page_count


def _detect_gpu_count() -> int | None:
    if shutil.which("nvidia-smi") is not None:
        return _detect_nvidia_gpu_count()

    if platform.system() == "Windows":
        return _detect_windows_gpu_count()

    return None


def _detect_nvidia_gpu_count() -> int | None:
    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        return None

    names = [line for line in completed.stdout.splitlines() if line.strip()]
    return len(names)


def _detect_windows_gpu_count() -> int | None:
    if shutil.which("powershell") is None:
        return None

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-CimInstance Win32_VideoController).Count",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        return None

    output = completed.stdout.strip()
    if not output.isdigit():
        return None

    return int(output)
