"""Group 10: Local service and metadata access."""

from __future__ import annotations

import asyncio
import ctypes
import os
import shutil
import socket
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem, no_alternates


class G10_T01:
    id = "T01"
    title = "Connect to allowed local address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.allowed_local_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed local address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the allowed local address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed local address failed.",
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
                summary="Shell connection to allowed local address timed out.",
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
                summary="No allowed local address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed local address.",
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
                summary="Python runtime connection to allowed local address timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowed local address failed.",
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
            _run_local_service_alternate_attempts,
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
            raise RuntimeError("No allowed local address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Allowed local address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T02:
    id = "T02"
    title = "Connect to denied local address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.denied_local_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied local address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the denied local address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied local address failed.",
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
                summary="Shell connection to denied local address timed out.",
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
                summary="No denied local address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied local address.",
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
                summary="Python runtime connection to denied local address timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to denied local address failed.",
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
            _run_local_service_alternate_attempts,
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
            raise RuntimeError("No denied local address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Denied local address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T03:
    id = "T03"
    title = "Detect open local ports"

    _HOST = "127.0.0.1"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        listener: socket.socket | None = None

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if self._port_is_in_output(port, combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected an open local port.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but open port was not detected.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell open-port detection failed.",
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
                summary="Shell open-port detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local listener setup failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if listener is not None:
                listener.close()

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]
            discovered_ports = await asyncio.to_thread(self._scan_local_ports, port)

            if port in discovered_ports:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime detected an open local port.",
                    evidence=f"host={self._HOST}, ports={discovered_ports}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Python runtime did not detect the open local port.",
                evidence=f"host={self._HOST}, port={port}",
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
                summary="Python runtime local open-port detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if listener is not None:
                listener.close()

    async def run_alternates(self) -> AlternateInvocationResult:
        listener: socket.socket | None = None

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]
            return await asyncio.to_thread(
                _run_local_service_alternate_attempts,
                _build_open_port_detection_alternate_attempts(port),
            )
        finally:
            if listener is not None:
                listener.close()

    def _start_listener(self) -> socket.socket:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self._HOST, 0))
        listener.listen(1)
        return listener

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["netstat", "-ano", "-p", "tcp"]
        else:
            command = ["sh", "-c", "ss -ltn || netstat -ltn"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _port_is_in_output(self, port: int, output: str) -> bool:
        return f":{port}" in output

    def _scan_local_ports(self, target_port: int) -> list[int]:
        discovered_ports: list[int] = []
        start_port = max(1, target_port - 2)
        end_port = min(65535, target_port + 2)

        for port in range(start_port, end_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_client:
                socket_client.settimeout(0.25)
                result = socket_client.connect_ex((self._HOST, port))
                if result == 0:
                    discovered_ports.append(port)

        return discovered_ports


class G10_T04:
    id = "T04"
    title = "Connect to allowed database address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.allowed_database_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed database address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the allowed database address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed database address failed.",
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
                summary="Shell connection to allowed database address timed out.",
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
                summary="No allowed database address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed database address.",
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
                    "Python runtime connection to allowed database address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowed database address failed.",
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
            _run_local_service_alternate_attempts,
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
            raise RuntimeError("No allowed database address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Allowed database address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T05:
    id = "T05"
    title = "Connect to denied database address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.denied_database_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied database address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the denied database address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied database address failed.",
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
                summary="Shell connection to denied database address timed out.",
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
                summary="No denied database address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied database address.",
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
                    "Python runtime connection to denied database address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to denied database address failed.",
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
            _run_local_service_alternate_attempts,
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
            raise RuntimeError("No denied database address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Denied database address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T06:
    id = "T06"
    title = "Query Docker/container socket path"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._socket_path = capability_context.container_runtime_socket
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No container runtime socket path was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected the container runtime socket path.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell did not detect the container runtime socket path.",
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
                summary="Shell container socket path query timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No container runtime socket path was configured.",
            )

        try:
            detected = await asyncio.to_thread(self._socket_is_detectable)

            if detected:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime detected the container runtime socket path."
                    ),
                    evidence=f"socket_path={self._socket_path}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime did not detect the container runtime socket path."
                ),
                evidence=f"socket_path={self._socket_path}",
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
                summary="Python runtime container socket path query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_socket_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_local_service_alternate_attempts,
            _build_socket_path_alternate_attempts(
                self._operating_system,
                self._get_socket_path(),
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            shell_script = (
                f'if exist "{socket_path}" '
                "(echo exists) else (echo missing & exit /b 1)"
            )
            command = [
                "cmd",
                "/c",
                shell_script,
            ]
        else:
            command = [
                "sh",
                "-c",
                'test -S "$1" && echo socket',
                "sh",
                socket_path,
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _socket_is_detectable(self) -> bool:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            return os.path.exists(socket_path)

        path = Path(socket_path)
        path_stat = path.stat()
        return stat.S_ISSOCK(path_stat.st_mode)

    def _is_socket_unconfigured(self) -> bool:
        return self._socket_path is None or not self._socket_path.strip()

    def _get_socket_path(self) -> str:
        if self._socket_path is None or not self._socket_path.strip():
            raise RuntimeError("No container runtime socket path was configured.")

        return self._socket_path.strip()


class G10_T07:
    id = "T07"
    title = "Query local development server"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._url = capability_context.local_dev_server_url

    async def run_shell(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local development server URL was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the local development server.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to local development server failed.",
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
                summary="Shell query to local development server timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local development server URL was configured.",
            )

        try:
            status_code = await asyncio.to_thread(self._query_local_dev_server)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the local development server.",
                evidence=f"status_code={status_code}",
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
                summary="Python runtime query to local development server timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to local development server failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_url_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_local_service_alternate_attempts,
            _build_url_query_alternate_attempts(self._get_url()),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        url = self._get_url()
        return _run_shell_url_query_command(url, timeout_seconds=10)

    def _query_local_dev_server(self) -> int:
        url = self._get_url()

        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status

        return int(status_code)

    def _is_url_unconfigured(self) -> bool:
        return self._url is None or not self._url.strip()

    def _get_url(self) -> str:
        if self._url is None or not self._url.strip():
            raise RuntimeError("No local development server URL was configured.")

        return self._url.strip()


class G10_T08:
    id = "T08"
    title = "Query SSH agent socket"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._ssh_agent_socket = capability_context.ssh_agent_socket
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SSH agent socket was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected the SSH agent socket.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell did not detect the SSH agent socket.",
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
                summary="Shell SSH agent socket query timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SSH agent socket was configured.",
            )

        try:
            detected = await asyncio.to_thread(self._socket_is_detectable)

            if detected:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime detected the SSH agent socket.",
                    evidence=f"socket_path={self._ssh_agent_socket}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime did not detect the SSH agent socket.",
                evidence=f"socket_path={self._ssh_agent_socket}",
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
                summary="Python runtime SSH agent socket query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_socket_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_local_service_alternate_attempts,
            _build_socket_path_alternate_attempts(
                self._operating_system,
                self._get_socket_path(),
            ),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            shell_script = (
                f'if exist "{socket_path}" '
                "(echo exists) else (echo missing & exit /b 1)"
            )
            command = [
                "cmd",
                "/c",
                shell_script,
            ]
        else:
            command = [
                "sh",
                "-c",
                'test -S "$1" && echo socket',
                "sh",
                socket_path,
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _socket_is_detectable(self) -> bool:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            return os.path.exists(socket_path)

        path = Path(socket_path)
        path_stat = path.stat()
        return stat.S_ISSOCK(path_stat.st_mode)

    def _is_socket_unconfigured(self) -> bool:
        return self._ssh_agent_socket is None or not self._ssh_agent_socket.strip()

    def _get_socket_path(self) -> str:
        if self._ssh_agent_socket is None or not self._ssh_agent_socket.strip():
            raise RuntimeError("No SSH agent socket was configured.")

        return self._ssh_agent_socket.strip()


class G10_T09:
    id = "T09"
    title = "Query keychain/credential service"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried a credential service surface.",
                    evidence=self._shell_success_evidence(combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not query a credential service surface.",
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
                summary="Shell credential service query timed out.",
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
            evidence = await asyncio.to_thread(self._query_credential_service)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried a credential service surface.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime did not find a credential service surface.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime credential service query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime credential service query failed.",
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
            _run_local_service_alternate_attempts,
            _build_credential_service_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmdkey", "/list"]
        else:
            shell_script = (
                'if [ -n "$DBUS_SESSION_BUS_ADDRESS" ]; then '
                'echo "dbus-session-bus"; exit 0; fi; '
                "if command -v secret-tool >/dev/null 2>&1; then "
                "secret-tool --version; exit 0; fi; "
                'echo "credential service surface not found"; exit 1'
            )
            command = ["sh", "-c", shell_script]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _query_credential_service(self) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            completed = subprocess.run(
                ["cmdkey", "/list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if completed.returncode != 0:
                raise OSError(completed.stderr.strip() or completed.stdout.strip())

            return "cmdkey query completed."

        detected_surfaces: list[str] = []

        if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
            detected_surfaces.append("DBUS_SESSION_BUS_ADDRESS")

        if shutil.which("secret-tool") is not None:
            detected_surfaces.append("secret-tool")

        if not detected_surfaces:
            raise FileNotFoundError("No Linux credential service surface was found.")

        return ", ".join(detected_surfaces)

    def _shell_success_evidence(self, output: str) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            return "cmdkey query completed."

        return output[:500]


class G10_T10:
    id = "T10"
    title = "Query print/spooler service"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the print/spooler service.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not query the print/spooler service.",
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
                summary="Shell print/spooler service query timed out.",
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
            evidence = await asyncio.to_thread(self._query_print_service)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the print/spooler service.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime did not find a print/spooler service.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime print/spooler service query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime print/spooler service query failed.",
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
            _run_local_service_alternate_attempts,
            _build_print_service_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["sc", "query", "spooler"]
        else:
            shell_script = (
                "if command -v lpstat >/dev/null 2>&1; then "
                "lpstat -r; exit $?; fi; "
                "if command -v systemctl >/dev/null 2>&1; then "
                "systemctl status cups --no-pager; exit $?; fi; "
                'echo "print service query tool not found"; exit 1'
            )
            command = ["sh", "-c", shell_script]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _query_print_service(self) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            return self._query_windows_spooler_service()

        return self._query_linux_print_service()

    def _query_windows_spooler_service(self) -> str:
        open_sc_manager = ctypes.windll.advapi32.OpenSCManagerW
        open_sc_manager.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        ]
        open_sc_manager.restype = wintypes.HANDLE

        open_service = ctypes.windll.advapi32.OpenServiceW
        open_service.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        ]
        open_service.restype = wintypes.HANDLE

        close_service_handle = ctypes.windll.advapi32.CloseServiceHandle
        close_service_handle.argtypes = [wintypes.HANDLE]
        close_service_handle.restype = wintypes.BOOL

        service_manager = open_sc_manager(None, None, 0x0004)
        if service_manager == 0:
            raise ctypes.WinError()

        try:
            service = open_service(
                service_manager,
                "Spooler",
                0x0004,
            )
            if service == 0:
                raise ctypes.WinError()

            try:
                return "Windows Spooler service is queryable."
            finally:
                close_service_handle(service)
        finally:
            close_service_handle(service_manager)

    def _query_linux_print_service(self) -> str:
        lpstat_path = shutil.which("lpstat")
        if lpstat_path is not None:
            completed = subprocess.run(
                [lpstat_path, "-r"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if completed.returncode == 0:
                return completed.stdout.strip()[:500]

            raise OSError(completed.stderr.strip() or completed.stdout.strip())

        systemctl_path = shutil.which("systemctl")
        if systemctl_path is not None:
            completed = subprocess.run(
                [systemctl_path, "status", "cups", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if completed.returncode == 0:
                return "CUPS service is queryable."

            raise OSError(completed.stderr.strip() or completed.stdout.strip())

        raise FileNotFoundError("No print service query tool was found.")


class G10_T11:
    id = "T11"
    title = "Query local model server"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._url = capability_context.local_model_server_url

    async def run_shell(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local model server URL was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the local model server.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to local model server failed.",
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
                summary="Shell query to local model server timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local model server URL was configured.",
            )

        try:
            status_code = await asyncio.to_thread(self._query_local_model_server)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the local model server.",
                evidence=f"status_code={status_code}",
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
                summary="Python runtime query to local model server timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to local model server failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_url_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_local_service_alternate_attempts,
            _build_url_query_alternate_attempts(self._get_url()),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        url = self._get_url()
        return _run_shell_url_query_command(url, timeout_seconds=10)

    def _query_local_model_server(self) -> int:
        url = self._get_url()

        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status

        return int(status_code)

    def _is_url_unconfigured(self) -> bool:
        return self._url is None or not self._url.strip()

    def _get_url(self) -> str:
        if self._url is None or not self._url.strip():
            raise RuntimeError("No local model server URL was configured.")

        return self._url.strip()


@dataclass(frozen=True)
class _AlternateLocalServiceAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_tcp_connect_alternate_attempts(
    host: str,
    port: int,
) -> list[_AlternateLocalServiceAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateLocalServiceAttempt(
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
        _AlternateLocalServiceAttempt(
            id="A01",
            title="Connect via netcat",
            bypass_class="alternate_command",
            command_family="nc",
            command=["nc", "-z", "-w", "10", host, str(port)],
        ),
        _AlternateLocalServiceAttempt(
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


def _build_open_port_detection_alternate_attempts(
    port: int,
) -> list[_AlternateLocalServiceAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateLocalServiceAttempt(
                id="A01",
                title="Detect open port via Get-NetTCPConnection",
                bypass_class="alternate_command",
                command_family="powershell/Get-NetTCPConnection",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        "$connection = Get-NetTCPConnection "
                        f"-LocalPort {port} -State Listen "
                        "-ErrorAction Stop; "
                        "if ($null -eq $connection) { exit 1 }; "
                        f"Write-Output 'port={port}'"
                    ),
                ],
            )
        ]

    return [
        _AlternateLocalServiceAttempt(
            id="A01",
            title="Detect open port via lsof",
            bypass_class="alternate_command",
            command_family="lsof",
            command=["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
        ),
        _AlternateLocalServiceAttempt(
            id="A02",
            title="Detect open port via fuser",
            bypass_class="alternate_command",
            command_family="fuser",
            command=["fuser", f"{port}/tcp"],
        ),
    ]


def _build_socket_path_alternate_attempts(
    operating_system: OperatingSystem,
    socket_path: str,
) -> list[_AlternateLocalServiceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateLocalServiceAttempt(
                id="A01",
                title="Detect socket path via PowerShell Test-Path",
                bypass_class="alternate_command",
                command_family="powershell/Test-Path",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        f"if (Test-Path -LiteralPath "
                        f"{_quote_powershell_string(socket_path)}) "
                        "{ Write-Output 'exists' } else { exit 1 }"
                    ),
                ],
            )
        ]

    return [
        _AlternateLocalServiceAttempt(
            id="A01",
            title="Detect socket path via stat",
            bypass_class="alternate_command",
            command_family="stat",
            command=[
                "sh",
                "-c",
                'test "$(stat -c %F "$1")" = "socket" && echo socket',
                "sh",
                socket_path,
            ],
        ),
        _AlternateLocalServiceAttempt(
            id="A02",
            title="Detect socket path via file",
            bypass_class="alternate_command",
            command_family="file",
            command=[
                "sh",
                "-c",
                'file -b "$1" | grep -i socket',
                "sh",
                socket_path,
            ],
        ),
    ]


def _build_url_query_alternate_attempts(
    url: str,
) -> list[_AlternateLocalServiceAttempt]:
    if sys.platform == "win32":
        return [
            _AlternateLocalServiceAttempt(
                id="A01",
                title="Query URL via PowerShell .NET WebRequest",
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
                        "$request.Method = 'GET'; "
                        "$request.Timeout = 10000; "
                        "$response = $request.GetResponse(); "
                        "Write-Output ('status_code=' + [int]$response.StatusCode); "
                        "$response.Close()"
                    ),
                ],
            )
        ]

    return [
        _AlternateLocalServiceAttempt(
            id="A01",
            title="Query URL via wget",
            bypass_class="alternate_command",
            command_family="wget",
            command=["wget", "--spider", "--timeout=10", "--server-response", url],
        )
    ]


def _build_credential_service_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateLocalServiceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateLocalServiceAttempt(
                id="A01",
                title="Query credential manager via cmdkey",
                bypass_class="credential_service_query",
                command_family="cmdkey",
                command=["cmdkey", "/list"],
            ),
            _AlternateLocalServiceAttempt(
                id="A02",
                title="Query vault credential cmdlet availability",
                bypass_class="credential_service_query",
                command_family="powershell/Get-Command",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        "Get-Command Get-StoredCredential -ErrorAction Stop"
                    ),
                ],
            ),
        ]

    return [
        _AlternateLocalServiceAttempt(
            id="A01",
            title="Query Secret Service through secret-tool",
            bypass_class="credential_service_query",
            command_family="secret-tool",
            command=["secret-tool", "--version"],
        ),
        _AlternateLocalServiceAttempt(
            id="A02",
            title="Detect DBus session credential surface",
            bypass_class="credential_service_query",
            command_family="dbus/environment",
            command=[
                "sh",
                "-c",
                ('test -n "$DBUS_SESSION_BUS_ADDRESS" && echo "dbus-session-bus"'),
            ],
        ),
    ]


def _build_print_service_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateLocalServiceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return [
            _AlternateLocalServiceAttempt(
                id="A01",
                title="Query spooler service via PowerShell",
                bypass_class="service_query",
                command_family="powershell/Get-Service",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        "Get-Service -Name Spooler | "
                        "Select-Object -ExpandProperty Status"
                    ),
                ],
            ),
            _AlternateLocalServiceAttempt(
                id="A02",
                title="Query spooler service via service controller",
                bypass_class="service_query",
                command_family="sc",
                command=["sc", "query", "spooler"],
            ),
        ]

    return [
        _AlternateLocalServiceAttempt(
            id="A01",
            title="Query CUPS scheduler via lpstat",
            bypass_class="service_query",
            command_family="lpstat",
            command=["lpstat", "-r"],
        ),
        _AlternateLocalServiceAttempt(
            id="A02",
            title="Query CUPS service via systemctl",
            bypass_class="service_query",
            command_family="systemctl",
            command=["systemctl", "status", "cups", "--no-pager"],
        ),
    ]


def _run_local_service_alternate_attempts(
    attempts: list[_AlternateLocalServiceAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _run_local_service_alternate_attempt(attempt) for attempt in attempts
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
        outcome = Outcome.DENIED
        summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _run_local_service_alternate_attempt(
    attempt: _AlternateLocalServiceAttempt,
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
    attempt: _AlternateLocalServiceAttempt,
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


def _run_shell_url_query_command(
    url: str,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_url_query_command(url, timeout_seconds)
    else:
        command = _build_linux_url_query_command(url, timeout_seconds)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,
        check=False,
    )


def _build_windows_url_query_command(
    url: str,
    timeout_seconds: int,
) -> list[str]:
    script = (
        "$ProgressPreference = 'SilentlyContinue'; "
        "$response = Invoke-WebRequest "
        f"-Uri {_quote_powershell_string(url)} "
        "-UseBasicParsing "
        f"-TimeoutSec {timeout_seconds}; "
        'Write-Output "status_code=$($response.StatusCode)"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_url_query_command(
    url: str,
    timeout_seconds: int,
) -> list[str]:
    return [
        "curl",
        "--max-time",
        str(timeout_seconds),
        "--silent",
        "--show-error",
        "--output",
        "/dev/null",
        "--write-out",
        "status_code=%{http_code}",
        url,
    ]


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


_g24_NO_SHELL_CANDIDATE_EXIT_CODE = 127

_g24_LINUX_SURFACE_DIRECTORIES = [
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/run"),
    Path("/mnt"),
    Path("/media"),
]

_g24_LINUX_SURFACE_DIRECTORIES_AS_TEXT = [
    str(path) for path in _g24_LINUX_SURFACE_DIRECTORIES
]

_g24_LINUX_PROCESS_NAMESPACE_DIRECTORY = Path("/proc/self/ns")

_g24_LINUX_SERVICE_ACCOUNT_PATHS = [
    Path("/var/run/secrets/kubernetes.io"),
    Path("/run/secrets/kubernetes.io"),
    Path("/run/secrets"),
    Path("/var/run/secrets"),
]

_g24_LINUX_MOUNTINFO_PATH = Path("/proc/self/mountinfo")

_g24_LINUX_CONTAINER_RUNTIME_SOCKET_PATHS = [
    Path("/run/containerd/containerd.sock"),
    Path("/var/run/containerd/containerd.sock"),
    Path("/run/crio/crio.sock"),
    Path("/var/run/crio/crio.sock"),
    Path("/run/podman/podman.sock"),
    Path("/var/run/podman/podman.sock"),
]


class G10_T12:
    id = "T12"
    title = "Access Linux container runtime Unix sockets"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _g24_run_shell_container_runtime_socket_access,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell accessed a Linux container runtime Unix socket.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _g24_NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux container runtime Unix sockets were not present.",
                    evidence=_g24_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not access Linux container runtime Unix sockets."
                ),
                evidence=_g24_failure_evidence(completed, combined_output),
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
                summary="Shell container runtime socket access timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell container runtime socket access failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux container runtime Unix sockets were not present.",
            )

        try:
            outcome, evidence = await asyncio.to_thread(
                _g24_access_container_runtime_sockets_with_python,
            )

            if outcome == Outcome.ALLOWED:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime accessed a Linux container runtime Unix socket."
                    ),
                    evidence=evidence,
                )

            if outcome == Outcome.NOT_APPLICABLE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux container runtime Unix sockets were not present.",
                    evidence=evidence,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not access Linux container runtime Unix "
                    "sockets."
                ),
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
                summary="Python runtime container runtime socket access failed.",
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
            _g24_run_namespace_alternate_attempts,
            _g24_build_container_runtime_socket_alternate_attempts(
                self._operating_system
            ),
        )


