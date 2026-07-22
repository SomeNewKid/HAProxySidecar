"""Group 09: Network access."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import os
import random
import smtplib
import socket
import ssl
import struct
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import (
    CapabilityContext,
    CapabilityGroup,
    OperatingSystem,
    no_alternates,
)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class G09_T01:
    id = "T01"
    title = "Resolve DNS name"

    _DOMAIN_NAME = "examplemalwaredomain.com"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}"

            if self._has_valid_non_authoritative_answer(combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell resolved the DNS name.",
                    evidence=combined_output.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell DNS lookup succeeded, but no valid non-authoritative "
                        "IP address was found."
                    ),
                    evidence=completed.stdout[:500],
                )

            if self._is_nslookup_missing(completed.stderr):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The nslookup command is not installed.",
                    evidence=completed.stderr[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell DNS lookup failed.",
                evidence=completed.stderr[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The nslookup command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell DNS lookup timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            _hostname, _aliases, ip_addresses = await asyncio.to_thread(
                socket.gethostbyname_ex,
                self._DOMAIN_NAME,
            )
            valid_ip_addresses = [
                ip_address
                for ip_address in ip_addresses
                if self._is_valid_ip_address(ip_address)
            ]

            if valid_ip_addresses:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime resolved the DNS name.",
                    evidence=", ".join(valid_ip_addresses[:10]),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Python runtime did not return a valid IP address.",
                evidence=", ".join(ip_addresses[:10]),
            )
        except socket.gaierror as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime DNS lookup failed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime DNS lookup timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_dns_alternate_attempts(self._DOMAIN_NAME),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = ["nslookup", self._DOMAIN_NAME]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _has_valid_non_authoritative_answer(self, output: str) -> bool:
        lines = output.splitlines()
        has_non_authoritative_answer = any(
            line.strip().startswith("Non-authoritative answer") for line in lines
        )

        if not has_non_authoritative_answer:
            return False

        for line in lines:
            normalized_line = line.strip()
            if normalized_line.startswith("Address:"):
                _label, _separator, value = normalized_line.partition(":")
                if self._is_valid_ip_address(value.strip()):
                    return True

            if normalized_line.startswith("Addresses:"):
                _label, _separator, value = normalized_line.partition(":")
                if self._is_valid_ip_address(value.strip()):
                    return True

            if self._is_valid_ip_address(normalized_line):
                return True

        return False

    def _is_valid_ip_address(self, value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    def _is_nslookup_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T02:
    id = "T02"
    title = "Connect to known HTTP endpoint"

    _URL = "http://gov.uk"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the known HTTP endpoint.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP connection failed.",
                evidence=combined_output[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP connection timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the known HTTP endpoint.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the HTTP endpoint.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP connection failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP connection timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_http_head_alternate_attempts(self._URL),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T03:
    id = "T03"
    title = "Connect to known HTTPS endpoint"

    _URL = "https://gov.uk"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the known HTTPS endpoint.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTPS connection failed.",
                evidence=combined_output[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTPS connection timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the known HTTPS endpoint.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the HTTPS endpoint.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTPS connection failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTPS connection timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_http_head_alternate_attempts(self._URL),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T05:
    id = "T05"
    title = "Connect to allowlisted domain"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._domain_name = capability_context.allowed_domain

    async def run_shell(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowlisted domain was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the configured allowlisted domain.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowlisted domain failed.",
                evidence=combined_output[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowlisted domain timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowlisted domain was configured.",
            )

        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowlisted domain.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the allowlisted domain.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowlisted domain failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowlisted domain timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_domain_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_http_head_alternate_attempts(self._get_url()),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._get_url(),
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._get_url(),
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _get_url(self) -> str:
        if self._domain_name is None:
            raise RuntimeError("No allowlisted domain was configured.")

        domain_name = self._domain_name.strip()
        if domain_name.startswith("http://") or domain_name.startswith("https://"):
            return domain_name

        return f"https://{domain_name}"

    def _is_domain_unconfigured(self) -> bool:
        return self._domain_name is None or not self._domain_name.strip()

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T06:
    id = "T06"
    title = "Connect to blocked test domain"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._domain_name = capability_context.denied_domain

    async def run_shell(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No blocked test domain was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the configured blocked test domain.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to blocked test domain failed.",
                evidence=combined_output[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to blocked test domain timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No blocked test domain was configured.",
            )

        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the blocked test domain.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the blocked test domain.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to blocked test domain failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to blocked test domain timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_domain_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_http_head_alternate_attempts(self._get_url()),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._get_url(),
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._get_url(),
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _get_url(self) -> str:
        if self._domain_name is None:
            raise RuntimeError("No blocked test domain was configured.")

        domain_name = self._domain_name.strip()
        if domain_name.startswith("http://") or domain_name.startswith("https://"):
            return domain_name

        return f"https://{domain_name}"

    def _is_domain_unconfigured(self) -> bool:
        return self._domain_name is None or not self._domain_name.strip()

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T07:
    id = "T07"
    title = "Connect to raw IP address"

    _URL = "http://1.1.1.1"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            status_code = self._get_http_status_code(combined_output)

            if completed.returncode == 0 and self._is_successful_status(status_code):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the raw IP address.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to raw IP address failed.",
                evidence=combined_output[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to raw IP address timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            if not self._is_successful_status(response.status):
                return InvocationResult(
                    outcome=Outcome.DENIED,
                    summary=(
                        "Python runtime raw IP address response was not successful."
                    ),
                    evidence=evidence[:500],
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the raw IP address.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            outcome = Outcome.ALLOWED
            summary = "Python runtime reached the raw IP address."
            if not self._is_successful_status(error.code):
                outcome = Outcome.DENIED
                summary = "Python runtime raw IP address response was not successful."

            return InvocationResult(
                outcome=outcome,
                summary=summary,
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to raw IP address failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to raw IP address timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_http_head_alternate_attempts(self._URL),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        opener = urllib.request.build_opener(_NoRedirectHandler)
        return opener.open(request, timeout=10)

    def _get_http_status_code(self, output: str) -> int | None:
        status_code = None
        for line in output.splitlines():
            parts = line.strip().split(maxsplit=2)
            if len(parts) < 2 or not parts[0].startswith("HTTP/"):
                continue

            try:
                status_code = int(parts[1])
            except ValueError:
                continue

        return status_code

    def _is_successful_status(self, status_code: int | None) -> bool:
        if status_code is None:
            return False

        return 200 <= status_code < 400

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T08:
    id = "T08"
    title = "Connect to non-HTTP port"

    _HOST = "github.com"
    _PORT = 22

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the non-HTTP TCP port.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to non-HTTP TCP port failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to non-HTTP TCP port timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the non-HTTP TCP port.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to non-HTTP TCP port timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to non-HTTP TCP port failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_tcp_connect_alternate_attempts(self._HOST, self._PORT),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        return _run_shell_tcp_connect_command(
            self._HOST,
            self._PORT,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        with socket.create_connection(
            (self._HOST, self._PORT), timeout=10
        ) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))


class G09_T09:
    id = "T09"
    title = "Send HTTP POST"

    _URL = "https://httpbin.org/post"
    _PAYLOAD = {
        "source": "sandbox-tester",
        "purpose": "network-post-test",
    }

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell sent an HTTP POST request.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP POST request failed.",
                evidence=combined_output[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP POST request timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                response_body = response.read(500).decode("utf-8", errors="replace")
                evidence = (
                    f"url={response.url}, status={response.status}, {response_body}"
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime sent an HTTP POST request.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the HTTP POST endpoint.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP POST request failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP POST request timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        payload = json.dumps(self._PAYLOAD)
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_http_post_alternate_attempts(self._URL, payload),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        payload = json.dumps(self._PAYLOAD)
        command = [
            "curl",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            "--request",
            "POST",
            "--header",
            "Content-Type: application/json",
            "--data",
            payload,
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        payload = json.dumps(self._PAYLOAD).encode("utf-8")
        request = urllib.request.Request(
            self._URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SandboxTester/1.0",
            },
            method="POST",
        )
        return urllib.request.urlopen(request, timeout=10)

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T10:
    id = "T10"
    title = "Download small file"

    _URL = "https://httpbin.org/bytes/128"
    _EXPECTED_SIZE_BYTES = 128
    _RETRY_DELAYS_SECONDS = (2, 10)

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._shell_file = capability_context.allowed_directory / "g09_t10_shell.bin"
        self._tool_file = capability_context.allowed_directory / "g09_t10_tool.bin"

    async def run_shell(self) -> InvocationResult:
        return await self._run_with_retries(
            self._run_shell_once,
            "Shell file download failed after 3 attempts.",
        )

    async def _run_shell_once(self) -> InvocationResult:
        self._delete_file_if_exists(self._shell_file)

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if self._was_downloaded(self._shell_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell downloaded a small file.",
                    evidence=(
                        f"path={self._shell_file}, "
                        f"size={self._shell_file.stat().st_size}"
                    ),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but file was not downloaded.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell file download failed.",
                evidence=combined_output[:500],
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell file download timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        return await self._run_with_retries(
            self._run_tool_once,
            "Python runtime file download failed after 3 attempts.",
        )

    async def _run_tool_once(self) -> InvocationResult:
        self._delete_file_if_exists(self._tool_file)

        try:
            await asyncio.to_thread(self._download_tool_file)

            if self._was_downloaded(self._tool_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime downloaded a small file.",
                    evidence=(
                        f"path={self._tool_file}, size={self._tool_file.stat().st_size}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but file was not downloaded.",
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file download failed with HTTP error.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file download failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file download timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def _run_with_retries(
        self,
        operation: Callable[[], Awaitable[InvocationResult]],
        failed_summary: str,
    ) -> InvocationResult:
        attempts: list[InvocationResult] = []

        for attempt_index in range(len(self._RETRY_DELAYS_SECONDS) + 1):
            result = await operation()
            attempts.append(result)
            if result.outcome in {Outcome.ALLOWED, Outcome.NOT_APPLICABLE}:
                return self._with_attempt_evidence(result, attempts)

            if attempt_index < len(self._RETRY_DELAYS_SECONDS):
                await asyncio.sleep(self._RETRY_DELAYS_SECONDS[attempt_index])

        final_result = attempts[-1]
        return InvocationResult(
            outcome=final_result.outcome,
            summary=failed_summary,
            evidence=self._attempts_evidence(attempts),
        )

    def _with_attempt_evidence(
        self,
        result: InvocationResult,
        attempts: list[InvocationResult],
    ) -> InvocationResult:
        if len(attempts) == 1:
            return result

        return InvocationResult(
            outcome=result.outcome,
            summary=f"{result.summary} Succeeded on attempt {len(attempts)}.",
            evidence=self._attempts_evidence(attempts),
        )

    def _attempts_evidence(self, attempts: list[InvocationResult]) -> str:
        lines = []
        for index, attempt in enumerate(attempts, start=1):
            evidence = attempt.evidence or ""
            compact_evidence = str(evidence).replace("\n", " | ")[:300]
            lines.append(
                f"attempt={index}; outcome={attempt.outcome.value}; "
                f"summary={attempt.summary}; evidence={compact_evidence}"
            )

        return "\n".join(lines)[:1000]

    async def run_alternates(self) -> AlternateInvocationResult:
        alternate_file = self._shell_file.with_name("g09_t10_alternate.bin")
        self._delete_file_if_exists(alternate_file)

        try:
            return await asyncio.to_thread(
                _run_network_alternate_attempts,
                _build_download_alternate_attempts(self._URL, alternate_file),
            )
        finally:
            self._delete_file_if_exists(alternate_file)

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            "--output",
            str(self._shell_file),
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _download_tool_file(self) -> None:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read()

        self._tool_file.write_bytes(content)

    def _delete_file_if_exists(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def _was_downloaded(self, path: Path) -> bool:
        return path.is_file() and path.stat().st_size == self._EXPECTED_SIZE_BYTES

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T11:
    id = "T11"
    title = "Start local listening socket"

    _HOST = "127.0.0.1"

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_shell_listener()
            port = await asyncio.to_thread(self._read_listener_port, child_process)
            completed = await asyncio.to_thread(
                _run_shell_tcp_connect_command,
                self._HOST,
                port,
                5,
            )
            child_process.wait(timeout=5)

            if child_process.returncode == 0 and completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell started a local listening socket.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            stderr = self._read_child_stderr(child_process)
            combined_output = f"{completed.stdout}\n{completed.stderr}\n{stderr}"
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell listener process exited with an unexpected status.",
                evidence=combined_output.strip()[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local listening socket timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local listening socket test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None
        client: socket.socket | None = None
        accepted_connection: socket.socket | None = None

        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self._HOST, 0))
            listener.listen(1)
            listener.settimeout(5)
            port = listener.getsockname()[1]

            client = socket.create_connection((self._HOST, port), timeout=5)
            accepted_connection, _address = listener.accept()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime started a local listening socket.",
                evidence=f"host={self._HOST}, port={port}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local socket connection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local listening socket test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if client is not None:
                client.close()
            if listener is not None:
                listener.close()

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_local_listener_alternate_attempts(self._HOST),
        )

    def _start_shell_listener(self) -> subprocess.Popen[str]:
        command = _build_shell_tcp_listener_command(self._HOST)

        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _read_listener_port(self, child_process: subprocess.Popen[str]) -> int:
        if child_process.stdout is None:
            raise RuntimeError("Listener process stdout was not captured.")

        line = child_process.stdout.readline().strip()
        if not line:
            stderr = self._read_child_stderr(child_process)
            raise RuntimeError(f"Listener process did not report a port: {stderr}")

        return int(line)

    def _read_child_stderr(self, child_process: subprocess.Popen[str]) -> str:
        if child_process.stderr is None:
            return ""

        return child_process.stderr.read()

    def _cleanup_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.terminate()

        try:
            child_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child_process.kill()
            child_process.wait(timeout=5)


class G09_T12:
    id = "T12"
    title = "Connect to local loopback service"

    _HOST = "127.0.0.1"

    async def run_shell(self) -> InvocationResult:
        service_process: subprocess.Popen[str] | None = None

        try:
            service_process = self._start_loopback_service()
            port = await asyncio.to_thread(self._read_service_port, service_process)
            completed = await asyncio.to_thread(self._run_shell_command, port)
            service_process.wait(timeout=5)

            if completed.returncode == 0 and service_process.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to a local loopback service.",
                    evidence=completed.stdout.strip()[:500],
                )

            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local loopback service failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local loopback service timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local loopback service test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if service_process is not None:
                self._cleanup_service_process(service_process)

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None
        accepted_connection: socket.socket | None = None
        server_errors: list[BaseException] = []

        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self._HOST, 0))
            listener.listen(1)
            listener.settimeout(5)
            port = listener.getsockname()[1]

            def accept_connection() -> None:
                nonlocal accepted_connection

                try:
                    accepted_connection, _address = listener.accept()
                except BaseException as error:
                    server_errors.append(error)

            server_thread = threading.Thread(target=accept_connection)
            server_thread.start()

            with socket.create_connection((self._HOST, port), timeout=5) as client:
                peer_name = client.getpeername()

            server_thread.join(timeout=5)
            if server_thread.is_alive():
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Loopback service did not accept the connection in time.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            if server_errors:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Loopback service raised an exception.",
                    evidence=repr(server_errors[0]),
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to a local loopback service.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local loopback connection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local loopback service test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if listener is not None:
                listener.close()

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_loopback_service_alternate_attempts(self._HOST),
        )

    def _start_loopback_service(self) -> subprocess.Popen[str]:
        command = _build_shell_tcp_listener_command(self._HOST)

        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _read_service_port(self, service_process: subprocess.Popen[str]) -> int:
        if service_process.stdout is None:
            raise RuntimeError("Loopback service stdout was not captured.")

        line = service_process.stdout.readline().strip()
        if not line:
            stderr = self._read_service_stderr(service_process)
            raise RuntimeError(f"Loopback service did not report a port: {stderr}")

        return int(line)

    def _run_shell_command(self, port: int) -> subprocess.CompletedProcess[str]:
        return _run_shell_tcp_connect_command(
            self._HOST,
            port,
            timeout_seconds=5,
        )

    def _read_service_stderr(self, service_process: subprocess.Popen[str]) -> str:
        if service_process.stderr is None:
            return ""

        return service_process.stderr.read()

    def _cleanup_service_process(self, service_process: subprocess.Popen[str]) -> None:
        if service_process.poll() is not None:
            return

        service_process.terminate()

        try:
            service_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            service_process.kill()
            service_process.wait(timeout=5)


class G09_T13:
    id = "T13"
    title = "Connect to allowed localnet address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.allowed_localnet_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed localnet address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the allowed localnet address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed localnet address failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed localnet address timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed localnet address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed localnet address.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime connection to allowed localnet address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowed localnet address failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_endpoint_unconfigured():
            return await no_alternates()

        host, port = self._parse_address()
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_tcp_connect_alternate_attempts(host, port),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        host, port = self._parse_address()
        return _run_shell_tcp_connect_command(
            host,
            port,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        host, port = self._parse_address()

        with socket.create_connection((host, port), timeout=10) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))

    def _is_endpoint_unconfigured(self) -> bool:
        return self._address is None or not self._address.strip()

    def _parse_address(self) -> tuple[str, int]:
        if self._address is None or not self._address.strip():
            raise RuntimeError("No allowed localnet address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Allowed localnet address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G09_T14:
    id = "T14"
    title = "Connect to denied localnet address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.denied_localnet_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied localnet address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the denied localnet address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied localnet address failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied localnet address timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied localnet address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied localnet address.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime connection to denied localnet address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to denied localnet address failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_endpoint_unconfigured():
            return await no_alternates()

        host, port = self._parse_address()
        return await asyncio.to_thread(
            _run_network_alternate_attempts,
            _build_tcp_connect_alternate_attempts(host, port),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        host, port = self._parse_address()
        return _run_shell_tcp_connect_command(
            host,
            port,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        host, port = self._parse_address()

        with socket.create_connection((host, port), timeout=10) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))

    def _is_endpoint_unconfigured(self) -> bool:
        return self._address is None or not self._address.strip()

    def _parse_address(self) -> tuple[str, int]:
        if self._address is None or not self._address.strip():
            raise RuntimeError("No denied localnet address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Denied localnet address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


@dataclass(frozen=True)
class _AlternateNetworkAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_dns_alternate_attempts(domain_name: str) -> list[_AlternateNetworkAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateNetworkAttempt(
                id="A01",
                title="Resolve DNS name via PowerShell DNS API",
                bypass_class="alternate_command",
                command_family="powershell/dns",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        f"[System.Net.Dns]::GetHostAddresses("
                        f"{_quote_powershell_string(domain_name)}) | "
                        "ForEach-Object { $_.IPAddressToString }"
                    ),
                ],
            ),
            _AlternateNetworkAttempt(
                id="A02",
                title="Resolve DNS name via Resolve-DnsName",
                bypass_class="alternate_command",
                command_family="powershell/Resolve-DnsName",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        f"Resolve-DnsName {_quote_powershell_string(domain_name)} "
                        "-Type A | Select-Object -ExpandProperty IPAddress"
                    ),
                ],
            ),
        ]

    return [
        _AlternateNetworkAttempt(
            id="A01",
            title="Resolve DNS name via getent",
            bypass_class="alternate_command",
            command_family="getent",
            command=["getent", "hosts", domain_name],
        ),
        _AlternateNetworkAttempt(
            id="A02",
            title="Resolve DNS name via host",
            bypass_class="alternate_command",
            command_family="host",
            command=["host", domain_name],
        ),
        _AlternateNetworkAttempt(
            id="A03",
            title="Resolve DNS name via dig",
            bypass_class="alternate_command",
            command_family="dig",
            command=["dig", "+short", domain_name],
        ),
    ]


def _build_http_head_alternate_attempts(url: str) -> list[_AlternateNetworkAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateNetworkAttempt(
                id="A01",
                title="Connect via PowerShell .NET WebRequest",
                bypass_class="alternate_command",
                command_family="powershell/WebRequest",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        f"$request = [System.Net.WebRequest]::Create("
                        f"{_quote_powershell_string(url)}); "
                        "$request.Method = 'HEAD'; "
                        "$request.Timeout = 10000; "
                        "$request.AllowAutoRedirect = $false; "
                        "try { "
                        "$response = $request.GetResponse(); "
                        "Write-Output ('status=' + [int]$response.StatusCode); "
                        "$response.Close(); "
                        "} catch [System.Net.WebException] { "
                        "if ($_.Exception.Response -eq $null) { throw }; "
                        "$response = $_.Exception.Response; "
                        "Write-Output ('status=' + [int]$response.StatusCode); "
                        "$response.Close(); "
                        "}"
                    ),
                ],
            )
        ]

    return [
        _AlternateNetworkAttempt(
            id="A01",
            title="Connect via wget spider request",
            bypass_class="alternate_command",
            command_family="wget",
            command=["wget", "--spider", "--timeout=10", "--server-response", url],
        )
    ]


def _build_http_post_alternate_attempts(
    url: str,
    payload: str,
) -> list[_AlternateNetworkAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateNetworkAttempt(
                id="A01",
                title="Send POST via PowerShell .NET WebRequest",
                bypass_class="alternate_command",
                command_family="powershell/WebRequest",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        f"$request = [System.Net.WebRequest]::Create("
                        f"{_quote_powershell_string(url)}); "
                        "$request.Method = 'POST'; "
                        "$request.Timeout = 10000; "
                        "$request.ContentType = 'application/json'; "
                        "$body = [System.Text.Encoding]::UTF8.GetBytes("
                        f"{_quote_powershell_string(payload)}); "
                        "$request.ContentLength = $body.Length; "
                        "$stream = $request.GetRequestStream(); "
                        "$stream.Write($body, 0, $body.Length); "
                        "$stream.Close(); "
                        "try { "
                        "$response = $request.GetResponse(); "
                        "Write-Output ('status=' + [int]$response.StatusCode); "
                        "$response.Close(); "
                        "} catch [System.Net.WebException] { "
                        "if ($_.Exception.Response -eq $null) { throw }; "
                        "$response = $_.Exception.Response; "
                        "Write-Output ('status=' + [int]$response.StatusCode); "
                        "$response.Close(); "
                        "}"
                    ),
                ],
            )
        ]

    return [
        _AlternateNetworkAttempt(
            id="A01",
            title="Send POST via wget",
            bypass_class="alternate_command",
            command_family="wget",
            command=[
                "wget",
                "--timeout=10",
                "--quiet",
                "--server-response",
                "--output-document=-",
                "--header=Content-Type: application/json",
                f"--post-data={payload}",
                url,
            ],
        )
    ]


def _build_download_alternate_attempts(
    url: str,
    target: Path,
) -> list[_AlternateNetworkAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateNetworkAttempt(
                id="A01",
                title="Download via PowerShell .NET WebClient",
                bypass_class="alternate_command",
                command_family="powershell/WebClient",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        f"$target = {_quote_powershell_string(str(target))}; "
                        "$client = [System.Net.WebClient]::new(); "
                        f"$client.DownloadFile({_quote_powershell_string(url)}, "
                        "$target); "
                        "$item = Get-Item -LiteralPath $target; "
                        "Write-Output ('size=' + $item.Length)"
                    ),
                ],
            )
        ]

    return [
        _AlternateNetworkAttempt(
            id="A01",
            title="Download via wget",
            bypass_class="alternate_command",
            command_family="wget",
            command=[
                "wget",
                "--timeout=10",
                "--quiet",
                "--output-document",
                str(target),
                url,
            ],
        )
    ]


def _build_tcp_connect_alternate_attempts(
    host: str,
    port: int,
) -> list[_AlternateNetworkAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateNetworkAttempt(
                id="A01",
                title="Connect via Test-NetConnection",
                bypass_class="alternate_command",
                command_family="powershell/Test-NetConnection",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        "$result = Test-NetConnection "
                        f"-ComputerName {_quote_powershell_string(host)} "
                        f"-Port {port} -InformationLevel Quiet; "
                        "if (-not $result) { exit 1 }; "
                        f"Write-Output 'peer={host}:{port}'"
                    ),
                ],
            )
        ]

    return [
        _AlternateNetworkAttempt(
            id="A01",
            title="Connect via netcat",
            bypass_class="alternate_command",
            command_family="nc",
            command=["nc", "-z", "-w", "10", host, str(port)],
        ),
        _AlternateNetworkAttempt(
            id="A02",
            title="Connect via bash TCP redirection",
            bypass_class="alternate_command",
            command_family="bash/dev-tcp",
            command=[
                "bash",
                "-c",
                f"timeout 10 bash -c '</dev/tcp/{host}/{port}'",
            ],
        ),
    ]


def _build_local_listener_alternate_attempts(
    host: str,
) -> list[_AlternateNetworkAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateNetworkAttempt(
                id="A01",
                title="Start local listener via PowerShell .NET sockets",
                bypass_class="local_socket_creation",
                command_family="powershell/TcpListener",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    _build_windows_local_listener_script(host),
                ],
            )
        ]

    return [
        _AlternateNetworkAttempt(
            id="A01",
            title="Start local listener via netcat",
            bypass_class="local_socket_creation",
            command_family="nc",
            command=[
                "sh",
                "-c",
                _build_linux_local_listener_script(host, use_bash_client=False),
            ],
        ),
        _AlternateNetworkAttempt(
            id="A02",
            title="Start local listener via netcat and bash TCP client",
            bypass_class="local_socket_creation",
            command_family="nc/bash-dev-tcp",
            command=[
                "bash",
                "-lc",
                _build_linux_local_listener_script(host, use_bash_client=True),
            ],
        ),
    ]


def _build_loopback_service_alternate_attempts(
    host: str,
) -> list[_AlternateNetworkAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateNetworkAttempt(
                id="A01",
                title="Connect to loopback service via PowerShell .NET sockets",
                bypass_class="loopback_connection",
                command_family="powershell/TcpClient",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    _build_windows_local_listener_script(host),
                ],
            )
        ]

    return [
        _AlternateNetworkAttempt(
            id="A01",
            title="Connect to loopback service via netcat",
            bypass_class="loopback_connection",
            command_family="nc",
            command=[
                "sh",
                "-c",
                _build_linux_local_listener_script(host, use_bash_client=False),
            ],
        ),
        _AlternateNetworkAttempt(
            id="A02",
            title="Connect to loopback service via bash TCP redirection",
            bypass_class="loopback_connection",
            command_family="bash/dev-tcp",
            command=[
                "bash",
                "-lc",
                _build_linux_local_listener_script(host, use_bash_client=True),
            ],
        ),
    ]


def _build_windows_local_listener_script(host: str) -> str:
    return (
        "$ErrorActionPreference = 'Stop'; "
        "$address = [System.Net.IPAddress]::Parse("
        f"{_quote_powershell_string(host)}); "
        "$listener = [System.Net.Sockets.TcpListener]::new($address, 0); "
        "$listener.Start(); "
        "$port = $listener.LocalEndpoint.Port; "
        "$accept = $listener.AcceptTcpClientAsync(); "
        "$client = [System.Net.Sockets.TcpClient]::new(); "
        "$client.Connect($address, $port); "
        "$serverClient = $accept.GetAwaiter().GetResult(); "
        "$serverClient.Close(); "
        "$client.Close(); "
        "$listener.Stop(); "
        'Write-Output "host='
        f"{host}"
        '; port=$port; connected=true"'
    )


def _build_linux_local_listener_script(host: str, use_bash_client: bool) -> str:
    port = 30000 + (os.getpid() % 20000)
    quoted_host = _quote_shell_string(host)
    if use_bash_client:
        connect_command = (
            f"timeout 5 bash -c {_quote_shell_string(f'</dev/tcp/{host}/{port}')}"
        )
    else:
        connect_command = f"nc -z -w 5 {quoted_host} {port}"

    return (
        "command -v nc >/dev/null 2>&1 || exit 127; "
        f"(nc -l {quoted_host} {port} >/dev/null & echo $! > /tmp/st-g09-nc.pid); "
        "sleep 1; "
        f"{connect_command}; "
        "status=$?; "
        "pid=$(cat /tmp/st-g09-nc.pid 2>/dev/null); "
        'if [ -n "$pid" ]; then kill "$pid" 2>/dev/null; fi; '
        "rm -f /tmp/st-g09-nc.pid; "
        'if [ "$status" -eq 0 ]; then '
        f"echo 'host={host}; port={port}; connected=true'; "
        "fi; "
        'exit "$status"'
    )


def _run_network_alternate_attempts(
    attempts: list[_AlternateNetworkAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_network_alternate_attempt(attempt) for attempt in attempts]
    allowed_count = sum(
        1 for result in attempt_results if result.outcome == Outcome.ALLOWED
    )

    if allowed_count:
        outcome = Outcome.ALLOWED
        summary = (
            f"{allowed_count} of {len(attempt_results)} alternate shell attempts "
            "succeeded."
        )
    else:
        outcome = Outcome.DENIED
        summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _run_network_alternate_attempt(
    attempt: _AlternateNetworkAttempt,
) -> AlternateAttemptResult:
    try:
        completed = subprocess.run(
            attempt.command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=15,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_alternate_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _alternate_exception_result(attempt, Outcome.ERROR, error)


def _alternate_exception_result(
    attempt: _AlternateNetworkAttempt,
    outcome: Outcome,
    error: Exception,
) -> AlternateAttemptResult:
    return AlternateAttemptResult(
        id=attempt.id,
        title=attempt.title,
        outcome=outcome,
        bypass_class=attempt.bypass_class,
        command_family=attempt.command_family,
        evidence=repr(error),
    )


def _alternate_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def _run_shell_tcp_connect_command(
    host: str,
    port: int,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_tcp_connect_command(host, port, timeout_seconds)
    else:
        command = _build_linux_tcp_connect_command(host, port, timeout_seconds)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,
        check=False,
    )


def _build_windows_tcp_connect_command(
    host: str,
    port: int,
    timeout_seconds: int,
) -> list[str]:
    timeout_milliseconds = timeout_seconds * 1000
    script = (
        "$client = [System.Net.Sockets.TcpClient]::new(); "
        f"$async = $client.BeginConnect({_quote_powershell_string(host)}, {port}, "
        "$null, $null); "
        f"$connected = $async.AsyncWaitHandle.WaitOne({timeout_milliseconds}, "
        "$false); "
        "if (-not $connected) { $client.Close(); Write-Error 'timeout'; exit 2 }; "
        "$client.EndConnect($async); "
        "$endpoint = $client.Client.RemoteEndPoint.ToString(); "
        "$client.Close(); "
        'Write-Output "peer=$endpoint"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_tcp_connect_command(
    host: str,
    port: int,
    timeout_seconds: int,
) -> list[str]:
    quoted_host = _quote_shell_string(host)
    script = (
        "if command -v nc >/dev/null 2>&1; then "
        f"nc -z -w {timeout_seconds} {quoted_host} {port}; "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then '
        f"echo 'peer={host}:{port}'; "
        "fi; "
        'exit "$status"; '
        "fi; "
        "if command -v bash >/dev/null 2>&1; then "
        f"timeout {timeout_seconds} bash -c "
        f"{_quote_shell_string(f'</dev/tcp/{host}/{port}')} "
        ">/dev/null 2>&1; "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then '
        f"echo 'peer={host}:{port}'; "
        "fi; "
        'exit "$status"; '
        "fi; "
        "echo 'no TCP shell client found'; "
        "exit 127"
    )
    return ["sh", "-c", script]


def _build_shell_tcp_listener_command(host: str) -> list[str]:
    if sys.platform == "win32":
        return _build_windows_tcp_listener_command(host)

    return _build_linux_tcp_listener_command(host)


def _build_windows_tcp_listener_command(host: str) -> list[str]:
    script = (
        "$address = [System.Net.IPAddress]::Parse("
        f"{_quote_powershell_string(host)}); "
        "$listener = [System.Net.Sockets.TcpListener]::new($address, 0); "
        "$listener.Start(); "
        "$port = $listener.LocalEndpoint.Port; "
        "Write-Output $port; "
        "[Console]::Out.Flush(); "
        "$client = $listener.AcceptTcpClient(); "
        "$client.Close(); "
        "$listener.Stop()"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_tcp_listener_command(host: str) -> list[str]:
    port = 30000 + (os.getpid() % 20000)
    script = (
        "if command -v nc >/dev/null 2>&1; then "
        f"echo {port}; "
        f"exec nc -l {_quote_shell_string(host)} {port} >/dev/null; "
        "fi; "
        "echo 'netcat not found' >&2; "
        "exit 127"
    )
    return ["sh", "-c", script]


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


_g25_DNS_TEST_DOMAIN = "example.com"

_g25_DNS_TEST_SERVER = "1.1.1.1"

_g25_DNS_TEST_PORT = 53

_g25_NO_SHELL_CANDIDATE_EXIT_CODE = 127

_g25_METADATA_TIMEOUT_SECONDS = 2

_g25_INTRANET_CONNECT_TIMEOUT_SECONDS = 2

_g25_LINUX_PRIVILEGED_BIND_ADDRESS = "127.0.0.1"

_g25_LINUX_PRIVILEGED_BIND_PORT = 80

_g25_PROXY_ENVIRONMENT_VARIABLES = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
]

_g25_DEFAULT_INTRANET_PORTS = [
    445,
    80,
    443,
    5000,
    5001,
]

_g25_DEFAULT_METADATA_PROBES = [
    (
        "AWS",
        "http://169.254.169.254/latest/meta-data/",
        {},
    ),
    (
        "Azure",
        "http://169.254.169.254/metadata/instance?api-version=2021-02-01",
        {"Metadata": "true"},
    ),
    (
        "Google",
        "http://169.254.169.254/computeMetadata/v1/",
        {"Metadata-Flavor": "Google"},
    ),
    (
        "Google",
        "http://metadata.google.internal/computeMetadata/v1/",
        {"Metadata-Flavor": "Google"},
    ),
]


class G09_T15:
    id = "T15"
    title = "UDP send/receive"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_udp_shell_command(
                self._operating_system
            ),
            allowed_summary="Shell sent and received UDP data.",
            denied_summary="Shell could not send and receive UDP data.",
            not_applicable_summary="No supported shell UDP test command was available.",
            timeout_summary="Shell UDP send/receive test timed out.",
            failure_summary="Shell UDP send/receive test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(_g25_run_udp_echo_with_python)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime sent and received UDP data.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime UDP send/receive test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _g25_run_single_network_policy_alternate(
            title="UDP send/receive with alternate local datagram command",
            bypass_class="udp_send_receive",
            command_family=_g25_udp_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_udp_shell_command(self._operating_system)
            ),
        )


class G09_T16:
    id = "T16"
    title = "ICMP ping / raw socket creation"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_ping_shell_command(
                self._operating_system
            ),
            allowed_summary="Shell ran an ICMP ping command.",
            denied_summary="Shell could not run an ICMP ping command.",
            not_applicable_summary="No supported shell ping command was available.",
            timeout_summary="Shell ICMP ping test timed out.",
            failure_summary="Shell ICMP ping test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(_g25_create_raw_icmp_socket)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime created a raw ICMP socket.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not create a raw ICMP socket.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _g25_run_single_network_policy_alternate(
            title="ICMP reachability with alternate ping command",
            bypass_class="icmp_ping_or_raw_socket",
            command_family="ping",
            operation=lambda: _g25_run_command(
                _g25_build_ping_shell_command(self._operating_system)
            ),
        )


class G09_T17:
    id = "T17"
    title = "DNS over TCP vs UDP"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_dns_shell_command(
                self._operating_system
            ),
            allowed_summary="Shell queried DNS over both UDP and TCP.",
            denied_summary="Shell could not query DNS over both UDP and TCP.",
            not_applicable_summary="No supported shell DNS command was available.",
            timeout_summary="Shell DNS transport test timed out.",
            failure_summary="Shell DNS transport test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            udp_answer_count = await asyncio.to_thread(
                _g25_query_dns_with_python,
                use_tcp=False,
            )
            tcp_answer_count = await asyncio.to_thread(
                _g25_query_dns_with_python,
                use_tcp=True,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried DNS over both UDP and TCP.",
                evidence=(
                    f"server={_g25_DNS_TEST_SERVER}; domain={_g25_DNS_TEST_DOMAIN}; "
                    f"udp_answers={udp_answer_count}; "
                    f"tcp_answers={tcp_answer_count}"
                ),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime DNS transport query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _g25_run_single_network_policy_alternate(
            title="DNS UDP/TCP query with alternate resolver command",
            bypass_class="dns_transport_query",
            command_family=_g25_dns_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_dns_shell_command(self._operating_system)
            ),
        )


class G09_T18:
    id = "T18"
    title = "Connect to link-local metadata endpoint"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._metadata_endpoint_url = capability_context.metadata_endpoint_url

    async def run_shell(self) -> InvocationResult:
        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_metadata_shell_command(
                self._operating_system, self._metadata_endpoint_url
            ),
            allowed_summary="Shell connected to a metadata endpoint.",
            denied_summary="Shell could not connect to a metadata endpoint.",
            not_applicable_summary=(
                "No supported shell metadata endpoint command was available."
            ),
            timeout_summary="Shell metadata endpoint probe timed out.",
            failure_summary="Shell metadata endpoint probe failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _g25_probe_metadata_endpoints_with_python,
                self._metadata_endpoint_url,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to a metadata endpoint.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not connect to a metadata endpoint.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime metadata endpoint probe failed.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _g25_run_single_network_policy_alternate(
            title="Metadata endpoint probe with alternate HTTP command",
            bypass_class="metadata_endpoint_probe",
            command_family=_g25_metadata_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_metadata_shell_command(
                    self._operating_system,
                    self._metadata_endpoint_url,
                )
            ),
        )


class G09_T19:
    id = "T19"
    title = "Connect to allowed intranet target"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._intranet_target = capability_context.allowed_intranet_target

    async def run_shell(self) -> InvocationResult:
        if _g25_target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed intranet target was configured.",
            )

        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_intranet_shell_command(
                self._operating_system,
                str(self._intranet_target),
            ),
            allowed_summary="Shell connected to the allowed intranet target.",
            denied_summary="Shell could not connect to the allowed intranet target.",
            not_applicable_summary=(
                "No supported shell intranet connection command was available."
            ),
            timeout_summary="Shell allowed intranet connection test timed out.",
            failure_summary="Shell allowed intranet connection test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        if _g25_target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed intranet target was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g25_connect_to_intranet_target_with_python,
                str(self._intranet_target),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed intranet target.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not connect to the allowed intranet target."
                ),
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if _g25_target_is_unconfigured(self._intranet_target):
            return _g25_no_network_policy_alternates(
                "No allowed intranet target was configured."
            )

        return await _g25_run_single_network_policy_alternate(
            title="Allowed intranet target connection with alternate socket command",
            bypass_class="allowed_intranet_connection",
            command_family=_g25_intranet_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_intranet_shell_command(
                    self._operating_system,
                    str(self._intranet_target),
                )
            ),
        )


class G09_T20:
    id = "T20"
    title = "Connect to denied intranet target"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._intranet_target = capability_context.denied_intranet_target

    async def run_shell(self) -> InvocationResult:
        if _g25_target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied intranet target was configured.",
            )

        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_intranet_shell_command(
                self._operating_system,
                str(self._intranet_target),
            ),
            allowed_summary="Shell connected to the denied intranet target.",
            denied_summary="Shell could not connect to the denied intranet target.",
            not_applicable_summary=(
                "No supported shell intranet connection command was available."
            ),
            timeout_summary="Shell denied intranet connection test timed out.",
            failure_summary="Shell denied intranet connection test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        if _g25_target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied intranet target was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g25_connect_to_intranet_target_with_python,
                str(self._intranet_target),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied intranet target.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not connect to the denied intranet target."
                ),
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if _g25_target_is_unconfigured(self._intranet_target):
            return _g25_no_network_policy_alternates(
                "No denied intranet target was configured."
            )

        return await _g25_run_single_network_policy_alternate(
            title="Denied intranet target connection with alternate socket command",
            bypass_class="denied_intranet_connection",
            command_family=_g25_intranet_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_intranet_shell_command(
                    self._operating_system,
                    str(self._intranet_target),
                )
            ),
        )


class G09_T21:
    id = "T21"
    title = "Listen on loopback interface"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_listen_shell_command(
                self._operating_system,
                "127.0.0.1",
            ),
            allowed_summary="Shell listened on the loopback interface.",
            denied_summary="Shell could not listen on the loopback interface.",
            not_applicable_summary=(
                "No supported shell listening socket command was available."
            ),
            timeout_summary="Shell loopback listening socket test timed out.",
            failure_summary="Shell loopback listening socket test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _g25_listen_with_python,
                "127.0.0.1",
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime listened on the loopback interface.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not listen on the loopback interface.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _g25_run_single_network_policy_alternate(
            title="Loopback listener bind with alternate socket command",
            bypass_class="loopback_listener_bind",
            command_family=_g25_listen_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_listen_shell_command(
                    self._operating_system,
                    "127.0.0.1",
                )
            ),
        )


class G09_T22:
    id = "T22"
    title = "Listen on public/all interfaces"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_listen_shell_command(
                self._operating_system,
                "0.0.0.0",
            ),
            allowed_summary="Shell listened on all network interfaces.",
            denied_summary="Shell could not listen on all network interfaces.",
            not_applicable_summary=(
                "No supported shell listening socket command was available."
            ),
            timeout_summary="Shell all-interface listening socket test timed out.",
            failure_summary="Shell all-interface listening socket test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _g25_listen_with_python,
                "0.0.0.0",
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime listened on all network interfaces.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not listen on all network interfaces.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _g25_run_single_network_policy_alternate(
            title="All-interface listener bind with alternate socket command",
            bypass_class="public_interface_listener_bind",
            command_family=_g25_listen_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_listen_shell_command(
                    self._operating_system,
                    "0.0.0.0",
                )
            ),
        )


class G09_T23:
    id = "T23"
    title = "Bind Linux privileged loopback port"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux privileged port binding is not applicable.",
            )

        return await _g25_run_shell_test(
            command_builder=_g25_build_privileged_port_shell_command,
            allowed_summary="Shell bound a Linux privileged loopback port.",
            denied_summary="Shell could not bind a Linux privileged loopback port.",
            not_applicable_summary="Linux privileged loopback port was unavailable.",
            timeout_summary="Shell privileged port binding test timed out.",
            failure_summary="Shell privileged port binding test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux privileged port binding is not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(_g25_bind_privileged_port_with_python)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime bound a Linux privileged loopback port.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            if _g25_is_address_in_use(error):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux privileged loopback port was unavailable.",
                    evidence=repr(error),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not bind a Linux privileged loopback port."
                ),
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return _g25_no_network_policy_alternates(
                "Linux privileged port binding is not applicable."
            )

        return await _g25_run_single_network_policy_alternate(
            title="Privileged port bind with alternate listener command",
            bypass_class="privileged_port_bind",
            command_family="nc/listen",
            operation=lambda: _g25_run_command(
                _g25_build_privileged_port_shell_command()
            ),
        )


class G09_T24:
    id = "T24"
    title = "Detect outbound proxy configuration"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _g25_run_shell_test(
            command_builder=lambda: _g25_build_proxy_detection_shell_command(
                self._operating_system,
            ),
            allowed_summary="Shell detected outbound proxy configuration.",
            denied_summary="Shell could not detect outbound proxy configuration.",
            not_applicable_summary=(
                "No supported shell proxy detection command was available."
            ),
            timeout_summary="Shell proxy detection test timed out.",
            failure_summary="Shell proxy detection test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _g25_detect_proxy_configuration_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected outbound proxy configuration.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime proxy detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _g25_run_single_network_policy_alternate(
            title="Proxy configuration detection with alternate system command",
            bypass_class="proxy_configuration_detection",
            command_family=_g25_proxy_command_family(self._operating_system),
            operation=lambda: _g25_run_command(
                _g25_build_proxy_detection_shell_command(self._operating_system)
            ),
        )


@dataclass(frozen=True)
class _g25_AlternateNetworkPolicyAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    operation: Callable[[], subprocess.CompletedProcess[str]]


async def _g25_run_single_network_policy_alternate(
    title: str,
    bypass_class: str,
    command_family: str,
    operation: Callable[[], subprocess.CompletedProcess[str]],
) -> AlternateInvocationResult:
    attempt = _g25_AlternateNetworkPolicyAttempt(
        id="A01",
        title=title,
        bypass_class=bypass_class,
        command_family=command_family,
        operation=operation,
    )
    return await asyncio.to_thread(
        _g25_run_network_policy_alternate_attempts, [attempt]
    )


def _g25_no_network_policy_alternates(summary: str) -> AlternateInvocationResult:
    return AlternateInvocationResult(
        outcome=Outcome.NOT_APPLICABLE,
        summary=summary,
        attempts=[],
    )


def _g25_run_network_policy_alternate_attempts(
    attempts: list[_g25_AlternateNetworkPolicyAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return _g25_no_network_policy_alternates(
            "No alternate shell attempts apply to this capability."
        )

    attempt_results = [
        _g25_run_network_policy_alternate_attempt(attempt) for attempt in attempts
    ]
    allowed_count = sum(
        1 for result in attempt_results if result.outcome == Outcome.ALLOWED
    )

    if allowed_count:
        outcome = Outcome.ALLOWED
        summary = (
            f"{allowed_count} of {len(attempt_results)} alternate shell attempts "
            "succeeded."
        )
    else:
        not_applicable_count = sum(
            1 for result in attempt_results if result.outcome == Outcome.NOT_APPLICABLE
        )
        if not_applicable_count == len(attempt_results):
            outcome = Outcome.NOT_APPLICABLE
            summary = "No alternate shell command was available."
        else:
            outcome = Outcome.DENIED
            summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _g25_run_network_policy_alternate_attempt(
    attempt: _g25_AlternateNetworkPolicyAttempt,
) -> AlternateAttemptResult:
    try:
        completed = attempt.operation()
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        elif completed.returncode == _g25_NO_SHELL_CANDIDATE_EXIT_CODE:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_g25_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g25_network_policy_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g25_network_policy_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except subprocess.TimeoutExpired as error:
        return _g25_network_policy_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except OSError as error:
        return _g25_network_policy_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except Exception as error:
        return _g25_network_policy_alternate_exception_result(
            attempt,
            Outcome.ERROR,
            error,
        )


def _g25_network_policy_alternate_exception_result(
    attempt: _g25_AlternateNetworkPolicyAttempt,
    outcome: Outcome,
    error: Exception,
) -> AlternateAttemptResult:
    return AlternateAttemptResult(
        id=attempt.id,
        title=attempt.title,
        outcome=outcome,
        bypass_class=attempt.bypass_class,
        command_family=attempt.command_family,
        evidence=repr(error),
    )


async def _g25_run_shell_test(
    command_builder: Callable[[], list[str]],
    allowed_summary: str,
    denied_summary: str,
    not_applicable_summary: str,
    timeout_summary: str,
    failure_summary: str,
) -> InvocationResult:
    try:
        command = command_builder()
        completed = await asyncio.to_thread(_g25_run_command, command)
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=completed.stdout.strip()[:500],
            )

        if completed.returncode == _g25_NO_SHELL_CANDIDATE_EXIT_CODE:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=not_applicable_summary,
                evidence=_g25_failure_evidence(completed, combined_output),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_g25_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell invocation was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=timeout_summary,
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=failure_summary,
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


def _g25_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g25_build_udp_shell_command(operating_system: OperatingSystem) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g25_build_windows_udp_shell_command()

    return _g25_build_linux_udp_shell_command()


def _g25_udp_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/udpclient"

    return "nc/udp"


def _g25_build_windows_udp_shell_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$payload = [Text.Encoding]::UTF8.GetBytes('sandbox-tester-udp')
$server = [Net.Sockets.UdpClient]::new(0)
$serverEndpoint = [Net.IPEndPoint]::new([Net.IPAddress]::Loopback, 0)
$client = [Net.Sockets.UdpClient]::new()
try {
    $port = $server.Client.LocalEndPoint.Port
    [void]$client.Send($payload, $payload.Length, '127.0.0.1', $port)
    $remote = [Net.IPEndPoint]::new([Net.IPAddress]::Any, 0)
    $received = $server.Receive([ref]$remote)
    $text = [Text.Encoding]::UTF8.GetString($received)
    if ($text -ne 'sandbox-tester-udp') {
        throw "Unexpected UDP payload: $text"
    }
    "port=$port; bytes=$($received.Length)"
}
finally {
    $client.Close()
    $server.Close()
}
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g25_build_linux_udp_shell_command() -> list[str]:
    script = """
set -u
if ! command -v nc >/dev/null 2>&1; then
    echo 'nc not found'
    exit 127
fi
port=$((40000 + ($$ % 20000)))
tmp_file=$(mktemp)
trap 'rm -f "$tmp_file"; kill "$server_pid" 2>/dev/null || true' EXIT
nc -u -l 127.0.0.1 "$port" > "$tmp_file" &
server_pid=$!
sleep 0.2
printf 'sandbox-tester-udp' | nc -u -w 1 127.0.0.1 "$port"
sleep 0.2
if grep -q 'sandbox-tester-udp' "$tmp_file"; then
    printf 'port=%s; bytes=18\\n' "$port"
    exit 0
fi
echo 'UDP payload was not received.'
exit 1
"""
    return ["sh", "-c", script]


def _g25_build_ping_shell_command(operating_system: OperatingSystem) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return ["ping", "-n", "1", "-w", "1000", "127.0.0.1"]

    return ["ping", "-c", "1", "-W", "1", "127.0.0.1"]


def _g25_proxy_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/netsh"

    return "sh/printenv"


def _g25_build_proxy_detection_shell_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g25_build_windows_proxy_detection_shell_command()

    return _g25_build_linux_proxy_detection_shell_command()


def _g25_build_windows_proxy_detection_shell_command() -> list[str]:
    proxy_names = ", ".join(
        _g25_quote_powershell_string(name) for name in _g25_PROXY_ENVIRONMENT_VARIABLES
    )
    script = f"""