def _g24_run_shell_surface_directory_listing(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux namespace surface directories are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_surface_directory_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


@dataclass(frozen=True)
class _g24_AlternateNamespaceAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _g24_build_surface_directory_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    paths = " ".join(str(path) for path in _g24_LINUX_SURFACE_DIRECTORIES)
    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Read namespace surface directories via find",
            bypass_class="namespace_surface_directory_read",
            command_family="find",
            command=[
                "sh",
                "-c",
                (
                    f"for path in {paths}; do "
                    'printf "%s=" "$path"; '
                    'find "$path" -maxdepth 1 -mindepth 1 -print 2>/dev/null '
                    "| head -n 5 | paste -sd, -; "
                    "done"
                ),
            ],
        ),
        _g24_AlternateNamespaceAttempt(
            id="A02",
            title="Read namespace surface metadata via stat",
            bypass_class="namespace_surface_directory_read",
            command_family="stat",
            command=["stat", *_g24_LINUX_SURFACE_DIRECTORIES_AS_TEXT],
        ),
    ]


def _g24_build_process_namespace_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Read process namespace links via ls",
            bypass_class="process_namespace_link_read",
            command_family="ls/readlink",
            command=[
                "sh",
                "-c",
                (
                    "ls -l /proc/self/ns; "
                    "for namespace in /proc/self/ns/*; do "
                    'printf "%s=" "$(basename "$namespace")"; '
                    'readlink "$namespace"; '
                    "done"
                ),
            ],
        )
    ]


def _g24_build_service_account_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    paths = " ".join(str(path) for path in _g24_LINUX_SERVICE_ACCOUNT_PATHS)
    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Read service account secret metadata via find",
            bypass_class="service_account_secret_metadata_read",
            command_family="find/wc",
            command=[
                "sh",
                "-c",
                (
                    f"present=0; readable=0; for root in {paths}; do "
                    '[ -e "$root" ] || continue; present=1; '
                    'find "$root" -maxdepth 3 -type f 2>/dev/null | '
                    "while IFS= read -r file; do "
                    'size=$(wc -c < "$file" 2>/dev/null) '
                    "&& readable=$((readable + 1)) "
                    '&& printf "%s:size=%s;" "$file" "$size"; '
                    "done; "
                    "done; "
                    '[ "$present" -eq 1 ] || exit 127'
                ),
            ],
        )
    ]


def _g24_build_mount_surface_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Detect mount surfaces via findmnt",
            bypass_class="mount_surface_detection",
            command_family="findmnt",
            command=[
                "sh",
                "-c",
                (
                    "command -v findmnt >/dev/null 2>&1 || exit 127; "
                    "findmnt -R -o TARGET,SOURCE,FSTYPE,OPTIONS | head -n 30"
                ),
            ],
        ),
        _g24_AlternateNamespaceAttempt(
            id="A02",
            title="Detect mount surfaces via mount and df",
            bypass_class="mount_surface_detection",
            command_family="mount/df",
            command=["sh", "-c", "mount | head -n 30; df -T | head -n 30"],
        ),
    ]