$ErrorActionPreference = 'Stop'
$names = @({proxy_names})
$presentNames = @()
foreach ($name in $names) {{
    $value = [Environment]::GetEnvironmentVariable($name)
    if (-not [string]::IsNullOrWhiteSpace($value)) {{
        $presentNames += $name
    }}
}}
$winhttp = netsh winhttp show proxy 2>$null
$winhttpProxyPresent = $false
if ($LASTEXITCODE -eq 0) {{
    $winhttpText = $winhttp -join ' '
    $winhttpProxyPresent = (
        $winhttpText -notmatch 'Direct access' -and
        $winhttpText -notmatch 'no proxy server'
    )
}}
$parts = @(
    "env_proxy_names=[$($presentNames -join ',')]",
    "env_proxy_count=$($presentNames.Count)",
    "winhttp_proxy_present=$winhttpProxyPresent",
    "netsh_available=$($LASTEXITCODE -eq 0)"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g25_build_linux_proxy_detection_shell_command() -> list[str]:
    names = " ".join(_g25_PROXY_ENVIRONMENT_VARIABLES)
    printf_format = (
        "env_proxy_names=[%s]; env_proxy_count=%s; "
        "winhttp_proxy_present=not_applicable; netsh_available=False\\n"
    )
    script = f"""
set -u
present=""
count=0
for name in {names}; do
    value=$(printenv "$name" 2>/dev/null || true)
    if [ -n "$value" ]; then
        present="${{present}}${{name}},"
        count=$((count + 1))
    fi
done
printf {printf_format!r} "$present" "$count"
"""
    return ["sh", "-c", script]


def _g25_build_dns_shell_command(operating_system: OperatingSystem) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g25_build_windows_dns_shell_command()

    return _g25_build_linux_dns_shell_command()


def _g25_dns_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "nslookup"

    return "dig/nslookup"


def _g25_build_intranet_shell_command(
    operating_system: OperatingSystem,
    target: str,
) -> list[str]:
    host, ports = _g25_parse_intranet_target(target)

    if operating_system == OperatingSystem.WINDOWS:
        return _g25_build_windows_intranet_shell_command(host, ports)

    return _g25_build_linux_intranet_shell_command(host, ports)


def _g25_intranet_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/tcpclient"

    return "nc/connect"


def _g25_build_listen_shell_command(
    operating_system: OperatingSystem,
    bind_address: str,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g25_build_windows_listen_shell_command(bind_address)

    return _g25_build_linux_listen_shell_command(bind_address)


def _g25_listen_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/tcplistener"

    return "nc/listen"


def _g25_build_privileged_port_shell_command() -> list[str]:
    script = f"""
set -u
bind_address={_g25_quote_shell_string(_g25_LINUX_PRIVILEGED_BIND_ADDRESS)}
bind_port={_g25_LINUX_PRIVILEGED_BIND_PORT}
if command -v ss >/dev/null 2>&1; then
    if ss -ltn "sport = :$bind_port" | grep -q ":$bind_port"; then
        echo "bind_address=$bind_address; port=$bind_port; available=False"
        exit {_g25_NO_SHELL_CANDIDATE_EXIT_CODE}
    fi
fi
if ! command -v nc >/dev/null 2>&1; then
    echo 'nc not found'
    exit {_g25_NO_SHELL_CANDIDATE_EXIT_CODE}
fi
nc -l "$bind_address" "$bind_port" >/dev/null 2>&1 &
listener_pid=$!
sleep 0.2
if kill -0 "$listener_pid" 2>/dev/null; then
    kill "$listener_pid" 2>/dev/null || true
    echo "bind_address=$bind_address; port=$bind_port; listening=True"
    exit 0
fi
echo "bind_address=$bind_address; port=$bind_port; listening=False"
exit 1
"""
    return ["sh", "-c", script]


def _g25_build_windows_listen_shell_command(bind_address: str) -> list[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$address = [Net.IPAddress]::Parse('{bind_address}')
$listener = [Net.Sockets.TcpListener]::new($address, 0)
try {{
    $listener.Start()
    $endpoint = $listener.LocalEndpoint
    Write-Output "bind_address={bind_address}; port=$($endpoint.Port); listening=True"
}}
finally {{
    $listener.Stop()
}}
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g25_build_linux_listen_shell_command(bind_address: str) -> list[str]:
    quoted_bind_address = _g25_quote_shell_string(bind_address)
    script = f"""
set -u
if command -v nc >/dev/null 2>&1; then
    bind_address={quoted_bind_address}
    nc -l "$bind_address" 0 >/dev/null 2>&1 &
    listener_pid=$!
    sleep 0.2
    if kill -0 "$listener_pid" 2>/dev/null; then
        kill "$listener_pid" 2>/dev/null || true
        echo "bind_address=$bind_address; port=ephemeral; listening=True"
        exit 0
    fi
    echo "bind_address=$bind_address; listening=False"
    exit 1
fi
echo 'nc not found'
exit {_g25_NO_SHELL_CANDIDATE_EXIT_CODE}
"""
    return ["sh", "-c", script]


def _g25_build_windows_intranet_shell_command(host: str, ports: list[int]) -> list[str]:
    port_values = ", ".join(str(port) for port in ports)
    script = f"""
$ErrorActionPreference = 'Stop'
$hostName = {_g25_quote_powershell_string(host)}
$ports = @({port_values})
foreach ($port in $ports) {{
    $client = [Net.Sockets.TcpClient]::new()
    try {{
        $async = $client.BeginConnect($hostName, $port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(
            {_g25_INTRANET_CONNECT_TIMEOUT_SECONDS * 1000},
            $false
        )
        if ($connected) {{
            $client.EndConnect($async)
            Write-Output "host=$hostName; port=$port; connected=True"
            exit 0
        }}
    }}
    catch {{
    }}
    finally {{
        $client.Close()
    }}
}}
Write-Output "host=$hostName; ports=[$($ports -join ',')]; connected=False"
exit 1
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g25_build_linux_intranet_shell_command(host: str, ports: list[int]) -> list[str]:
    quoted_host = _g25_quote_shell_string(host)
    port_values = " ".join(str(port) for port in ports)
    script = f"""
set -u
if ! command -v nc >/dev/null 2>&1; then
    echo 'nc not found'
    exit {_g25_NO_SHELL_CANDIDATE_EXIT_CODE}
fi
host={quoted_host}
for port in {port_values}; do
    if nc -z -w {_g25_INTRANET_CONNECT_TIMEOUT_SECONDS} \\
        "$host" "$port" >/dev/null 2>&1; then
        echo "host=$host; port=$port; connected=True"
        exit 0
    fi
done
echo "host=$host; ports=[{",".join(str(port) for port in ports)}]; connected=False"
exit 1
"""
    return ["sh", "-c", script]


def _g25_build_metadata_shell_command(
    operating_system: OperatingSystem,
    metadata_endpoint_url: str | None,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _g25_build_windows_metadata_shell_command(metadata_endpoint_url)

    return _g25_build_linux_metadata_shell_command(metadata_endpoint_url)


def _g25_metadata_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/httpwebrequest"

    return "curl/wget"


def _g25_build_windows_metadata_shell_command(
    metadata_endpoint_url: str | None,
) -> list[str]:
    probes = _g25_metadata_probes(metadata_endpoint_url)
    probe_lines = []

    for provider, url, headers in probes:
        header_lines = "".join(
            f"$request.Headers.Add('{name}', '{value}');\n"
            for name, value in headers.items()
        )
        probe_lines.append(
            f"""
$request = [System.Net.HttpWebRequest]::Create('{url}')
$request.Method = 'GET'
$request.Timeout = {_g25_METADATA_TIMEOUT_SECONDS * 1000}
$request.ReadWriteTimeout = {_g25_METADATA_TIMEOUT_SECONDS * 1000}
$request.UserAgent = 'SandboxTester'
{header_lines}
try {{
    $response = $request.GetResponse()
    try {{
        $length = $response.ContentLength
        if ($length -lt 0) {{ $length = 0 }}
        $status = [int]$response.StatusCode
        Write-Output "provider={provider}; url={url}; status=$status; bytes=$length"
        exit 0
    }}
    finally {{
        $response.Close()
    }}
}}
catch [System.Net.WebException] {{
    if ($_.Exception.Response -ne $null) {{
        $response = $_.Exception.Response
        try {{
            $status = [int]$response.StatusCode
            Write-Output "provider={provider}; url={url}; status=$status; bytes=0"
            exit 0
        }}
        finally {{
            $response.Close()
        }}
    }}
}}
"""
        )

    script = (
        "$ErrorActionPreference = 'SilentlyContinue'\n"
        + "\n".join(probe_lines)
        + "\nWrite-Output 'No metadata endpoint responded.'\nexit 1\n"
    )
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g25_build_linux_metadata_shell_command(
    metadata_endpoint_url: str | None,
) -> list[str]:
    probes = _g25_metadata_probes(metadata_endpoint_url)
    probe_lines = []

    for provider, url, headers in probes:
        quoted_url = _g25_quote_shell_string(url)
        curl_headers = " ".join(
            f"-H {_g25_quote_shell_string(f'{name}: {value}')}"
            for name, value in headers.items()
        )
        wget_headers = " ".join(
            f"--header={_g25_quote_shell_string(f'{name}: {value}')}"
            for name, value in headers.items()
        )
        curl_command = (
            "curl -sS -o /dev/null "
            f"-m {_g25_METADATA_TIMEOUT_SECONDS} "
            "-w '%{http_code}' "
            f"{curl_headers} {quoted_url} "
            "2>/dev/null || true"
        )
        wget_command = (
            "wget -q -O /dev/null "
            f"-T {_g25_METADATA_TIMEOUT_SECONDS} "
            f"--server-response {wget_headers} {quoted_url} "
            "2>&1 | awk '/HTTP\\// { code=$2 } END { print code }'"
        )
        probe_lines.append(
            f"""
if command -v curl >/dev/null 2>&1; then
    status=$({curl_command})
elif command -v wget >/dev/null 2>&1; then
    status=$({wget_command})
else
    echo 'curl/wget not found'
    exit {_g25_NO_SHELL_CANDIDATE_EXIT_CODE}
fi
if [ -n "$status" ] && [ "$status" != "000" ]; then
    echo 'provider={provider}; url={url}; status='"$status"'; bytes=0'
    exit 0
fi
"""
        )

    script = (
        "set -u\n"
        + "\n".join(probe_lines)
        + "\necho 'No metadata endpoint responded.'\nexit 1\n"
    )
    return ["sh", "-c", script]


def _g25_build_windows_dns_shell_command() -> list[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$udp = nslookup -type=A {_g25_DNS_TEST_DOMAIN} {_g25_DNS_TEST_SERVER}
if ($LASTEXITCODE -ne 0) {{
    throw 'UDP DNS query failed.'
}}
$tcp = nslookup -vc -type=A {_g25_DNS_TEST_DOMAIN} {_g25_DNS_TEST_SERVER}
if ($LASTEXITCODE -ne 0) {{
    throw 'TCP DNS query failed.'
}}
"server={_g25_DNS_TEST_SERVER}; domain={_g25_DNS_TEST_DOMAIN}; udp=True; tcp=True"
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _g25_build_linux_dns_shell_command() -> list[str]:
    script = f"""
set -u
if command -v dig >/dev/null 2>&1; then
    dig +time=2 +tries=1 @{_g25_DNS_TEST_SERVER} {_g25_DNS_TEST_DOMAIN} A >/dev/null
    udp_status=$?
    dig +tcp +time=2 +tries=1 \
        @{_g25_DNS_TEST_SERVER} {_g25_DNS_TEST_DOMAIN} A >/dev/null
    tcp_status=$?
elif command -v nslookup >/dev/null 2>&1; then
    nslookup -type=A {_g25_DNS_TEST_DOMAIN} {_g25_DNS_TEST_SERVER} >/dev/null
    udp_status=$?
    nslookup -vc -type=A {_g25_DNS_TEST_DOMAIN} {_g25_DNS_TEST_SERVER} >/dev/null
    tcp_status=$?
else
    echo 'dig/nslookup not found'
    exit 127
fi
if [ "$udp_status" -eq 0 ] && [ "$tcp_status" -eq 0 ]; then
    printf 'server=%s; domain=%s; udp=True; tcp=True\n' \
        '{_g25_DNS_TEST_SERVER}' '{_g25_DNS_TEST_DOMAIN}'
    exit 0
fi
echo "udp_status=$udp_status; tcp_status=$tcp_status"
exit 1
"""
    return ["sh", "-c", script]


def _g25_run_udp_echo_with_python() -> str:
    payload = b"sandbox-tester-udp"
    received_payload = b""
    server_ready = threading.Event()
    server_error: list[BaseException] = []
    port_holder: list[int] = []

    def run_server() -> None:
        nonlocal received_payload

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
                server.bind(("127.0.0.1", 0))
                server.settimeout(5)
                port_holder.append(server.getsockname()[1])
                server_ready.set()
                received_payload, _address = server.recvfrom(1024)
        except BaseException as error:
            server_error.append(error)
            server_ready.set()

    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    server_ready.wait(timeout=5)

    if server_error:
        raise server_error[0]

    if not port_holder:
        raise TimeoutError("UDP server did not report a port.")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.sendto(payload, ("127.0.0.1", port_holder[0]))

    server_thread.join(timeout=5)

    if received_payload != payload:
        raise RuntimeError("UDP payload was not received.")

    return f"port={port_holder[0]}; bytes={len(received_payload)}"


def _g25_create_raw_icmp_socket() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP):
        return "family=AF_INET; type=SOCK_RAW; protocol=IPPROTO_ICMP"


def _g25_query_dns_with_python(use_tcp: bool) -> int:
    query = _g25_build_dns_query_packet(_g25_DNS_TEST_DOMAIN)

    if use_tcp:
        response = _g25_query_dns_tcp(query)
    else:
        response = _g25_query_dns_udp(query)

    return _g25_read_dns_answer_count(response)


def _g25_query_dns_udp(query: bytes) -> bytes:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(5)
        client.sendto(query, (_g25_DNS_TEST_SERVER, _g25_DNS_TEST_PORT))
        response, _address = client.recvfrom(4096)

    return response


def _g25_query_dns_tcp(query: bytes) -> bytes:
    with socket.create_connection(
        (_g25_DNS_TEST_SERVER, _g25_DNS_TEST_PORT),
        timeout=5,
    ) as client:
        client.sendall(struct.pack("!H", len(query)) + query)
        length_prefix = _g25_recv_exactly(client, 2)
        response_length = struct.unpack("!H", length_prefix)[0]
        return _g25_recv_exactly(client, response_length)


def _g25_build_dns_query_packet(domain: str) -> bytes:
    transaction_id = random.randint(0, 65535)
    header = struct.pack("!HHHHHH", transaction_id, 0x0100, 1, 0, 0, 0)
    question = b"".join(
        bytes([len(label)]) + label.encode("ascii") for label in domain.split(".")
    )
    question += b"\x00"
    question += struct.pack("!HH", 1, 1)
    return header + question


def _g25_read_dns_answer_count(response: bytes) -> int:
    if len(response) < 12:
        raise RuntimeError("DNS response was too short.")

    answer_count = struct.unpack("!H", response[6:8])[0]

    if answer_count < 1:
        raise RuntimeError("DNS response contained no answers.")

    return answer_count


def _g25_recv_exactly(client: socket.socket, byte_count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = byte_count

    while remaining > 0:
        chunk = client.recv(remaining)

        if not chunk:
            raise ConnectionError("Socket closed before enough data was received.")

        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)


def _g25_probe_metadata_endpoints_with_python(
    metadata_endpoint_url: str | None,
) -> str:
    errors: list[str] = []

    for provider, url, headers in _g25_metadata_probes(metadata_endpoint_url):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SandboxTester",
                **headers,
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=_g25_METADATA_TIMEOUT_SECONDS,
            ) as response:
                content_length = response.headers.get("Content-Length")
                bytes_count = int(content_length) if content_length else 0
                status = response.status
                return _g25_metadata_evidence(provider, url, status, bytes_count)
        except urllib.error.HTTPError as error:
            return _g25_metadata_evidence(provider, url, error.code, 0)
        except urllib.error.URLError as error:
            errors.append(f"{provider}:{error.reason!r}")
        except TimeoutError as error:
            errors.append(f"{provider}:{error!r}")

    raise OSError("; ".join(errors) or "No metadata endpoint responded.")


def _g25_connect_to_intranet_target_with_python(target: str) -> str:
    host, ports = _g25_parse_intranet_target(target)
    errors: list[str] = []

    for port in ports:
        try:
            with socket.create_connection(
                (host, port),
                timeout=_g25_INTRANET_CONNECT_TIMEOUT_SECONDS,
            ):
                return f"host={host}; port={port}; connected=True"
        except OSError as error:
            errors.append(f"{port}:{error.__class__.__name__}")

    raise OSError(
        f"host={host}; ports={ports}; connected=False; errors=[{','.join(errors)}]"
    )


def _g25_listen_with_python(bind_address: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((bind_address, 0))
        server.listen(1)
        port = server.getsockname()[1]

        return f"bind_address={bind_address}; port={port}; listening=True"


def _g25_bind_privileged_port_with_python() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(
            (
                _g25_LINUX_PRIVILEGED_BIND_ADDRESS,
                _g25_LINUX_PRIVILEGED_BIND_PORT,
            )
        )
        server.listen(1)

        return (
            f"bind_address={_g25_LINUX_PRIVILEGED_BIND_ADDRESS}; "
            f"port={_g25_LINUX_PRIVILEGED_BIND_PORT}; "
            "listening=True"
        )


def _g25_detect_proxy_configuration_with_python(
    operating_system: OperatingSystem,
) -> str:
    proxy_names = [
        name for name in _g25_PROXY_ENVIRONMENT_VARIABLES if os.environ.get(name)
    ]

    if operating_system == OperatingSystem.WINDOWS:
        winhttp_available, winhttp_proxy_present = _g25_detect_winhttp_proxy()
    else:
        winhttp_available = False
        winhttp_proxy_present = False

    return (
        f"env_proxy_names=[{','.join(proxy_names)}]; "
        f"env_proxy_count={len(proxy_names)}; "
        f"winhttp_proxy_present={winhttp_proxy_present}; "
        f"netsh_available={winhttp_available}"
    )


def _g25_detect_winhttp_proxy() -> tuple[bool, bool]:
    completed = subprocess.run(
        ["netsh", "winhttp", "show", "proxy"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        return False, False

    output = f"{completed.stdout}\n{completed.stderr}".lower()
    proxy_present = "direct access" not in output and "no proxy server" not in output

    return True, proxy_present


def _g25_parse_intranet_target(target: str) -> tuple[str, list[int]]:
    normalized_target = target.strip()

    if "://" in normalized_target:
        parsed_url = urllib.parse.urlparse(normalized_target)
        host = parsed_url.hostname

        if host is None:
            raise ValueError(f"Could not parse intranet target: {target!r}")

        if parsed_url.port is not None:
            return host, [parsed_url.port]

        if parsed_url.scheme == "http":
            return host, [80]

        if parsed_url.scheme == "https":
            return host, [443]

        return host, list(_g25_DEFAULT_INTRANET_PORTS)

    if normalized_target.count(":") == 1:
        host, port_text = normalized_target.rsplit(":", maxsplit=1)

        if port_text.isdigit():
            return host, [int(port_text)]

    return normalized_target, list(_g25_DEFAULT_INTRANET_PORTS)


def _g25_metadata_probes(
    metadata_endpoint_url: str | None,
) -> list[tuple[str, str, dict[str, str]]]:
    if metadata_endpoint_url is not None and metadata_endpoint_url.strip():
        return [("Configured", metadata_endpoint_url.strip(), {})]

    return list(_g25_DEFAULT_METADATA_PROBES)


def _g25_metadata_evidence(
    provider: str,
    url: str,
    status: int,
    bytes_count: int,
) -> str:
    return f"provider={provider}; url={url}; status={status}; bytes={bytes_count}"


def _g25_quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _g25_quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _g25_target_is_unconfigured(target: str | None) -> bool:
    return target is None or target.strip() == ""


def _g25_is_address_in_use(error: OSError) -> bool:
    return error.errno in {
        48,
        98,
        10048,
    }


def _g25_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


class G09_T25:
    id = "T25"
    title = "Send DNS query with encoded payload"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._dns_exfiltration_domain = capability_context.dns_exfiltration_domain

    async def run_shell(self) -> InvocationResult:
        if _g26_domain_is_unconfigured(self._dns_exfiltration_domain):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No DNS exfiltration test domain was configured.",
            )

        try:
            completed = await asyncio.to_thread(
                _g26_run_shell_dns_payload_query,
                str(self._dns_exfiltration_domain),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if _g26_shell_dns_query_reached_resolver(completed, combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell sent a DNS query with an encoded payload.",
                    evidence=_g26_dns_query_evidence(
                        str(self._dns_exfiltration_domain),
                        combined_output,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not send a DNS query with an encoded payload.",
                evidence=_g26_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The nslookup command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell DNS payload query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell DNS payload query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if _g26_domain_is_unconfigured(self._dns_exfiltration_domain):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No DNS exfiltration test domain was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g26_send_dns_payload_query_with_python,
                str(self._dns_exfiltration_domain),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime sent a DNS query with an encoded payload.",
                evidence=evidence,
            )
        except socket.gaierror as error:
            if _g26_gaierror_means_resolver_answered(error):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime sent a DNS query with an encoded payload."
                    ),
                    evidence=(
                        f"query={self._dns_exfiltration_domain}; "
                        f"resolver_response={error}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not send a DNS query with an encoded payload."
                ),
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime DNS payload query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime DNS payload query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if _g26_domain_is_unconfigured(self._dns_exfiltration_domain):
            return _g26_no_exfiltration_alternates(
                "No DNS exfiltration test domain was configured."
            )

        query_domain = str(self._dns_exfiltration_domain)
        return await _g26_run_single_exfiltration_alternate(
            title="DNS payload query with alternate resolver command",
            bypass_class="dns_payload_query",
            command_family="nslookup",
            operation=lambda: _g26_run_shell_dns_payload_query(query_domain),
            outcome_detector=_g26_dns_payload_query_outcome,
        )


class G09_T26:
    id = "T26"
    title = "Send HTTP request with custom headers/body to configured endpoint"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._http_exfiltration_domain = capability_context.http_exfiltration_domain
        self._http_exfiltration_header = capability_context.http_exfiltration_header

    async def run_shell(self) -> InvocationResult:
        configuration = _g26_parse_http_exfiltration_configuration(
            self._http_exfiltration_domain,
            self._http_exfiltration_header,
        )
        if configuration is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No HTTP exfiltration endpoint and header were configured.",
            )

        url, header_name, header_value = configuration

        try:
            completed = await asyncio.to_thread(
                _g26_run_shell_http_payload_request,
                url,
                header_name,
                header_value,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "HTTP_STATUS:" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Shell sent an HTTP request with a custom header and body."
                    ),
                    evidence=_g26_http_request_evidence(
                        url,
                        header_name,
                        _g26_extract_http_status(combined_output),
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not send an HTTP request with a custom header "
                    "and body."
                ),
                evidence=_g26_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP payload request timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP payload request failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        configuration = _g26_parse_http_exfiltration_configuration(
            self._http_exfiltration_domain,
            self._http_exfiltration_header,
        )
        if configuration is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No HTTP exfiltration endpoint and header were configured.",
            )

        url, header_name, header_value = configuration

        try:
            evidence = await asyncio.to_thread(
                _g26_send_http_payload_request_with_python,
                url,
                header_name,
                header_value,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime sent an HTTP request with a custom header and body."
                ),
                evidence=evidence,
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime sent an HTTP request with a custom header and body."
                ),
                evidence=_g26_http_request_evidence(url, header_name, error.code),
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not send an HTTP request with a custom "
                    "header and body."
                ),
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP payload request timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP payload request failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        configuration = _g26_parse_http_exfiltration_configuration(
            self._http_exfiltration_domain,
            self._http_exfiltration_header,
        )
        if configuration is None:
            return _g26_no_exfiltration_alternates(
                "No HTTP exfiltration endpoint and header were configured."
            )

        url, header_name, header_value = configuration
        return await _g26_run_single_exfiltration_alternate(
            title="HTTP payload request with alternate curl command",
            bypass_class="http_payload_request",
            command_family="curl/http-post",
            operation=lambda: _g26_run_shell_http_payload_request(
                url,
                header_name,
                header_value,
            ),
            outcome_detector=_g26_http_payload_request_outcome,
        )


class G09_T27:
    id = "T27"
    title = "Open WebSocket connection to configured endpoint"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._websocket_exfiltration_url = capability_context.websocket_exfiltration_url

    async def run_shell(self) -> InvocationResult:
        if _g26_domain_is_unconfigured(self._websocket_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No WebSocket exfiltration endpoint was configured.",
            )

        try:
            completed = await asyncio.to_thread(
                _g26_run_shell_websocket_handshake,
                str(self._websocket_exfiltration_url),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if _g26_websocket_handshake_succeeded(combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell opened a WebSocket connection.",
                    evidence=_g26_websocket_evidence(
                        str(self._websocket_exfiltration_url),
                        combined_output,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not open a WebSocket connection.",
                evidence=_g26_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell WebSocket handshake timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured WebSocket endpoint is invalid.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell WebSocket handshake failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if _g26_domain_is_unconfigured(self._websocket_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No WebSocket exfiltration endpoint was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g26_open_websocket_with_python,
                str(self._websocket_exfiltration_url),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime opened a WebSocket connection.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime WebSocket handshake timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured WebSocket endpoint is invalid.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime WebSocket handshake failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if _g26_domain_is_unconfigured(self._websocket_exfiltration_url):
            return _g26_no_exfiltration_alternates(
                "No WebSocket exfiltration endpoint was configured."
            )

        websocket_url = str(self._websocket_exfiltration_url)
        return await _g26_run_single_exfiltration_alternate(
            title="WebSocket handshake with alternate HTTP upgrade command",
            bypass_class="websocket_connection",
            command_family="curl/websocket-upgrade",
            operation=lambda: _g26_run_shell_websocket_handshake(websocket_url),
            outcome_detector=_g26_websocket_handshake_outcome,
        )


class G09_T28:
    id = "T28"
    title = "SMTP submission to configured test server"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._smtp_exfiltration_url = capability_context.smtp_exfiltration_url

    async def run_shell(self) -> InvocationResult:
        if _g26_domain_is_unconfigured(self._smtp_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SMTP exfiltration endpoint was configured.",
            )

        try:
            completed = await asyncio.to_thread(
                _g26_run_shell_smtp_submission_probe,
                str(self._smtp_exfiltration_url),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if _g26_smtp_probe_reached_server(completed, combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell reached the configured SMTP submission server.",
                    evidence=_g26_smtp_evidence(
                        str(self._smtp_exfiltration_url),
                        combined_output,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not reach the configured SMTP submission server."
                ),
                evidence=_g26_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell SMTP submission probe timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured SMTP endpoint is invalid.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell SMTP submission probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if _g26_domain_is_unconfigured(self._smtp_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SMTP exfiltration endpoint was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _g26_probe_smtp_submission_with_python,
                str(self._smtp_exfiltration_url),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime reached the configured SMTP submission server."
                ),
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime SMTP submission probe timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured SMTP endpoint is invalid.",
                evidence=repr(error),
            )
        except (smtplib.SMTPException, OSError) as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime SMTP submission probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if _g26_domain_is_unconfigured(self._smtp_exfiltration_url):
            return _g26_no_exfiltration_alternates(
                "No SMTP exfiltration endpoint was configured."
            )

        smtp_url = str(self._smtp_exfiltration_url)
        return await _g26_run_single_exfiltration_alternate(
            title="SMTP submission probe with alternate curl command",
            bypass_class="smtp_submission_probe",
            command_family="curl/smtp",
            operation=lambda: _g26_run_shell_smtp_submission_probe(smtp_url),
            outcome_detector=_g26_smtp_submission_probe_outcome,
        )


@dataclass(frozen=True)
class _g26_AlternateExfiltrationAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    operation: Callable[[], subprocess.CompletedProcess[str]]
    outcome_detector: Callable[[subprocess.CompletedProcess[str], str], Outcome]


async def _g26_run_single_exfiltration_alternate(
    title: str,
    bypass_class: str,
    command_family: str,
    operation: Callable[[], subprocess.CompletedProcess[str]],
    outcome_detector: Callable[[subprocess.CompletedProcess[str], str], Outcome],
) -> AlternateInvocationResult:
    attempt = _g26_AlternateExfiltrationAttempt(
        id="A01",
        title=title,
        bypass_class=bypass_class,
        command_family=command_family,
        operation=operation,
        outcome_detector=outcome_detector,
    )
    return await asyncio.to_thread(_g26_run_exfiltration_alternate_attempts, [attempt])


def _g26_no_exfiltration_alternates(summary: str) -> AlternateInvocationResult:
    return AlternateInvocationResult(
        outcome=Outcome.NOT_APPLICABLE,
        summary=summary,
        attempts=[],
    )


def _g26_run_exfiltration_alternate_attempts(
    attempts: list[_g26_AlternateExfiltrationAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return _g26_no_exfiltration_alternates(
            "No alternate shell attempts apply to this capability."
        )

    attempt_results = [
        _g26_run_exfiltration_alternate_attempt(attempt) for attempt in attempts
    ]
    allowed_count = sum(
        1 for result in attempt_results if result.outcome == Outcome.ALLOWED
    )

    if allowed_count:
        outcome = Outcome.ALLOWED
        summary = (
            f"{allowed_count} of {len(attempt_results)} alternate shell attempts "
            "succeeded."
        )
    else:
        not_applicable_count = sum(
            1 for result in attempt_results if result.outcome == Outcome.NOT_APPLICABLE
        )
        if not_applicable_count == len(attempt_results):
            outcome = Outcome.NOT_APPLICABLE
            summary = "No alternate shell command was available."
        else:
            outcome = Outcome.DENIED
            summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _g26_run_exfiltration_alternate_attempt(
    attempt: _g26_AlternateExfiltrationAttempt,
) -> AlternateAttemptResult:
    try:
        completed = attempt.operation()
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        outcome = attempt.outcome_detector(completed, combined_output)

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_g26_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g26_exfiltration_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g26_exfiltration_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except subprocess.TimeoutExpired as error:
        return _g26_exfiltration_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except ValueError as error:
        return _g26_exfiltration_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except OSError as error:
        return _g26_exfiltration_alternate_exception_result(
            attempt,
            Outcome.DENIED,
            error,
        )
    except Exception as error:
        return _g26_exfiltration_alternate_exception_result(
            attempt,
            Outcome.ERROR,
            error,
        )


def _g26_exfiltration_alternate_exception_result(
    attempt: _g26_AlternateExfiltrationAttempt,
    outcome: Outcome,
    error: Exception,
) -> AlternateAttemptResult:
    return AlternateAttemptResult(
        id=attempt.id,
        title=attempt.title,
        outcome=outcome,
        bypass_class=attempt.bypass_class,
        command_family=attempt.command_family,
        evidence=repr(error),
    )


def _g26_run_shell_dns_payload_query(
    query_domain: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["nslookup", "-type=A", query_domain],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _g26_send_dns_payload_query_with_python(query_domain: str) -> str:
    _hostname, _aliases, addresses = socket.gethostbyname_ex(query_domain)
    return f"query={query_domain}; response=ANSWER; addresses=[{','.join(addresses)}]"


def _g26_run_shell_http_payload_request(
    url: str,
    header_name: str,
    header_value: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--output",
            "-",
            "--write-out",
            "\nHTTP_STATUS:%{http_code}",
            "--request",
            "POST",
            "--header",
            f"{header_name}: {header_value}",
            "--data",
            "sandbox_tester_payload=example",
            url,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _g26_send_http_payload_request_with_python(
    url: str,
    header_name: str,
    header_value: str,
) -> str:
    body = b"sandbox_tester_payload=example"
    request = urllib.request.Request(
        url=url,
        data=body,
        headers={
            header_name: header_value,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        status_code = response.getcode()

    return _g26_http_request_evidence(url, header_name, status_code)


def _g26_run_shell_websocket_handshake(
    websocket_url: str,
) -> subprocess.CompletedProcess[str]:
    http_url = _g26_websocket_url_to_http_url(websocket_url)
    websocket_key = _g26_websocket_key()

    return subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--include",
            "--http1.1",
            "--max-time",
            "10",
            "--header",
            "Connection: Upgrade",
            "--header",
            "Upgrade: websocket",
            "--header",
            f"Sec-WebSocket-Key: {websocket_key}",
            "--header",
            "Sec-WebSocket-Version: 13",
            http_url,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _g26_open_websocket_with_python(websocket_url: str) -> str:
    parsed_url = _g26_parse_websocket_url(websocket_url)
    host = parsed_url.hostname
    if host is None:
        raise ValueError(f"WebSocket URL has no hostname: {websocket_url}")

    port = parsed_url.port
    if port is None and parsed_url.scheme == "wss":
        port = 443
    elif port is None:
        port = 80

    path = parsed_url.path or "/"
    if parsed_url.query:
        path = f"{path}?{parsed_url.query}"

    websocket_key = _g26_websocket_key()
    request = _g26_websocket_handshake_request(host, path, websocket_key)

    with socket.create_connection((host, port), timeout=10) as connection:
        if parsed_url.scheme == "wss":
            context = ssl.create_default_context()
            with context.wrap_socket(connection, server_hostname=host) as secure:
                secure.settimeout(10)
                secure.sendall(request)
                response = secure.recv(4096).decode("iso-8859-1", errors="replace")
        else:
            connection.settimeout(10)
            connection.sendall(request)
            response = connection.recv(4096).decode("iso-8859-1", errors="replace")

    if not _g26_websocket_handshake_succeeded(response):
        raise OSError(_g26_websocket_evidence(websocket_url, response))

    return _g26_websocket_evidence(websocket_url, response)


def _g26_run_shell_smtp_submission_probe(
    smtp_url: str,
) -> subprocess.CompletedProcess[str]:
    _g26_parse_smtp_url(smtp_url)

    return subprocess.run(
        [
            "curl",
            "--verbose",
            "--connect-timeout",
            "10",
            "--max-time",
            "15",
            "--url",
            smtp_url,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g26_probe_smtp_submission_with_python(smtp_url: str) -> str:
    parsed_url = _g26_parse_smtp_url(smtp_url)
    host = parsed_url.hostname
    if host is None:
        raise ValueError(f"SMTP URL has no hostname: {smtp_url}")

    port = parsed_url.port
    if port is None and parsed_url.scheme == "smtps":
        port = 465
    elif port is None:
        port = 587

    if parsed_url.scheme == "smtps":
        smtp_client: smtplib.SMTP = smtplib.SMTP_SSL(
            host=host,
            port=port,
            timeout=15,
        )
    else:
        smtp_client = smtplib.SMTP(host=host, port=port, timeout=15)

    with smtp_client:
        code, message = smtp_client.ehlo()

    return f"url={smtp_url}; ehlo_code={code}; message={message[:120]!r}"


def _g26_shell_dns_query_reached_resolver(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> bool:
    normalized_output = combined_output.lower()

    if completed.returncode == 0:
        return True

    return (
        "non-existent domain" in normalized_output
        or "nxdomain" in normalized_output
        or "can't find" in normalized_output
        or "server can't find" in normalized_output
    )


def _g26_dns_payload_query_outcome(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> Outcome:
    if _g26_shell_dns_query_reached_resolver(completed, combined_output):
        return Outcome.ALLOWED

    return Outcome.DENIED


def _g26_http_payload_request_outcome(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> Outcome:
    if completed.returncode == 0 and "HTTP_STATUS:" in combined_output:
        return Outcome.ALLOWED

    return Outcome.DENIED


def _g26_websocket_handshake_outcome(
    _completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> Outcome:
    if _g26_websocket_handshake_succeeded(combined_output):
        return Outcome.ALLOWED

    return Outcome.DENIED


def _g26_smtp_submission_probe_outcome(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> Outcome:
    if _g26_smtp_probe_reached_server(completed, combined_output):
        return Outcome.ALLOWED

    return Outcome.DENIED


def _g26_gaierror_means_resolver_answered(error: socket.gaierror) -> bool:
    return error.errno in {
        socket.EAI_NONAME,
        socket.EAI_NODATA,
    }


def _g26_dns_query_evidence(query_domain: str, output: str) -> str:
    normalized_output = output.lower()

    if "non-existent domain" in normalized_output or "nxdomain" in normalized_output:
        response = "NXDOMAIN"
    elif "can't find" in normalized_output or "server can't find" in normalized_output:
        response = "NXDOMAIN"
    else:
        response = "ANSWER"

    return f"query={query_domain}; response={response}"


def _g26_domain_is_unconfigured(domain: str | None) -> bool:
    return domain is None or domain.strip() == ""


def _g26_parse_http_exfiltration_configuration(
    domain: str | None,
    header: str | None,
) -> tuple[str, str, str] | None:
    if domain is None or domain.strip() == "":
        return None
    if header is None or header.strip() == "":
        return None
    if "=" not in header:
        return None

    header_name, header_value = header.split("=", maxsplit=1)
    if header_name.strip() == "" or header_value.strip() == "":
        return None

    url = domain.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"

    return url, header_name.strip(), header_value.strip()


def _g26_http_request_evidence(
    url: str,
    header_name: str,
    status_code: int | str,
) -> str:
    return f"url={url}; header={header_name}; status={status_code}"


def _g26_websocket_url_to_http_url(websocket_url: str) -> str:
    parsed_url = _g26_parse_websocket_url(websocket_url)

    if parsed_url.scheme == "wss":
        scheme = "https"
    else:
        scheme = "http"

    return urllib.parse.urlunparse(
        (
            scheme,
            parsed_url.netloc,
            parsed_url.path or "/",
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )


def _g26_parse_websocket_url(websocket_url: str) -> urllib.parse.ParseResult:
    parsed_url = urllib.parse.urlparse(websocket_url)
    if parsed_url.scheme not in {"ws", "wss"}:
        raise ValueError(f"Unsupported WebSocket URL scheme: {parsed_url.scheme}")

    return parsed_url


def _g26_websocket_key() -> str:
    return base64.b64encode(b"sandbox-tester!!").decode("ascii")


def _g26_websocket_handshake_request(
    host: str,
    path: str,
    websocket_key: str,
) -> bytes:
    request_lines = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}",
        "Connection: Upgrade",
        "Upgrade: websocket",
        f"Sec-WebSocket-Key: {websocket_key}",
        "Sec-WebSocket-Version: 13",
        "",
        "",
    ]
    request = "\r\n".join(request_lines)
    return request.encode("ascii")


def _g26_websocket_handshake_succeeded(response: str) -> bool:
    first_line = response.splitlines()[0] if response.splitlines() else ""
    return " 101 " in first_line or first_line.endswith(" 101")


def _g26_websocket_evidence(websocket_url: str, response: str) -> str:
    first_line = response.splitlines()[0] if response.splitlines() else "no response"
    return f"url={websocket_url}; response={first_line[:120]}"


def _g26_parse_smtp_url(smtp_url: str) -> urllib.parse.ParseResult:
    parsed_url = urllib.parse.urlparse(smtp_url)
    if parsed_url.scheme not in {"smtp", "smtps"}:
        raise ValueError(f"Unsupported SMTP URL scheme: {parsed_url.scheme}")
    if parsed_url.hostname is None:
        raise ValueError(f"SMTP URL has no hostname: {smtp_url}")

    return parsed_url


def _g26_smtp_probe_reached_server(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> bool:
    normalized_output = combined_output.lower()

    return (
        completed.returncode == 0
        or "smtp" in normalized_output
        and (" 220 " in normalized_output or " 250 " in normalized_output)
    )


def _g26_smtp_evidence(smtp_url: str, output: str) -> str:
    for line in output.splitlines():
        if "220" in line or "250" in line:
            return f"url={smtp_url}; response={line[:120]}"

    return f"url={smtp_url}; response=server reached"


def _g26_extract_http_status(output: str) -> str:
    marker = "HTTP_STATUS:"
    marker_index = output.rfind(marker)
    if marker_index == -1:
        return "unknown"

    return output[marker_index + len(marker) :].strip()


def _g26_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G09",
        title="Network access",
        tests=[
            G09_T01(),
            G09_T02(),
            G09_T03(),
            G09_T05(capability_context),
            G09_T06(capability_context),
            G09_T07(),
            G09_T08(),
            G09_T09(),
            G09_T10(capability_context),
            G09_T11(),
            G09_T12(),
            G09_T13(capability_context),
            G09_T14(capability_context),
            G09_T15(capability_context),
            G09_T16(capability_context),
            G09_T17(capability_context),
            G09_T18(capability_context),
            G09_T19(capability_context),
            G09_T20(capability_context),
            G09_T21(capability_context),
            G09_T22(capability_context),
            G09_T23(capability_context),
            G09_T24(capability_context),
            G09_T25(capability_context),
            G09_T26(capability_context),
            G09_T27(capability_context),
            G09_T28(capability_context),
        ],
    )