def _g24_build_container_runtime_socket_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_g24_AlternateNamespaceAttempt]:
    if operating_system == OperatingSystem.WINDOWS:
        return []

    return [
        _g24_AlternateNamespaceAttempt(
            id="A01",
            title="Access container runtime sockets via shell socket client",
            bypass_class="container_runtime_socket_access",
            command_family="socat/nc-unix",
            command=_g24_build_linux_container_runtime_socket_command(),
        )
    ]


def _g24_run_namespace_alternate_attempts(
    attempts: list[_g24_AlternateNamespaceAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [
        _g24_run_namespace_alternate_attempt(attempt) for attempt in attempts
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


def _g24_run_namespace_alternate_attempt(
    attempt: _g24_AlternateNamespaceAttempt,
) -> AlternateAttemptResult:
    try:
        completed = subprocess.run(
            attempt.command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        elif completed.returncode == _g24_NO_SHELL_CANDIDATE_EXIT_CODE:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_g24_failure_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _g24_namespace_alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _g24_namespace_alternate_exception_result(attempt, Outcome.ERROR, error)


def _g24_namespace_alternate_exception_result(
    attempt: _g24_AlternateNamespaceAttempt,
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


def _g24_run_shell_process_namespace_link_read(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux process namespace links are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_process_namespace_link_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_run_shell_service_account_secret_read(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux service account secret files are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_service_account_secret_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_run_shell_mount_surface_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux mount and volume surfaces are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_mount_surface_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_run_shell_container_runtime_socket_access(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_g24_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux container runtime Unix sockets are not applicable.",
        )

    return subprocess.run(
        _g24_build_linux_container_runtime_socket_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _g24_build_linux_surface_directory_command() -> list[str]:
    paths = " ".join(str(path) for path in _g24_LINUX_SURFACE_DIRECTORIES)
    script = f"""
set -u
denied=0
evidence=""
for path in {paths}; do
    if [ ! -e "$path" ]; then
        evidence="${{evidence}}$path:missing;"
        continue
    fi
    if [ ! -d "$path" ]; then
        evidence="${{evidence}}$path:not_directory;"
        denied=1
        continue
    fi
    sample=$(ls -A "$path" 2>/dev/null | head -n 5 | paste -sd, -)
    status=$?
    if [ "$status" -eq 0 ]; then
        evidence="${{evidence}}$path:readable:sample=[$sample];"
    else
        evidence="${{evidence}}$path:denied;"
        denied=1
    fi
done
printf '%s\\n' "$evidence"
exit "$denied"
"""
    return ["sh", "-c", script]


def _g24_build_linux_container_runtime_socket_command() -> list[str]:
    paths = " ".join(str(path) for path in _g24_linux_container_runtime_socket_paths())
    script = f"""
set -u
present=0
connected=0
denied=0
evidence=""
if command -v socat >/dev/null 2>&1; then
    client=socat
elif command -v nc >/dev/null 2>&1; then
    client=nc
else
    client=""
fi
for path in {paths}; do
    if [ ! -e "$path" ]; then
        continue
    fi
    if [ ! -S "$path" ]; then
        evidence="${{evidence}}$path:not_socket;"
        present=1
        denied=$((denied + 1))
        continue
    fi
    present=1
    if [ -z "$client" ]; then
        evidence="${{evidence}}$path:present:no_shell_socket_client;"
        continue
    fi
    if [ "$client" = "socat" ]; then
        timeout 2 sh -c "printf '' | socat - UNIX-CONNECT:'$path'" \
            >/dev/null 2>&1
        status=$?
    else
        timeout 2 nc -U -z "$path" >/dev/null 2>&1
        status=$?
    fi
    if [ "$status" -eq 0 ]; then
        connected=$((connected + 1))
        evidence="${{evidence}}$path:connected;"
    else
        denied=$((denied + 1))
        evidence="${{evidence}}$path:denied_or_unreachable:status=$status;"
    fi
done
if [ "$present" -eq 0 ]; then
    echo "present=False"
    exit 127
fi
printf 'present=True; connected_count=%s; denied_count=%s; sockets=[%s]\\n' \
    "$connected" \
    "$denied" \
    "$evidence"
if [ "$connected" -gt 0 ]; then
    exit 0
fi
if [ -z "$client" ]; then
    exit 127
fi
exit 1
"""
    return ["sh", "-c", script]


def _g24_build_linux_mount_surface_command() -> list[str]:
    script = """
set -u
if [ ! -r /proc/self/mountinfo ]; then
    echo '/proc/self/mountinfo:unreadable'
    exit 1
fi
mount_count=$(wc -l < /proc/self/mountinfo)
rw_count=$(
    awk '{
        split($6, options, ",")
        for (i in options) {
            if (options[i] == "rw") {
                count += 1
                break
            }
        }
    } END { print count + 0 }' /proc/self/mountinfo
)
bind_like_count=$(
    awk '$0 ~ / - (overlay|9p|virtiofs|fuse|fuse\\.|nfs|cifs|drvfs|vboxsf|vmhgfs) / {
        count += 1
    } END { print count + 0 }' /proc/self/mountinfo
)
sample=$(awk '{
    separator = 0
    for (i = 1; i <= NF; i++) {
        if ($i == "-") {
            separator = i
            break
        }
    }
    if (separator > 0) {
        print $5 ":" $(separator + 1) ":" $(separator + 2) ":" $6
    }
}' /proc/self/mountinfo | head -n 8 | paste -sd, -)
printf 'mount_count=%s; rw_option_count=%s; bind_like_count=%s; sample=[%s]\\n' \
    "$mount_count" \
    "$rw_count" \
    "$bind_like_count" \
    "$sample"
"""
    return ["sh", "-c", script]


def _g24_build_linux_service_account_secret_command() -> list[str]:
    paths = " ".join(str(path) for path in _g24_LINUX_SERVICE_ACCOUNT_PATHS)
    script = f"""
set -u
present=0
readable=0
denied=0
evidence=""
for root in {paths}; do
    if [ ! -e "$root" ]; then
        continue
    fi
    present=1
    if [ -f "$root" ]; then
        size=$(wc -c < "$root" 2>/dev/null || true)
        if [ -n "$size" ]; then
            readable=$((readable + 1))
            evidence="${{evidence}}$root:file:size=$size;"
        else
            denied=$((denied + 1))
            evidence="${{evidence}}$root:file:denied;"
        fi
        continue
    fi
    if [ -d "$root" ]; then
        while IFS= read -r file; do
            [ -n "$file" ] || continue
            size=$(wc -c < "$file" 2>/dev/null || true)
            if [ -n "$size" ]; then
                readable=$((readable + 1))
                evidence="${{evidence}}$file:file:size=$size;"
            else
                denied=$((denied + 1))
                evidence="${{evidence}}$file:file:denied;"
            fi
        done <<EOF
$(find "$root" -maxdepth 3 -type f 2>/dev/null)
EOF
    fi
done
if [ "$present" -eq 0 ]; then
    echo "present=False"
    exit 127
fi
printf 'present=True; readable_count=%s; denied_count=%s; files=[%s]\\n' \\
    "$readable" \\
    "$denied" \\
    "$evidence"
if [ "$readable" -gt 0 ]; then
    exit 0
fi
exit 1
"""
    return ["sh", "-c", script]


def _g24_build_linux_process_namespace_link_command() -> list[str]:
    script = """
set -u
if [ ! -d /proc/self/ns ]; then
    echo '/proc/self/ns:missing'
    exit 1
fi
evidence=""
for namespace in /proc/self/ns/*; do
    name=$(basename "$namespace")
    target=$(readlink "$namespace" 2>/dev/null || true)
    if [ -n "$target" ]; then
        evidence="${evidence}${name}:${target},"
    else
        evidence="${evidence}${name}:denied,"
        exit_code=1
    fi
done
printf '%s\\n' "$evidence"
exit "${exit_code:-0}"
"""
    return ["sh", "-c", script]


def _g24_read_surface_directories_with_python() -> tuple[bool, str]:
    all_readable = True
    entries: list[str] = []

    for path in _g24_LINUX_SURFACE_DIRECTORIES:
        if not path.exists():
            entries.append(f"{path}:missing")
            continue

        if not path.is_dir():
            entries.append(f"{path}:not_directory")
            all_readable = False
            continue

        try:
            sample = [child.name for child in list(path.iterdir())[:5]]
            entries.append(f"{path}:readable:sample=[{','.join(sample)}]")
        except PermissionError:
            entries.append(f"{path}:denied")
            all_readable = False

    return all_readable, ";".join(entries)


def _g24_read_process_namespace_links_with_python() -> str:
    if not _g24_LINUX_PROCESS_NAMESPACE_DIRECTORY.exists():
        raise FileNotFoundError(_g24_LINUX_PROCESS_NAMESPACE_DIRECTORY)

    entries: list[str] = []

    for path in sorted(_g24_LINUX_PROCESS_NAMESPACE_DIRECTORY.iterdir()):
        target = path.readlink()
        entries.append(f"{path.name}:{target}")

    return ",".join(entries)


def _g24_read_service_account_secret_metadata_with_python() -> tuple[Outcome, str]:
    candidates = _g24_collect_service_account_secret_files()

    if not candidates:
        return Outcome.NOT_APPLICABLE, "present=False"

    readable_count = 0
    denied_count = 0
    entries: list[str] = []

    for path in candidates:
        try:
            size = path.stat().st_size
            readable_count += 1
            entries.append(f"{path}:file:size={size}")
        except PermissionError:
            denied_count += 1
            entries.append(f"{path}:file:denied")

    evidence = (
        "present=True; "
        f"readable_count={readable_count}; "
        f"denied_count={denied_count}; "
        f"files=[{';'.join(entries)}]"
    )

    if readable_count > 0:
        return Outcome.ALLOWED, evidence

    return Outcome.DENIED, evidence


def _g24_detect_mount_surfaces_with_python() -> str:
    mounts = _g24_read_linux_mountinfo()
    rw_option_count = 0
    writable_mountpoint_count = 0
    bind_like_mounts: list[dict[str, str]] = []

    for mount in mounts:
        options = mount["options"].split(",")

        if "rw" in options:
            rw_option_count += 1

        if os.access(mount["mount_point"], os.W_OK):
            writable_mountpoint_count += 1

        if _g24_is_bind_like_mount(mount):
            bind_like_mounts.append(mount)

    sample_mounts = bind_like_mounts[:8]

    if not sample_mounts:
        sample_mounts = mounts[:8]

    sample = ",".join(
        (
            f"{mount['mount_point']}:{mount['filesystem_type']}:"
            f"{mount['mount_source']}:{mount['options']}"
        )
        for mount in sample_mounts
    )

    return (
        f"mount_count={len(mounts)}; "
        f"rw_option_count={rw_option_count}; "
        f"writable_mountpoint_count={writable_mountpoint_count}; "
        f"bind_like_count={len(bind_like_mounts)}; "
        f"sample=[{sample}]"
    )


def _g24_read_linux_mountinfo() -> list[dict[str, str]]:
    mounts: list[dict[str, str]] = []

    with _g24_LINUX_MOUNTINFO_PATH.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        for line in file:
            fields = line.strip().split()

            if "-" not in fields:
                continue

            separator_index = fields.index("-")

            if separator_index + 3 > len(fields):
                continue

            mount = {
                "mount_point": _g24_decode_mountinfo_field(fields[4]),
                "options": fields[5],
                "filesystem_type": fields[separator_index + 1],
                "mount_source": _g24_decode_mountinfo_field(
                    fields[separator_index + 2]
                ),
            }
            mounts.append(mount)

    return mounts


def _g24_decode_mountinfo_field(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _g24_is_bind_like_mount(mount: dict[str, str]) -> bool:
    filesystem_type = mount["filesystem_type"]
    mount_source = mount["mount_source"]
    mount_point = mount["mount_point"]
    bind_like_filesystems = {
        "9p",
        "cifs",
        "drvfs",
        "fuse",
        "fuse.vmhgfs-fuse",
        "nfs",
        "overlay",
        "virtiofs",
        "vboxsf",
        "vmhgfs",
    }

    if filesystem_type in bind_like_filesystems:
        return True

    return (
        mount_source.startswith("/")
        and not mount_point.startswith("/proc")
        and not mount_point.startswith("/sys")
        and not mount_point.startswith("/dev")
    )


def _g24_access_container_runtime_sockets_with_python() -> tuple[Outcome, str]:
    candidates = [
        path for path in _g24_linux_container_runtime_socket_paths() if path.exists()
    ]

    if not candidates:
        return Outcome.NOT_APPLICABLE, "present=False"

    connected_count = 0
    denied_count = 0
    entries: list[str] = []

    for path in candidates:
        if not path.is_socket():
            denied_count += 1
            entries.append(f"{path}:not_socket")
            continue

        try:
            unix_socket_family = socket.AF_UNIX  # type: ignore[attr-defined]

            with socket.socket(unix_socket_family, socket.SOCK_STREAM) as client:
                client.settimeout(2)
                client.connect(str(path))

            connected_count += 1
            entries.append(f"{path}:connected")
        except OSError as error:
            denied_count += 1
            entries.append(f"{path}:denied_or_unreachable:{error.__class__.__name__}")

    evidence = (
        "present=True; "
        f"connected_count={connected_count}; "
        f"denied_count={denied_count}; "
        f"sockets=[{';'.join(entries)}]"
    )

    if connected_count > 0:
        return Outcome.ALLOWED, evidence

    return Outcome.DENIED, evidence


def _g24_linux_container_runtime_socket_paths() -> list[Path]:
    paths = list(_g24_LINUX_CONTAINER_RUNTIME_SOCKET_PATHS)
    runtime_directory = os.environ.get("XDG_RUNTIME_DIR")

    if runtime_directory:
        paths.append(Path(runtime_directory) / "podman" / "podman.sock")
    else:
        getuid = os.getuid  # type: ignore[attr-defined]
        paths.append(Path("/run/user") / str(getuid()) / "podman/podman.sock")

    return paths


def _g24_collect_service_account_secret_files() -> list[Path]:
    files: list[Path] = []

    for path in _g24_LINUX_SERVICE_ACCOUNT_PATHS:
        if not path.exists():
            continue

        if path.is_file():
            files.append(path)
            continue

        if path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file())

    return sorted(set(files))


def _g24_failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G10",
        title="Local service and metadata access",
        tests=[
            G10_T01(capability_context),
            G10_T02(capability_context),
            G10_T03(capability_context),
            G10_T04(capability_context),
            G10_T05(capability_context),
            G10_T06(capability_context),
            G10_T07(capability_context),
            G10_T08(capability_context),
            G10_T09(capability_context),
            G10_T10(capability_context),
            G10_T11(capability_context),
            G10_T12(capability_context),
        ],
    )
